#!/usr/bin/env bash
# Prepare a Macawiki PR branch with validation.
# Usage: bash scripts/prepare_pr.sh <type> "<description>"
#   type: feat, fix, docs, refactor, test, chore
# Example: bash scripts/prepare_pr.sh docs "add fuzzy search to query engine"
set -euo pipefail

PR_TYPE="${1:-}"
PR_DESC="${2:-}"
BRANCH="pr-${PR_TYPE}-$(echo "${PR_DESC}" | tr ' ' '-' | tr -cd '[:alnum:]-' | head -c40)"
BRANCH="$(echo "$BRANCH" | sed 's/--*/-/g')"

if [ -z "$PR_TYPE" ] || [ -z "$PR_DESC" ]; then
    echo "Usage: bash scripts/prepare_pr.sh <type> \"<description>\""
    echo "  type: feat, fix, docs, refactor, test, chore"
    exit 1
fi

echo "=== Macawiki PR preparation ==="
echo "Type: $PR_TYPE"
echo "Description: $PR_DESC"
echo "Branch: $BRANCH"
echo ""

# Ensure working directory is clean
if ! git diff-index --quiet HEAD --; then
    echo "Working tree has uncommitted changes."
    echo "Commit or stash them before running this script."
    exit 1
fi

# Run baseline validation
echo "==> Running baseline validation..."
make all || {
    echo "ERROR: make all failed on baseline. Fix existing issues first."
    exit 1
}

# Create branch
echo ""
echo "==> Creating branch: $BRANCH"
git checkout -b "$BRANCH"

# Summary
echo ""
echo "=== Branch '$BRANCH' ready ==="
echo ""
echo "Next steps:"
echo "  1. Make your changes"
echo "  2. Run: make all"
echo "  3. Run: git add <files>"
echo "  4. Commit: git commit -m '$PR_TYPE: $PR_DESC'"
echo "  5. Push:   git push origin $BRANCH"
echo "  6. Create PR with body:"
echo "     Change summary: ..."
echo "     Verification: make all output"
echo "     Unresolved issues: ..."
echo ""
echo "PR title format: $PR_TYPE: $PR_DESC"
