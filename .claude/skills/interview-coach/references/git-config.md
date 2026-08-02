# Git 认证配置

> 使用 SSH 方式推送，不再依赖 Token（免过期问题）。

---

## 凭证

| 配置项 | 值 |
|--------|-----|
| GITHUB_USERNAME | `Dddddduo` |
| GITHUB_REPO | `dduo-interview-coach` |
| GIT_REMOTE_URL | `git@github.com:Dddddduo/dduo-interview-coach.git` |
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

# 配置 remote（SSH 方式，无需 Token）
git remote set-url origin git@github.com:Dddddduo/dduo-interview-coach.git

# 提交并推送
git add outputs/ questions/ docs/
git commit -m "docs: 面经解答 + 题库更新 — $(date +%Y-%m-%d_%H:%M)"
git push origin main
```

---

## 故障排查

如果 push 返回 SSH 认证错误：
1. 检查 `~/.ssh/id_rsa.pub` 是否已添加到 GitHub → Settings → SSH Keys
2. `ssh -T git@github.com` 测试连接
