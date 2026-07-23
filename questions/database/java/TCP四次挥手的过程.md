---
id: q0066
question: "TCP四次挥手的过程"
category: java
tags: ["TCP 四次挥手 TIME_WAIT CLOSE_WAIT"]
difficulty: medium
created: 2026-07-23 10:20:18
source: 用户输入
---

# TCP四次挥手的过程

1. A发送FIN（FIN_WAIT_1）→2. B回复ACK（CLOSE_WAIT，A进FIN_WAIT_2）→3. B发送FIN（LAST_ACK）→4. A回复ACK（TIME_WAIT 2MSL）。TCP全双工需单独关闭每个方向。TIME_WAIT确保最后一个ACK能到达。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `TCP 四次挥手 TIME_WAIT CLOSE_WAIT`
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-07-23 10:20:18
