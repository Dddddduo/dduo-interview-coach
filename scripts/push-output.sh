#!/bin/bash
# ======================================================
# Interview Coach — Git Auto-Push Script
# Pushes docs, questions database, and outputs to GitHub
# ======================================================

set -e

PROJECT_DIR="$HOME/Documents/projects/interview-coach"
BRANCH="main"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}[Interview Coach]${NC} Auto-push script..."

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}[ERROR]${NC} Project directory not found: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# Regenerate site data (sync index.json to docs/)
echo -e "${GREEN}[INFO]${NC} Regenerating site data..."
python3 scripts/generate_site.py 2>/dev/null || echo "  ⚠️  generate_site.py 失败，跳过"

# Check remote
if ! git remote get-url origin &>/dev/null; then
    echo -e "${RED}[ERROR]${NC} No git remote 'origin' configured."
    exit 1
fi

# Stage everything
echo -e "${GREEN}[INFO]${NC} Staging files..."
git add outputs/ questions/ docs/index.json 2>/dev/null || true

# Check if there are changes
if git diff --quiet --cached; then
    echo -e "${YELLOW}[SKIP]${NC} No changes to push."
    exit 0
fi

# Commit
TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
COMMIT_MSG="docs: 面经解答 + 题库更新 — ${TIMESTAMP}"

echo -e "${GREEN}[INFO]${NC} Committing: ${COMMIT_MSG}"
git commit -m "$COMMIT_MSG" || {
    echo -e "${YELLOW}[SKIP]${NC} Nothing to commit."
    exit 0
}

# Push
echo -e "${GREEN}[INFO]${NC} Pushing to origin/${BRANCH}..."
git push origin "$BRANCH"

echo -e "${GREEN}[DONE]${NC} Successfully pushed to GitHub! 🚀"
echo -e "🌐 https://ddddduo.github.io/dduo-interview-coach/questions.html"
