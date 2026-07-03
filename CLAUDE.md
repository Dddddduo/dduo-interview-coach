# CLAUDE.md — Interview Coach 项目文档

## 项目概述

Interview Coach 是一个基于 **Harness Engineering（驾驭工程）** 的 Claude Code 面试解答 Agent 项目。通过多 Agent 协作、Workflow 编排和自动质量门控，将面试题转化为深度解答文档并自动推送到 GitHub。

## 核心架构

- **3 个专用 Agent**: `interview-answerer` (答题), `quality-reviewer` (审查), `doc-assembler` (组装)
- **1 个 Skill**: `/面经助手` — 用户入口，编排全流程
- **6 阶段 Workflow**: 解析 → 并行答题 → 审查 → 组装 → 落盘 → 推送

## 技术约定

### Agent 定义规范
- Agent 文件位于 `.claude/agents/*.md`
- 使用 YAML frontmatter: `name`, `description`, `model`, `color`, `tools`
- `description` 必须包含 "Use this agent when..." 格式
- 所有 Agent 继承项目 effort level (`max`)

### Skill 定义规范
- Skill 文件位于 `.claude/skills/<name>/SKILL.md`
- Frontmatter 包含: `user-invocable: true`, `allowed-tools`
- Skill body 是完整的执行指令，必须包含所有阶段的详细说明
- 使用 `$ARGUMENTS` 捕获用户输入

### 输出规范
- 文档输出到 `outputs/` 目录
- 文件命名: `面经解答-YYYYMMDD-HHMM.md`
- 每道题必须包含: 联想记忆法 → 深度解答 → 回答思路（顺序不可变）
- 深度解答必须按 "是什么→为什么→怎么用→注意事项" 展开

### Git 规范
- Commit message 格式: `docs: 添加面经解答 — YYYY-MM-DD HH:MM`
- 只 push `outputs/` 目录下的变化
- Branch: `main`

## Harness Engineering 关键原则

1. **关注点分离**: 答题、审查、组装三个职责分离到独立 Agent
2. **质量内建**: 审查是流程的强制阶段，不是事后补救
3. **失败快速恢复**: 审查不合格自动重答，最多 2 次
4. **确定性编排**: Workflow 控制流是确定的，不是模型自主决定的
5. **可观测性**: 每个阶段有明确的输出，方便调试和追溯

## 开发注意事项

- 修改 Agent system prompt 后要重新测试答题质量
- quality-reviewer 的检查清单是质量的最后防线，修改需谨慎
- 不要直接在 SKILL.md 中展开大段内容，将详细逻辑放到 Agent 定义中
- 新增 Agent 能力时，同步更新 README 的架构图和 Agent 体系表
