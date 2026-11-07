#!/usr/bin/env bash
# Set Projects v2 Status for an issue on the Grid Pulse board.
# Usage: scripts/github/project-set-status.sh <issue-number> <Todo|In Progress|Done>
set -euo pipefail

ISSUE_NUMBER="${1:-}"
STATUS="${2:-}"

if [[ -z "$ISSUE_NUMBER" || -z "$STATUS" ]]; then
  echo "usage: $0 <issue-number> <Todo|In Progress|Done>" >&2
  exit 1
fi

case "$STATUS" in
  Todo|"In Progress"|Done) ;;
  *)
    echo "status must be one of: Todo | In Progress | Done" >&2
    exit 1
    ;;
esac

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
      issue(number: $number) { id title url }
    }
  }' -f owner="$OWNER" -f name="$REPO" -F number="$ISSUE_NUMBER")"

CONTENT_ID="$(echo "$ISSUE_NODE_ID" | jq -r '.data.repository.issue.id')"
ISSUE_URL="$(echo "$ISSUE_NODE_ID" | jq -r '.data.repository.issue.url')"
if [[ -z "$CONTENT_ID" || "$CONTENT_ID" == "null" ]]; then
  echo "issue #${ISSUE_NUMBER} not found on ${OWNER}/${REPO}" >&2
  exit 1
fi

# Find project item for this issue (or add it).
ITEM_ID="$(gh api graphql -f query='
  query($projectId: ID!) {
    node(id: $projectId) {
      ... on ProjectV2 {
        items(first: 100) {
          nodes {
            id
            content {
              ... on Issue { id }
            }
          }
        }
      }
    }
  }' -f projectId="$PROJECT_ID" \
  | jq -r --arg cid "$CONTENT_ID" '
    .data.node.items.nodes[] | select(.content.id == $cid) | .id' \
  | head -n1)"

if [[ -z "$ITEM_ID" || "$ITEM_ID" == "null" ]]; then
  echo "==> Issue not on project yet; adding"
  ITEM_ID="$(gh api graphql -f query='
    mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
        item { id }
      }
    }' -f projectId="$PROJECT_ID" -f contentId="$CONTENT_ID" \
    --jq '.data.addProjectV2ItemById.item.id')"
fi

STATUS_META="$(gh api graphql -f query='
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

STATUS_FIELD_ID="$(echo "$STATUS_META" | jq -r '.data.node.field.id')"
OPTION_ID="$(echo "$STATUS_META" | jq -r --arg s "$STATUS" '
  .data.node.field.options[] | select(.name == $s) | .id' | head -n1)"

if [[ -z "$STATUS_FIELD_ID" || "$STATUS_FIELD_ID" == "null" || -z "$OPTION_ID" || "$OPTION_ID" == "null" ]]; then
  echo "could not resolve Status option '${STATUS}' on project" >&2
  exit 1
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
    -f fieldId="$STATUS_FIELD_ID" -f optionId="$OPTION_ID" >/dev/null

echo "Set Status='${STATUS}' for ${ISSUE_URL} (item ${ITEM_ID})"
