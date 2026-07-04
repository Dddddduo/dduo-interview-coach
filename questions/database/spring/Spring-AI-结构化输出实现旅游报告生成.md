---
id: q0004
question: "Spring AI 结构化输出实现旅游报告生成，将 AI 回复转为结构化价格对象，展开讲解"
category: spring
tags: ["Spring AI", "Structured Output", "BeanOutputConverter", "JSON Schema", "LLM", "POJO映射"]
difficulty: hard
created: 2026-07-04 14:40:00
source: 面经助手-20260704
---

# Spring AI 结构化输出实现旅游报告生成，将 AI 回复转为结构化价格对象

## 🧠 联想记忆法

**记忆口诀/联想**: "AI 说人话 → POJO 说结构话" — 把 LLM 的"散文"用 Spring AI 的 `BeanOutputConverter` "翻译"成 Java 对象，就像旅行社把散乱的价格信息填入标准化的 Excel 表格。

**记忆原理**: 
核心意象是"翻译官"——LLM 输出的是自然语言（如"机票 2000 元，酒店 800 元/晚"），Spring AI 的 `StructuredOutputConverter` 充当翻译官，将这段"散文"按照预定义的 JSON Schema（对应 Java POJO）重新组织成结构化的 `PriceInfo` 对象。记忆锚点是：**非结构化输入 → 结构化输出 = LLM 自由文本 → POJO 约束**。

**关联知识**:
- Jackson 的 `@JsonProperty` 注解映射 JSON → Java 对象，Spring AI 在此基础上增加了 LLM-aware 的 schema 生成和 prompt 注入
- Java 的 `Record` 类型（Java 14+）天然适合做不可变的数据传输对象（DTO, Data Transfer Object）
- 与传统的正则提取 JSON block 的方案对比：正则提取是"事后补救"，Spring AI Structured Output 是"事前约定"

---

## 📖 深度解答

### 1. 核心概念（是什么）

**Spring AI Structured Output（结构化输出）** 是 Spring AI 框架提供的一种机制，用于将大语言模型（Large Language Model, LLM）返回的非结构化自然语言文本，自动映射为预先定义的 Java POJO（Plain Old Java Object）或 Record 类型。

传统上，调用 LLM API 获取的是字符串文本（如 OpenAI 的 `choices[0].message.content`），开发者需要自行解析这段文本——提取 JSON 片段、处理格式异常、手动反序列化。Spring AI Structured Output 从根本上解决了这一问题：**在调用 LLM 之前就约定好输出格式，让 LLM 直接生成符合 JSON Schema 的结构化数据**，框架自动完成反序列化。

**核心价值**：
- 类型安全（Type Safety）：编译期即可确定输出类型，而非运行时字符串
- 消除样板代码（Boilerplate Elimination）：无需手动编写 JSON 提取和解析逻辑
- 一致性保证（Consistency Guarantee）：通过 prompt 工程 + schema 约束，大幅提升输出格式的稳定性

### 2. 底层原理（为什么）

Spring AI Structured Output 的底层实现遵循 **"Schema 注入 + 结构化解析 + 容错降级"** 的三层架构：

**第一层：Schema 注入（Prompt Engineering Layer）**
Spring AI 在发送给 LLM 的 prompt 中自动附加一段 **JSON Schema 描述**。例如，当目标类型是 `PriceInfo` 时，框架会生成类似以下的 schema 声明：

```
You MUST respond in JSON format following this schema:
{
  "type": "object",
  "properties": {
    "itemName": {"type": "string"},
    "amount": {"type": "number"},
    "currency": {"type": "string"},
    "date": {"type": "string"},
    "category": {"type": "string"}
  },
  "required": ["itemName", "amount", "currency"]
}
```

这一层利用了 LLM 的 **指令遵循能力（Instruction Following）**——现代 LLM（GPT-4、Claude 3 等）经过训练后能够高度可靠地按照指定格式输出 JSON。

**第二层：结构化解析（Parsing Layer）**
`BeanOutputConverter` 是核心类，其工作流程如下：

```
BeanOutputConverter.convert(text) 的调用链：
1. 接收 LLM 返回的原始字符串 text
2. 尝试从 text 中提取 JSON 块（查找第一个 { 和最后一个 })
3. 使用 Jackson ObjectMapper 反序列化为目标类型
4. 如果失败，尝试常见的 LLM 输出修复（如去除 markdown 代码块标记）
```

