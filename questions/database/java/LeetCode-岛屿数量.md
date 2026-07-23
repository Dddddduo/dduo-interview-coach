---
id: q0110
question: "LeetCode 岛屿数量"
category: java
tags: ["LeetCode 岛屿 DFS BFS 并查集"]
difficulty: medium
created: 2026-07-23 10:21:19
source: 用户输入
---

# LeetCode 岛屿数量

DFS解法：遍历网格，遇到'1'就DFS淹掉整个岛（上下左右递归置'0'），岛屿数+1。时间O(m*n)。变体：BFS（队列）、Union-Find（并查集）。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `LeetCode 岛屿 DFS BFS 并查集`
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-07-23 10:21:19
