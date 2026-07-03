# Interview Coach — 面经深度解答 Agent

> 基于 **Harness Engineering（驾驭工程）** 构建的 AI 面试备考助手

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-orange)](https://claude.com/claude-code)

## 是什么？

**Interview Coach** 是一个 Claude Code Skill，输入面试题 → 自动深度解答 → 质量审查 → 生成文档 → 推送到 GitHub。

不是简单的"AI 答题"，而是通过 **多 Agent 协作 + Workflow 编排 + 质量门控** 的驾驭工程体系，确保每道题的回答：
- 🧠 **可记忆** — 联想记忆法最先给出，帮你编码到长期记忆
- 📖 **有深度** — 按"是什么→为什么→怎么用→注意事项"拆解底层原理
- 🗺️ **可答题** — 附赠面试答题框架，告诉你该怎么说、怎么得分
- ✅ **有保障** — 专用审查 Agent 逐项验证，不合格自动返工

## 架构

```
用户输入面试题
    ↓
┌─────────────────────────────────┐
│       阶段1: 题目解析            │  Skill 入口
└──────────────┬──────────────────┘
               ↓
┌──────────────────────────────────┐
│    阶段2: 并行深度答题            │  interview-answerer × N
│    ┌─────┐ ┌─────┐ ┌─────┐     │  每个 Agent 独立答一题
│    │ Q1  │ │ Q2  │ │ Q3  │     │
│    └──┬──┘ └──┬──┘ └──┬──┘     │
└───────┼───────┼───────┼─────────┘
        ↓       ↓       ↓
┌──────────────────────────────────┐
│    阶段3: 质量审查               │  quality-reviewer × N
│    逐题按 15 项清单检查          │  不通过自动重答(最多2次)
└──────────────┬───────────────────┘
               ↓
┌──────────────────────────────────┐
│    阶段4: 文档组装               │  doc-assembler
│    生成完整 .md 文档             │
└──────────────┬───────────────────┘
               ↓
┌──────────────────────────────────┐
│   阶段5+6: 落盘 & 推送           │  Write + git push
│   outputs/面经解答-*.md → GitHub │
└──────────────────────────────────┘
```

## Harness Engineering 体现

| 驾驭工程维度 | 本项目实现 |
|-------------|-----------|
| **多 Agent 协作** | 3 个专用 Agent（解题者 + 审查者 + 文档者），各司其职 |
| **Workflow 编排** | 确定性 6 阶段流水线，每阶段有明确的输入输出契约 |
| **质量门控** | 审查 Agent 逐项检查 15 条标准，不合格自动返工重答 |
| **Skill 封装** | `/面经助手` 一行命令触发全流程，用户只需输入题目 |
| **自动部署** | 文档生成后自动 git commit + push 到 GitHub |
| **可追溯性** | 每步输出落盘，Git 历史追踪每次解答 |

## 快速开始

### 前置条件

- [Claude Code](https://claude.com/claude-code) 已安装
- Git 已配置
- GitHub SSH 已配置

### 安装

```bash
# 1. 克隆仓库
git clone git@github.com:Dddddduo/MyLover-gc.git
cd MyLover-gc

# 2. 安装 Agent 和 Skill 到 Claude Code
# 将 .claude/ 目录下的内容链接或复制到你的项目或全局配置中
# 或者直接在 interview-coach 目录下打开 Claude Code
claude
```

### 使用

在 Claude Code 中输入：

```
/面经助手
第1题：请解释MySQL的索引底层数据结构，为什么选用B+树而不是红黑树或Hash？
第2题：Redis的过期策略有哪些？如何保证缓存与数据库的一致性？
第3题：请描述你在项目中遇到的最大的技术挑战，以及你是如何解决的
```

Agent 会自动：
1. 识别并拆分 3 道题
2. 并行深度解答每道题
3. 质量审查（不合格自动返工）
4. 生成文档到 `outputs/面经解答-{时间}.md`
5. 推送到 GitHub

## 每道题的回答结构

```
🧠 联想记忆法（最先给出！）
  ├── 记忆口诀/联想
  ├── 记忆原理
  └── 关联知识

📖 深度解答
  ├── 核心概念（是什么）
  ├── 底层原理（为什么）
  ├── 实践应用（怎么用）
  └── 深入思考（注意事项）

🗺️ 回答思路
  ├── 答题逻辑框架
  ├── 重点得分点
  ├── 常见误区
  ├── 时间分配建议
  └── 过渡话术
```

## 项目结构

```
interview-coach/
├── README.md                           # 本文件
├── CLAUDE.md                           # Claude Code 项目文档
├── .gitignore
├── .claude/
│   ├── settings.json                   # 项目级 harness 配置
│   ├── agents/
│   │   ├── interview-answerer.md       # 核心 Agent：深度解答面试题
│   │   ├── quality-reviewer.md         # 审查 Agent：15项清单验证
│   │   └── doc-assembler.md            # 文档 Agent：组装最终交付物
│   └── skills/
│       └── interview-coach/
│           └── SKILL.md                # /面经助手 Skill 入口
├── scripts/
│   └── push-output.sh                  # Git 自动推送脚本
├── outputs/                            # 生成的文档
└── examples/
    └── sample-output.md                # 示例输出
```

## Agent 体系

| Agent | 模型 | 职责 |
|-------|------|------|
| `interview-answerer` | Opus | 深度解答单道面试题，产出记忆法+原理+思路 |
| `quality-reviewer` | Sonnet | 15 项清单审查，PASS/FAIL + 具体修改建议 |
| `doc-assembler` | Sonnet | 组装最终文档，格式化、目录、元信息 |

## 许可

MIT License
