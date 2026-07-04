---
id: q0015
question: "Redis 主从切换、异常导致锁丢失，有什么补救措施"
category: redis
tags: ["分布式锁", "Redis", "主从复制", "CAP", "RedLock", "ZooKeeper"]
difficulty: hard
created: 2026-07-04 16:30:00
source: /面经助手-20260704
---

# Redis 主从切换、异常导致锁丢失，有什么补救措施

## 🧠 联想记忆法

**口诀：「五把锁，锁住 Redis 锁丢失」**

> **Red**Lock — **延**迟重启 — Z**oo**Keeper — **fe**ncing — **幂**等

取每个方案的首字或关键字：**Red-延-Zoo-fe-幂** → 谐音「红颜祖废密」，想象一个穿红衣（Red）的**红**颜女子，在**祖**屋前**延**迟开门，发现门锁**废**了，用**密**码（幂等）救场。

| 关键词 | 方案 | 一句话记忆 |
|--------|------|-----------|
| **Red** | RedLock 红锁 | 向 N 个独立节点请求锁，过半即得锁 |
| **延** | 延迟重启 | 切换主节点前等够锁过期时间，让旧锁自然消失 |
| **Zoo** | ZooKeeper | CP 系统，写前先过半确认（ZAB 协议），强一致 |
| **fe** | fencing token | 每次拿锁配一个递增令牌，写时校验，过期拒绝 |
| **幂** | 业务幂等 | 锁失效了也不怕，唯一索引 + 乐观锁兜底 |

## 📖 深度解答

### 一、核心概念

#### 1.1 问题场景还原

在 Redis 分布式锁（Distributed Lock）的典型实现中，客户端向 Redis 主节点（Master）写入一个带有过期时间（TTL）的 Key 来获取锁。Redis 的主从复制（Master-Slave Replication）默认是异步的（Asynchronous Replication）——Master 将命令写入复制积压缓冲区（Replication Backlog），Slave 通过 `replicaof` 命令异步拉取。

当出现以下时序时锁会丢失：

```
T0: Client A 向 Master SET lock:key random_value NX PX 30000  → 加锁成功
T1: Master 尚未将命令同步到 Slave（异步延迟）
T2: Master 宕机
T3: Sentinel 执行故障转移（Failover），Slave 晋升为 Master
T4: Client B 向新 Master SET lock:key random_value2 NX PX 30000  → **加锁成功！**
→ Client A 和 Client B 同时认为自己持有锁，锁的互斥性（Mutual Exclusion）被打破
```

这就是 Redis 分布式锁在主从切换场景下的**锁丢失（Lock Loss）**问题。

#### 1.2 根因分析

| 因素 | 说明 |
|------|------|
| **异步复制** | `SET` 命令先返回客户端成功，再异步同步到 Slave，无法保证主从强一致（Strong Consistency） |
| **AP 倾向** | Redis 设计优先保证可用性（Availability）和分区容错性（Partition Tolerance），牺牲了一致性（Consistency），属于 CAP 理论的 AP 系统 |
| **故障切换时机** | Failover 可能在复制完成前的任意时刻发生 |

### 二、底层原理

#### 2.1 Redis 主从复制的异步机制

Redis 主从复制围绕 `replicationId` 和 `replicationOffset` 两个核心概念工作：

- Master 维护一个**复制积压缓冲区（Replication Backlog）**，默认 1MB 环形缓冲区
- Slave 发送 `PSYNC {replicationId} {offset}` 命令请求增量同步
- 如果 slave 的 offset 落后太多或 replicationId 不匹配，触发全量重同步（Full Resynchronization），生成 RDB 快照传输

**关键缺陷**：Master 执行完 `SET lock:key value NX PX 30000` 后立即返回 `+OK` 给客户端，然后将命令写入 backlog。如果 Master 在 backlog 被 Slave 拉取之前宕机，这条锁记录就永远丢失了。

Redis 官方在 `redis.conf` 中提供了 `min-replicas-to-write` 和 `min-replicas-max-lag` 参数，可以要求 Master 在写入时至少有一定数量的 Slave 确认（Weakly Acknowledged），但这只能降低概率，**无法从根本解决**——因为这是异步模型的天生局限。

#### 2.2 分布式锁的正确性要求

一个可靠的分布式锁必须满足三个性质：

| 性质 | 英文 | 说明 |
|------|------|------|
| **互斥性** | Mutual Exclusion | 任何时刻只有一个客户端持有锁 |
| **死锁逃生** | Deadlock Freedom | 持有锁的客户端崩溃后，锁能自动释放（通过 TTL 实现） |
| **容错性** | Fault Tolerance | 部分节点宕机不影响锁的整体正确性 |

当主从切换发生时，互斥性被破坏——这就是需要补救措施的根源。

### 三、实践应用：五大补救方案

#### 方案一：RedLock（红锁算法）

**提出者**：Redis 作者 Antirez（Salvatore Sanfilippo）

**核心思想**：不再依赖单个 Redis 主从结构，而是在 N（通常 N=5）个**完全独立**的 Redis 节点上同时申请锁，只要在 `N/2 + 1` 个节点上成功获取到锁，就认为加锁成功。

