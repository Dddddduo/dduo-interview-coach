---
id: q0080
question: "MySQL的锁有哪些？"
category: java
tags: ["MySQL 锁 行锁 间隙锁 临键锁 意向锁"]
difficulty: hard
created: 2026-07-23 10:20:40
source: 用户输入
---

# MySQL的锁有哪些？

按粒度：表级锁（MyISAM/DDL）、行级锁（InnoDB默认）、间隙锁（Gap Lock防幻读）、临键锁（Next-Key Lock=行锁+间隙锁）。按模式：共享锁S Lock（读锁）、排他锁X Lock（写锁）、意向锁（表级锁表示准备获取行锁）。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `MySQL 锁 行锁 间隙锁 临键锁 意向锁`
> 📊 **难度**: 进阶
> 📅 **归档时间**: 2026-07-23 10:20:40
