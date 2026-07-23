---
id: q0079
question: "MVCC是什么？解决什么问题？"
category: java
tags: ["MVCC 多版本并发控制 Undo Log 快照读"]
difficulty: hard
created: 2026-07-23 10:20:32
source: 用户输入
---

# MVCC是什么？解决什么问题？

MVCC（多版本并发控制）是InnoDB核心机制，每个事务看到数据快照。解决：读写不冲突、一致性读（可重复读）、大幅提升并发性能。实现：Undo Log + Read View + 隐藏字段（DB_TRX_ID/DB_ROLL_PTR）。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `MVCC 多版本并发控制 Undo Log 快照读`
> 📊 **难度**: 进阶
> 📅 **归档时间**: 2026-07-23 10:20:32
