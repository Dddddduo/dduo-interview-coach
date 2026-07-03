#!/bin/bash
# ======================================================
# Interview Coach — Git Auto-Push Script
# Pushes generated interview docs to GitHub automatically
# ======================================================

set -e

PROJECT_DIR="$HOME/Documents/projects/interview-coach"
OUTPUTS_DIR="$PROJECT_DIR/outputs"
BRANCH="main"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}[Interview Coach]${NC} Auto-push script started..."

# Check project directory
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}[ERROR]${NC} Project directory not found: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# Check if there are changes to commit
if git diff --quiet && git diff --staged --quiet && [ -z "$(git ls-files --others --exclude-standard outputs/)" ]; then
    echo -e "${YELLOW}[SKIP]${NC} No changes to push."
    exit 0
fi

# Check if remote is configured
if ! git remote get-url origin &>/dev/null; then
    echo -e "${RED}[ERROR]${NC} No git remote 'origin' configured."
    echo "  Run: git remote add origin <your-repo-url>"
    exit 1
fi

# Stage and commit
echo -e "${GREEN}[INFO]${NC} Staging files in outputs/..."
git add outputs/

TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
COMMIT_MSG="docs: 添加面经解答 — ${TIMESTAMP}"

echo -e "${GREEN}[INFO]${NC} Committing: ${COMMIT_MSG}"
git commit -m "$COMMIT_MSG" || {
    echo -e "${YELLOW}[SKIP]${NC} Nothing to commit."
    exit 0
}

# Push
echo -e "${GREEN}[INFO]${NC} Pushing to origin/${BRANCH}..."
git push origin "$BRANCH"

echo -e "${GREEN}[DONE]${NC} Successfully pushed to GitHub! 🚀"
