---
id: q0097
question: "MySQL慢查询解决思路"
category: java
tags: ["慢查询 EXPLAIN SQL优化 数据库调优"]
difficulty: medium
created: 2026-07-23 10:20:56
source: 用户输入
---

# MySQL慢查询解决思路

排查步骤：开慢查询日志（slow_query_log=ON）→设置阈值（long_query_time=1）→mysqldumpslow分析→EXPLAIN分析（type/key/rows/Extra）→针对性优化（索引/SQL改写/分表）。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `慢查询 EXPLAIN SQL优化 数据库调优`
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-07-23 10:20:56
