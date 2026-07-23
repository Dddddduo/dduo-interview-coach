---
id: q0072
question: "HTTPS用到的加密算法"
category: java
tags: ["HTTPS 加密 对称加密 非对称加密 AES TLS"]
difficulty: hard
created: 2026-07-23 10:20:24
source: 用户输入
---

# HTTPS用到的加密算法

三层体系：非对称加密（RSA/ECDHE）安全交换密钥、对称加密（AES/ChaCha20）加密数据、哈希算法（SHA256）验完整性。TLS 1.3废弃RSA密钥交换，强制ECDHE，握手从2-RTT降到1-RTT。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `HTTPS 加密 对称加密 非对称加密 AES TLS`
> 📊 **难度**: 进阶
> 📅 **归档时间**: 2026-07-23 10:20:24
