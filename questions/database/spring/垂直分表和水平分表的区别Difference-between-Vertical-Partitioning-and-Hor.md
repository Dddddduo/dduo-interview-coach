---
id: q0028
question: "垂直分表和水平分表的区别（Difference between Vertical Partitioning and Horizontal Partitioning）"
category: spring
tags: ["分表", "水平分表", "Sharding", "数据库优化", "分片", "垂直分表", "分区"]
difficulty: medium
created: 2026-07-04 14:26:09
source: /面经助手-20260704
---

# 垂直分表和水平分表的区别（Difference between Vertical Partitioning and Horizontal Partitioning）

### 🧠 联想记忆法

- **记忆口诀/联想**: "竖切蛋糕横切饼" —— 垂直分表像竖着切蛋糕（按列切，每块含不同配料），水平分表像横着切饼（按行切，每块结构一样）。
  - 补充口诀："竖拆列，横拆行；列不同，行相同"

- **记忆原理**:
  - "竖"（垂直）对应数据库的列（Column），"横"（水平）对应数据库的行（Row）—— 中文的"竖/横"与数据库的"列/行"自然对应，不易混淆。
  - 蛋糕横切和竖切的生活场景人人熟悉，竖切出来的每块成分不同（类比垂直分表每张表结构不同），横切出来的每块成分一致（类比水平分表每张表结构相同）。

- **关联知识**:
  - 与文件系统的 RAID 0/1 类比：垂直分表 ≈ RAID 1（不同数据分布），水平分表 ≈ RAID 0（数据条带化，Stripe）
  - 与分布式系统的 Region Split（HBase/MongoDB）概念相通
  - 与数据库设计中的第三范式（3NF）有联系 —— 垂直分表本质上是拆分范式化的过程

### 📖 深度解答

#### 一、核心概念（Core Concepts）

**垂直分表（Vertical Partitioning）**，又称列拆分（Column Splitting），是指将一张字段较多的宽表（Wide Table）按列拆分成多张结构不同的窄表（Narrow Table）。每张子表包含原表的部分列，通过主键（Primary Key）关联。

**水平分表（Horizontal Partitioning / Sharding）**，又称行拆分（Row Splitting），是指将一张数据量大的表按行拆分**结构完全相同**的多张子表。每张子表拥有相同的列定义，但存储不同的数据行。

| 维度 | 垂直分表 | 水平分表 |
|------|---------|---------|
| 拆分方向 | 按列（Column） | 按行（Row） |
| 子表结构 | 不同（Different Schema） | 相同（Identical Schema） |
| 拆分依据 | 字段属性（大小、访问频率） | 分片键（Sharding Key） |
| 数据量减少 | 每张表行数不变，列数减少 | 每张表列数不变，行数减少 |
| 主键关系 | 子表共享同一主键 | 子表各自独立主键 |

**典型举例**：

垂直分表 —— 用户表（User）拆分为：
```sql
-- 用户主表：高频、小字段
CREATE TABLE user_main (
    user_id    BIGINT PRIMARY KEY,
    username   VARCHAR(32),
    mobile     VARCHAR(16),
    email      VARCHAR(64),
    status     TINYINT,
    created_at DATETIME
);

-- 用户扩展表：低频、大字段
CREATE TABLE user_ext (
    user_id     BIGINT PRIMARY KEY,
    avatar_url  VARCHAR(256),
    bio         TEXT,
    preferences JSON,
    last_login  DATETIME
);
```

水平分表 —— 订单表（Order）按 `user_id` 哈希分16张表：
```java
// 分片路由算法：user_id % 16
public class OrderShardingAlgorithm {
    public String getTableName(Long userId) {
        int shard = (int)(userId % 16);
        return "order_" + shard;
    }
}
```

#### 二、底层原理（Underlying Principles）

**垂直分表的底层原理**：

1. **InnoDB 页存储（Page Storage）**：MySQL InnoDB 存储引擎的最小存储单位是页（Page），默认大小为 16KB。一个页内存储的行数越多，每次 I/O 能读取的有效数据越多。宽表的每行数据过大 → 每个页能存储的行数减少 → 相同行数的数据需要更多页 → 增加 I/O 次数。

2. **行溢出（Row Overflow）**：当一行数据超过一个页的大小（16KB），InnoDB 会将部分数据存储在溢出页（Overflow Page）中。TEXT、BLOB、过长 VARCHAR 都会触发行溢出。查询时即使只需要一个字段，也需要读取溢出页，造成额外的随机 I/O。

3. **聚簇索引（Clustered Index）**：InnoDB 的主键是聚簇索引，行数据直接存储在 B+ 树的叶子节点上。宽表意味着每棵 B+ 树的叶子节点存储的数据量更大，树的高度更高。高度每增加一层，每次查询就多一次磁盘 I/O。

4. **缓冲池（Buffer Pool）污染**：宽表中的大字段被加载到 Buffer Pool 后，会挤占热门数据的缓存空间，降低缓存命中率（Cache Hit Ratio）。

**水平分表的底层原理**：

