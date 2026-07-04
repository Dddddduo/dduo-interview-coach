---
id: q0015
question: "[技术-Redis] Redis 集群、哨兵的作用"
category: redis
tags: ["redis", "哨兵", "集群", "高可用", "分片", "Sentinel", "Cluster"]
difficulty: medium
created: 2026-07-04 16:00:00
source: "/面经助手-20260704"
---

# Redis 集群（Cluster）与哨兵（Sentinel）深度解析

---

## 🧠 联想记忆法

**记忆口诀：「哨兵看门，集群分家」**

- **哨兵 = 看门大爷**：哨兵（Sentinel）就是给 Redis 主从架构（Master-Slave Replication）请的「看门大爷」。他每天干三件事：**盯着门**（监控 Monitoring）、**发现门坏了喊人来修**（故障转移 Failover）、**告诉街坊邻居新门的位置**（通知 Notification）。为啥要请好几个大爷？因为一个大爷也会生病——**哨兵集群（Sentinel Cluster）** 用投票（Quorum）机制决定是否真的出事了，防止误判。

- **集群 = 分家过日子**：集群（Cluster）是把数据分到多个「小家庭」（节点）里。分家的规矩是 **CRC16 哈希算法**——对所有 key 做 CRC16 取模得 16384 个哈希槽（Hash Slot）。每个节点分管一部分槽。找数据时，客户端直接算 key 属于哪个槽→哪个节点。如果数据挪到别人家了，节点告诉你「去找他」（MOVED 重定向）或「我帮你转交」（ASK 重定向）。节点之间靠 **Gossip 协议**（八卦协议）聊天交换信息。

- **一句话区分**：哨兵管**高可用**（High Availability）——保证主挂了有备用；集群管**高性能+大数据**——把数据分片（Sharding）存到多台机器，同时自带高可用。

---

## 📖 深度解答

### 一、核心概念

#### 1.1 Redis Sentinel（哨兵）

**定义**：Redis Sentinel 是 Redis 官方提供的高可用（High Availability）解决方案，主要对 Redis 主从架构进行监控、通知和自动故障转移。

**核心功能**：
- **监控（Monitoring）**：持续检查主节点（Master）和从节点（Slave）是否正常运行
- **通知（Notification）**：当被监控的 Redis 实例出问题时，哨兵可以通过 API 通知系统管理员
- **自动故障转移（Automatic Failover）**：当主节点宕机，哨兵自动将一个从节点提升（Promote）为新的主节点
- **配置提供（Configuration Provider）**：客户端连接哨兵获取当前主节点地址

#### 1.2 Redis Cluster（集群）

**定义**：Redis Cluster 是 Redis 3.0 引入的分布式（Distributed）解决方案，提供数据自动分片和高可用能力。

**核心特性**：
- **自动分片（Auto Sharding）**：数据自动分布到多个节点
- **高可用**：每个分片支持主从结构，主节点故障时自动切换
- **去中心化（Decentralized）**：所有节点通过 Gossip 协议通信，无中心节点
- **线性扩展（Linear Scalability）**：增加节点即可线性提升吞吐量

---

### 二、底层原理

#### 2.1 哨兵：监控与故障转移机制

##### 2.1.1 主观下线和客观下线

- **主观下线（Subjective Down, SDOWN）**：单个哨兵发现某节点超过 `down-after-milliseconds` 时间无响应，标记为 SDOWN
- **客观下线（Objective Down, ODOWN）**：多个哨兵（达到 quorum 数量）都认为某节点不可用，标记为 ODOWN——这是触发故障转移的前提

##### 2.1.2 故障转移流程

```
步骤1: 哨兵 A 发现主节点 ping 超时 → 标记 SDOWN
步骤2: 哨兵 A 向其他哨兵发送 `SENTINEL is-master-down-by-addr` 命令
步骤3: 达到 quorum 数量的哨兵确认故障 → 标记 ODOWN
步骤4: 发起领导者（Leader）选举——Raft 算法选出一个哨兵领导故障转移
步骤5: 领导者选出一个从节点作为新主节点（优先级 replica-priority 高→复制偏移量大→runid 小）
步骤6: 执行 `SLAVEOF NO ONE` 将从节点提升为主节点
步骤7: 其他从节点执行 `SLAVEOF new-master` 重新指向新主节点
```

##### 2.1.3 哨兵投票（Quorum）机制

Quorum 不是多数票，而是「认定故障所需的最少哨兵数」。例如 3 个哨兵，quorum=2，则至少 2 个哨兵认定故障才触发转移。**建议 quorum = N/2 + 1**（N 为哨兵总数）。

