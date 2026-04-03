#!/usr/bin/env bash
set -euo pipefail

echo "▶ sba: user=$(whoami) claude=$(which claude 2>/dev/null || echo 'NOT FOUND')"

if [ -n "${GITHUB_TOKEN:-}" ]; then
  git config --global url."https://${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"
fi

if [ -z "${REPO:-}" ]; then
  echo "Error: REPO is required in env file (e.g. REPO=owner/repo)"
  exit 1
fi

git clone "https://github.com/$REPO.git" /workspace/repo
cd /workspace/repo

if [ -n "${BRANCH:-}" ]; then
  git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH"
fi

case "${AGENT:-claude}" in
  claude)
    linear_prompt=""
    if [ -n "${LINEAR_API_KEY:-}" ]; then
      linear_prompt="Task identifiers like HDW-20 or ENG-123 are Linear issue identifiers. Use your Linear MCP tools to fetch issue details before starting work."
    fi

    if [ -n "${TASK:-}" ]; then
      if [ "${INTERACTIVE:-}" = "1" ]; then
        exec claude --dangerously-skip-permissions ${linear_prompt:+--append-system-prompt "$linear_prompt"} "$TASK"
      else
        echo "▶ sba: running claude -p '$TASK'..." >&2
        # Build command with proper quoting for script -c
        cmd=(claude --dangerously-skip-permissions -p)
        [ -n "$linear_prompt" ] && cmd+=(--append-system-prompt "$linear_prompt")
        cmd+=("$TASK")
        exec script -qfc "$(printf '%q ' "${cmd[@]}")" /dev/null
      fi
    else
      exec claude --dangerously-skip-permissions
    fi
    ;;
  codex)
    if [ -n "${TASK:-}" ]; then
      exec codex "$TASK"
    else
      exec codex
    fi
    ;;
  gemini)
    if [ -n "${TASK:-}" ]; then
      exec gemini "$TASK"
    else
      exec gemini
    fi
    ;;
  *)
    echo "Error: Unknown agent '$AGENT'. Supported: claude, codex, gemini"
    exit 1
    ;;
esac