1. **B+树高度与数据量**：InnoDB B+树的高度与数据量的关系为：`高度 h = log_{扇出数}(总行数)`。设扇出数（Fan-out）约为 1200（16KB / 索引键大小），则：
   - 高度 h=3：可存储约 1200³ ≈ 17 亿行
   - 但实际上，由于索引项与行数据共同存储在叶子节点，有效扇出数远小于理论值
   - 当单表数据量超过千万级别，B+树高度达到 3-4 层，每次查询需 3-4 次 I/O

2. **锁竞争（Lock Contention）**：单表数据量过大时，行锁（Record Lock）、间隙锁（Gap Lock）的竞争加剧，特别是在高并发写入场景下。

3. **索引维护成本**：B+树的维护（分裂、合并）成本随数据量增加呈超线性增长。水平分表后，每张子表独立维护 B+树，单树规模大幅减小。

#### 三、实践应用（Practical Applications）

**垂直分表应用场景**：

1. **电商用户系统**：用户表包含基本信息 + 收货地址 + 会员信息 + 偏好设置，每天查询频率差异极大将基本信息分离为高频访问表
2. **内容管理系统**：文章表包含标题、摘要、正文（TEXT）、封面图URL，正文只在点击详情时查询，应拆分
3. **SaaS 多租户系统**：租户配置表中的 JSON 配置字段与核心业务字段分离

```yaml
# ShardingSphere 垂直分表配置示例
rules:
  - !SHARDING
    tables:
      user_main:
        actualDataNodes: ds0.user_main
      user_ext:
        actualDataNodes: ds0.user_ext
```

**水平分表应用场景**：

1. **订单系统**：按用户 ID 分片，确保同一用户的订单在同一个分片上，便于查询
2. **日志系统**：按时间范围分片（Range Sharding），按月创建日志表
3. **消息记录**：按 Hash 分片，均匀分布写入压力

```yaml
# ShardingSphere 水平分表配置示例
rules:
  - !SHARDING
    tables:
      order:
        actualDataNodes: ds0.order_${0..15}
        tableStrategy:
          standard:
            shardingColumn: user_id
            shardingAlgorithmName: order_hash
    shardingAlgorithms:
      order_hash:
        type: HASH_MOD
        props:
          shardingCount: 16
```

**分片键（Sharding Key）选择原则**：
- 高频查询条件字段（Where 中的核心条件）
- 数据分布均匀（避免数据倾斜 Data Skew）
- 不可变性（Immutable）—— 一旦选择不应变更
- 与业务聚合性一致（如按用户分片便于管理订单数据）

#### 四、深入思考（Deep Thinking）

**垂直分表的 JOIN 问题与反范式化**：
垂直分表后，查询需要跨表 JOIN，影响性能。可通过反范式化（Denormalization）—— 在子表中冗余存储少量高频查询字段，减少 JOIN 次数。这是一次空间换时间的设计权衡（Trade-off）。

**水平分表的扩容难题**：
- 取模分片（Mod Sharding）：扩容时数据迁移量大，需要全量 rehash
- 一致性哈希（Consistent Hashing）：每次扩容仅需迁移 1/N 的数据量
- Range 分片：新增分片无需重分布，但可能产生热点（Hot Spot）

**跨分片查询（Cross-shard Query）**：
水平分表后，不带分片键的查询需要广播到所有分片（Broadcast Query），再在应用层聚合结果（结果归并 Result Merge）。生产实践中应尽量避免，或通过 Elasticsearch 的倒排索引（Inverted Index）做二级索引。

### 🗺️ 回答思路

**答题逻辑框架**（总-分-总结构）：
1. **总起**：一句话定义两种分表方式 —— "垂直分表按列拆分，解决单行过大问题；水平分表按行拆分，解决单表行数过多问题"
2. **分述**：分别展开概念、原理、应用场景、优缺点
3. **对比**：列出对比表格，强调本质区别
4. **总结**：两者不是互斥关系，可组合使用，给出选型建议

**重点得分点**：
- 点出本质区别（列 vs 行）—— 这是最基础也是最重要的区分
- 说出底层存储原理（InnoDB Page、B+树高度）展现深度
- 给出实际分片配置（YAML/代码）展现工程经验
- 指出方案缺陷（JOIN问题、扩容难题）体现全面思考

**常见误区**：
- 混淆"分表"（Table Splitting）与"分区"（Partitioning，如 MySQL PARTITION BY RANGE）
- 以为水平分表一定需要中间件（实际也可以应用层硬编码路由）
- 忽略水平分表对事务和聚合查询的影响

**时间分配建议**（5分钟答案）：
| 阶段 | 时间 | 内容 |
|------|------|------|
| 概念定义 | 1分钟 | 两种分表的定义和本质区别 |
| 对比分析 | 2分钟 | 优缺点对比、适用场景举例 |
| 底层原理 | 1分钟 | B+树、Page存储、锁竞争 |
| 深入拓展 | 1分钟 | 分布式问题、选型思考 |

**过渡话术**：
- "在了解概念后，我们从底层存储原理来看看为什么需要这样拆分……"
- "以上是垂直分表和水平分表的区别，接下来我们深入讨论分库和分表各自解决什么具体问题……"

---

> 📋 **分类**: Spring 框架
> 🏷️ **标签**: `分表` `水平分表` `Sharding` `数据库优化` `分片` `垂直分表` `分区`
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-07-04 14:26:09
