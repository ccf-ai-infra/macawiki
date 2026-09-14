#!/usr/bin/env bash
# Macawiki one-command bootstrap installer.
# Usage: curl -sSL <url>/install.sh | bash
# Or:    bash install.sh [install_dir]
set -euo pipefail

REPO_URL="${MACAWIKI_REPO_URL:-https://www.gitlink.org.cn/ccf-ai-infra/macawiki.git}"
INSTALL_DIR="${1:-$HOME/macawiki}"
BRANCH="${MACAWIKI_BRANCH:-master}"

echo "=== Macawiki installer ==="
echo "Install dir: $INSTALL_DIR"
echo ""

# Prerequisite checks
for cmd in git python3; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: $cmd is required but not found. Please install it first."
        exit 1
    fi
done

PYVER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' 2>/dev/null; then
    echo "ERROR: Python >= 3.9 required, found $PYVER"
    exit 1
fi
echo "  Python: $PYVER"

# Clone or update
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "==> Repository exists, updating..."
    git -C "$INSTALL_DIR" fetch origin "$BRANCH"
    git -C "$INSTALL_DIR" checkout "$BRANCH"
    git -C "$INSTALL_DIR" pull origin "$BRANCH" 2>/dev/null || true
else
    echo "==> Cloning macawiki to $INSTALL_DIR..."
    git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# Run health checks
echo ""
echo "==> Running doctor check..."
python3 scripts/doctor.py

echo ""
echo "==> Running full validation (make all)..."
make all

# Detect and install agent skills
echo ""
echo "==> Agent skill setup"

detect_agent() {
    # CodeBuddy Code
    if command -v codebuddy &>/dev/null || [ -d "$HOME/.codebuddy" ]; then
        echo "codebuddy"
        return
    fi
    # Claude Code
    if command -v claude &>/dev/null || [ -d "$HOME/.claude" ]; then
        echo "claude"
        return
    fi
    # Codex
    if [ -d "$HOME/.agents" ] || [ -d "$HOME/.codex" ]; then
        echo "codex"
        return
    fi
    # OpenCode
    if command -v opencode &>/dev/null || [ -d "$HOME/.opencode" ]; then
        echo "opencode"
        return
    fi
    echo ""
}

AGENT=$(detect_agent)

if [ -n "$AGENT" ]; then
    echo "  Detected agent: $AGENT (installing for all supported agents)"
    # Install for every supported agent: a skill installed only into another
    # agent's directory is invisible to the running agent (see evals/porting-ab).
    INSTALL_FLAGS="--agent both --mode symlink"
    if [ "$INSTALL_DIR" != "$(pwd)" ]; then
        echo "  (Installing from $INSTALL_DIR)"
    fi
    python3 scripts/install.py $INSTALL_FLAGS --scope user --replace || echo "  Skill install skipped (run manually if needed): python3 scripts/install.py --agent both --mode symlink --replace"
else
    echo "  No Claude Code/Codex/OpenCode detected."
    echo "  To install manually:"
    echo "    python3 scripts/install.py --agent claude --mode symlink"
    echo "    python3 scripts/install.py --agent codex --mode symlink"
fi

# Final summary
echo ""
echo "=== Macawiki installed ==="
echo ""
echo "Quick start:"
echo "  cd $INSTALL_DIR"
echo "  python3 scripts/query.py \"算子\" --compact"
echo "  python3 scripts/get_page.py pattern-establish-performance-baseline --follow-sources"
echo ""
if [ -n "$AGENT" ]; then
    echo "In your agent:"
    echo "  CodeBuddy Code: skill auto-triggers (~/.codebuddy/skills/macawiki)"
    echo "  Claude Code:    /macawiki <question>"
    echo "  Codex:          \$macawiki <question>"
    echo ""
fi
echo "Run the tutorial: python3 scripts/tutorial.py"
echo "Docs: $INSTALL_DIR/docs/"
echo ""