##### 2.1.4 为什么要部署哨兵集群？

单个哨兵存在**单点故障（Single Point of Failure）**——如果唯一的哨兵进程挂了，整个高可用体系失效。部署多个哨兵（通常奇数个：3、5、7）可以实现：
- 避免误判（一个哨兵网络抖动不算下线）
- 脑裂（Split-Brain）保护
- 领导者选举需要多数派

##### 2.1.5 哨兵配置文件 sentinel.conf 关键配置项

```bash
# sentinel.conf - 最小配置示例
port 26379                                         # 哨兵监听端口
daemonize no                                       # 是否后台运行
pidfile /var/run/redis-sentinel.pid                # PID 文件

# 监控主节点：sentinel monitor <master-name> <ip> <port> <quorum>
sentinel monitor mymaster 127.0.0.1 6379 2

# 主观下线判定时间（毫秒），超时未 ping 通则标记 SDOWN
sentinel down-after-milliseconds mymaster 30000

# 故障转移超时（毫秒）
sentinel failover-timeout mymaster 180000

# 同时向新主节点同步的从节点数量（值越小，故障转移期间丢失数据越少）
sentinel parallel-syncs mymaster 1

# 认证密码（如果 Redis 设了密码）
sentinel auth-pass mymaster MySecretPassword

# 通知脚本（故障转移时触发）
sentinel notification-script mymaster /var/redis/notify.sh
```

#### 2.2 集群：哈希槽、CRC16、Gossip

##### 2.2.1 哈希槽（Hash Slot）与 CRC16

Redis Cluster 将 key 空间分为 **16384 个哈希槽**（0~16383），每个 key 通过以下公式确定其所属槽：

```
HASH_SLOT = CRC16(key) % 16384
```

每个集群节点负责一部分连续或离散的哈希槽，使用 `CLUSTER ADDSLOTS` 命令分配：

```bash
# 集群节点配置示例（redis.conf）
port 7000
cluster-enabled yes                            # 开启集群模式
cluster-config-file nodes-7000.conf            # 集群节点配置文件
cluster-node-timeout 5000                      # 集群节点超时时间（毫秒）
appendonly yes
daemonize no
protected-mode no
bind 0.0.0.0

# 分配哈希槽示例（在节点上执行）
redis-cli -p 7000 CLUSTER ADDSLOTS 0 1 2 ... 5460
redis-cli -p 7001 CLUSTER ADDSLOTS 5461 5462 ... 10922
redis-cli -p 7002 CLUSTER ADDSLOTS 10923 10924 ... 16383
```

> **为什么是 16384 个槽？** 因为 CRC16 输出 16 位（65536 种可能），但集群节点间的心跳包（Heartbeat Packet）用位图（Bitmap）表示槽分布——16384 个槽只需 2KB 位图，65536 则需要 8KB，而 16384 对大多数集群规模（<=1000 节点）已足够均衡。

##### 2.2.2 CRC16 算法

CRC16（Cyclic Redundancy Check 16-bit）是一种循环冗余校验算法。Redis 使用 `CRC16_MODBUS` 变体（即 IBM CRC-16/Modbus 多项式 `0x8005`），对 key 做 16 位校验和（Checksum），再对 16384 取模得到哈希槽。

**特殊处理**：如果 key 包含 `{...}` 大括号，则只对大括号内的内容计算哈希，确保特定 key 强制映射到同一节点：

```
user:{1001}:name    → CRC16("1001") % 16384 → 槽 6257
user:{1001}:email   → CRC16("1001") % 16384 → 槽 6257（与上面相同）
```

这在**批量操作**（Pipeline、事务）中至关重要——同一个槽的 key 可以在一次命令中完成。

##### 2.2.3 Gossip 协议

Gossip（八卦协议）是 Redis Cluster 节点间交换元数据（Metadata）的通信协议。每个节点每秒向若干随机节点发送 **PING** 消息，其中包含自己知道的其他节点状态。收到 PING 的节点回复 **PONG**。

**消息类型**：
| 消息类型 | 用途 |
|---------|------|
| MEET | 将新节点加入集群 |
| PING | 周期性探活和交换信息 |
| PONG | 对 PING/MEET 的响应 |
| FAIL | 广播某节点已故障 |
| PUBLISH | 广播发布/订阅消息 |

**Gossip 消息字段**：
```bash
# 每个 Gossip 消息包含的节点信息
clusterMsgDataGossip {
    nodename  (节点名称, 40字节)
    ping_sent (上次PING时间戳)
    pong_recd (上次PONG时间戳)
    flags     (节点状态标记)
    ip        (节点IP)
    port      (节点端口)
}
```

