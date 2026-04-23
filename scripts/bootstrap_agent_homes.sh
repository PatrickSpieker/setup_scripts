#!/usr/bin/env bash
set -euo pipefail

# Usage: bootstrap_agent_homes.sh <repo-dir> [--moat]
#
# Links skills and Claude settings into $HOME/.claude and $HOME/.codex.
# Pass --moat when running inside a Moat container so the container-specific
# settings file (defaults/settings-moat.json) is linked instead of the host
# file. The container file differs only in the Playwright MCP args (headless,
# no-sandbox).

MOAT_MODE=false
POSITIONAL=()
for arg in "$@"; do
  case "$arg" in
    --moat) MOAT_MODE=true ;;
    *) POSITIONAL+=("$arg") ;;
  esac
done

REPO_DIR="${POSITIONAL[0]:-$HOME/setup_scripts}"

SETTINGS_FILE="settings.json"
if $MOAT_MODE; then
  SETTINGS_FILE="settings-moat.json"
fi

link_skills() {
  local agent_home="$1"
  local skills_dir="$agent_home/skills"

  if [[ -L "$skills_dir" ]]; then
    rm "$skills_dir"
  fi

  mkdir -p "$skills_dir"

  for skill in "$REPO_DIR"/skills/*/; do
    [[ -d "$skill" ]] || continue
    ln -sfn "$skill" "$skills_dir/$(basename "$skill")"
  done
}

mkdir -p "$HOME/.claude" "$HOME/.codex"
link_skills "$HOME/.claude"
link_skills "$HOME/.codex"

ln -sfn "$REPO_DIR/defaults/$SETTINGS_FILE" "$HOME/.claude/settings.json"
ln -sfn "$REPO_DIR/AGENTS.md" "$HOME/.claude/CLAUDE.md"
