#!/usr/bin/env bash
# Bootstrap GitHub Issues labels + Projects v2 board for Grid Pulse.
# Usage: scripts/github/bootstrap-project.sh
# Env overrides: GH_OWNER, GH_REPO, PROJECT_TITLE
set -euo pipefail

OWNER="${GH_OWNER:-ahmedmsabry2000}"
REPO="${GH_REPO:-grid-pulse}"
PROJECT_TITLE="${PROJECT_TITLE:-Grid Pulse}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing required command: $1" >&2; exit 1; }; }
need gh
need jq

if ! gh auth status -h github.com >/dev/null 2>&1; then
  echo "gh is not authenticated. Run: gh auth login" >&2
  exit 1
fi

echo "==> Ensuring repo labels on ${OWNER}/${REPO}"
ensure_label() {
  local name="$1" color="$2" desc="$3"
  if gh label list --repo "${OWNER}/${REPO}" --json name --jq '.[].name' | grep -Fxq "$name"; then
    echo "  label exists: $name"
  else
    gh label create "$name" --repo "${OWNER}/${REPO}" --color "$color" --description "$desc" >/dev/null
    echo "  created label: $name"
  fi
}

ensure_label "effort:S" "0E8A16" "Small effort"
ensure_label "effort:M" "FBCA04" "Medium effort"
ensure_label "effort:L" "D93F0B" "Large effort"
ensure_label "type:feature" "1D76DB" "Feature work"
ensure_label "type:fix" "5319E7" "Bug fix"

echo "==> Resolving owner node id"
OWNER_ID="$(gh api graphql -f query='
  query($login: String!) {
    user(login: $login) { id }
  }' -f login="$OWNER" --jq '.data.user.id')"
if [[ -z "$OWNER_ID" || "$OWNER_ID" == "null" ]]; then
  echo "could not resolve user id for ${OWNER}" >&2
  exit 1
fi

echo "==> Finding or creating project '${PROJECT_TITLE}'"
PROJECT_JSON="$(gh api graphql -f query='
  query($login: String!, $title: String!) {
    user(login: $login) {
      projectsV2(first: 50, query: $title) {
        nodes { id title number url }
      }
    }
  }' -f login="$OWNER" -f title="$PROJECT_TITLE")"

PROJECT_ID="$(echo "$PROJECT_JSON" | jq -r --arg t "$PROJECT_TITLE" '
  [.data.user.projectsV2.nodes[] | select(.title == $t) | .id] | first // empty')"

if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "null" ]]; then
  CREATE_JSON="$(gh api graphql -f query='
    mutation($ownerId: ID!, $title: String!) {
      createProjectV2(input: {ownerId: $ownerId, title: $title}) {
        projectV2 { id title number url }
      }
    }' -f ownerId="$OWNER_ID" -f title="$PROJECT_TITLE")"
  PROJECT_ID="$(echo "$CREATE_JSON" | jq -r '.data.createProjectV2.projectV2.id')"
  PROJECT_URL="$(echo "$CREATE_JSON" | jq -r '.data.createProjectV2.projectV2.url')"
  PROJECT_NUMBER="$(echo "$CREATE_JSON" | jq -r '.data.createProjectV2.projectV2.number')"
  echo "  created project #${PROJECT_NUMBER}: ${PROJECT_URL}"
else
  PROJECT_URL="$(echo "$PROJECT_JSON" | jq -r --arg id "$PROJECT_ID" '
    .data.user.projectsV2.nodes[] | select(.id == $id) | .url')"
  PROJECT_NUMBER="$(echo "$PROJECT_JSON" | jq -r --arg id "$PROJECT_ID" '
    .data.user.projectsV2.nodes[] | select(.id == $id) | .number')"
  echo "  project exists #${PROJECT_NUMBER}: ${PROJECT_URL}"
fi

echo "==> Linking repo ${OWNER}/${REPO} to project"
REPO_ID="$(gh api graphql -f query='
  query($owner: String!, $name: String!) {
    repository(owner: $owner, name: $name) { id }
  }' -f owner="$OWNER" -f name="$REPO" --jq '.data.repository.id')"

gh api graphql -f query='
  mutation($projectId: ID!, $repositoryId: ID!) {
    linkProjectV2ToRepository(input: {projectId: $projectId, repositoryId: $repositoryId}) {
      repository { nameWithOwner }
    }
  }' -f projectId="$PROJECT_ID" -f repositoryId="$REPO_ID" >/dev/null || true

