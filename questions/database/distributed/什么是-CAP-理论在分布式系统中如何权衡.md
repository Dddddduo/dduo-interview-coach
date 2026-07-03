---
id: q0003
question: "什么是 CAP 理论？在分布式系统中如何权衡？"
category: distributed
tags: ["CAP", "分布式", "一致性", "可用性", "BASE"]
difficulty: medium
created: 2026-07-04 02:46:47
source: 示例归档
---

# 什么是 CAP 理论？在分布式系统中如何权衡？

### 联想记忆法
**记忆口诀**: "CAP 三角，只能选两角" — C=一致性(Consistency)、A=可用性(Availability)、P=分区容错(Partition Tolerance)，三者只能同时满足两个
**记忆原理**: 三角形是最容易记住"三选二"的视觉隐喻；记住 CAP 三个字母代表的含义即可
**关联知识**: BASE 理论（Basically Available, Soft state, Eventually consistent）是 CAP 的工程实践

### 深度解答

#### 核心概念（是什么）
CAP 理论是分布式系统的基石，由 Eric Brewer 在 2000 年提出：
- **C (Consistency) 一致性**: 所有节点在同一时刻看到相同的数据
- **A (Availability) 可用性**: 每个请求都能收到（非错误的）响应
- **P (Partition Tolerance) 分区容错**: 系统在部分节点间网络断开时仍能继续工作

CAP 定理的核心结论：**任何分布式系统最多只能同时满足其中两个**。

#### 底层原理（为什么）
CAP 不能三者兼得的根本原因在于网络分区的不可避免性：
1. 当网络发生分区（P 发生），系统必须在 C 和 A 之间做选择
2. 如果要保证 C，必须拒绝某些写操作 → 牺牲 A
3. 如果要保证 A，必须允许不一致 → 牺牲 C

**设计哲学**: P 是分布式系统的"宿命"——网络分区不可预测且不可避，所以实际上选择的是"CP"还是"AP"。

#### 实践应用（怎么用）
| 系统 | 选择 | 理由 |
|------|------|------|
| ZooKeeper / etcd | CP | 配置数据一致性优先，短暂不可用可接受 |
| Eureka / Consul | AP | 服务发现可用性优先，允许短暂不一致 |
| MySQL 主从 | CP/AP | 取决于同步策略（全同步=CP，半同步=折中） |
| Redis Cluster | AP | 高可用优先，允许最终一致性 |

#### 深入思考（注意事项）
- CAP 不是"要么有要么没有"，而是程度问题——可以做到"基本 CP 但尽量保证 A"
- PACELC 是对 CAP 的补充：发生分区时选 A 或 C，无分区时在延迟(Latency)和一致性(Consistency)之间权衡
- BASE 理论（Basically Available, Soft state, Eventually consistent）是 AP 系统的工程实践

---

> 📋 **分类**: 分布式系统
> 🏷️ **标签**: `CAP` `分布式` `一致性` `可用性` `BASE`
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-07-04 02:46:47