**特点**：
- **最终一致性（Eventual Consistency）**：状态传播有延迟，但最终所有节点一致
- **容错（Fault Tolerance）**：少量节点故障不影响集群元数据交换
- **带宽友好**：每个心跳包只带少量节点信息（约 1/10），避免广播风暴

##### 2.2.4 MOVED vs ASK 重定向

| 特性 | MOVED 重定向 | ASK 重定向 |
|------|-------------|-----------|
| **触发场景** | 哈希槽**已永久迁移**到其他节点 | 哈希槽**正在迁移**中，数据可能还在旧节点 |
| **状态码** | `-MOVED <slot> <ip>:<port>` | `-ASK <slot> <ip>:<port>` |
| **客户端行为** | 刷新本地路由表，后续请求直接发新节点 | 先发 ASKING 命令给目标节点，再发原命令（不更新路由表） |
| **本质** | 数据归属已变更 | 数据正在搬家，暂时帮忙查一下 |

**MOVED 示例**：

```bash
# 客户端向节点 A 请求 key="mykey"（槽 12345）
$ GET mykey
-MOVED 12345 127.0.0.1:7001
#    ↑槽号   ↑目标节点

# 客户端更新本地槽映射表（Slot Map），重新发送到 127.0.0.1:7001
$ GET mykey
"hello"
```

**ASK 示例**：

```bash
# 当集群正在 rebalancing（重平衡）时，槽 12345 从节点 A 迁移到节点 B
# 客户端请求 key 可能还在节点 A
$ GET mykey
-ASK 12345 127.0.0.1:7002
# 客户端先向节点 B 发送 ASKING（临时标记）
$ ASKING
+OK
$ GET mykey
"hello"

# 注意：ASK 不更新路由表，节点 A 的槽映射仍指向自己
```

> **面试加分点**：Smart Client（智能客户端如 Redis Cluster 的 `redis-py-cluster`、Jedis Cluster）会缓存槽映射表，MOVED 触发路由表更新，ASK 则只做一次临时重定向。MOVED 表示槽归属永久变化，ASK 表示槽正在迁移的过渡状态。

##### 2.2.5 集群主从结构

Redis Cluster 中，每个主节点可以配置多个从节点（Slave/Replica）。主节点负责处理该分片的读写请求，从节点提供读流量负载分担和数据冗余。

**主从故障转移**：当主节点失效（被多数节点标记为 PFAIL/FAIL），其从节点会通过 **集群选举（Cluster Election）** 机制提升为新主节点——基于 Raft 算法的变体，获得超过半数（N/2+1）主节点投票的从节点当选。

```bash
# 添加从节点（在从节点上执行）
redis-cli -p 7003 CLUSTER REPLICATE <master-node-id>
```

---

### 三、实践应用

#### 3.1 架构演进路径

```
单机 Redis → 主从复制 → 哨兵+主从 → Redis Cluster
  (1 node)   (1主N从)  (HA保障)    (分片+原生HA)
```

| 架构 | 数据容量 | 高可用 | 写扩展 | 读扩展 | 适用场景 |
|------|---------|-------|-------|-------|---------|
| 单机 | 单机内存 | 无 | 无 | 无 | 开发/测试 |
| 主从复制 | 单机内存 | 手动切换 | 无 | 从节点分担读 | 读多写少 |
| 哨兵+主从 | 单机内存 | 自动故障转移 | 无 | 从节点分担读 | 生产环境高可用 |
| 集群 | 多机总和 | 自动分片+故障转移 | 横向扩展 | 横向扩展 | 海量数据高并发 |

#### 3.2 哨兵 vs 集群：对比总结

| 对比维度 | Redis Sentinel | Redis Cluster |
|---------|---------------|--------------|
| 数据分片 | 不支持（全量数据单机） | 支持（16384 哈希槽） |
| 数据容量 | 受单机内存限制 | 可横向扩展至多 TB |
| 高可用方式 | 哨兵监控 + 自动故障转移 | 节点自发现 + 自动故障转移 |
| 节点数目 | 适合少量节点（主+N从） | 适合大量节点（官方推荐 ≤1000） |
| 客户端 | 直连主节点 | Smart Client + 槽映射 |
| 运维复杂度 | 中等（需独立部署哨兵） | 较高（需规划分片策略） |
| 事务支持 | 完整（单机事务） | 有限（仅支持同一槽的 MULTI/EXEC） |
| 多 key 操作 | 完全支持 | 仅支持同一哈希槽 |