field_id_by_name() {
  local name="$1"
  gh api graphql -f query='
    query($id: ID!) {
      node(id: $id) {
        ... on ProjectV2 {
          fields(first: 50) {
            nodes {
              ... on ProjectV2Field { id name }
              ... on ProjectV2SingleSelectField { id name }
              ... on ProjectV2IterationField { id name }
            }
          }
        }
      }
    }' -f id="$PROJECT_ID" \
    | jq -r --arg n "$name" '.data.node.fields.nodes[] | select(.name == $n) | .id' \
    | head -n1
}

ensure_single_select() {
  local field_name="$1"
  shift
  local -a options=("$@")
  local existing
  existing="$(field_id_by_name "$field_name")"
  if [[ -n "$existing" && "$existing" != "null" ]]; then
    echo "  field exists: ${field_name} (${existing})"
    return 0
  fi

  # Projects v2 requires name + color + description for each single-select option.
  local opts_json
  opts_json="$(printf '%s\n' "${options[@]}" | jq -R . | jq -s '
    map({
      name: .,
      color: (if . == "S" or . == "Todo" then "GREEN"
              elif . == "M" or . == "In Progress" then "YELLOW"
              elif . == "L" or . == "Done" then "RED"
              else "GRAY" end),
      description: ""
    })')"
  local mutation
  mutation="$(jq -n \
    --arg projectId "$PROJECT_ID" \
    --arg name "$field_name" \
    --argjson options "$opts_json" \
    '{
      query: "mutation($input: CreateProjectV2FieldInput!) { createProjectV2Field(input: $input) { projectV2Field { ... on ProjectV2SingleSelectField { id name } } } }",
      variables: {
        input: {
          projectId: $projectId,
          dataType: "SINGLE_SELECT",
          name: $name,
          singleSelectOptions: $options
        }
      }
    }')"
  local created
  created="$(echo "$mutation" | gh api graphql --input -)"
  local new_id
  new_id="$(echo "$created" | jq -r '.data.createProjectV2Field.projectV2Field.id')"
  echo "  created field: ${field_name} (${new_id})"
}

echo "==> Ensuring Status field (Todo / In Progress / Done)"
# New projects often ship with a Status field already; create only if missing.
STATUS_ID="$(field_id_by_name "Status")"
if [[ -z "$STATUS_ID" || "$STATUS_ID" == "null" ]]; then
  ensure_single_select "Status" "Todo" "In Progress" "Done"
else
  echo "  field exists: Status (${STATUS_ID})"
  # Ensure required options exist by reading current options; add missing via update if needed.
  CURRENT_OPTS="$(gh api graphql -f query='
    query($id: ID!) {
      node(id: $id) {
        ... on ProjectV2 {
          field(name: "Status") {
            ... on ProjectV2SingleSelectField {
              id
              options { id name }
            }
          }
        }
      }
    }' -f id="$PROJECT_ID")"
  for opt in "Todo" "In Progress" "Done"; do
    if ! echo "$CURRENT_OPTS" | jq -e --arg o "$opt" '
      [.data.node.field.options[].name] | index($o) != null' >/dev/null; then
      echo "  warning: Status option '${opt}' missing — add it in the Project UI if workflows fail" >&2
    else
      echo "  Status option ok: ${opt}"
    fi
  done
fi

echo "==> Ensuring Effort field (S / M / L)"
ensure_single_select "Effort" "S" "M" "L"

# Persist ids for sibling scripts (optional local cache; gitignored-friendly path under scripts).
CACHE_DIR="$(cd "$(dirname "$0")" && pwd)/.cache"
mkdir -p "$CACHE_DIR"
{
  printf 'GH_OWNER=%q\n' "$OWNER"
  printf 'GH_REPO=%q\n' "$REPO"
  printf 'PROJECT_TITLE=%q\n' "$PROJECT_TITLE"
  printf 'PROJECT_ID=%q\n' "$PROJECT_ID"
  printf 'PROJECT_NUMBER=%q\n' "$PROJECT_NUMBER"
  printf 'PROJECT_URL=%q\n' "$PROJECT_URL"
} >"${CACHE_DIR}/project.env"

echo
echo "Bootstrap complete."
echo "  Project: ${PROJECT_URL}"
echo "  Project id: ${PROJECT_ID}"
echo "  Cache: ${CACHE_DIR}/project.env"
