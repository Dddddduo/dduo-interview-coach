---
id: q0067
question: "TIME_WAIT可以调吗？"
category: java
tags: ["TIME_WAIT TCP 调优 端口耗尽"]
difficulty: medium
created: 2026-07-23 10:20:18
source: 用户输入
---

# TIME_WAIT可以调吗？

可以：tcp_fin_timeout（默认60s）、tcp_tw_reuse（复用TIME_WAIT连接）、tcp_tw_recycle（Linux 4.12后移除）。风险：缩短TIME_WAIT可能导致最后一个ACK无法重传。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `TIME_WAIT TCP 调优 端口耗尽`
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-07-23 10:20:18