#### 3.3 生产部署最佳实践

**哨兵部署建议**：
- 哨兵节点必须部署奇数个（至少 3 个），且分布在不同的物理机/可用区
- quorum 设置为 `N/2 + 1`（3 个哨兵设 2，5 个哨兵设 3）
- 哨兵本身不存业务数据，资源占用很小（每个哨兵约 30MB 内存）
- 设置 `down-after-milliseconds` 为 30~60 秒，避免网络抖动误触发

**集群部署建议**：
- 节点数量建议为 3 的倍数（3主3从、6主6从等），保证分片均匀
- 每个主节点配一个从节点做冗余（生产环境建议至少 1 个从节点）
- 使用 `redis-trib.rb` 或 `redis-cli --cluster` 命令管理集群
- 开启 `cluster-require-full-coverage no`（部分节点故障时仍提供服务）
- 多 key 操作尽量使用哈希标签（Hash Tag）`{user_id}` 保证 key 在同一槽

---

### 四、深入思考

#### 4.1 哨兵 vs 集群，我该选谁？

- **数据量 < 单机内存（如 10GB）且需要高可用** → 选哨兵。简单、可靠、运维成本低
- **数据量 > 单机内存（如 100GB）或写吞吐极高** → 选集群。水平扩展是唯一出路
- **混合架构**：一些大厂使用「集群+哨兵」联合——集群中每个主节点的从节点由哨兵管理，实现双层保障

#### 4.2 常见面试追问

**Q：哨兵 quorum=2 但只有 2 个哨兵会怎样？**
A：如果主节点宕机，一个哨兵标记 SDOWN 后广播，另一个哨兵响应 ODOWN，触发故障转移。但如果其中一个哨兵自身故障，只剩单个哨兵，无法达到 quorum，故障转移失败。因此生产环境必须用 3 个以上哨兵。

**Q：集群脑裂（Split-Brain）怎么处理？**
A：Redis Cluster 通过「多数派原则」防止脑裂。当网络分区发生时，少数分区的节点无法与多数节点通信，如果少数分区节点数 < N/2+1，则这些节点会被标记为 FAIL，停止服务。`cluster-node-timeout` 配置控制超时后断连。

**Q：集群模式还能用事务（Transaction）吗？**
A：可以，但有限制——MULTI/EXEC 事务内的所有 key 必须在同一哈希槽。否则返回 `CROSSSLOT` 错误。使用哈希标签 `{...}` 将相关 key 聚合到同一槽即可。

#### 4.3 扩展阅读

- Redis Cluster 在 7.0 版本引入了 **Redis Function**，可以跨槽执行 Lua 脚本
- 腾讯云、阿里云的 Redis 集群产品（如腾讯云 CRS）在原生集群基础上增加了代理层（Proxy），对客户端更友好
- 业界也在探索 **Redis Cluster + 读写分离**——从节点处理读请求，主节点处理写请求

---

## 🗺️ 回答思路

这道题在面试中考察的是 **对 Redis 高可用和数据分片方案的系统理解**。面试官期待你不仅知道「哨兵是什么」「集群是什么」，还能说出：

1. **底层原理深度**：SDOWN vs ODOWN、Raft 选举、CRC16 选槽逻辑、Gossip 协议细节——网上教程很少讲全
2. **对比辩证思维**：不止是简单列表，要能说清「为什么有哨兵还要集群」「什么场景选谁」
3. **实践感知**：配置文件怎么配、MOVED 和 ASK 有什么区别、Smart Client 如何处理——表明你真的用过

**回答结构建议**（面试时口头表达）：
1. 开门见山：「Redis 哨兵负责高可用，集群负责分片和高可用。两者定位不同，但可以互补。」
2. 先讲哨兵：监控→投票→故障转移，部署奇数个哨兵的原因
3. 再讲集群：哈希槽→CRC16→Gossip→MOVED vs ASK，结合示意图说清
4. 最后对比：给面试官一个「什么场景用什么」的框架
5. 收尾升华：如果再深入，可以提 Proxy 方案、跨槽事务限制等

**面试加分项**：主动提及 `hash tag` 解决跨槽问题、Raft 算法在选举中的应用、16384 槽的设计取舍——这些「为什么」比「是什么」更能打动面试官。

---

> 📋 **分类**: Redis / 缓存
> 🏷️ **标签**: `redis` `哨兵` `集群` `高可用` `分片` `Sentinel` `Cluster`
> 📊 **难度**: 中等
> 📅 **归档时间**: 2026-07-04 16:00:00
