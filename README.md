# Interview Coach — 面经深度解答 Agent

> **基于 Harness Engineering（驾驭工程）构建的 AI 面试备考系统**
>
> 输入面试题 → 深度解答 → 质量审查 → 自动归档题库 → 生成文档 → 推送到 GitHub → 网页浏览

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-orange)](https://claude.com/claude-code)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Pages](https://img.shields.io/badge/GitHub-Pages-blue)](https://ddddduo.github.io/dduo-interview-coach/)

🌐 **在线题库**: [ddddduo.github.io/dduo-interview-coach/questions.html](https://ddddduo.github.io/dduo-interview-coach/questions.html)

---

## 目录

1. [Harness Engineering 驾驭工程](#harness-engineering-驾驭工程)
2. [架构总览](#架构总览)
3. [完整工作流（10 阶段）](#完整工作流10-阶段)
4. [Agent 体系](#agent-体系)
5. [开箱即用](#开箱即用)
6. [使用方式](#使用方式)
7. [项目结构](#项目结构)
8. [数据流](#数据流)

---

## Harness Engineering 驾驭工程

### 什么是驾驭工程？

**Harness Engineering（驾驭工程）** 是构建可靠 AI Agent 系统的工程方法论。核心理念：**不是写一个 prompt 然后祈祷模型做对，而是通过工程手段约束和引导 AI 的行为，确保结果可控、可追溯、可复现**。

在 Interview Coach 中，驾驭工程体现在 **10 个维度**：

### 驾驭工程 10 维度对照表

| # | 维度 | 含义 | 本项目实现 |
|---|------|------|-----------|
| **1** | **多 Agent 协作** | 不同 Agent 各司其职，通过契约协作而非一个巨型 prompt | 3 个专用 Agent：`interview-answerer`（答题）、`quality-reviewer`（审查）、`doc-assembler`（组装）。每个有独立的 system prompt、独立的职责边界、独立的输入输出契约 |
| **2** | **确定性编排** | 流程由工程层定义，不是模型自主决定"下一步做什么" | SKILL.md 硬编码 10 阶段流程。Agent 不能跳过、不能调换顺序、不能"我觉得不需要这一步" |
| **3** | **质量门控** | 每个阶段的输出必须通过检查才能进入下一阶段 | `quality-reviewer` 对每道题的答案执行 15 项检查。FAIL → 自动重答（最多 2 次）。2 次后仍 FAIL → 标记"需人工审核"，不静默丢弃 |
| **4** | **关注点分离** | 答题、审查、归档、部署各自独立 | 答题者不知道审查逻辑，审查者不知道归档逻辑，归档者不知道部署逻辑。修改审查标准不会影响答题质量 |
| **5** | **强制持久化** | AI 产出不能只留在对话中，必须结构化落盘 | 每道题强制归档到 `questions/database/`，每题一个独立 .md 文件，带 YAML frontmatter 元信息。同时更新 `index.json` 索引 |
| **6** | **自动部署** | 产出物自动推送到可访问的位置 | 答案生成后自动 `git commit` + `git push`，同时 `generate_site.py` 生成 HTML 到 `docs/q/`，GitHub Pages 自动更新 |
| **7** | **幂等性** | 同样的输入跑两次，结果一致且不产生副作用 | `question_manager.py` 的 `add` 命令执行 MD5 去重检查。同一道题归档两次只会跳过一次。`generate_site.py` 增量生成——MD 没变就不重新生成 HTML |
| **8** | **失败可恢复** | 每个环节有明确的失败处理策略，不静默失败 | Agent 超时 → 自动重试 1 次；审查不通过 → 重答 2 次；Git push 失败 → 提示用户文档已保存本地；题库归档失败 → 不影响主流程，事后可补 |
| **9** | **可观测性** | 每步有可见输出，方便调试 | 每个阶段完成后向用户报告进度。统计信息：几道通过、几道重试、归档到哪些文件、推送是否成功 |
| **10** | **Skill 封装** | 复杂流程对用户透明，一个命令触发全流程 | `/面经助手` 一行命令，用户只关心"输入题目"。10 个阶段的复杂度完全封装在 Skill 和 Agent 内部 |

### 驾驭工程 vs 普通 Prompt

| | 普通 Prompt 工程 | 驾驭工程 (本项目) |
|---|---|---|
| 答题 | "请回答以下面试题" | 专用 `interview-answerer` agent，system prompt 硬约束输出结构 |
| 质量 | 依赖模型自觉 | 专用 `quality-reviewer` agent，15 项清单逐项检查 |
| 失败 | 静默吞下或直接报错 | 自动重答 + 反馈修正，2 次后标记人工审核 |
| 归档 | 手动复制粘贴 | `question_manager.py` 自动分类+标签+去重+落盘 |
| 部署 | 手动 git push | `generate_site.py` + `git push` 全自动 |
| 可追溯 | 对话记录 | 每题独立文件 + index.json + Git 历史 |

---

## 架构总览

```
                            ┌──────────────────┐
                            │   用户输入题目     │
                            │  /面经助手 [题]    │
                            └────────┬─────────┘
                                     │
              ┌──────────────────────┴──────────────────────┐
              │           SKILL.md (驾驭工程编排层)           │
              │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐      │
              │  │阶段1 │→│阶段2 │→│阶段3 │→│...  │→阶段10│
              │  │ 解析 │ │ 答题 │ │ 审查 │ │      │  报告  │
              │  └──────┘ └──────┘ └──────┘ └──────┘      │
              └──────────────────┬──────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
  ┌──────▼──────┐          ┌────────▼────────┐        ┌─────────▼────────┐
  │ Agent 层    │          │   Python 脚本层   │        │   数据持久层      │
  │             │          │                  │        │                  │
  │ answerer   │          │ interview_agent  │        │ questions/       │
  │ reviewer   │          │ question_manager │        │   index.json     │
  │ assembler  │          │ generate_site    │        │   database/      │
  │             │          │ memory_trainer   │        │ outputs/         │
  └─────────────┘          │ batch_process    │        │ docs/q/          │
                           │ md_to_pdf        │        │ docs/data.json   │
                           └──────────────────┘        └──────────────────┘
```

---

## 完整工作流（10 阶段）

每次 `/面经助手` 按此流程执行，**不可跳过、不可调换顺序**：

```
阶段 1  ──→ 题目解析
  │ 输入: 用户原始文本
  │ 输出: 题目列表 [Q1, Q2, Q3...] + 类型标注
  │ 约束: 每题独立完整，不合并、不截断
  │
  ▼
阶段 2  ──→ 并行深度答题
  │ Agent: interview-answerer × N（并行）
  │ 输入: 每道题的完整文本
  │ 输出: 每道题的 联想记忆法 + 深度解答 + 回答思路
  │ 约束: 记忆法最先给出；必须按"是什么→为什么→怎么用→注意事项"展开
  │
  ▼
阶段 3  ──→ 质量审查
  │ Agent: quality-reviewer × N
  │ 输入: 原题 + 答案
  │ 输出: PASS/FAIL + 具体问题列表
  │ 约束: 15 项检查逐项验证，FAIL 必须给出具体修改建议
  │
  ▼
阶段 4  ──→ 重答循环（条件触发）
  │ 条件: 阶段 3 结果为 FAIL
  │ Agent: interview-answerer（携带审查反馈）
  │ 约束: 最多重试 2 次，2 次后标记"需人工审核"
  │
  ▼
阶段 5  ──→ 文档组装
  │ Agent: doc-assembler
  │ 输入: 全部通过的答案
  │ 输出: 完整 Markdown 文档（目录+正文+元信息）
  │ 约束: 保留全部原内容，不删减
  │
  ▼
阶段 6  ──→ 输出落盘
  │ 工具: Write
  │ 输出: outputs/面经解答-YYYYMMDD-HHMM.md
  │ 约束: 必须写入文件，不可仅在对话中展示
  │
  ▼
阶段 7  ──→ 题库归档
  │ 脚本: question_manager.py add（每题一次）
  │ 输入: 题目 + 答案
  │ 输出: questions/database/{category}/{slug}.md + 更新 index.json
  │ 约束: 自动分类 + 自动标签 + 去重检查
  │
  ▼
阶段 8  ──→ 站点生成
  │ 脚本: generate_site.py
  │ 输入: questions/database/ 下所有 .md
  │ 输出: docs/q/{id}.html + docs/data.json
  │ 约束: 增量生成，未变化的题目跳过
  │
  ▼
阶段 9  ──→ Git 部署
  │ 工具: Bash(git add + commit + push)
  │ 范围: outputs/ + questions/ + docs/
  │ 约束: 使用 zhudaoyang/1732446549@qq.com 身份提交
  │
  ▼
阶段 10 ──→ 结果报告
  │ 输出: 统计信息 + 归档路径 + GitHub URL + Pages URL
  │ 约束: 如实报告通过/失败/重试/人工审核数量
```

---

## Agent 体系

本项目包含 **3 个专用 Agent**，每个有独立的职责边界和输入输出契约：

### Agent 1: `interview-answerer`（答题者）

| 属性 | 值 |
|------|-----|
| **模型** | Opus（需要深度推理） |
| **工具** | WebSearch, WebFetch |
| **角色** | 深度解答单道面试题 |
| **输入** | 一道面试题的完整文本 |
| **输出** | 三部分：🧠联想记忆法 → 📖深度解答 → 🗺️回答思路 |

**硬约束（MUST）**:
- 联想记忆法**必须在最前面**，包含口诀 + 记忆原理 + 关联知识
- 深度解答**必须**按"核心概念→底层原理→实践应用→深入思考"四层递进
- 回答思路**必须**包含：答题框架 + 得分点 + 误区 + 时间分配 + 过渡话术
- 技术题**必须**有代码示例
- 行为题**必须**按 STAR 框架展开
- 语言正式专业，中英术语对照

**禁止（MUST NOT）**:
- 不允许跳过联想记忆法
- 不允许只给表面结论不讲原理
- 不允许口语化、随意化表述
- 不允许"我觉得"、"可能"、"大概"等模糊词

### Agent 2: `quality-reviewer`（审查者）

| 属性 | 值 |
|------|-----|
| **模型** | Sonnet（快速审查） |
| **工具** | 无 |
| **角色** | 15 项清单逐项验证答案质量 |
| **输入** | 原题 + 答案全文 |
| **输出** | JSON: `{result: PASS/FAIL, failed_items: [...], specific_issues: "..."}` |

**15 项检查清单**:

| # | 类别 | 检查项 |
|---|------|--------|
| 1 | 结构 | 联想记忆法是否在第一部分？ |
| 2 | 结构 | 记忆法含口诀+原理+关联知识？ |
| 3 | 结构 | 深度解答含 4 个子章节？ |
| 4 | 结构 | 回答思路含 5 个要素？ |
| 5 | 深度 | 是否深入讲解原理（非表面结论）？ |
| 6 | 深度 | 技术题有代码示例？行为题有 STAR？ |
| 7 | 深度 | 是否包含最佳实践？ |
| 8 | 深度 | 是否包含常见误区和边界情况？ |
| 9 | 语言 | 语言是否专业正式？ |
| 10 | 语言 | 术语是否中英对照？ |
| 11 | 可用 | 答案是否可直接用于面试口述？ |
| 12 | 结构 | 是否有面试官追问的预判？ |
| 13 | 记忆 | 记忆法是否具象、可操作（非"多练习"类废话）？ |
| 14 | 记忆 | 是否解释了记忆法的认知原理？ |
| 15 | 记忆 | 是否锚定到已有知识？ |

**约束**: FAIL 必须给出具体修改建议，不允许"不够好"这种模糊评价。

### Agent 3: `doc-assembler`（组装者）

| 属性 | 值 |
|------|-----|
| **模型** | Sonnet |
| **工具** | 无 |
| **角色** | 将多道题答案组装为完整文档 |
| **输入** | N 道题的答案 |
| **输出** | 完整 Markdown 文档（含目录+元信息） |

**约束**:
- 必须生成可点击目录
- 代码块必须有语言标签
- 保留 100% 原有内容，不允许删减或改写
- 添加生成时间和题数元信息

---

## 开箱即用

### 前置条件

- **macOS** / Linux，Python 3.10+
- **Git** 已配置 SSH（`ssh -T git@github.com` 通过）
- **Claude Code** 已安装（或仅用 Python 脚本 + Anthropic API Key）

### 一键安装

```bash
# 1. 克隆
git clone git@github.com:Dddddduo/dduo-interview-coach.git
cd dduo-interview-coach

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化（生成站点数据）
python scripts/generate_site.py --force

# 4. 验证
python scripts/question_manager.py stats
# 输出: 总题数: 3  ...
```

### 使用方式

**方式 1: Claude Code Skill（推荐 — 全自动）**

在项目目录打开 Claude Code：
```bash
claude
```

输入：
```
/面经助手
第1题：请解释 JVM 的内存模型
第2题：MySQL 索引为什么用 B+ 树？
```

**全自动流程**：答题 → 审查 → 归档题库 → 生成 HTML → Git push → 网页更新

**方式 2: Python 脚本（独立运行，无需 Claude Code）**

```bash
export ANTHROPIC_API_KEY='your-api-key'

# 答一道题
python scripts/interview_agent.py "什么是 CAP 理论？"

# 批量答题
python scripts/batch_process.py examples/questions-example.json

# 记忆训练（交互式）
python scripts/memory_trainer.py --mode random outputs/*.md

# 导出 PDF
python scripts/md_to_pdf.py outputs/*.md
```

---

## 使用方式

### 题库管理

```bash
# 查看统计
python scripts/question_manager.py stats

# 搜索
python scripts/question_manager.py search "CAP"

# 手动添加题目
python scripts/question_manager.py add \
  --question "你的题目" \
  --answer "你的答案（Markdown）" \
  --category java --tags "JVM,并发"

# 导出全部题库
python scripts/question_manager.py export --format markdown --output all.md
```

### 记忆训练

```bash
# 闪卡模式（看到题目→回忆→看答案）
python scripts/memory_trainer.py outputs/*.md

# 填空模式（口诀挖掉关键词，你来补）
python scripts/memory_trainer.py --mode cloze outputs/*.md

# 随机挑战（10轮，答对加分）
python scripts/memory_trainer.py --mode random --rounds 10 outputs/*.md
```

### 网页端

启用 GitHub Pages 后（Settings → Pages → `/docs` → Save）：

| 页面 | URL | 功能 |
|------|-----|------|
| **题库浏览器** | `.../questions.html` | 搜索、分类筛选、标签云、按日期分组 |
| **每日复习** | `.../daily.html` | 连续打卡、30天月历、进度条、一键标记已复习 |
| **题目阅读** | `.../q/q0001.html` | 深色主题、代码高亮、复习打卡按钮 |

---

## 项目结构

```
dduo-interview-coach/
│
├── .claude/                            # ⚙️ Claude Code 驾驭工程配置
│   ├── settings.json                   #    权限白名单 + 环境变量
│   ├── agents/                         #    Agent 定义层
│   │   ├── interview-answerer.md       #      答题 Agent（Opus, 硬约束输出结构）
│   │   ├── quality-reviewer.md         #      审查 Agent（Sonnet, 15项清单）
│   │   └── doc-assembler.md            #      组装 Agent（Sonnet, 文档排版）
│   └── skills/interview-coach/
│       └── SKILL.md                    #    /面经助手 — 统一入口 + 10阶段编排
│
├── scripts/                            # 🐍 Python 脚本层（可独立运行）
│   ├── interview_agent.py              #    核心 Agent（Anthropic API + 自动归档）
│   ├── batch_process.py                #    批量处理器（JSON 题库批量答题）
│   ├── question_manager.py             #    题库管理器（增删查改、分类、标签、去重）
│   ├── memory_trainer.py               #    记忆训练器（闪卡/填空/随机挑战）
│   ├── md_to_pdf.py                    #    Markdown → PDF 转换器
│   ├── generate_site.py                #    站点生成器（MD→HTML + data.json）
│   └── push-output.sh                  #    自动推送脚本
│
├── questions/                          # 📚 题库持久层
│   ├── index.json                      #    题库主索引（被网页端动态加载）
│   └── database/                       #    13 个分类目录，每题独立 .md
│       ├── java/                       #    ☕ Java（JVM、并发、集合...）
│       ├── mysql/                      #    🗄️ MySQL（索引、事务、SQL...）
│       ├── redis/                      #    ⚡ Redis（缓存策略、数据结构...）
│       ├── spring/                     #    🍃 Spring（IoC、AOP、Boot...）
│       ├── distributed/                #    🌐 分布式（CAP、消息队列、微服务...）
│       ├── os/                         #    💻 操作系统（进程线程、内存管理...）
│       ├── network/                    #    🌍 计算机网络（TCP/IP、HTTP...）
│       ├── python/go/frontend/         #    ... 共 13 个分类
│       └── behavioral/system-design/devops/
│
├── docs/                               # 🌐 GitHub Pages 站点
│   ├── index.html                      #    Landing Page
│   ├── questions.html                  #    题库浏览器（列表/日期双视图）
│   ├── questions.js                    #    浏览器 JS 引擎
│   ├── daily.html                      #    每日复习页（打卡+月历+进度）
│   ├── daily.js                        #    复习引擎（localStorage）
│   ├── sample.html                     #    示例输出页
│   ├── data.json                       #    前端数据（generate_site.py 生成）
│   ├── index.json                      #    题库索引（同步自 questions/）
│   └── q/                             #    题目 HTML 页（generate_site.py 生成）
│       ├── q0001.html                  #      每道题独立美化的阅读页面
│       └── ...
│
├── outputs/                            # 📄 生成的答题文档
├── examples/                           # 📋 示例
│   ├── sample-output.md                #    2 道题完整示例
│   └── questions-example.json          #    示例题库（5道Java题）
│
├── requirements.txt                    # Python 依赖
├── README.md                           # 本文件 — 驾驭工程完整文档
└── CLAUDE.md                           # Claude Code 项目指引
```

---

## 数据流

```
┌─────────────────┐
│  /面经助手 [题]   │  ← 用户唯一入口
└────────┬────────┘
         │
    ┌────▼────────────────────────────────────────────┐
    │  SKILL.md 编排 10 阶段                           │
    │  阶段1: 解析题目                                  │
    │  阶段2: interview-answerer agent → 深度答题       │
    │  阶段3: quality-reviewer agent → 15项审查         │
    │  阶段4: FAIL → 重答 (max 2次)                     │
    │  阶段5: doc-assembler agent → 文档组装            │
    └────┬────────────────────────────────────────────┘
         │
    ┌────▼─────────────┐
    │  Write 工具       │ → outputs/面经解答-*.md
    └────┬─────────────┘
         │
    ┌────▼─────────────┐
    │  question_manager │ → questions/database/{cat}/{slug}.md
    │  .py add (×N)     │ → questions/index.json (更新)
    └────┬─────────────┘
         │
    ┌────▼─────────────┐
    │  generate_site.py │ → docs/q/{id}.html (MD→HTML)
    │                   │ → docs/data.json (前端数据)
    │                   │ → docs/index.json (同步)
    └────┬─────────────┘
         │
    ┌────▼─────────────┐
    │  git add + commit │ → push → GitHub
    │  + push           │ → GitHub Pages 自动更新
    └──────────────────┘
```

**关键设计决策**：

1. **为什么题目存两份？** — `questions/database/` 是源（结构化、分目录、方便管理），`docs/q/` 是发布版（HTML、美化排版、Pages 可访问）。`generate_site.py` 作为中间桥梁。

2. **为什么不用数据库？** — 全部文件系统 + JSON。GitHub Pages 只能托管静态文件，JSON 可在浏览器端直接 fetch，无需后端。

3. **为什么复习打卡用 localStorage？** — 无需后端、无需登录、隐私安全。每个用户的复习数据留在自己浏览器里。

4. **为什么 10 个阶段这么严格？** — 驾驭工程的核心就是确定性。每一步有明确的输入、输出、约束、失败处理。Agent 不能"灵活跳过"，只能按契约执行。

---

## 驾驭工程设计决策

| 决策 | 理由 |
|------|------|
| 3 个 Agent 而非 1 个 | 答题、审查、组装三个职责不应耦合。审查出问题只需改 reviewer prompt，不影响 answerer |
| Agent 定义在 .md 文件 | 声明式配置，可版本控制，可 diff，可 review |
| Python 脚本 + Agent 双轨 | Python 脚本不依赖 Claude Code，可独立运行；Agent 利用 Claude Code 的 tool use 能力 |
| 文件系统做数据库 | GitHub Pages 兼容、零依赖、Git 版本追踪 |
| 每题独立 .md + frontmatter | 方便检索、可单独修改、YAML 元信息可被程序读取 |
| 增量生成 HTML | `generate_site.py` 只重新生成变化的题目，减少构建时间 |
| MD5 去重 | 幂等性保证 — 同一题运行两次不产生重复 |
| 审查 FAIL 最多 2 次重试 | 防止无限循环，同时给模型 2 次修正机会 |
