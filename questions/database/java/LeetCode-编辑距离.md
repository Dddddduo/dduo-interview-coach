---
id: q0087
question: "LeetCode 编辑距离"
category: java
tags: ["LeetCode 编辑距离 动态规划 DP"]
difficulty: hard
created: 2026-07-23 10:20:48
source: 用户输入
---

# LeetCode 编辑距离

编辑距离（Edit Distance）DP解法：dp[i][j]表示word1前i个字符到word2前j个字符的最小编辑次数。dp[i][j]=dp[i-1][j-1]（字符相等）or 1+min(删除,插入,替换)。时间O(mn)，空间可优化到O(min(m,n))。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `LeetCode 编辑距离 动态规划 DP`
> 📊 **难度**: 进阶
> 📅 **归档时间**: 2026-07-23 10:20:48
