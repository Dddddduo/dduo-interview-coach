---
id: q0008
question: "介绍一下你的 AI 相关项目"
category: behavioral
tags: ["AI项目", "RAG", "LLM应用", "Spring AI", "Prompt Engineering"]
difficulty: medium
created: 2026-07-04 16:30:00
source: 面经助手-20260704
---

# 介绍一下你的 AI 相关项目

---

### 🧠 联想记忆法

**记忆口诀 / 联想**

> **"AI-PIER" 五维记忆模型**
>
> **A** — Architecture（架构）：前端 + 后端 + AI网关 + 向量库
> **I** — Integration（集成）：Spring AI / LangChain 框架对接LLM
> **P** — Pipeline（流水线）：Embedding → Retrieval → Augmentation → Generation
> **I** — Index（索引）：向量索引（Vector Index）+ 关键词索引（Keyword Index）双路召回
> **E** — Evaluation（评估）：ROUGE-L / BLEU / Answer Relevance 量化指标
> **R** — Refinement（优化）：Prompt Tuning + 模型微调 + 缓存策略

**记忆原理**

将整个AI项目拆解为六个关键维度，每个维度提取一个核心关键字，组成"AIPIER"（"AI的根基"）这一便于记忆的单词。面试时按照这个单词顺序展开，可以确保不遗漏任何重要模块，同时体现出系统性思维。

**关联知识**

| 记忆点 | 关联技术栈 |
|--------|-----------|
| Architecture | 前后端分离架构、Docker容器化、Kubernetes编排 |
| Integration | Spring AI、LangChain、OpenAI API、Azure OpenAI |
| Pipeline | RAG流水线、Embedding Model、Chunking策略 |
| Index | FAISS、Pinecone、Milvus、Elasticsearch |
| Evaluation | RAGAS框架、TruLens、人工评估标注 |
| Refinement | Prompt Engineering、LoRA微调、KV Cache优化 |

---

### 📖 深度解答

#### 1. 项目概述

该项目的技术名称为 **"企业级智能知识问答平台 (Enterprise Intelligent Q&A Platform)"**，基于 **Spring AI** 框架构建，底层对接 **OpenAI GPT-4o** 及 **Azure OpenAI Service**。项目采用 **RAG（Retrieval-Augmented Generation，检索增强生成）** 架构模式，旨在解决企业内部文档检索效率低、知识复用困难的问题。

该系统支持用户通过自然语言（Natural Language）对技术文档、产品手册、会议纪要等非结构化数据（Unstructured Data）进行智能检索与问答。核心能力覆盖了文档上传与解析、向量化存储、语义检索（Semantic Search）、大模型生成回复（LLM Generation）以及对话历史管理（Conversation Memory）。

**技术栈总览：**
- 后端框架：Spring Boot 3.2 + Spring AI 0.8.x
- AI框架层：LangChain4j（Java生态）、LangChain（Python原型验证）
- 向量数据库：Pinecone Serverless + Redis Stack（本地缓存）
- 嵌入模型（Embedding Model）：text-embedding-3-small（1536维）
- 大语言模型：GPT-4o / GPT-4-turbo（Chat Completion API）
- 前端：React 18 + TypeScript + Ant Design Pro
- 部署：Docker + Kubernetes（AWS EKS）

#### 2. 核心技术

##### 2.1 LLM 调用（Chat Completion）

核心通过 Spring AI 的 `ChatClient` 封装 OpenAI Chat Completion API，支持流式输出（Streaming）与同步输出两种模式。

```java
// Spring AI ChatClient 调用示例
@Autowired
private ChatClient chatClient;

public Flux<String> streamAnswer(String question, List<Document> contexts) {
    String prompt = buildPrompt(question, contexts);
    return chatClient.prompt(prompt)
            .stream()
            .content();
}

private String buildPrompt(String question, List<Document> contexts) {
    StringBuilder sb = new StringBuilder();
    sb.append("You are a professional technical assistant. ");
    sb.append("Answer the question based strictly on the provided context.\n\n");
    sb.append("Context:\n");
    for (int i = 0; i < contexts.size(); i++) {
        sb.append("[").append(i + 1).append("] ")
          .append(contexts.get(i).getContent()).append("\n");
    }
    sb.append("\nQuestion: ").append(question).append("\nAnswer:");
    return sb.toString();
}
```

##### 2.2 Prompt Engineering

采用三层 Prompt 模板结构：

1. **System Prompt（系统提示词）**：定义AI的角色定位、行为边界和输出规范
2. **Context Template（上下文模板）**：将检索结果按固定格式注入
3. **User Query Template（用户查询模板）**：支持few-shot示例注入

```java
// Prompt Template 示例
public String buildSystemPrompt(String userRole) {
    return """
        You are an enterprise knowledge assistant.
        Your role: supporting %s in daily Q&A.
        Rules:
        - If the answer cannot be found in the context, say "I cannot find relevant information."
        - Always cite the source document index (e.g., [1], [2]).
        - Answer in the same language as the question.
        - Keep responses concise, maximum 300 tokens.
        """.formatted(userRole);
}
```

