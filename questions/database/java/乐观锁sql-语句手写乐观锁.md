---
id: q0043
question: "乐观锁，sql 语句手写乐观锁"
category: java
tags: ["乐观锁 并发控制 版本号 CAS"]
difficulty: medium
created: 2026-07-23 10:19:48
source: 用户输入
---

# 乐观锁，sql 语句手写乐观锁

乐观锁（Optimistic Locking）通过版本号机制实现并发控制，在表中增加version字段，更新时检查version是否变化。SQL: UPDATE account SET balance=balance-50, version=version+1 WHERE id=1 AND version=3。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `乐观锁 并发控制 版本号 CAS`
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-07-23 10:19:48
