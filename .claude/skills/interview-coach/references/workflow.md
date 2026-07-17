# 10 阶段执行流程

> 本文件定义 Interview Coach 的完整 10 阶段执行步骤。SKILL.md 执行前必须读取。

---

## 阶段 1：题目解析

1. 解析 `$ARGUMENTS`，按编号规则拆分题目（支持 "第N题"、"N."、"QN:" 等格式）
2. 识别每道题的类型（技术题 / 行为题 / 系统设计题）
3. 输出确认清单，让用户确认解析结果

## 阶段 2：并行深度答题

**必须并行**启动所有 `interview-answerer` agent：

```
Agent(subagent_type="interview-answerer", description="解答第N题", prompt="请解答：{题目内容}")
```

`subagent_type` 必须与 `.claude/agents/interview-answerer.md` 中定义的 `name: interview-answerer` 一致。

## 阶段 3：质量审查

逐题启动 `quality-reviewer` agent：

```
Agent(subagent_type="quality-reviewer", description="审查第N题", prompt="审查以下答案：{answerer 输出}")
```

审查标准参见 `.claude/agents/quality-reviewer.md`（15 项清单）。

## 阶段 4：重答循环

- FAIL → 携带审查反馈重新调用 `interview-answerer` agent
- 重试不超过 **2 次**（M5 约束）
- 2 次后仍 FAIL → 标记该题为"审查未通过"，在最终报告中如实报告（M10 约束）

## 阶段 5：文档组装

启动 `doc-assembler` agent 组装完整 Markdown：

```
Agent(subagent_type="doc-assembler", description="组装最终文档", prompt="请组装以下答案：{所有题目的最终答案}")
```

## 阶段 6：输出落盘

使用 **Write 工具**写入文件（M6 约束）：

```
Write(file_path="outputs/面经解答-YYYYMMDD-HHMM.md", content="{doc-assembler 输出}")
```

时间戳取当前系统时间。

## 阶段 7：题库归档

对每道题执行（M7 约束）：

```bash
cd ~/Documents/projects/interview-coach
python3 scripts/question_manager.py add --question "{题目}" --answer "{答案}" --category "{分类}"
```

## 阶段 8：站点生成

```bash
cd ~/Documents/projects/interview-coach
python3 scripts/generate_site.py
```

## 阶段 9：Git 部署

使用 `references/git-config.md` 中定义的凭证执行以下精确命令（G1 ~ G6 约束）：

```bash
cd ~/Documents/projects/interview-coach

# 确保使用正确的 git 身份
git config user.name "zhudaoyang"
git config user.email "1732446549@qq.com"

# 确保 remote 指向含 Token 的 URL（从 references/git-config.md 获取）
git remote set-url origin <GIT_REMOTE_URL_FROM_git-config.md>

# 暂存所有变更
git add outputs/ questions/ docs/

# 提交
git commit -m "docs: 面经解答 + 题库更新 — $(date +%Y-%m-%d_%H:%M)"

# 推送到 main 分支
git push origin main
```

如果 push 失败，检查 Token 是否过期，提示用户更新 `references/git-config.md`。

## 阶段 10：结果报告

向用户输出完整报告：

- 题目数量统计（通过 / 失败 / 重答次数）
- 每题答案质量评估
- 归档路径（题库 / 文档）
- GitHub Pages URL
- 如有 FAIL 题目，明确列出并说明原因

---

## 使用示例

```
/面经助手
第1题：请解释 JVM 的内存模型，堆、栈、方法区各自的职责
第2题：MySQL 索引底层为什么用 B+ 树？从磁盘 I/O 角度分析
第3题：Redis 缓存穿透、击穿、雪崩是什么？如何解决？
```