**第三层：容错降级（Fallback Layer）**
当 LLM 输出的格式不符合预期时，Spring AI 提供了多层防护：
1. **格式检测**：检测 JSON 结构完整性
2. **重试机制**：重新调用 LLM，附加"请确保输出符合 JSON 格式"的指令
3. **默认值降级**：在 POJO 中定义 `@JsonProperty(defaultValue = ...)` 或字段默认值

**设计哲学**：Spring AI 选择"约束 LLM"而非"事后解析"——与其费力处理混乱的输出，不如从一开始就让 LLM 输出规范格式。这体现了 **"Shift Left"（左移）** 的质量理念。

### 3. 实践应用（怎么用）

#### 3.1 定义结构化 POJO

```java
public record PriceInfo(
    @JsonProperty("item_name") String itemName,
    @JsonProperty("amount") BigDecimal amount,
    @JsonProperty("currency") String currency,
    @JsonProperty("date") String date,
    @JsonProperty("category") String category,
    @JsonProperty("description") String description
) {
    public static PriceInfo defaults() {
        return new PriceInfo("", BigDecimal.ZERO, "CNY", "", "", "");
    }
}

public record TravelReport(
    @JsonProperty("destination") String destination,
    @JsonProperty("trip_start") String tripStart,
    @JsonProperty("trip_end") String tripEnd,
    @JsonProperty("total_cost") BigDecimal totalCost,
    @JsonProperty("currency") String currency,
    @JsonProperty("items") List<PriceInfo> items
) {}
```

#### 3.2 配置 StructuredOutputConverter

```java
@Configuration
public class AiConfig {
    @Bean
    public StructuredOutputConverter<TravelReport> travelReportOutputConverter() {
        return new BeanOutputConverter<>(TravelReport.class);
    }
    
    @Bean
    public ChatClient chatClient(ChatModel chatModel) {
        return ChatClient.builder(chatModel).build();
    }
}
```

#### 3.3 完整调用链路

**Controller 层**：暴露 REST API，接收前端请求，调用 Service 层。
**Service 层**：构造 Prompt，调用 AI，通过 `BeanOutputConverter` 解析结构化结果，包含重试和降级逻辑。

#### 3.4 Prompt 设计

Prompt 设计是结构化输出成功的关键因素。必须在 System Prompt 中明确约束输出格式，并提供 JSON Schema 定义。

### 4. 深入思考（注意事项）

#### 异常处理矩阵

| 异常类型 | 原因 | 处理策略 |
|---------|------|---------|
| JsonParseException | LLM 输出非 JSON 文本 | 重试 + 加强 prompt 约束 |
| UnrecognizedPropertyException | 字段名不匹配 | 添加 `@JsonIgnoreProperties(ignoreUnknown = true)` |
| NumberFormatException | 金额格式错误 | 自定义反序列化器 + 默认值 |
| 空返回值 | AI 拒绝回答或 API 超时 | 重试 + Circuit Breaker |

#### 与传统方案对比

| 维度 | Spring AI Structured Output | 传统方案 |
|------|---------------------------|---------|
| 工作时机 | 调用前约束 | 调用后解析 |
| 类型安全 | 编译期检查 | 运行时操作 |
| 格式稳定性 | 高 | 低 |
| 维护成本 | 低 | 高 |

---

## 🗺️ 回答思路

### 答题逻辑框架

采用 **"问题 → 方案 → 原理 → 代码 → 对比"** 的五段式递进结构。

### 重点得分点

1. **Schema 注入机制**（30%）：Spring AI 如何自动将 POJO 转换为 JSON Schema
2. **异常处理策略**（25%）：重试、降级、默认值的完整思考
3. **代码实现完整度**（25%）：Controller → Service → AI 调用的完整链路
4. **Prompt 工程细节**（20%）：retry prompt 的差异化设计

### 常见误区

- "Structured Output 就是 JSON 解析"——实际上是 prompt 约束 + 结构化解析的组合
- "不需要异常处理"——LLM 的随机性意味着格式异常永远可能出现
- "所有字段必须映射"——使用 `@JsonIgnoreProperties(ignoreUnknown = true)`

### 时间分配建议

- 破题引入：30 秒
- 核心概念 + 底层原理：1 分 30 秒
- 代码示例：2 分钟
- Prompt 设计 + 异常处理：1 分钟
- 对比 + 追问应对：1 分钟
- **总计**：约 6 分钟

---

> **分类**: Spring 框架
> **标签**: `Spring AI` `Structured Output` `BeanOutputConverter` `JSON Schema`
> **难度**: 进阶
> **归档时间**: 2026-07-04 14:40
