#!/bin/bash
# =============================================================================
# Dev Container Initialization Script
# =============================================================================
# Runs on every container start. Installs dependencies
# =============================================================================

set -e

uv sync --all-packages --reinstall

# Activate the virtual environment for interactive shells
ACTIVATE_LINE='source /workspaces/halo/.venv/bin/activate'
for RC_FILE in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$RC_FILE" ] && ! grep -qF "$ACTIVATE_LINE" "$RC_FILE"; then
        echo "$ACTIVATE_LINE" >> "$RC_FILE"
    fi
done

echo "✅ Dev container ready!"