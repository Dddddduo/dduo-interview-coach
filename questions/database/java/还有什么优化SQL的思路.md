---
id: q0101
question: "还有什么优化SQL的思路？"
category: java
tags: ["SQL优化 索引提示 批处理 反范式 分区裁剪"]
difficulty: medium
created: 2026-07-23 10:21:04
source: 用户输入
---

# 还有什么优化SQL的思路？

高阶优化：索引提示（FORCE INDEX）、连接池调优（HikariCP参数）、批处理（批量INSERT）、延迟关联（先查主键再JOIN）、反范式（冗余字段减少JOIN）、分区裁剪（按分区键WHERE跳过无关分区）。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `SQL优化 索引提示 批处理 反范式 分区裁剪`
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-07-23 10:21:04
