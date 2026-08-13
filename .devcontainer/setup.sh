#!/bin/bash
set -e

# Install dev dependencies
pip install -e '.[dev]' 2>/dev/null || true

# Install Claude Code via native installer (lclaude prefers this over npm)
curl -fsSL https://claude.ai/install.sh | bash || npm install -g @anthropic-ai/claude-code

# Set up Claude auth from host config (mounted read-only at ~/.claude-host)
if [ -d /home/vscode/.claude-host ]; then
    mkdir -p /home/vscode/.claude

    # Copy settings, patching home directory paths
    if [ -f /home/vscode/.claude-host/settings.json ]; then
        sed 's|/home/claude-bouchard|/home/vscode|g' \
            /home/vscode/.claude-host/settings.json > /home/vscode/.claude/settings.json
    fi

    # Copy any other config files (credentials, etc.)
    for f in /home/vscode/.claude-host/*; do
        fname=$(basename "$f")
        [ "$fname" = "settings.json" ] && continue
        [ "$fname" = "claude-api-key-helper" ] && continue
        [ -f "$f" ] && cp "$f" /home/vscode/.claude/"$fname" 2>/dev/null || true
    done

    # Point api-key-helper to lclaude (handles API key via ai-proxy)
    ln -sf /home/vscode/.local/bin/lclaude /home/vscode/.claude/claude-api-key-helper
fi

# Verify
echo "=== Dev Environment ==="
ansible --version | head -1
python --version
claude --version 2>/dev/null || echo "claude: installed (run 'claude' or 'lclaude' to start)"
echo "Dev environment ready."
