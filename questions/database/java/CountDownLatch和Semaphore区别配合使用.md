---
id: q0042
question: "CountDownLatch和Semaphore区别，配合使用"
category: java
tags: ["JUC 并发 CountDownLatch Semaphore"]
difficulty: medium
created: 2026-07-23 10:19:47
source: 用户输入
---

# CountDownLatch和Semaphore区别，配合使用

CountDownLatch（倒计时门闩）和Semaphore（信号量）是Java并发包中的两种同步工具类。CountDownLatch允许线程等待直到其他线程的操作完成（计数器归零），不可重用。Semaphore控制同时访问资源的线程数量（许可证），可重用。两者可配合使用实现限流聚合。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `JUC 并发 CountDownLatch Semaphore`
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-07-23 10:19:47
