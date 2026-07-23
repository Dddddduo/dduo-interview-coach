---
id: q0085
question: "怎么判断SQL是否用到了索引？"
category: java
tags: ["EXPLAIN 索引 执行计划 SQL优化"]
difficulty: medium
created: 2026-07-23 10:20:40
source: 用户输入
---

# 怎么判断SQL是否用到了索引？

用EXPLAIN。关键字段：type（const>ref>range>index>ALL）、key（使用的索引名，NULL表示没走）、rows（扫描行数）、Extra（Using index=覆盖索引，Using filesort=文件排序）。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `EXPLAIN 索引 执行计划 SQL优化`
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-07-23 10:20:40
