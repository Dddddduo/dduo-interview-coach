# Git 认证配置

> 本文件包含 Git 推送所需的全部认证信息。Token 需要定期更新。

---

## 凭证

| 配置项 | 值 |
|--------|-----|
| GITHUB_TOKEN | `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` |
| GITHUB_USERNAME | `Dddddduo` |
| GITHUB_REPO | `dduo-interview-coach` |
| GIT_REMOTE_URL | `https://Dddddduo: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@github.com/Dddddduo/dduo-interview-coach.git` |
| GIT_USER_NAME | `zhudaoyang` |
| GIT_USER_EMAIL | `1732446549@qq.com` |
| GIT_BRANCH | `main` |

---

## Git 操作命令模板

```bash
cd ~/Documents/projects/interview-coach

# 配置身份
git config user.name "zhudaoyang"
git config user.email "1732446549@qq.com"

# 配置 remote（含 Token）
git remote set-url origin https://Dddddduo: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@github.com/Dddddduo/dduo-interview-coach.git

# 提交并推送
git add outputs/ questions/ docs/
git commit -m "docs: 面经解答 + 题库更新 — $(date +%Y-%m-%d_%H:%M)"
git push origin main
```

---

## Token 过期处理

如果 push 返回 401/403 错误：
1. 到 GitHub Settings → Developer settings → Personal access tokens 生成新 Token
2. 更新本文件中的 `GITHUB_TOKEN` 和 `GIT_REMOTE_URL`
3. 同步更新 `.claude/settings.json` 中的 `GITHUB_TOKEN` 和 `GIT_REMOTE_URL` 环境变量
4. 重新执行阶段 9
