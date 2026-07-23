---
id: q0074
question: "TCP粘包及解决方式"
category: java
tags: ["TCP 粘包 半包 Netty 网络编程"]
difficulty: medium
created: 2026-07-23 10:20:32
source: 用户输入
---

# TCP粘包及解决方式

TCP是流式协议不维护消息边界，多个包可能粘在一起。三种解决：定长（固定字节数）、分隔符（如\n）、长度前缀（TLV，最常用）。Netty用LengthFieldBasedFrameDecoder处理。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `TCP 粘包 半包 Netty 网络编程`
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-07-23 10:20:32
