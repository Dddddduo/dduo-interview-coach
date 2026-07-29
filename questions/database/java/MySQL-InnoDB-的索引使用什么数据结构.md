---
id: q0143
question: "MySQL InnoDB 的索引使用什么数据结构"
category: java
tags: []
difficulty: medium
created: 2026-07-27 22:21:03
source: 用户输入
---

# MySQL InnoDB 的索引使用什么数据结构

B+树。非叶子节点只存键值做路由，叶子节点存完整数据(聚簇索引)或主键值(二级索引)。扇出高，三层可存数亿条

---

> 📋 **分类**: Java
> 🏷️ **标签**: 
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-07-27 22:21:03
