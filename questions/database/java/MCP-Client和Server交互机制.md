---
id: q0111
question: "MCP Client和Server交互机制"
category: java
tags: ["MCP AI Agent 工具调用 JSON-RPC"]
difficulty: hard
created: 2026-07-23 10:21:19
source: 用户输入
---

# MCP Client和Server交互机制

MCP（Model Context Protocol）是Anthropic开放协议，让AI Agent标准化调用外部工具。交互：Initialize（Client请求，Server返回tools/resources/prompts）→工具调用（tools/call）→资源读取→提示获取。传输：STDIO（进程通信）、HTTP+SSE（远程通信）。

---

> 📋 **分类**: Java
> 🏷️ **标签**: `MCP AI Agent 工具调用 JSON-RPC`
> 📊 **难度**: 进阶
> 📅 **归档时间**: 2026-07-23 10:21:19
