# 驾驭工程硬约束 (Harness Engineering Hard Constraints)

> 本文件定义 Interview Coach 的全部硬约束。SKILL.md 执行前必须读取并完全遵守。

---

## 流程完整性 MUST（M1 ~ M10）

| # | 规则 |
|---|------|
| M1 | **必须执行全部 10 个阶段**，不可跳过任何阶段 |
| M2 | **阶段顺序不可调换**：1→2→3→4→5→6→7→8→9→10 |
| M3 | **阶段 2 必须并行启动所有 answerer agent**，不可串行 |
| M4 | **阶段 3 必须对每道题执行审查**，不可只抽查 |
| M5 | **阶段 4 重试不超过 2 次**，不可无限循环 |
| M6 | **阶段 6 必须用 Write 工具写入文件**，不可仅在对话展示 |
| M7 | **阶段 7 必须对每道题执行 question_manager.py add** |
| M8 | **阶段 8 必须运行 generate_site.py** |
| M9 | **阶段 9 必须 git commit + git push，使用硬编码的 GitHub Token** |
| M10 | **阶段 10 必须如实报告统计**，不美化、不隐藏失败 |

---

## Git 操作 MUST（G1 ~ G6）

> Git 凭证读取 `references/git-config.md`。

| # | 规则 |
|---|------|
| G1 | **所有 git push 必须使用 Git Config 中定义的 GIT_REMOTE_URL** |
| G2 | **git config user.name 必须设为 "zhudaoyang"** |
| G3 | **git config user.email 必须设为 "1732446549@qq.com"** |
| G4 | **每次 push 前必须确保 remote 指向正确的 URL**：`git remote set-url origin <GIT_REMOTE_URL>` |
| G5 | **严禁**使用 SSH 方式 (`git@github.com:...`) 推送 |
| G6 | **严禁**使用其他 GitHub 用户名或 Token |

---

## 输出质量 MUST（Q1 ~ Q6）

| # | 规则 |
|---|------|
| Q1 | 每道题的答案**必须包含三部分**：🧠 联想记忆法 → 📖 深度解答 → 🗺️ 回答思路 |
| Q2 | 联想记忆法**必须在最前面** |
| Q3 | 深度解答**必须按"核心概念→底层原理→实践应用→深入思考"四层展开 |
| Q4 | 技术题**必须有代码示例** |
| Q5 | 行为题**必须按 STAR 框架** |
| Q6 | 首次出现的术语**必须中英对照** |

---

## 禁止行为 MUST NOT（N1 ~ N7）

| # | 规则 |
|---|------|
| N1 | **不允许**将多道题合并为一题笼统回答 |
| N2 | **不允许**遗漏任何一道用户输入的题目 |
| N3 | **不允许**跳过联想记忆法 |
| N4 | **不允许**以"略"、"同上"、"类似"等词跳过任何内容 |
| N5 | **不允许**在审查 FAIL 时不重答直接继续 |
| N6 | **不允许**使用 SSH 或非指定 Token 进行 git 操作 |
| N7 | **不允许**修改或覆盖远程仓库的 URL 配置 |
