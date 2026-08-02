---
id: q0182
question: "Function Calling 是怎么设计的？"
category: java
tags: []
difficulty: medium
created: 2026-08-02 09:41:22
source: 用户输入
---

# Function Calling 是怎么设计的？

# Function Calling 是怎么设计的？

## 🧠 联想记忆法

**核心口诀："一张菜单，两句话点单，三笔回账，四道保险"。**

把 Function Calling 想象成给 AI 配一个"点外卖"的完整流程，一次记住全链路：

1. **菜单（Schema 函数声明）**：把每个工具写成菜单项——菜名（`name` 函数名）、口味介绍（`description` 描述）、可选配料（`parameters` 参数 JSON Schema）。模型看菜单，不进后厨。
2. **点单（tool_call 工具调用指令）**：模型只输出一张"小票"——点了哪道菜（`function.name`）、要什么配料（`function.arguments` 参数 JSON）。**关键记忆锚点：模型只点菜，永远不做饭**——执行权 100% 在应用侧。
3. **回账（结果回填）**：应用执行完把"菜品"（工具结果）端回给模型（`role: "tool"` 消息，带 `tool_call_id` 对账），模型尝一口再决定继续点还是上齐了（输出最终答案）。
4. **四道保险（工程护栏）**：后厨白名单（工具注册与权限）、验单（参数校验）、限时（超时与最大步数）、防投毒（工具输出当数据不当指令）。

第二个联想钩子，区分两个高频混淆概念：**ReAct（Reasoning+Acting，思考-行动-观察循环）是"工作流程"，Function Calling 是流程里"行动"这一步的"标准协议"**。FC ⊂ ReAct 的一个动作，但 FC 也可独立用于单步任务。

## 📖 深度解答

## 1. 核心概念

**Function Calling（函数调用，业界也常称 Tool Calling 工具调用）**是 LLM（Large Language Model，大语言模型）应用层的一项能力与协议：把可执行的外部工具以结构化声明暴露给模型，模型**不真正执行任何函数**，而是输出一段结构化 JSON——`tool_call`（工具调用指令），包含函数名（`function.name`）与参数（`function.arguments`，本身是 JSON 字符串）。真正执行发生在应用程序侧，执行结果再以消息形式回填给模型，驱动多轮推理直至给出最终答案。

三个必须讲透的本质点：

- **决策与执行分离**：模型是"决策者"，只负责把自然语言翻译成结构化的动作指令；应用是"执行者"。这是 Function Calling 区别于"让模型直接输出文本再正则解析"的根本优势——输出受约束（可校验、可并行、可回滚），而不是靠字符串匹配猜。
- **它解决什么问题**：模型知识有截止日期、没有实时数据、无法操作外部系统（数据库、HTTP API、内部服务）。Function Calling 就是把 LLM 的"大脑"接到应用的"手脚"上。
- **与 ReAct 的关系**：ReAct（思考-行动-观察循环，源于 Yao et al., 2022）是 Agent 的经典范式——Thought（思考）→ Action（行动）→ Observation（观察）循环往复。Function Calling 是其中 **Action 一步的工程化实现**：用受控的 JSON 协议替代自由文本动作，让"行动"可解析、可校验、可并行。因此，一个基于 Function Calling 的多轮 Agent 循环，本质上就是一个 ReAct 循环。

## 2. 底层原理

**能力来源（训练层）**：模型的函数调用能力来自专门的指令微调（instruction tuning）——训练数据里包含大量"给定 tools 声明 → 输出对应 JSON 调用"的样本，模型从而学会理解 Schema 并产出合规的 JSON。Schema 在推理时本质上是注入 System Message 的一段结构化描述文本。

**生成机制（推理层）**：底层仍是 next-token prediction（下一个词预测），模型自回归地"写"出 JSON。工程上为提高可靠性，部分推理引擎会对函数名做受约束解码（constrained decoding）或对参数部分做 JSON grammar 约束，保证产物可解析；即使如此，解析失败仍需兜底（重试或回传错误让模型修正）。

**消息协议（协议层）**——这是面试必画的时序图：

```
user(问题) → model 返回 assistant 消息(含 tool_calls)
→ 应用解析并执行函数 → 追加 role="tool" 消息(带 tool_call_id，OpenAI 风格)
→ 模型看到结果继续生成 → 直至输出无 tool_calls 的最终答案
```

Claude 协议略有差异（`tool_use` / `tool_result` content block），但循环语义一致：**每执行一次工具，对话里就多两条消息（assistant 的调用 + tool 的回执），上下文随之增长**——这也是 Agent 长任务容易爆上下文的根源。

## 3. 实践应用

设计一个完整的 Function Calling 系统，六个要点缺一不可：

