import sys
sys.path.insert(0, r'C:\Users\28757\dduo-interview-coach\scripts')

from question_manager import QuestionManager

qm = QuestionManager()

# Question 1: 垂直分表和水平分表的区别
q1_answer = r"""
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
"""

# Question 2: 分库、分表分别的作用
q2_answer = r"""
### 🧠 联想记忆法

- **记忆口诀/联想**: "分表治胖，分库治挤"
  - 分表解决表太"胖"（数据量大）的问题
  - 分库解决库太"挤"（连接数/IO/CPU瓶颈）的问题
  - 进阶口诀："分表减负单表，分库增源实例"

- **记忆原理**:
  - 拟人化记忆把"数据库"比作"仓库"：分表是在仓库内多放几个货架（仍在一个房间），分库是把货物分到不同房间甚至不同楼栋。
  - "胖"和"挤"都是实际瓶颈的直观感受——"胖"是单表数据太多，"挤"是单库承载不住压力。

- **关联知识**:
  - 与计算机体系结构的层次缓存（L1/L2/L3 Cache）类比：分表≈增加缓存行，分库≈增加核心数
  - 与微服务拆分（Microservice Decomposition）思想一致：先垂直拆分（按业务域），再水平扩展（按数据量）
  - 与操作系统的虚拟内存管理共享概念：通过分页（Paging）将大内存空间映射为小页面

### 📖 深度解答

#### 一、核心概念（Core Concepts）

**分表（Table Partitioning / Table Splitting）**：在同一个数据库实例内部，将一张大表拆分成多张结构相同的子表。所有子表共享同一个数据库连接池、同一个 Buffer Pool、同一份 CPU 和 I/O 资源。

**分库（Database Sharding）**：将数据分布到多个独立的数据库实例（Database Instance）中。每个数据库实例拥有独立的连接池、Buffer Pool、CPU、内存、磁盘 I/O。

**分库分表（Combined Sharding）**：同时进行分库和分表，数据被分布到多个库的多个表中，是分布式数据库最完整的形态。

| 维度 | 分表（同库） | 分库（不同实例） | 分库分表 |
|------|------------|----------------|---------|
| 单表数据量 | 大幅减少 | 减少 | 大幅减少 |
| 连接数上限 | 不解决 | 线性扩展 | 线性扩展 |
| CPU瓶颈 | 不解决 | 线性扩展 | 线性扩展 |
| I/O 瓶颈 | 轻微改善 | 有效缓解 | 有效缓解 |
| 事务支持 | 完整支持 | 需分布式事务 | 需分布式事务 |
| 复杂度 | 低 | 高 | 最高 |

#### 二、底层原理（Underlying Principles）

**单表的瓶颈分析与量化**：

1. **B+树深度与 I/O 次数**：
   - 设 InnoDB 页大小为 16KB，非叶子节点每行索引项约 14 字节（8B 主键 + 6B 指针）
   - 每个非叶节点可存储约 1170 个索引项（16KB / 14B）
   - 叶节点每行数据约 200B（平均行大小），每个叶节点可存约 80 行
   - 总行数 = 1170^(h-1) × 80
   - h=3 时约 1.1 亿行 → 但在实际生产中，h=3 时最佳性能的行数上限为 **500万~2000万行**

2. **MySQL 连接数瓶颈**：
   ```sql
   SHOW VARIABLES LIKE 'max_connections';  -- 默认 151
   SHOW STATUS LIKE 'Threads_connected';
   ```
   单个 MySQL 实例的最大连接数有上限（默认 151，可调但受内存限制）。每个连接消耗约 256KB~1MB 的内存。微服务架构中，每个服务实例需要一个连接池，连接数是稀缺资源。

3. **磁盘 I/O 瓶颈的量化**：
   - 普通 HDD：IOPS ≈ 100~200
   - SATA SSD：IOPS ≈ 10,000~50,000
   - NVMe SSD：IOPS ≈ 500,000~1,000,000
   - 单个数据库实例的写入操作需要写 Binlog、Redo Log、数据文件、Doublewrite Buffer
   - 当单库 QPS 超过 5000，磁盘 IOPS 会成为首要瓶颈

4. **Buffer Pool 锁竞争**：
   - InnoDB Buffer Pool 内部有多个 Free List、LRU List、Flush List
   - 高并发下对这些链表的 Mutex 竞争会急剧增加
   - 大表意味着更多的脏页（Dirty Page）管理，加剧锁竞争

**分库的底层架构**：

分库的架构主要有两种模式：

```
模式一：JDBC 驱动层（Client-Side Sharding）
┌─────────────────────────────┐
│      应用服务 (Application)     │
│  ┌───────────────────────┐  │
│  │ ShardingSphere-JDBC   │  │
│  │  SQL解析 → 路由 → 执行  │  │
│  └──────┬──────┬──────┬──┘  │
│         │      │      │     │
└─────────┼──────┼──────┼─────┘
          │      │      │
    ┌─────┴─┐ ┌─┴────┐ ┌┴─────┐
    │ ds_0  │ │ ds_1 │ │ ds_2  │
    │ 库0   │ │ 库1  │ │ 库2   │
    └───────┘ └──────┘ └──────┘

模式二：Proxy 代理层（Server-Side Sharding）
┌──────────┐
│  应用服务   │
└─────┬────┘
      │
┌─────┴──────┐
│ ShardingSphere │
│   -Proxy    │
│   SQL解析/路由 │
└─────┬──────┘
      │
    ┌─┼─────┐
  ds_0 ds_1 ds_2
```

**递进关系：先分表 → 分库 → 分库分表**：

```
性能瓶颈分级决策树：
┌─ 单表数据量 > 500万行 或 行数据过大？
│  ├─ 是 → 分表（先尝试，成本最低）
│  └─ 否 → 检查下一个条件
│
┌─ 单库QPS > 5000 或 连接数不足？
│  ├─ 是 → 分库（水平扩展节点）
│  └─ 否 → 保持现状
│
┌─ 既大表又高并发？
   └─ 分库分表（最终方案）
```

#### 三、实践应用（Practical Applications）

**分表的典型实践**：

```sql
-- 场景：订单表单月数据量过大
-- 按月水平分表（Range Sharding）
public class OrderService {
    public List<Order> queryOrders(Long userId, LocalDate start, LocalDate end) {
        List<String> tables = getMonthlyTables(start, end);
        List<Order> result = new ArrayList<>();
        for (String table : tables) {
            String sql = "SELECT * FROM " + table + " WHERE user_id = ?";
            result.addAll(jdbcTemplate.query(sql, userId));
        }
        return result;
    }

    private List<String> getMonthlyTables(LocalDate start, LocalDate end) {
        List<String> tables = new ArrayList<>();
        LocalDate cursor = start.withDayOfMonth(1);
        while (!cursor.isAfter(end)) {
            tables.add("order_" + cursor.format(DateTimeFormatter.ofPattern("yyyyMM")));
            cursor = cursor.plusMonths(1);
        }
        return tables;
    }
}
```

**分库的典型实践**：

```yaml
# ShardingSphere 分库分表配置（分4库 × 16表）
rules:
  - !SHARDING
    tables:
      order:
        actualDataNodes: ds_${0..3}.order_${0..15}
        databaseStrategy:
          standard:
            shardingColumn: user_id
            shardingAlgorithmName: db_hash
        tableStrategy:
          standard:
            shardingColumn: user_id
            shardingAlgorithmName: table_hash
    shardingAlgorithms:
      db_hash:
        type: HASH_MOD
        props:
          shardingCount: 4
      table_hash:
        type: HASH_MOD
        props:
          shardingCount: 16

# 路由计算：库 = user_id % 4 , 表 = user_id % 16
```

**数据迁移方案（双写迁移 Double-Write Migration）**：
```
阶段1：并行双写 → 应用写入旧库+新库
阶段2：全量同步 → ETL 同步历史数据
阶段3：切换读流量 → 验证后切换写流量
阶段4：下线旧库
```

#### 四、深入思考（Deep Thinking）

**分库带来的分布式问题**：

1. **分布式事务（Distributed Transaction）**：
   - XA 协议（2PC）：强一致性，性能低下
   - Seata AT 模式：全局锁 + 分支事务，性能折中
   - TCC：业务侵入性强，性能最优
   - SAGA：适用于长事务、最终一致性场景

2. **分布式 ID 生成**：
   Snowflake：1 bit | 41 bits 时间戳 | 10 bits 工作节点 | 12 bits 序列号

3. **跨库聚合查询**：
   - 排序：归并排序（Merge Sort）
   - 分页：取 offset+limit 到各分片后合并
   - COUNT/SUM/AVG：各分片计算后二次聚合

4. **数据倾斜（Data Skew）**：热点数据集中，需复合分片键

5. **扩容方案对比**：Mod翻牌、一致性Hash、Range预分片、虚拟槽

**中间件选型对比**：

| 中间件 | 架构模式 | 语言 | 特点 |
|-------|---------|------|------|
| ShardingSphere | JDBC + Proxy | Java | Apache顶级项目，功能全面 |
| MyCat | Proxy | Java | 传统方案，部署简单 |
| Vitess | Proxy | Go | CNCF，云原生 |
| TiDB | 原生分布式 | Rust/Go | NewSQL，自动分片 |

### 🗺️ 回答思路

**答题逻辑框架**（问题-方案-代价结构）：
1. **问题**：先阐述单库单表的瓶颈（数据量、连接数、IOPS）
2. **方案**：分表和分库如何解决这些瓶颈
3. **递进关系**：分表→分库→分库分表的演进路径
4. **代价**：分布式带来的复杂度

**重点得分点**：
- 清楚区分"分表解决什么问题"和"分库解决什么问题"
- 用量化数据说话（max_connections=151、B+树高度计算、IOPS数值）
- 提到分布式带来的代价和解决方案
- 给出实际配置示例

**常见误区**：
- 认为分库一定比分表好（忽略成本）
- 忽略分布式事务的代价
- 认为分库分表可以解决所有问题

**时间分配建议**（5分钟答案）：
| 阶段 | 时间 | 内容 |
|------|------|------|
| 瓶颈分析 | 1.5分钟 | 单表/单库瓶颈量化 |
| 分表作用 | 1分钟 | 概念、场景、配置 |
| 分库作用 | 1分钟 | 概念、场景、配置 |
| 分布式代价 | 1.5分钟 | 事务/ID/查询/扩容 |

**过渡话术**：
- "在分析了单库单表的瓶颈后，我们来看分表如何解决数据量问题……"
- "当分表还不够时，就需要分库来提供更多计算资源……"
- "分库分表带来了可观的能力提升，但也引入了分布式系统的经典挑战……"
"""

# Add Q1
print("=" * 60)
print("Adding Question 1: 垂直分表和水平分表的区别")
print("=" * 60)
result1 = qm.add(
    question="垂直分表和水平分表的区别（Difference between Vertical Partitioning and Horizontal Partitioning）",
    answer=q1_answer.strip(),
    tags=["垂直分表", "水平分表", "分表", "分片", "Sharding", "数据库优化", "分区"],
    difficulty="medium",
    source="/面经助手-20260704"
)
print(f"Result: {result1['id']}")

# Add Q2
print("\n" + "=" * 60)
print("Adding Question 2: 分库、分表分别的作用")
print("=" * 60)
result2 = qm.add(
    question="分库、分表分别的作用（The Roles and Purposes of Database Sharding and Table Partitioning）",
    answer=q2_answer.strip(),
    tags=["分库", "分表", "分库分表", "Sharding", "数据库扩展", "分布式数据库", "扩容"],
    difficulty="hard",
    source="/面经助手-20260704"
)
print(f"Result: {result2['id']}")

print("\n" + "=" * 60)
print("All questions added successfully!")
print(f"Total questions in bank: {len(qm.index['questions'])}")
