#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${1:-$HOME/setup_scripts}"

link_skills() {
  local agent_home="$1"
  local skills_dir="$agent_home/skills"
  mkdir -p "$skills_dir"

  for skill in "$REPO_DIR"/skills/*/; do
    ln -sfn "$skill" "$skills_dir/$(basename "$skill")"
  done
}

mkdir -p "$HOME/.claude" "$HOME/.codex"
link_skills "$HOME/.claude"
link_skills "$HOME/.codex"

ln -sfn "$REPO_DIR/defaults/settings.json" "$HOME/.claude/settings.json"
ln -sfn "$REPO_DIR/defaults/codex-config.toml" "$HOME/.codex/config.toml"