**(a) 函数声明 Schema**：`name`（唯一函数名）+ `description`（语义描述——**决定模型选工具准确率的关键因素**）+ `parameters`（JSON Schema：类型、必填、`additionalProperties: false` 拒绝多余参数）。描述写得像"说明书"而非"字段列表"，效果天差地别。

**(b) 工具注册与权限**：工具采用注册制而非模型自由调用——应用侧维护注册表 + 白名单；敏感工具（删数据、发消息、支付）必须加权限校验或人工二次确认。

**(c) 参数校验与反序列化**：`arguments` 是 JSON 字符串，需反序列化 + 按 Schema 校验（类型、必填、枚举、长度），非法参数直接拒绝并回传结构化错误，而不是带着脏数据执行。

**(d) 执行结果回填**：工具输出转字符串，以 `tool` 角色消息带 `tool_call_id` 回填，继续多轮。回填内容要裁剪（工具输出可能很大，做摘要/截断防爆上下文）。

**(e) 异常处理**：工具抛异常时不裸传堆栈，回传结构化 error；支持重试（注意幂等性）或降级（切换备用工具、或坦诚告知用户失败）。

代码示例一（OpenAI 风格，完整循环）：

```python
import json
from openai import OpenAI

client = OpenAI()

# ===== 1. 函数声明 Schema：给模型的"菜单"（模型只读不执行）=====
tools = [
    {
        "type": "function",
        "function": {
            "name": "query_weather",
            "description": "查询指定城市的实时天气。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 北京"}
                },
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    }
]

messages = [{"role": "user", "content": "北京今天天气怎么样？"}]

# ===== 2. ReAct 式循环：思考 -> 行动 -> 观察 -> 再思考 =====
MAX_STEPS = 5  # 死循环防护：最大步数限制
for step in range(MAX_STEPS):
    resp = client.chat.completions.create(
        model="gpt-4o", messages=messages, tools=tools
    )
    msg = resp.choices[0].message
    messages.append(msg)          # assistant 消息可能携带 tool_calls

    if not msg.tool_calls:        # 模型不再"点单" -> 输出最终答案
        break

    for tc in msg.tool_calls:     # 支持并行：一次返回多个 tool_call
        try:
            args = json.loads(tc.function.arguments)  # 反序列化
            assert "city" in args, "缺少必填参数"       # 参数校验
            result = real_query_weather(args["city"]) # 白名单内才执行
        except Exception as e:
            result = {"error": str(e)}                # 异常兜底回传

        # ===== 3. 结果回填：tool 消息携带 tool_call_id 继续多轮 =====
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(result, ensure_ascii=False),
        })

print(messages[-1].content)  # 最终自然语言回答
```

代码示例二（Spring AI 风格，对应简历背景）：

```java
// ===== 1. @Tool 注解声明：Spring AI 根据方法签名自动生成 JSON Schema =====
@Component
public class WeatherTools {
    @Tool(description = "查询指定城市的实时天气")
    public String queryWeather(@ToolParam(description = "城市名，如 北京") String city) {
        return weatherService.getWeather(city);  // 真实执行只发生在这里
    }
}

// ===== 2. 工具注册（白名单）+ 构建带记忆的 ChatClient =====
ChatClient client = ChatClient.builder(chatModel)
        .defaultTools(new WeatherTools())
        .defaultAdvisors(new MessageChatMemoryAdvisor(new InMemoryChatMemory()))
        .build();

// ===== 3. 一次调用即一个完整 ReAct 循环 =====
// 内部 ToolCallingManager 自动完成：解析 tool_call -> 反射执行 -> 结果回填 -> 继续追问
String answer = client.prompt("北京今天天气怎么样？").call().content();
```

（注：Spring AI 各小版本 API 略有差异，面试中讲清"注解声明 + 自动生成 Schema + 循环引擎"三层即可。）

我简历中 OrbitQA 的"域 Agent 基于 Spring AI 实现 ReAct 循环自主调用工具执行流水线"，本质就是上面这套：域 Agent 只注册本域工具，天然形成**工具分组 + 白名单**，Spring AI 的 ToolCallingManager 充当循环引擎（仅作背景，不展开细节）。

## 4. 深入思考

**工程化细节（按面试高频程度排序）：**

- **工具数量太多时如何选工具**：几十个工具全塞进 Prompt 既烧 Token 又稀释注意力。三种策略：① **few-shot 工具选择**——在提示词里给出"什么场景该调哪个工具"的示例，利用上下文学习；② **工具分组（namespace 化）**——按领域拆成多个域 Agent，每个 Agent 只暴露自己的小工具集；③ **工具检索路由**——对工具描述做向量检索，动态注入 Top-K 个候选工具。
- **并行工具调用**：OpenAI 支持一条回复返回多个 `tool_calls`，可批量查询合并往返；并行时每个参数独立校验，且要注意总上下文开销。
- **流式输出工具调用**：流式下 `tool_call` 是增量分片到达的（arguments 被切成 delta），需**累积拼接 JSON 字符串**，等 `finish_reason` 为 `tool_calls` 的事件后再统一执行，不能边收边执行。
- **工具调用超时**：单次执行设超时（如 5s），超时返回错误或走缓存；循环整体设最大步数（5~10 步）并限制单轮总 Token，防止"死循环烧钱"。

