---
id: q0106
question: "A or B 的判断条件会用到索引吗？"
category: java
tags: ["OR条件 索引合并 Index Merge UNION"]
difficulty: medium
created: 2026-07-23 10:21:11
source: 用户输入
---

# A or B 的判断条件会用到索引吗？

A和B都有索引→可能Index Merge（索引合并）；A有索引B没有→全表扫描。优化：用UNION ALL替代OR。MySQL 5.0+支持Index Merge Access Method。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `OR条件 索引合并 Index Merge UNION`
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-07-23 10:21:11
