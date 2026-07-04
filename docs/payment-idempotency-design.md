# 支付消息幂等设计深度解析

> **消费者收到重复的支付消息如何处理**

---

## 文档信息

| 条目 | 内容 |
|------|------|
| **题目标题** | 消费者收到重复的支付消息如何处理（幂等设计） |
| **生成日期** | 2026-07-04 |
| **文档版本** | v1.0 |
| **技术标签** | `幂等设计` `分布式系统` `支付系统` `高可用` `最终一致性` |
| **关键词** | Idempotency, 唯一键, 乐观锁, 状态机, Outbox Pattern, 防重放 |

---

## 目录（Table of Contents）

- [1. 联想记忆法](#1-联想记忆法)
  - [1.1 核心口诀](#11-核心口诀)
  - [1.2 场景联想：电梯按钮](#12-场景联想电梯按钮)
  - [1.3 核心方案关键词链（PAST）](#13-核心方案关键词链past)
  - [1.4 三层校验记忆法](#14-三层校验记忆法)
  - [1.5 中英对照挂钩](#15-中英对照挂钩)
- [2. 深度解答](#2-深度解答)
  - [2.1 核心概念：幂等的本质与支付场景的特殊性](#21-核心概念幂等的本质与支付场景的特殊性)
  - [2.2 底层原理：四大幂等方案的技术拆解](#22-底层原理四大幂等方案的技术拆解)
    - [方案 1：支付单号（Payment ID）作为唯一键](#方案-1支付单号payment-id作为唯一键)
    - [方案 2：前置流水表 + Outbox Pattern](#方案-2前置流水表--outbox-pattern)
    - [方案 3：支付网关侧的幂等](#方案-3支付网关侧的幂等)
    - [方案 4：Token 机制（防重放）](#方案-4token-机制防重放)
  - [2.3 实践应用：完整代码实现](#23-实践应用完整代码实现)
    - [3.1 支付入口 Service](#31-支付入口-service)
    - [3.2 支付回调处理](#32-支付回调处理)
  - [2.4 深入思考：数据库 + 缓存双写一致性](#24-深入思考数据库--缓存双写一致性)
- [3. 回答思路](#3-回答思路)
  - [3.1 破题：从"为什么会有重复"切入](#31-破题从为什么会有重复切入)
  - [3.2 回答节奏：由底向上](#32-回答节奏由底向上)
  - [3.3 代码落地关键考点](#33-代码落地关键考点)
  - [3.4 加分项](#34-加分项)
  - [3.5 中英术语矩阵](#35-中英术语矩阵)
- [4. 文档信息](#4-文档信息)

---

---

## 1. 联想记忆法

### 1.1 核心口诀

> **"一锁二查三更新，流水单号防重门"**

### 1.2 场景联想（电梯按钮）

电梯按钮按下一次会亮，反复按同一个按钮，电梯依然只响应一次。这就是**幂等**——同一个操作多次执行，结果不变。支付系统的幂等设计，本质就是给每个支付请求安装一个"电梯按钮"。

### 1.3 核心方案关键词链（PAST）

| 字母 | 关键词 | 说明 |
|------|--------|------|
| **P** | Payment ID | 支付单号作为唯一键 |
| **O** | Outbox Pattern | 前置流水表 |
| **A** | API Idempotency | 支付网关侧幂等 |
| **T** | Token Mechanism | Token 防重放 |

> 注：PAST 四个字母串联起幂等设计的四大核心方案，便于面试时逐层展开。

### 1.4 三层校验记忆法

| 层级 | 位置 | 机制 | 作用 |
|------|------|------|------|
| **第一层** | 数据库 | 唯一索引兜底 | Insert 失败即重复 |
| **第二层** | 应用 | 查流水表判定状态 | 状态机转移防乱序 |
| **第三层** | 网关 | `out_trade_no` 天然幂等 | 重复请求直接返回 |

### 1.5 中英对照挂钩

| 中文 | English |
|------|---------|
| 幂等 | Idempotent |
| 唯一键 | Unique Key |
| 流水表 | Transaction Log |
| 乐观锁 | Optimistic Lock |
| 状态机 | State Machine |

---

---

## 2. 深度解答

### 2.1 核心概念：幂等的本质与支付场景的特殊性

**幂等（Idempotency）** 源自数学，指一个操作执行一次与执行多次产生相同的结果。在分布式系统中，幂等是保证 **"至少一次交付"（At-Least-Once Delivery）** 语义下数据最终一致的核心手段。

支付场景是幂等设计最严苛的战场，原因有三：

1. **资金敏感性**：重复扣款直接导致资损，不可接受。
2. **消息传递的"至少一次"特性**：MQ 重试、网络重传、用户重复点击都会导致同一支付请求被多次投递。
3. **分布式环境的不可靠性**：支付网关超时后重试，无法区分是"网关处理中"还是"网关已处理但响应丢失"。

因此，支付幂等的目标不是"阻止重复请求到达"，而是**让重复请求的处理结果与首次完全相同，且不产生副作用**。

### 2.2 底层原理：四大幂等方案的技术拆解

---

#### 方案 1：支付单号（Payment ID）作为唯一键

**原理**：数据库唯一索引（Unique Index）是最底层的防重屏障。当两次 Insert 使用相同的主键或唯一键时，第二次 Insert 因违反唯一约束而失败，数据库直接返回 Duplicate Entry 错误。

```sql
-- 支付流水表核心设计
CREATE TABLE payment_transaction (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    payment_id    VARCHAR(64) NOT NULL COMMENT '全局唯一支付单号',
    order_id      VARCHAR(64) NOT NULL COMMENT '订单号',
    amount        DECIMAL(12,2) NOT NULL,
    status        TINYINT NOT NULL DEFAULT 0 COMMENT '0=处理中, 1=成功, 2=失败',
    version       INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
    created_at    DATETIME NOT NULL,
    updated_at    DATETIME NOT NULL,
    UNIQUE INDEX  uk_payment_id (payment_id),
    INDEX         idx_order_id (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**支付单号的生成**：必须全局唯一且携带业务语义。推荐方案：

- **雪花算法（Snowflake）**：64 位长整型，结合时间戳 + 机器 ID + 序列号，高性能且有序。
- **业务前缀 + UUID 短值**：如 `PAY20260704001_${UUID短串}`，兼具可读性和唯一性。

**数据流**：

```
请求到达 → INSERT INTO payment_transaction (payment_id, ...)
    ├── 成功 → 继续业务处理
    └── 唯一键冲突 → 查询已有记录 → 直接返回已有结果
```

---

#### 方案 2：前置流水表 + Outbox Pattern

**原理**：先写本地流水表（状态 = 处理中），再调支付网关。流水表作为 **"可靠事件日志"（Event Log）**，保证支付请求不丢失、不重复。

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   业务请求     │────>│  支付流水表(状态=0) │────>│  支付网关    │
│ (含PaymentID) │     │ (Outbox/前置写)  │     │ (微信/支付宝) │
└──────────────┘     └──────────────────┘     └──────────────┘
                              │                        │
                              │                        │
                              ▼                        ▼
                     ┌──────────────────────────────────────────┐
                     │   支付网关回调 → 更新流水状态为成功/失败     │
                     │   → 更新订单状态                            │
                     └──────────────────────────────────────────┘
```

**核心优势**：流水表是支付请求的 **"单次写入锚点"**。无论下游调用多少次，流水表的第一条记录就是 **"圣典"（Source of Truth）**，后续请求通过唯一索引被拒后，只需查询流水表状态即可返回。

---

#### 方案 3：支付网关侧的幂等

微信支付和支付宝的接口通过 `out_trade_no`（商户订单号）天然支持幂等。重复请求时，网关返回：

- **首次请求**：返回 `{"code": "SUCCESS", "trade_state": "NOTPAY"}`，创建支付订单。
- **重复请求**：返回 `{"code": "SUCCESS", "trade_state": "SUCCESS"}`，返回已支付结果而非新建订单。

> **因此**，支付网关的幂等是上游幂等设计的 **"最后一道防线"**，但不能完全依赖它——因为网关超时场景下，商户无法区分"网关真的失败了"还是"网关成功了但响应丢了"。

---

#### 方案 4：Token 机制（防重放）

**原理**：在下单阶段生成一次性的支付 Token，支付时通过 Redis 的 `SET NX`（Set if Not Exists）命令原子性校验 Token 是否已使用。

```java
// Token 生成（下单阶段）
String paymentToken = UUID.randomUUID().toString();
redisTemplate.opsForValue().set(
    "payment:token:" + paymentToken,
    orderId,
    30, TimeUnit.MINUTES
);

// Token 校验（支付阶段）
Boolean acquired = redisTemplate.opsForValue()
    .setIfAbsent("payment:used:" + paymentToken, "1");
if (Boolean.FALSE.equals(acquired)) {
    throw new RuntimeException("支付 Token 已使用，请勿重复支付");
}
```

> **注意**：Token 机制只能防**客户端的重复提交**（如用户快速连点），不能防**服务端重试**带来的重复——因为服务端重试用的是同一个 Token 但流程已跨过了 Token 校验阶段。

---

### 2.3 实践应用：完整代码实现

#### 3.1 支付入口 Service

```java
@Service
public class PaymentService {

    @Autowired
    private PaymentTransactionMapper transactionMapper;
    @Autowired
    private PaymentGatewayClient paymentGatewayClient;
    @Autowired
    private RedisTemplate<String, String> redisTemplate;

    @Transactional(rollbackFor = Exception.class)
    public PaymentResult pay(PaymentRequest request) {
        String paymentId = request.getPaymentId();

        // Step 1: 查流水表——已存在直接返回
        PaymentTransaction tx = transactionMapper.selectByPaymentId(paymentId);
        if (tx != null) {
            // 已存在且成功 → 直接返回成功（幂等返回）
            if (tx.getStatus() == 1) {
                return PaymentResult.success(tx.getTransactionId());
            }
            // 已存在且处理中 → 返回"处理中"状态
            if (tx.getStatus() == 0) {
                return PaymentResult.pending(tx.getTransactionId());
            }
            // 已存在且失败 → 允许重试（需走失败重试逻辑）
            if (tx.getStatus() == 2) {
                return PaymentResult.failed(tx.getTransactionId(), tx.getErrorMsg());
            }
        }

        // Step 2: 创建流水（唯一键防重）
        PaymentTransaction newTx = new PaymentTransaction();
        newTx.setPaymentId(paymentId);
        newTx.setOrderId(request.getOrderId());
        newTx.setAmount(request.getAmount());
        newTx.setStatus(0); // 处理中
        try {
            transactionMapper.insert(newTx);
        } catch (DuplicateKeyException e) {
            // 并发下唯一键冲突，查询已有记录返回
            tx = transactionMapper.selectByPaymentId(paymentId);
            return PaymentResult.ofStatus(tx);
        }

        // Step 3: 调用支付网关（带分布式锁防并发）
        String lockKey = "payment:lock:" + paymentId;
        Boolean locked = redisTemplate.opsForValue()
            .setIfAbsent(lockKey, "1", 5, TimeUnit.SECONDS);
        if (Boolean.FALSE.equals(locked)) {
            return PaymentResult.pending(paymentId);
        }
        try {
            GatewayResponse response = paymentGatewayClient.submit(paymentId,
                request.getAmount(), request.getDescription());
            // 更新流水为"已提交网关"
            newTx.setGatewayTradeNo(response.getTradeNo());
            newTx.setStatus(1);
            transactionMapper.updateById(newTx);
            return PaymentResult.success(response.getTradeNo());
        } catch (Exception e) {
            log.error("网关调用失败, paymentId={}", paymentId, e);
            return PaymentResult.pending(paymentId);
        } finally {
            redisTemplate.delete(lockKey);
        }
    }
}
```

#### 3.2 支付回调处理

```java
@Service
public class PaymentCallbackService {

    @Autowired
    private PaymentTransactionMapper transactionMapper;
    @Autowired
    private OrderService orderService;

    @Transactional(rollbackFor = Exception.class)
    public void handleCallback(PaymentCallback callback) {
        String paymentId = callback.getOutTradeNo();

        // Step 1: 幂等校验——查流水表
        PaymentTransaction tx = transactionMapper.selectByPaymentId(paymentId);
        if (tx == null) {
            log.warn("收到未知 paymentId 的回调: {}", paymentId);
            return;
        }

        // Step 2: 状态机校验——只有"处理中"可以转为"已支付"
        if (tx.getStatus() != 0) {
            log.info("重复回调忽略: paymentId={}, currentStatus={}",
                paymentId, tx.getStatus());
            return;
        }

        // Step 3: 使用乐观锁更新流水状态
        int affected = transactionMapper.updateStatusByIdempotent(
            paymentId,
            0,        // 期望的当前状态
            1,        // 目标状态
            callback.getGatewayTradeNo(),
            tx.getVersion()
        );

        if (affected == 0) {
            log.warn("乐观锁更新失败, paymentId={}", paymentId);
            return;
        }

        // Step 4: 更新订单状态
        if ("SUCCESS".equals(callback.getTradeStatus())) {
            orderService.markOrderPaid(tx.getOrderId(), tx.getAmount());
        } else {
            orderService.markOrderFailed(tx.getOrderId(), callback.getFailReason());
        }
    }
}
```

### 2.4 深入思考：数据库 + 缓存双写一致性

| 场景 | 问题 | 解决方案 |
|------|------|----------|
| 先写 DB 再写缓存 | 写 DB 成功，写缓存失败 → 数据不一致 | 使用 **Cache-Aside Pattern**：写 DB 后直接删除缓存 |
| 并发读写 | 线程 A 写 DB（status=1），线程 B 读旧缓存（status=0） | 缓存设置极短 TTL（如 5s） |
| 回调乱序 | 第二次回调先到，第一次回调后到 | 版本号 / 时间戳机制 |

**最佳实践**：

1. **更新时**：先写 DB → 后删缓存（延迟双删）
2. **查询时**：Cache Miss 时从 DB 回填缓存
3. **兜底**：缓存 TTL 不可过长（建议 1-5 分钟）

```java
// 延迟双删策略
public void updatePaymentStatus(String paymentId, int newStatus) {
    redisTemplate.delete("payment:cache:" + paymentId);
    transactionMapper.updateStatus(paymentId, newStatus);
    executor.schedule(() -> {
        redisTemplate.delete("payment:cache:" + paymentId);
    }, 500, TimeUnit.MILLISECONDS);
}
```

---

---

## 3. 回答思路

### 3.1 破题：从"为什么会有重复"切入

分析重复消息的来源：

- **用户重复点击**：前端未做防抖，用户快速连点"确认支付"。
- **MQ 重试**：消费端处理超时或异常，消息队列重新投递。
- **网关超时重传**：调用支付网关时网络超时，发起重试，但网关实际已处理成功。

点明 **"至少一次交付"（At-Least-Once Delivery）** 在分布式消息系统中的必然性——重复是常态，幂等是解决方案。

### 3.2 回答节奏：由底向上

| 层级 | 方案 | 作用 |
|------|------|------|
| **第一层（数据库兜底）** | 唯一索引 + Insert 防重 | 最后一道物理屏障 |
| **第二层（业务逻辑）** | 查询流水表 + 状态机控制 | 业务语义防重 |
| **第三层（分布式锁）** | Redis SET NX 控制并发 | 并发请求串行化 |
| **第四层（网关配合）** | 利用 `out_trade_no` 的网关幂等 | 外部系统兜底 |

### 3.3 代码落地关键考点

- **状态机转移**：只允许 `0 → 1` 或 `0 → 2`，防止回调乱序导致状态回滚。
- **Cache-Aside 模式**：写 DB 后删缓存而非更新缓存，避免并发写导致缓存与 DB 不一致。
- **乐观锁 vs 悲观锁**：支付回调用乐观锁避免长事务锁，提升并发吞吐。

### 3.4 加分项

提及 **"定时补偿任务"**——扫描"处理中"状态的流水，主动查询网关最终状态并修复。这是生产环境中保证最终一致性的关键兜底策略：

```
定时任务（每 5 分钟）→ 查询 status=0 且超过 2 分钟的流水
    → 调用网关查询接口获取最终状态
    → 更新流水和订单状态 → 完成补偿闭环
```

### 3.5 中英术语矩阵

| 中文 | English |
|------|---------|
| 幂等 | Idempotency / Idempotent |
| 唯一键 | Unique Key / Unique Constraint |
| 乐观锁 | Optimistic Locking |
| 状态机 | State Machine |
| 最终一致性 | Eventual Consistency |
| 至少一次交付 | At-Least-Once Delivery |
| 流水表 | Transaction Log / Journal Table |
| 外发模式 | Outbox Pattern |
| 补偿事务 | Compensating Transaction |
| 防重放 | Anti-Replay |

---

---

## 4. 文档信息

| 条目 | 内容 |
|------|------|
| **题目标题** | 消费者收到重复的支付消息如何处理（幂等设计） |
| **生成日期** | 2026-07-04 |
| **文档版本** | v1.0 |
| **技术标签** | `幂等设计` `分布式系统` `支付系统` `高可用` `最终一致性` |
| **关键词** | Idempotency, 唯一键, 乐观锁, 状态机, Outbox Pattern, 防重放 |
| **文档类型** | 面试题深度解答 |
| **领域** | 后端开发 / 分布式架构 / 支付系统 |

---

> **总结**：支付幂等设计的本质是用 **"空间换正确性"**——通过一个事前写入的流水表（唯一键），将分布式系统的不确定性降级为数据库的确定性约束。
