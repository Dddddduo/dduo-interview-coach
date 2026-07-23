---
id: q0114
question: "RAG检索不准确的原因"
category: java
tags: ["RAG 检索质量 分块 Embedding 重排序"]
difficulty: hard
created: 2026-07-23 10:21:19
source: 用户输入
---

# RAG检索不准确的原因

五大原因：分块策略不当（过大/过小/无重叠）、Embedding质量不足（模型不匹配/多语言差/术语生僻）、检索召回不足（Top K小/无关键词/无重排序）、Query问题（过短/表达差异/含噪音）、元数据过滤不足。优化：Query改写、混合检索、重排序、语义分块。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `RAG 检索质量 分块 Embedding 重排序`
> 📊 **难度**: 进阶
> 📅 **归档时间**: 2026-07-23 10:21:19