##### 2.3 RAG（检索增强生成）

RAG流水线分为三个阶段：

**阶段一：文档预处理（Document Ingestion）**
```
原始PDF/Word → 文本提取 → 段落分割（Chunking）→ Embedding → 入库
```
- 分割策略（Chunking Strategy）：采用 **RecursiveCharacterTextSplitter**，chunk_size=512，chunk_overlap=128
- 嵌入（Embedding）：调用 `text-embedding-3-small` 生成1536维向量

```python
# LangChain 文档预处理 Python 原型代码
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=128,
    separators=["\n\n", "\n", "。", "，", " ", ""]
)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

chunks = text_splitter.split_documents(raw_documents)
vectors = embeddings.embed_documents([c.page_content for c in chunks])
```

**阶段二：检索（Retrieval）**
```
用户查询 → Query Embedding → 向量相似度搜索（Cosine Similarity）→ Top-K 召回 → 重排序
```
- 检索方式：向量召回（Vector Search）+ 关键词召回（Keyword Search）的混合检索（Hybrid Search）
- Top-K 参数：K=5（检索），重排序后取 Top-3
- 重排序模型（Re-ranker）：BAAI/bge-reranker-v2-m3

**阶段三：生成（Generation）**
```
检索结果 + 原始查询 → Prompt组装 → LLM调用 → 结构化输出
```

##### 2.4 Vector Store（向量存储）

选择 **Pinecone** 作为主向量数据库。Schema设计如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 文档块唯一标识 |
| vector | float[] | 1536维嵌入向量 |
| content | string | 原始文本内容 |
| metadata.source | string | 来源文档路径 |
| metadata.chunk_index | int | 块序号 |
| metadata.doc_type | string | 文档类型（PDF/DOCX/MD） |

#### 3. 功能模块

**模块一：智能问答（Intelligent Q&A）**
- 支持连续多轮对话，基于 `ConversationBufferWindowMemory` 维护最近5轮上下文
- 流式输出（Server-Sent Events, SSE），首字延迟低于800ms
- 支持问题追问澄清（Clarification）和主动建议（Suggestion）

**模块二：文档分析（Document Analysis）**
- 批量上传支持：PDF、DOCX、Markdown、TXT 格式
- 自动标签提取（Auto Tagging）：基于 LLM 提取文档关键词和摘要
- 文档版本管理：基于 Git LFS 存储原始文件

**模块三：结构化输出（Structured Output）**
- 采用 `StructuredOutputConverter` 将 LLM 输出映射为 Java POJO

**模块四：对话记忆（Conversation Memory）**
- 短期记忆：基于内存的滑动窗口（5轮）
- 长期记忆：基于 Redis 持久化，按 sessionId 隔离
- 总结记忆（Summary Memory）：长对话自动摘要压缩

#### 4. 技术架构图描述

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │     │   AI Gateway   │     │  Model Service │
│  (React 18)  │────▶│  (Spring AI)   │────▶│  (OpenAI API)  │
│  Ant Design  │◀────│  Rate Limiter  │◀────│  GPT-4o/GPT-4  │
└─────────────┘     │  Auth Filter   │     └──────┬───────┘
        │           │  Load Balance  │            │
        │           └───────┬────────┘            │
        │                   │                     │
        ▼                   ▼                     ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  CDN/OSS    │     │  Vector Store │     │  Embedding    │
