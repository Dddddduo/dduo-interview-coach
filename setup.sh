#!/bin/bash
# ============================================================
# Interview Coach — 开箱即用安装脚本
# ============================================================
# 一键完成：依赖安装 → 环境检查 → 站点生成 → 就绪
#
# Usage:
#   bash setup.sh
#   bash setup.sh --check-only   # 仅检查环境
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════╗"
echo "║  🎯 Interview Coach — 开箱即用安装       ║"
echo "║  Harness Engineering Architecture        ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ---- 1. 检查 Python ----
echo -e "\n${BOLD}[1/5]${NC} 检查 Python..."
PYTHON=""
for cmd in python3 python; do
    if command -v $cmd &>/dev/null; then
        PYTHON=$cmd
        VER=$($PYTHON --version 2>&1)
        echo -e "  ${GREEN}✅${NC} $VER ($(which $PYTHON))"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo -e "  ${RED}❌${NC} 未找到 Python 3，请先安装"
    exit 1
fi

# ---- 2. 检查 Git ----
echo -e "\n${BOLD}[2/5]${NC} 检查 Git..."
if command -v git &>/dev/null; then
    GIT_VER=$(git --version)
    echo -e "  ${GREEN}✅${NC} $GIT_VER"
else
    echo -e "  ${RED}❌${NC} 未找到 Git"
    exit 1
fi

# 检查 Git 用户
GIT_USER=$(git config user.name 2>/dev/null || echo "")
GIT_EMAIL=$(git config user.email 2>/dev/null || echo "")
if [ -z "$GIT_USER" ] || [ -z "$GIT_EMAIL" ]; then
    echo -e "  ${YELLOW}⚠️${NC}  Git 用户未配置，将使用默认"
    git config user.name "zhudaoyang" 2>/dev/null || true
    git config user.email "1732446549@qq.com" 2>/dev/null || true
else
    echo -e "  ${GREEN}✅${NC} Git: $GIT_USER <$GIT_EMAIL>"
fi

# 检查 Git Remote
if git remote get-url origin &>/dev/null; then
    echo -e "  ${GREEN}✅${NC} Remote: $(git remote get-url origin)"
else
    echo -e "  ${YELLOW}⚠️${NC}  未配置 Git Remote，无法自动推送"
fi

# ---- 3. 安装 Python 依赖 ----
echo -e "\n${BOLD}[3/5]${NC} 安装 Python 依赖..."
$PYTHON -m pip install -r requirements.txt --quiet 2>&1 | tail -1 || {
    echo -e "  ${YELLOW}⚠️${NC}  部分依赖安装失败（非致命）"
}

# 验证关键依赖
for pkg in anthropic markdown; do
    if $PYTHON -c "import $pkg" 2>/dev/null; then
        echo -e "  ${GREEN}✅${NC} $pkg"
    else
        echo -e "  ${YELLOW}⚠️${NC}  $pkg 未安装（部分功能不可用）"
    fi
done

# ---- 4. 检查 Anthropic API Key ----
echo -e "\n${BOLD}[4/5]${NC} 检查 Anthropic API Key..."
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo -e "  ${GREEN}✅${NC} ANTHROPIC_API_KEY 已设置"
else
    echo -e "  ${YELLOW}⚠️${NC}  ANTHROPIC_API_KEY 未设置"
    echo -e "  Python 脚本需要: export ANTHROPIC_API_KEY='your-key'"
    echo -e "  Claude Code Skill 不需要（由 Claude 管理）"
fi

# ---- 5. 初始化站点 ----
echo -e "\n${BOLD}[5/5]${NC} 初始化站点数据..."
$PYTHON scripts/generate_site.py 2>&1 | sed 's/^/  /' || {
    echo -e "  ${YELLOW}⚠️${NC}  站点生成失败（非致命，可稍后手动运行）"
}

# ---- 完成 ----
echo -e "\n${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════╗"
echo "║  ✅ 安装完成！                            ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${BOLD}使用方式:${NC}"
echo -e ""
echo -e "  ${CYAN}方式 1: Claude Code Skill（推荐）${NC}"
echo -e "    cd $PROJECT_DIR"
echo -e "    claude"
echo -e "    /面经助手"
echo -e "    第1题：你的面试题..."
echo -e ""
echo -e "  ${CYAN}方式 2: Python 脚本${NC}"
echo -e "    export ANTHROPIC_API_KEY='your-key'"
echo -e "    python scripts/interview_agent.py \"你的面试题\""
echo -e ""
echo -e "  ${CYAN}方式 3: 题库管理${NC}"
echo -e "    python scripts/question_manager.py stats"
echo -e "    python scripts/memory_trainer.py outputs/*.md"
echo -e ""
echo -e "${BOLD}网页端:${NC}"
echo -e "  启用 GitHub Pages 后 (Settings → Pages → /docs → Save)"
echo -e "  🌐 https://ddddduo.github.io/dduo-interview-coach/questions.html"
echo -e "  📅 https://ddddduo.github.io/dduo-interview-coach/daily.html"
echo -e ""

CHECK_ONLY="$1"
if [ "$CHECK_ONLY" = "--check-only" ]; then
    echo -e "${GREEN}✅ 环境检查通过${NC}"
fi
