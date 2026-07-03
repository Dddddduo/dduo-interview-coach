# CLAUDE.md — Interview Coach 项目文档

## 项目概述

Interview Coach — 基于 **Harness Engineering（驾驭工程）** 的 AI 面试备考系统。

核心能力：输入面试题 → 深度解答 → 质量审查 → **自动归档题库** → 生成文档 → Git 推送。

## 核心架构

```
/面经助手 (Skill 统一入口)
    ├── 阶段1: 题目解析 & 分类
    ├── 阶段2: 并行答题 (interview-answerer × N)
    ├── 阶段3: 质量审查 (quality-reviewer × N)
    ├── 阶段4: 文档组装 (doc-assembler)
    ├── 阶段5: 题库归档 (question_manager.py)
    └── 阶段6: 落盘 & 推送 (git)
```

### 3 个 Agent

| Agent | 模型 | 职责 |
|-------|------|------|
| `interview-answerer` | Opus | 深度解答单题：记忆法 + 原理拆解 + 答题思路 |
| `quality-reviewer` | Sonnet | 15 项清单审查，FAIL → 自动重答 |
| `doc-assembler` | Sonnet | 组装最终 Markdown 文档 |

### 6 个 Python 脚本

| 脚本 | 职责 |
|------|------|
| `interview_agent.py` | 核心：独立运行的 AI Agent（调用 Anthropic API） |
| `batch_process.py` | 批量答题 |
| `question_manager.py` | 题库增删查改、分类标签 |
| `memory_trainer.py` | 交互式记忆训练 |
| `md_to_pdf.py` | Markdown → PDF |
| `generate_site.py` | 同步题库数据到 docs/ |

## 题库系统

- `questions/index.json` — 主索引（被网页端动态加载）
- `questions/database/{category}/{slug}.md` — 每道题独立归档
- 13 个分类，自动分类 + 自动标签 + 自动难度判断
- 网页端：`docs/questions.html` + `docs/questions.js` 动态渲染

## 技术约定

### Agent 定义
- `.claude/agents/*.md` — YAML frontmatter + system prompt
- `description` 必须包含 "Use this agent when..." 格式

### Skill 定义
- `.claude/skills/<name>/SKILL.md` — frontmatter + 执行指令
- `/面经助手` 是唯一用户入口

### Git 规范
- Git 身份：`zhudaoyang` / `1732446549@qq.com`
- Commit: `docs: 面经解答 + 题库更新 — YYYY-MM-DD HH:MM`
- Branch: `main`

### 输出规范
- 文档：`outputs/面经解答-YYYYMMDD-HHMM.md`
- 题库：`questions/database/{category}/{slug}.md`
- 每道题必含：🧠 联想记忆法 → 📖 深度解答 → 🗺️ 回答思路

## Harness Engineering 关键原则

1. **关注点分离** — 答题、审查、归档三个职责独立
2. **质量内建** — 审查是强制阶段，不是事后补救
3. **自动沉淀** — 每道题自动归档到题库，不需要手动操作
4. **数据驱动** — index.json 驱动网页端展示
5. **确定性编排** — Skill 定义 6 阶段，不依赖模型自主决策
