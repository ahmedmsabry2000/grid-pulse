#!/usr/bin/env bash
# Create a GitHub Issue from a Spec markdown file, label it, add to Project, set Effort + Status=Todo.
# Usage: scripts/github/new-issue-from-spec.sh path/to/spec.md
# Spec frontmatter (YAML between ---) should include:
#   title: string
#   effort: S|M|L
#   type: feature|fix
# Body after frontmatter becomes the issue body.
set -euo pipefail

SPEC_PATH="${1:-}"
if [[ -z "$SPEC_PATH" || ! -f "$SPEC_PATH" ]]; then
  echo "usage: $0 path/to/spec.md" >&2
  exit 1
fi

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

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CACHE_FILE="${SCRIPT_DIR}/.cache/project.env"
if [[ -f "$CACHE_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CACHE_FILE"
fi

# Parse simple YAML frontmatter without requiring python.
FRONTMATTER="$(awk '
  BEGIN { in_fm=0 }
  NR==1 && $0=="---" { in_fm=1; next }
  in_fm && $0=="---" { exit }
  in_fm { print }
' "$SPEC_PATH")"

BODY="$(awk '
  BEGIN { in_fm=0; seen=0 }
  NR==1 && $0=="---" { in_fm=1; next }
  in_fm && $0=="---" { in_fm=0; seen=1; next }
  seen { print }
' "$SPEC_PATH")"

fm_get() {
  local key="$1"
  echo "$FRONTMATTER" | awk -F': *' -v k="$key" '
    $1 == k {
      sub(/^[^:]+:[[:space:]]*/, "")
      gsub(/^["'\''"]|["'\'']$/, "")
      print
      exit
    }'
}

TITLE="$(fm_get title)"
EFFORT="$(fm_get effort | tr '[:lower:]' '[:upper:]')"
TYPE="$(fm_get type | tr '[:upper:]' '[:lower:]')"

if [[ -z "$TITLE" ]]; then
  # Fallback: first markdown H1
  TITLE="$(grep -m1 -E '^# ' "$SPEC_PATH" | sed 's/^# //')"
fi
if [[ -z "$TITLE" ]]; then
  echo "spec missing title (frontmatter title: or leading # heading)" >&2
  exit 1
fi

case "$EFFORT" in
  S|M|L) ;;
  *) echo "spec effort must be S, M, or L (got: '${EFFORT}')" >&2; exit 1 ;;
esac
case "$TYPE" in
  feature|fix) ;;
  *) echo "spec type must be feature or fix (got: '${TYPE}')" >&2; exit 1 ;;
esac

EFFORT_LABEL="effort:${EFFORT}"
TYPE_LABEL="type:${TYPE}"

echo "==> Creating issue on ${OWNER}/${REPO}"
ISSUE_URL="$(gh issue create \
  --repo "${OWNER}/${REPO}" \
  --title "$TITLE" \
  --body "$BODY" \
  --label "$EFFORT_LABEL" \
  --label "$TYPE_LABEL")"
ISSUE_NUMBER="$(basename "$ISSUE_URL")"
echo "  issue: ${ISSUE_URL}"

# Resolve project if cache missing
if [[ -z "${PROJECT_ID:-}" ]]; then
  PROJECT_ID="$(gh api graphql -f query='
    query($login: String!, $title: String!) {
      user(login: $login) {
        projectsV2(first: 50, query: $title) {
          nodes { id title }
        }
      }
    }' -f login="$OWNER" -f title="$PROJECT_TITLE" \
    | jq -r --arg t "$PROJECT_TITLE" '.data.user.projectsV2.nodes[] | select(.title == $t) | .id' \
    | head -n1)"
fi
if [[ -z "${PROJECT_ID:-}" || "$PROJECT_ID" == "null" ]]; then
  echo "project '${PROJECT_TITLE}' not found. Run scripts/github/bootstrap-project.sh first." >&2
  exit 1
fi

ISSUE_NODE_ID="$(gh api graphql -f query='
  query($owner: String!, $name: String!, $number: Int!) {
    repository(owner: $owner, name: $name) {
      issue(number: $number) { id }
    }
  }' -f owner="$OWNER" -f name="$REPO" -F number="$ISSUE_NUMBER" --jq '.data.repository.issue.id')"

echo "==> Adding issue #${ISSUE_NUMBER} to project"
ITEM_ID="$(gh api graphql -f query='
  mutation($projectId: ID!, $contentId: ID!) {
    addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
      item { id }
    }
  }' -f projectId="$PROJECT_ID" -f contentId="$ISSUE_NODE_ID" \
  --jq '.data.addProjectV2ItemById.item.id')"
echo "  project item: ${ITEM_ID}"

# Resolve Effort + Status field/option ids
FIELDS_JSON="$(gh api graphql -f query='
  query($id: ID!) {
    node(id: $id) {
      ... on ProjectV2 {
        fields(first: 50) {
          nodes {
            ... on ProjectV2SingleSelectField {
              id
              name
              options { id name }
            }
          }
        }
      }
    }
  }' -f id="$PROJECT_ID")"

option_id() {
  local field="$1" option="$2"
  echo "$FIELDS_JSON" | jq -r --arg f "$field" --arg o "$option" '
    .data.node.fields.nodes[]
    | select(.name == $f)
    | .options[]
    | select(.name == $o)
    | .id' | head -n1
}

field_id() {
  local field="$1"
  echo "$FIELDS_JSON" | jq -r --arg f "$field" '
    .data.node.fields.nodes[] | select(.name == $f) | .id' | head -n1
}

EFFORT_FIELD_ID="$(field_id "Effort")"
EFFORT_OPTION_ID="$(option_id "Effort" "$EFFORT")"
STATUS_FIELD_ID="$(field_id "Status")"
TODO_OPTION_ID="$(option_id "Status" "Todo")"

set_select() {
  local field_id="$1" option_id="$2" label="$3"
  if [[ -z "$field_id" || "$field_id" == "null" || -z "$option_id" || "$option_id" == "null" ]]; then
    echo "  skip ${label}: field/option not found" >&2
    return 0
  fi
  gh api graphql -f query='
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId
        itemId: $itemId
        fieldId: $fieldId
        value: { singleSelectOptionId: $optionId }
      }) {
        projectV2Item { id }
      }
    }' -f projectId="$PROJECT_ID" -f itemId="$ITEM_ID" \
      -f fieldId="$field_id" -f optionId="$option_id" >/dev/null
  echo "  set ${label}"
}

echo "==> Setting Effort=${EFFORT} and Status=Todo"
set_select "$EFFORT_FIELD_ID" "$EFFORT_OPTION_ID" "Effort=${EFFORT}"
set_select "$STATUS_FIELD_ID" "$TODO_OPTION_ID" "Status=Todo"

echo
echo "Done."
echo "  Issue: ${ISSUE_URL}"
echo "  Project item id: ${ITEM_ID}"
echo "ISSUE_URL=${ISSUE_URL}"
echo "ISSUE_NUMBER=${ISSUE_NUMBER}"
echo "ITEM_ID=${ITEM_ID}"