│  Static     │     │  (Pinecone)   │     │  Service      │
└─────────────┘     └──────────────┘     └──────────────┘
```

**层级说明：**

- **接入层**：Nginx 反向代理 + HTTPS 终止 + 限流（Rate Limiting），单用户 QPS 上限为 10
- **应用层**：Spring Boot 应用集群，水平扩展至 4 个 Pod，基于 Kubernetes HPA（Horizontal Pod Autoscaler）进行弹性伸缩
- **AI网关层**：统一管理 API Key 轮转、请求路由、模型降级（Model Fallback，GPT-4o 降级至 GPT-4-turbo）、Token 用量审计
- **向量检索层**：Pinecone Serverless 按量付费，配合 Redis 本地缓存热点查询，缓存命中率为 42%
- **存储层**：PostgreSQL（用户数据、对话记录）、OSS（原始文档）、Pinecone（向量索引）

#### 5. 遇到的挑战

**挑战一：模型幻觉（Hallucination）**
- 问题：当检索结果不相关时，LLM 仍会"编造"答案
- 方案：引入 **Confidence Threshold（置信度阈值）**，当向量相似度低于 0.75 时，系统返回"无法确认相关信息，请咨询领域专家"
- 效果：幻觉率从 12.3% 降至 2.1%

**挑战二：Token 限制（Token Limitation）**
- 问题：长文档上下文超出 128K Token 窗口
- 方案：**滑动窗口分块摘要（Sliding Window Chunk Summarization）**，对超长文档先做分层摘要再检索
- 效果：支持单文档 500 页以上，召回覆盖率 89%

**挑战三：响应速度（Response Latency）**
- 问题：RAG 全链路延迟达 5-8 秒
- 方案：引入 **Prefetch + Cache** 机制，热门文档提前加载 Embedding；采用 **Semantic Cache（语义缓存）**，相似查询直接返回缓存结果
- 效果：P50 延迟从 6.2s 降至 1.8s，P99 延迟降至 4.5s

**挑战四：成本控制（Cost Management）**
- 问题：GPT-4o Token 消耗导致 API 成本过高
- 方案：实施 **Token Budget 分级策略**——简单查询走 GPT-4-mini，复杂推理走 GPT-4o；对 Embedding 结果做本地缓存
- 效果：月度 API 成本降低 47%，月均节省约 $2,800

#### 6. 实际效果与量化指标

| 指标 | Baseline | 优化后 | 提升幅度 |
|------|----------|--------|----------|
| 答案准确率 (Answer Accuracy) | 72.4% | 91.3% | +18.9pp |
| 幻觉率 (Hallucination Rate) | 12.3% | 2.1% | -10.2pp |
| 首字响应延迟 (TTFT) | 2.8s | 0.7s | -75% |
| 用户满意度 (CSAT) | 3.8/5.0 | 4.6/5.0 | +0.8 |
| 知识利用率 (Knowledge Utilization) | 34% | 78% | +44pp |
| 日均查询量 (Daily Queries) | 1,200 | 8,500 | +608% |

该系统上线后在企业内部覆盖 3 个部门、约 2,000 名活跃用户，累计处理查询量超过 50 万次，知识检索平均耗时从 15 分钟人工查找降至 1.8 秒自动回复。

---

### 🗺️ 回答思路

#### 答题逻辑框架

采用 **STAR-S 扩展模型**（Situation — Task — Action — Result — System）：

1. **Situation（背景）**：企业内部知识碎片化，检索效率低
2. **Task（任务）**：构建统一的 AI 问答平台
3. **Action（行动）**：采用 RAG 架构 + Spring AI 框架
4. **Result（结果）**：量化指标展示（准确率、延迟、成本）
5. **System（系统思维）**：技术选型考虑、架构设计取舍、未来演进方向

#### 重点得分点

按权重排序：

| 得分点 | 权重 | 考察能力 |
|--------|------|----------|
| RAG 流水线完整理解 | ★★★★★ | AI系统工程能力 |
| 量化指标呈现 | ★★★★★ | 数据驱动思维 |
| 代码示例 | ★★★★☆ | 工程实现能力 |
| 挑战与解决方案 | ★★★★☆ | 问题解决能力 |
| 架构设计描述 | ★★★★☆ | 系统设计能力 |
| Token/成本策略 | ★★★☆☆ | 工程落地意识 |

#### 常见误区

1. **只谈概念不谈代码**：面试官期望看到真实的工程实现，而不仅仅是"我用了RAG"这种方案描述
2. **缺乏量化指标**："效果很好"是无效表达，必须给出可衡量的数据
3. **忽略挑战和失败**：只说成功经验显得不真实，展示解决问题的过程更有说服力
4. **技术栈过于堆砌**：列出大量技术名词但不说明选型理由和取舍，会给面试官"纸上谈兵"的印象
5. **忽视非功能性需求**：只讲功能模块，不提及延迟、高可用、安全性、成本等工程要素

#### 时间分配建议（5分钟回答）

| 阶段 | 时长 | 内容 |
|------|------|------|
| 开场定位 | 30秒 | 一句话概括项目名称和定位 |
| 项目概述 | 45秒 | 技术栈、团队规模、受众 |
| 核心技术 | 90秒 | RAG 流水线 + 代码示例 |
| 挑战与方案 | 60秒 | 选2-3个最亮眼的挑战 |
| 量化成果 | 45秒 | 核心指标 + 提升幅度 |
| 总结与延伸 | 30秒 | 一句话总结 + 未来规划 |

#### 过渡话术

**从概述过渡到技术细节：**
> "以上是项目的整体定位，接下来聚焦在核心技术实现上。我们的核心架构是 RAG 模式，下面我按 Retrieval 和 Generation 两个阶段来说明。"

**从技术细节过渡到挑战：**
> "以上是系统的主要功能设计。在实际落地过程中，我们遇到了几个关键挑战——模型幻觉、Token 限制和响应延迟。我想重点分享解决这些问题的方法。"

**结尾总结话术：**
> "总结来说，这个项目完整覆盖了从文档接入到智能问答的 RAG 全链路，在准确率、延迟和成本三个核心维度上都达到了预期指标。后续的演进方向是引入多模态支持（Multimodal）和 Agent 化的工作流编排（Agentic Workflow）。"

---

> **分类**: 行为面试
> **标签**: `AI项目` `RAG` `LLM应用` `Spring AI` `Prompt Engineering`
> **难度**: 中级
> **归档时间**: 2026-07-04 16:30:00
