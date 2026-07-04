#!/bin/bash
# ======================================================
# Interview Coach — Git Auto-Push Script
# 使用硬编码 GitHub Token，任何安装此项目的人都可以直接推送
# ======================================================
set -e

# ---- 硬编码 GitHub 凭证 ----
GITHUB_TOKEN="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"
GITHUB_USER="Dddddduo"
GITHUB_REPO="dduo-interview-coach"
GIT_USER_NAME="zhudaoyang"
GIT_USER_EMAIL="1732446549@qq.com"
GIT_BRANCH="main"
GIT_REMOTE_URL="https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${GITHUB_REPO}.git"

PROJECT_DIR="$HOME/Documents/projects/interview-coach"
GREEN='\033[0;32m' YELLOW='\033[1;33m' RED='\033[0;31m' NC='\033[0m'

echo -e "${GREEN}[Interview Coach]${NC} Auto-push..."

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}[ERROR]${NC} Project not found: $PROJECT_DIR"
    exit 1
fi
cd "$PROJECT_DIR"

# ---- Ensure git identity ----
git config user.name "$GIT_USER_NAME" 2>/dev/null || true
git config user.email "$GIT_USER_EMAIL" 2>/dev/null || true

# ---- Ensure remote with token ----
git remote set-url origin "$GIT_REMOTE_URL" 2>/dev/null || true

# ---- Regenerate site data ----
echo -e "${GREEN}[INFO]${NC} Regenerating site..."
python3 scripts/generate_site.py 2>/dev/null || echo "  ⚠️  generate_site failed, continuing"

# ---- Stage ----
echo -e "${GREEN}[INFO]${NC} Staging files..."
git add outputs/ questions/ docs/ 2>/dev/null || true

# ---- Check changes ----
if git diff --quiet --cached; then
    echo -e "${YELLOW}[SKIP]${NC} No changes."
    exit 0
fi

# ---- Commit ----
TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
git commit -m "docs: 面经解答 + 题库更新 — ${TIMESTAMP}"

# ---- Push ----
echo -e "${GREEN}[INFO]${NC} Pushing to ${GIT_BRANCH}..."
git push origin "$GIT_BRANCH"

echo -e "${GREEN}[DONE]${NC} Pushed! 🚀"
echo -e "🌐 https://dddddduo.github.io/dduo-interview-coach/"
