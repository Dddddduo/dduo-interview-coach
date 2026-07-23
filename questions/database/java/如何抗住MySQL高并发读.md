---
id: q0090
question: "如何抗住MySQL高并发读"
category: java
tags: ["高并发读 缓存 读写分离 分库分表"]
difficulty: hard
created: 2026-07-23 10:20:48
source: 用户输入
---

# 如何抗住MySQL高并发读

七大方案：Redis缓存热点数据、多级缓存（Caffeine+Redis）、读写分离（主写从读）、分库分表（ShardingSphere）、CDN加速、查询优化（索引/覆盖索引）、连接池调优（HikariCP）。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `高并发读 缓存 读写分离 分库分表`
> 📊 **难度**: 进阶
> 📅 **归档时间**: 2026-07-23 10:20:48
