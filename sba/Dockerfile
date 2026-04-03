FROM node:20

RUN apt-get update && apt-get install -y git curl \
  && corepack enable \
  && corepack prepare pnpm@latest --activate \
  && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash coder

RUN mkdir -p /workspace
COPY .mcp.json /workspace/.mcp.json
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
RUN chown -R coder:coder /workspace

USER coder

ENV PNPM_HOME="/home/coder/.local/share/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN mkdir -p "$PNPM_HOME"

RUN pnpm add -g \
    @anthropic-ai/claude-code \
    @openai/codex \
    @google/gemini-cli

RUN CLAUDE_VERSION=$(claude --version 2>/dev/null | head -1) && \
    echo "{\"hasCompletedOnboarding\": true, \"theme\": \"dark\", \"lastOnboardingVersion\": \"$CLAUDE_VERSION\"}" > /home/coder/.claude.json

WORKDIR /workspace

ENTRYPOINT ["/entrypoint.sh"]
