#!/usr/bin/env bash
set -euo pipefail

# Open every file changed on the current branch (vs main/master, plus
# uncommitted) in a NEW VS Code window. Per file: a `--diff` tab (old left,
# working tree right; right side is editable) and a plain live-file tab.

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
  echo "Not in a git repo." >&2
  exit 1
}
cd "$REPO_ROOT"

if ! command -v code >/dev/null 2>&1; then
  echo "VS Code 'code' CLI not on PATH." >&2
  echo "Install: VS Code → Cmd+Shift+P → 'Shell Command: Install code command in PATH'." >&2
  exit 1
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [[ "$BRANCH" == "main" || "$BRANCH" == "master" ]]; then
  BASE="HEAD"
  SCOPE="uncommitted vs HEAD (on $BRANCH)"
else
  if git rev-parse --verify --quiet main >/dev/null; then
    DEFAULT=main
  elif git rev-parse --verify --quiet master >/dev/null; then
    DEFAULT=master
  else
    echo "No 'main' or 'master' branch found locally." >&2
    exit 1
  fi
  if ! BASE=$(git merge-base "$DEFAULT" HEAD 2>/dev/null); then
    echo "No merge base between $DEFAULT and HEAD." >&2
    exit 1
  fi
  SCOPE="vs $DEFAULT (merge-base $(git rev-parse --short "$BASE"))"
fi

ALL_FILES=()
while IFS= read -r line; do
  [[ -n "$line" ]] && ALL_FILES+=("$line")
done < <(git diff --name-only "$BASE" --)

UNTRACKED_FILES=()
while IFS= read -r line; do
  [[ -n "$line" ]] && UNTRACKED_FILES+=("$line")
done < <(git ls-files --others --exclude-standard)

for u in "${UNTRACKED_FILES[@]:-}"; do
  [[ -z "${u:-}" ]] && continue
  ALL_FILES+=("$u")
done

if [[ ${#ALL_FILES[@]} -eq 0 ]]; then
  echo "No changes $SCOPE."
  exit 0
fi

BINARY_FILES=()
while IFS=$'\t' read -r added removed file; do
  if [[ "$added" == "-" && "$removed" == "-" ]]; then
    BINARY_FILES+=("$file")
  fi
done < <(git diff --numstat "$BASE" --)

TEXT_FILES=()
DELETED_FILES=()
for f in "${ALL_FILES[@]}"; do
  is_binary=0
  if [[ ${#BINARY_FILES[@]} -gt 0 ]]; then
    for b in "${BINARY_FILES[@]}"; do
      if [[ "$f" == "$b" ]]; then is_binary=1; break; fi
    done
  fi
  if [[ $is_binary -eq 1 ]]; then continue; fi
  if [[ ! -e "$f" ]]; then
    DELETED_FILES+=("$f")
    continue
  fi
  TEXT_FILES+=("$f")
done

if [[ ${#TEXT_FILES[@]} -eq 0 ]]; then
  echo "Nothing reviewable $SCOPE."
  [[ ${#BINARY_FILES[@]} -gt 0 ]] && echo "  Binary (skipped): ${BINARY_FILES[*]}"
  [[ ${#DELETED_FILES[@]} -gt 0 ]] && echo "  Deleted (not opened): ${DELETED_FILES[*]}"
  exit 0
fi

SHORT_BASE=$(git rev-parse --short "$BASE")
SAFE_BRANCH=$(printf '%s' "$BRANCH" | tr '/ ' '--')
TMP_ROOT="${TMPDIR:-/tmp}"
TMP_ROOT="${TMP_ROOT%/}"
SNAPSHOT_DIR="$TMP_ROOT/vscode-review-${SAFE_BRANCH}-${SHORT_BASE}"
rm -rf "$SNAPSHOT_DIR"
mkdir -p "$SNAPSHOT_DIR"

for f in "${TEXT_FILES[@]}"; do
  old_path="$SNAPSHOT_DIR/$f"
  mkdir -p "$(dirname "$old_path")"
  if git cat-file -e "$BASE:$f" 2>/dev/null; then
    git show "$BASE:$f" > "$old_path"
  else
    : > "$old_path"
  fi
done

echo "Opening ${#TEXT_FILES[@]} file(s) for review ($SCOPE)..."

first=1
for f in "${TEXT_FILES[@]}"; do
  if [[ $first -eq 1 ]]; then
    code -n --diff "$SNAPSHOT_DIR/$f" "$f"
    first=0
  else
    code -r --diff "$SNAPSHOT_DIR/$f" "$f"
  fi
done

code -r "${TEXT_FILES[@]}"

echo ""
echo "Review summary:"
echo "  Branch:    $BRANCH"
echo "  Scope:     $SCOPE"
echo "  Diffs:     ${#TEXT_FILES[@]} file(s) — diff tab + live tab each"
if [[ ${#BINARY_FILES[@]} -gt 0 ]]; then
  echo "  Binary:    ${#BINARY_FILES[@]} skipped — ${BINARY_FILES[*]}"
fi
if [[ ${#DELETED_FILES[@]} -gt 0 ]]; then
  echo "  Deleted:   ${#DELETED_FILES[@]} not opened — ${DELETED_FILES[*]}"
fi
echo "  Snapshot:  $SNAPSHOT_DIR"
