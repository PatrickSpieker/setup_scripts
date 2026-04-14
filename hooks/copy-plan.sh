#!/bin/bash
# Copy the most recently finalized plan into the current repo's plans/ directory.
# Invoked as a Claude Code PostToolUse hook on ExitPlanMode.
# Only fires on approval (PostToolUse), not on rejection (PostToolUseFailure).

PLAN_FILE=$(ls -t ~/.claude/plans/*.md 2>/dev/null | head -1)

if [ -z "$PLAN_FILE" ]; then
  echo "No plan file found" >&2
  exit 0
fi

mkdir -p "$PWD/plans"

DATE=$(date +%Y-%m-%d)
BASENAME=$(basename "$PLAN_FILE")

# Remove any older dated copies of this plan (handles cross-day re-approvals)
find "$PWD/plans" -name "*_${BASENAME}" -not -name "${DATE}_${BASENAME}" -delete 2>/dev/null

DEST="$PWD/plans/${DATE}_${BASENAME}"
cp "$PLAN_FILE" "$DEST"
echo "Plan saved to plans/${DATE}_${BASENAME}" >&2
