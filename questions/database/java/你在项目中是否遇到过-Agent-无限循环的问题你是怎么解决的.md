---
id: q0153
question: "你在项目中是否遇到过 Agent 无限循环的问题？你是怎么解决的？"
category: java
tags: []
difficulty: medium
created: 2026-07-29 16:02:36
source: 用户输入
---

# 你在项目中是否遇到过 Agent 无限循环的问题？你是怎么解决的？

在OrbitQA星轨平台中遇到过Agent无限循环，原因包括工具重试死循环、目标漂移、思维反刍等。解决方案：三层防护——硬限制(Max Iterations+Timeout)、智能检测(Focused ReAct的Loop Detection+Early Stop)、优雅降级(Graceful Degradation)。

---

> 📋 **分类**: Java
> 🏷️ **标签**: 
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-07-29 16:02:36