**安全（与"Prompt 注入防御"联动）：** ① 工具白名单——注册制，杜绝模型自由发明调用；② 参数注入校验——**工具的输出是"不可信数据"而非"指令"**：攻击者可能让网页/数据库内容携带"忽略之前的指令"等注入文本，绝不能把工具结果当 System 指令回传，只能作为 Observation 数据给模型参考，同时做好输出侧敏感信息过滤。

**常见坑（每个都要能对应解法）：**

1. **幻觉函数名**：模型可能编造不存在的工具 → 注册表校验，未知名工具回传"unknown tool"错误让它重选。
2. **参数类型错误/缺参**：Schema 校验不通过 → 把校验错误信息回传给模型，它通常能自纠（一次重试窗口）。
3. **死循环**：工具反复返回异常或模型反复调同一工具 → 最大步数 + 相似调用去重 + 熔断。
4. **arguments 解析失败**（被截断/非合法 JSON）→ 容错解析 + 提示重发。

**延伸视野**：Function Calling 是"协议"，而 **MCP（Model Context Protocol，模型上下文协议）** 是"工具分发的开放标准"——解决多 Agent、多客户端场景下工具注册、发现、调用的标准化问题，值得作为收尾的进阶话题。

## 🗺️ 回答思路

**答题逻辑框架（3-5 分钟口头回答）**

1. **一句话定性（30s）**："Function Calling 的本质是——模型输出结构化调用意图 JSON（tool_call，含函数名与参数），应用负责执行并回填结果。模型只决策，不执行。"
2. **协议层（1.5min）**：讲消息时序 `user → assistant(tool_calls) → tool(回执) → assistant(答案)`，并点明与 ReAct 的关系：FC 是 ReAct 循环中 Action 一步的标准化实现。
3. **工程层（1.5min）**：Schema 声明 → 注册白名单 → 参数校验 → 结果回填 → 异常兜底；附代码演示。
4. **升华层（1min）**：工具选择、并行、流式、超时、最大步数 + 安全（白名单/参数注入/输出当数据）+ 一个真实踩过的坑。
5. **收尾（30s）**：绑定简历 OrbitQA + 延伸 MCP。

**重点得分点（面试官 checklist）**

- 第一性原理讲对：**模型不执行函数，只输出 JSON**——这是最大的区分点。
- 能画出完整消息时序图并解释 `tool_call_id` 关联机制。
- 现场能写/复述 schema 和调用循环（双风格代码是超预期加分项）。
- 工程广度的四个关键词：工具选择、并行调用、流式拼接、最大步数。
- 安全意识：白名单 + 参数校验 + "工具输出是不可信数据"的 Prompt 注入联动。
- 概念辨析：FC 与 ReAct 的关系一句话讲清。

**常见误区（别踩）**

- ❌ 说成"模型执行函数"——执行永远在应用侧，讲错直接崩。
- ❌ 只讲"调 API"不提消息协议与多轮回填，显得只会用库。
- ❌ 把 FC 和 ReAct 混为一谈——一个是协议/一步，一个是循环范式。
- ❌ 忽略 `description` 的价值——它是选工具准确率的关键，也是工程细节的体现。
- ❌ 只谈功能不谈安全与死循环治理，暴露工程经验不足。

**时间分配建议**：定性 30s（10%）→ 概念+原理 1.5min（35%）→ 实践+代码 1.5min（35%）→ 工程化+安全+坑 1min（20%），全程控制在 4 分钟左右留出追问空间。

**过渡话术（背下来直接用）**

- 开场："先给一个最直观的理解——模型不会真的执行你的函数，它只是输出一张'调用小票'，执行的是我们的应用。"
- 从原理到实践："说完了协议层，再看工程上真正会踩的坑，我按'声明-注册-校验-回填-兜底'五个要点展开。"
- 从实践到升华："再拔高一层，当工具数量多起来，'选哪个工具'就比'怎么调用'更关键，常用三招：few-shot、分组、检索。"
- 收尾："回到我简历里的 OrbitQA，域 Agent 的做法正是把'工具分组 + 白名单 + ReAct 循环'落到 Spring AI 上；再往前看，MCP 正在把这些协议标准化，这也是我最近在跟进的方向。"

---

> 📋 **分类**: Java
> 🏷️ **标签**: 
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-08-02 09:41:22
