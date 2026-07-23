---
id: q0068
question: "高并发频繁TCP握手挥手问题"
category: java
tags: ["TCP 高并发 连接池 TIME_WAIT 长连接"]
difficulty: hard
created: 2026-07-23 10:20:24
source: 用户输入
---

# 高并发频繁TCP握手挥手问题

问题：TIME_WAIT堆积耗尽端口、三次握手延迟（1.5 RTT）、内核态切换开销、SYN Flood风险。解决方案：连接池、HTTP Keep-Alive/HTTP2多路复用、WebSocket长连接、tcp_tw_reuse、调整TIME_WAIT上限。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `TCP 高并发 连接池 TIME_WAIT 长连接`
> 📊 **难度**: 进阶
> 📅 **归档时间**: 2026-07-23 10:20:24