**实现步骤**：
1. 获取当前毫秒时间戳 `start_time`
2. 依次向 N 个 Redis 节点设置锁，每个 SET 的超时时间远小于锁 TTL（比如锁 TTL=10s，单节点超时=50ms）
3. 计算获取锁的耗时 `elapsed = now - start_time`
4. 如果成功节点数 >= N/2+1 **且** elapsed < lock_ttl，则锁有效
5. 释放锁时，删除所有 N 个节点上的 Key

**Java 伪代码示例**：
```java
public class RedLock {
    private static final int N = 5;
    private static final long LOCK_TTL_MS = 30000;
    private static final long PER_NODE_TIMEOUT_MS = 100;
    private List<RedisClient> nodes = initNodes(N);

    public boolean tryLock(String key, String value) {
        long start = System.currentTimeMillis();
        int successCount = 0;

        for (RedisClient node : nodes) {
            try {
                String result = node.set(key, value, 
                    SetArgs.Builder.nx().px(LOCK_TTL_MS), 
                    PER_NODE_TIMEOUT_MS);
                if ("OK".equals(result)) successCount++;
            } catch (TimeoutException e) {
                // 单个节点超时不影响整体
            }
        }

        long elapsed = System.currentTimeMillis() - start;
        int quorum = N / 2 + 1;

        if (successCount >= quorum && elapsed < LOCK_TTL_MS) {
            return true;
        }

        // 加锁失败，立即释放所有节点的锁
        for (RedisClient node : nodes) {
            node.delete(key);
        }
        return false;
    }
}
```

**优缺点**：优点是不依赖主从关系，独立节点间故障隔离；缺点是需要 5 个独立节点，运维成本高，依赖客户端时钟同步。适用于对一致性有较高要求、可接受额外硬件成本的场景。

#### 方案二：延迟重启（Delay Restart / Delayed Replica Promotion）

**核心思想**：在主从切换后，延迟从节点晋升为主节点的时间，等待旧 Master 上尚未同步的锁自然过期（超过 TTL）。实现简单，无需额外组件，但牺牲了可用性。适用于锁 TTL 较短（< 10s）、可用性要求不是极致的情况。

#### 方案三：使用 ZooKeeper / etcd 实现锁

**核心思想**：ZooKeeper 和 etcd 是 CP 系统（Consistency + Partition Tolerance），其底层一致性协议（ZAB / Raft）保证了写入的强一致性——写入必须过半节点确认后才算成功。

ZooKeeper 利用**临时顺序节点（Ephemeral Sequential Node）**实现锁，节点序号最小的持有锁，Watcher 机制监听前一个节点删除事件。etcd 利用 `lease`（租约）和 `revision`（版本号）机制。优点：强一致性保证；缺点：吞吐量低于 Redis。

#### 方案四：Fencing Token（栅栏令牌）

**提出者**：Martin Kleppmann（《Designing Data-Intensive Applications》作者）

每次锁服务分配锁时返回一个严格递增的全局序号（Token），客户端在操作共享资源时必须附带 Token，资源端拒绝过期 Token 的写入。与具体锁实现解耦，数学上严格保证安全，但需要改共享资源端代码。

#### 方案五：业务层幂等设计（Idempotent Design）

通过**唯一索引（Unique Index）**、**乐观锁（Optimistic Locking）**、**状态机（State Machine）**等手段兜底。即使锁失效导致同一个操作被执行多次，最终的业务状态仍然正确。这是所有分布式锁场景都应配合的最后防线。

### 四、深入思考

**方案对比总结**：

| 方案 | 一致性保证 | 运维复杂度 | 性能影响 | 推荐场景 |
|------|-----------|-----------|---------|---------|
| RedLock | 较强（多数同意） | 高 | 中 | 中等一致性要求 |
| 延迟重启 | 弱（等待过期） | 低 | 低 | 低一致性要求 |
| ZooKeeper/etcd | **强**（CP系统） | 中-高 | 较低 | **高一致性要求** |
| Fencing Token | 最强（严格递增） | 中 | 低 | **核心金融场景** |
| 业务幂等 | 最强（业务级保证） | 中 | 低 | **所有场景兜底** |

**黄金组合建议**：第一层 RedLock/ZooKeeper 预防；第二层 Fencing Token 兜底；第三层业务幂等最后防线。

**RedLock 学术争议**：Martin Kleppmann 指出 RedLock 依赖本地时钟且缺少 Fencing Token；Antirez 回应时钟误差可控。工程共识：绝对正确性要求用 ZK/etcd，高吞吐场景用 RedLock。

**CAP 理论启示**：Redis 是 AP 系统，ZooKeeper 是 CP 系统，选择取决于业务对一致性的敏感度。

## 🗺️ 回答思路

1. **给出问题场景**：展现场景分析能力，描述 Master 宕机 + 异步复制导致锁丢失的时序
2. **逐层展开方案**：展现知识体系广度，必须提到 RedLock、ZooKeeper/etcd、业务幂等，加分项是 Fencing Token 和延迟重启
3. **对比推荐**：金融场景用 ZK+Fencing+幂等三层组合；缓存场景用 RedLock+幂等
4. **理论支撑**：引用 CAP 理论、RedLock 学术讨论展现深度
5. **避坑提示**：不要只说 RedLock 结束，不要忽略幂等设计，不要回避 RedLock 争议

---

> 📋 **分类**: Redis / 缓存
> 🏷️ **标签**: `分布式锁` `Redis` `主从复制` `CAP` `RedLock` `ZooKeeper`
> 📊 **难度**: 进阶
> 📅 **归档时间**: 2026-07-04 16:30:00
