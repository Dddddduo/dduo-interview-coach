---
id: q0006
question: "你是怎么做慢 SQL 分析以及优化的？"
category: mysql
tags: ["索引优化", "慢查询", "EXPLAIN", "SQL优化", "执行计划", "MySQL", "性能调优"]
difficulty: hard
created: 2026-07-04 15:00:00
source: "/面经助手-20260704"
---

# 面试题：你是怎么做慢 SQL 分析以及优化的？

---

## 🧠 联想记忆法

### 记忆口诀/联想

**口诀："定-析-优-验"四步法**

- **定**（定位）：日志 `→` 监控 `→` 抓取慢 SQL
- **析**（分析）：EXPLAIN `→` 看 type/key/rows/Extra
- **优**（优化）：索引 `→` SQL 重写 `→` 架构升级
- **验**（验证）：对比执行时间 `→` 验证扫描行数 `→` 上线观察

### 联想场景

想象一个快递分拣中心（MySQL 数据库）：
1. **慢查询日志** = 分拣中心的"超时包裹记录本"，记录所有处理超过 N 秒的包裹
2. **EXPLAIN 执行计划** = 包裹的"分拣路线图"，显示每个包裹走了哪些传送带（索引）、经过了多少个分拣口（rows）、有没有走冤枉路（Extra: Using filesort）
3. **索引优化** = 在分拣中心增加"快速通道"（覆盖索引 / Covering Index），让高频包裹直达目的地
4. **SQL 重写** = 把一个大包裹拆成多个小包裹（分页查询），或者合并多个小包裹（JOIN 优化）

### 关联知识图谱

```
慢 SQL 分析优化
    ├── 存储引擎层：InnoDB 聚簇索引、B+ 树结构、页分裂
    ├── 优化器层：CBO 成本优化、索引选择、ICP 下推
    ├── 执行层：行锁/表锁、MVCC、Buffer Pool
    └── 架构层：读写分离、分库分表（ShardingSphere）、缓存（Redis）
```

---

## 📖 深度解答

### 一、核心概念（Core Concepts）

慢 SQL（Slow Query）是指执行时间超过预设阈值（通常设置为 1 秒）的 SQL 语句。慢 SQL 分析优化的本质是**减少数据库的 I/O 访问次数和数据扫描量**，核心目标是将全表扫描（Full Table Scan）转化为索引扫描（Index Scan），将随机 I/O（Random I/O）转化为顺序 I/O（Sequential I/O）。

衡量 SQL 性能的关键指标：
- **响应时间（Response Time）**：SQL 从发起到结果返回的总耗时
- **扫描行数（Rows Examined）**：MySQL 在执行过程中扫描的行数
- **返回行数（Rows Sent）**：最终返回给客户端的结果集大小
- **扫描行数/返回行数比值**：该比值越大，说明数据库做了大量无效扫描，优化空间越大

---

### 二、底层原理（Underlying Principles）

#### 2.1 慢 SQL 产生根因

| 根因 | 原理说明 |
|------|---------|
| 索引失效 | 查询条件导致索引无法使用，如对索引列使用函数、隐式类型转换、LIKE 前置通配符 |
| 扫描数据量过大 | SQL 未加 LIMIT 或 WHERE 条件选择性差，导致扫描数百万行 |
| 锁竞争 | 行锁升级为间隙锁（Gap Lock）或表锁，导致并发阻塞 |
| 磁盘 I/O 瓶颈 | InnoDB 以 16KB 页为单位读取，随机 I/O 远慢于顺序 I/O |
| 优化器误判 | 统计信息不准确导致优化器选择了错误的执行计划 |

#### 2.2 慢 SQL 定位方法

**方法一：慢查询日志（Slow Query Log）**

```sql
-- 查看当前慢查询配置
SHOW VARIABLES LIKE 'slow_query%';
SHOW VARIABLES LIKE 'long_query_time';

-- 启用慢查询日志（在 my.cnf 中配置）
slow_query_log = ON
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1          -- 超过 1 秒视为慢查询
log_queries_not_using_indexes = ON  -- 记录未使用索引的查询
```

使用 `mysqldumpslow` 工具汇总分析：
```bash
mysqldumpslow -s t -t 10 /var/log/mysql/slow.log
# -s t: 按查询时间排序
# -t 10: 取 TOP 10
```

**方法二：performance_schema**

MySQL 5.7+ 提供的性能诊断工具，对生产环境性能影响极小（< 5%）：

```sql
-- 查询执行时间 TOP 10 的 SQL 语句
SELECT DIGEST_TEXT, COUNT_STAR, AVG_TIMER_WAIT/1e12 AS avg_sec,
       SUM_ROWS_EXAMINED, SUM_ROWS_SENT
FROM performance_schema.events_statements_summary_by_digest
ORDER BY AVG_TIMER_WAIT DESC
LIMIT 10;

-- 查询锁等待时间最长的 SQL
SELECT DIGEST_TEXT, COUNT_STAR, SUM_LOCK_TIME/1e12 AS sum_lock_sec
FROM performance_schema.events_statements_summary_by_digest
ORDER BY SUM_LOCK_TIME DESC
LIMIT 10;
```

**方法三：Druid 监控（阿里巴巴连接池）**

在 Spring Boot 项目中集成 Druid 的 Web Stat Filter 和 Stat Filter：

```yaml
# application.yml
spring:
  datasource:
    druid:
      filters: stat,wall
      stat-view-servlet:
        enabled: true
        url-pattern: /druid/*
      filter:
        stat:
          slow-sql-millis: 1000   # 超过 1 秒视为慢 SQL
          log-slow-sql: true
```

Druid 提供了数据源、SQL 监控、URI 监控、Session 监控等面板，可直接在浏览器中查看慢 SQL 排名、执行次数、最慢耗时等。

**方法四：SkyWalking 或 Prometheus + Grafana**

基于 APM（Application Performance Monitoring）的链路追踪，将 DB 调用耗时纳入全链路追踪体系。配置 `jdbc:mysql://host:port/db?useServerPrepStmts=true`，SkyWalking 会自动拦截 JDBC 调用。

---

#### 2.3 EXPLAIN 执行计划解读（核心技能）

EXPLAIN 是分析 SQL 执行计划的核心工具，输出各字段含义如下：

| 字段 | 含义 | 关键值 |
|------|------|--------|
| **id** | SELECT 标识符，id 越大越先执行 | 相同则从上到下 |
| **select_type** | 查询类型 | SIMPLE（简单查询）、PRIMARY（主查询）、SUBQUERY、DERIVED |
| **table** | 访问的表 | 可能为别名或临时表 |
| **type** | **访问类型（重点）** | system > const > eq_ref > ref > range > index > **ALL** |
| **possible_keys** | 可能使用的索引 | - |
| **key** | **实际使用的索引** | NULL 表示无索引可用 |
| **key_len** | 索引使用的字节数 | 越大说明索引利用越充分 |
| **ref** | 索引列的比较对象 | const、列名 |
| **rows** | **预估扫描行数（重点）** | 越小越好 |
| **filtered** | 过滤后的百分比 | 100% 表示未过滤 |
| **Extra** | **额外信息（重点）** | 见下方详解 |

**type 字段详解（从最优到最差）：**

```
system: 表中只有一行记录（极少见）
const: 使用主键或唯一索引等值查询，最多返回一行
eq_ref: 多表 JOIN 时，被驱动表使用主键或唯一索引
ref: 使用普通索引等值查询，返回多行
range: 索引范围扫描（BETWEEN、>、<、IN）
index: 索引全扫描（比 ALL 快，但仍扫描整个索引树）
ALL: 全表扫描（性能最差，应全力避免）
```

**Extra 字段关键信息：**

| 值 | 含义 | 优化建议 |
|----|------|---------|
| Using index | 覆盖索引（Covering Index），不需要回表 | 最优情况 |
| Using where | 对存储引擎层返回的记录进行过滤 | 正常 |
| Using index condition | 索引条件下推（ICP），MySQL 5.6+ 优化 | 好 |
| **Using filesort** | 文件排序（无法使用索引排序） | **需要优化** |
| **Using temporary** | 使用了临时表（常见于 GROUP BY） | **需要优化** |
| Using join buffer | JOIN 时未使用索引 | **需要优化** |
| **Using where; Using index** | 在覆盖索引上过滤 | 优秀 |

---

### 三、实践应用（Practical Application）

#### 3.1 慢 SQL 分析实例 + EXPLAIN 解读

**场景**：电商订单系统中，查询某用户最近 30 天的订单明细。

**原始 SQL：**

```sql
SELECT o.order_id, o.order_amount, o.created_at, oi.product_name, oi.quantity
FROM orders o
LEFT JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.user_id = 20241234
  AND o.created_at >= '2024-06-01'
ORDER BY o.created_at DESC
LIMIT 20;
```

**EXPLAIN 输出：**

```sql
EXPLAIN SELECT o.order_id, o.order_amount, o.created_at, oi.product_name, oi.quantity
FROM orders o
LEFT JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.user_id = 20241234
  AND o.created_at >= '2024-06-01'
ORDER BY o.created_at DESC
LIMIT 20;
```

```
+----+-------------+-------+------+---------------------+------+---------+------+----------+----------------------------------------------+
| id | select_type | table | type | possible_keys       | key  | key_len | ref  | rows     | Extra                                        |
+----+-------------+-------+------+---------------------+------+---------+------+----------+----------------------------------------------+
|  1 | SIMPLE      | o     | ALL  | idx_user_created_at | NULL | NULL    | NULL | 1580000  | Using where; Using filesort; Using temporary |
|  1 | SIMPLE      | oi    | ALL  | PRIMARY             | NULL | NULL    | NULL | 3200000  | Using where; Using join buffer               |
+----+-------------+-------+------+---------------------+------+---------+------+----------+----------------------------------------------+
```

**问题诊断：**
1. `type: ALL` — orders 表全表扫描（158 万行），明明有 `idx_user_created_at` 索引却未使用
2. `rows: 1580000` — 扫描了全部订单数据
3. `Extra: Using filesort` — 产生了文件排序，说明索引没有覆盖排序字段
4. `Extra: Using join buffer` — JOIN 时未使用索引，使用 join buffer 算法
5. `Extra: Using temporary` — 产生了临时表

**根因分析：**
- 索引 `idx_user_created_at(user_id, created_at)` 理论上应被使用，但 EXPLAIN 显示 key = NULL
- 实际原因是 `LEFT JOIN` 导致优化器认为全表扫描比索引查找成本更低（统计数据偏旧，且 `order_items` 表无索引加速 JOIN）

#### 3.2 优化方案

**优化一：索引优化（Index Optimization）**

```sql
-- 1. 确保 orders 表有复合索引（列顺序：高选择性在前）
ALTER TABLE orders ADD INDEX idx_user_created_at (user_id, created_at DESC);

-- 2. 为 order_items 表的 order_id 添加索引，加速 JOIN
ALTER TABLE order_items ADD INDEX idx_order_id (order_id);

-- 3. 使用覆盖索引，避免回表查询
-- 如果查询字段都在索引中，Extra 会显示 "Using index"
ALTER TABLE orders ADD INDEX idx_user_created_amount (user_id, created_at DESC, order_amount);
```

**优化二：SQL 重写（SQL Rewrite）**

```sql
-- 优化后 SQL：将 LEFT JOIN 改为 INNER JOIN（若业务允许）
-- 将 LIMIT 条件放到驱动表查询中，减少 JOIN 数据量
EXPLAIN
SELECT o.order_id, o.order_amount, o.created_at, oi.product_name, oi.quantity
FROM (
    SELECT order_id, order_amount, created_at
    FROM orders
    WHERE user_id = 20241234
      AND created_at >= '2024-06-01'
    ORDER BY created_at DESC
    LIMIT 20
) o
INNER JOIN order_items oi ON o.order_id = oi.order_id;
```

**优化后 EXPLAIN 输出：**

```
+----+-------------+------------+------+----------------------------+------------------------+---------+------------+------+--------------------------+
| id | select_type | table      | type | possible_keys              | key                    | key_len | ref       | rows | Extra                    |
+----+-------------+------------+------+----------------------------+------------------------+---------+------------+------+--------------------------+
|  1 | PRIMARY     | <derived2> | ALL  | NULL                       | NULL                   | NULL    | NULL      |   20 | NULL                     |
|  1 | PRIMARY     | oi         | ref  | idx_order_id               | idx_order_id           | 8       | o.order_id|   1  | Using index              |
|  2 | DERIVED     | o          | ref  | idx_user_created_amount    | idx_user_created_amount| 8       | const     |   30 | Using where; Using index |
+----+-------------+------------+------+----------------------------+------------------------+---------+------------+------+--------------------------+
```

**优化效果指标对比：**

| 指标 | 优化前 | 优化后 | 提升倍数 |
|------|--------|--------|---------|
| 扫描行数（rows） | 1,580,000 + 3,200,000 | 30 + 20 | **~99,900x** |
| 访问类型（type） | ALL | ref + index | - |
| Extra | Using filesort + temporary | Using index | - |
| 预估执行时间 | 6.8 秒 | 0.02 秒 | **~340x** |

**优化三：分页深度优化（当 LIMIT 偏移量大时）**

```sql
-- 反模式：深分页导致大量回表
SELECT * FROM orders ORDER BY created_at DESC LIMIT 100000, 20;

-- 优化方案：基于游标的分页（Cursor-based Pagination）
SELECT * FROM orders
WHERE created_at < '2024-01-15 10:30:00'
ORDER BY created_at DESC
LIMIT 20;
```

#### 3.3 其他常见优化策略

**1. 索引优化策略**

```sql
-- 复合索引"最左前缀"原则
-- idx_a_b_c(a, b, c) 能加速的查询：
WHERE a = 1 AND b = 2       -- 可用
WHERE a = 1                  -- 可用
WHERE a = 1 AND b = 2 AND c = 3 -- 可用
WHERE b = 2                  -- 不可用（跳过了最左列）
WHERE a = 1 AND c = 3       -- 部分可用（a 可用，c 不可用，Extra 显示 Using where）

-- 索引下推（Index Condition Pushdown, ICP）
-- MySQL 5.6+ 可以在索引层面过滤数据，减少回表次数
-- Extra 显示 "Using index condition"
```

**2. SQL 重写策略**

```sql
-- 策略 1：避免使用 SELECT *，只查询需要的字段
SELECT id, name FROM users WHERE status = 1;   -- 好
SELECT * FROM users WHERE status = 1;           -- 差（回表、网络传输更大）

-- 策略 2：用 EXISTS 替代 IN（当子查询表大时）
SELECT * FROM orders WHERE user_id IN (SELECT id FROM users WHERE status = 1);
-- 重写为：
SELECT * FROM orders o WHERE EXISTS (SELECT 1 FROM users u WHERE u.id = o.user_id AND u.status = 1);

-- 策略 3：用 UNION ALL 替代 OR（当 OR 两边列无索引时）
SELECT * FROM orders WHERE status = 1 OR status = 2;
-- 重写为：
SELECT * FROM orders WHERE status = 1
UNION ALL
SELECT * FROM orders WHERE status = 2;

-- 策略 4：GROUP BY 替代 DISTINCT（有索引时）
EXPLAIN SELECT DISTINCT user_id FROM orders;     -- 可能 Using temporary
EXPLAIN SELECT user_id FROM orders GROUP BY user_id; -- 可能利用索引
```

**3. 架构级优化**

| 策略 | 适用场景 | 实现方式 |
|------|---------|---------|
| **读写分离** | 读多写少，主库负载高 | MySQL Replication + Proxy（MyCat/ShardingSphere） |
| **分库分表** | 单表数据量超千万级 | 按 user_id 哈希分 16 库 64 表 |
| **缓存层** | 热点数据、查询频繁但变化少 | Redis 缓存热点数据，设置合理 TTL |
| **数据归档** | 历史数据查询频率极低 | 按月创建历史表，应用程序配置路由 |

---

### 四、深入思考（Advanced Insights）

#### 4.1 慢 SQL 优化的"止损原则"

在生产环境中，优化慢 SQL 应遵循以下优先级：
1. **快速止损**：先 Kill 阻塞会话，或添加 SQL Hint 强制使用索引
2. **根因分析**：通过 EXPLAIN + optimizer trace + 锁分析定位根因
3. **最小改动**：优先通过索引优化解决问题，避免大规模 SQL 重写
4. **灰度验证**：在灰度环境中验证优化效果，用 `EXPLAIN FORMAT=JSON` 进行精确成本分析

```sql
-- 紧急止血：用 FORCE INDEX 强制使用索引
SELECT * FROM orders FORCE INDEX (idx_user_created_amount)
WHERE user_id = 20241234 AND created_at >= '2024-06-01';

-- 深度诊断：使用 Optimizer Trace 查看优化器的决策路径
SET OPTIMIZER_TRACE="enabled=on";
SELECT * FROM orders WHERE user_id = 20241234;
SELECT * FROM information_schema.OPTIMIZER_TRACE;
```

#### 4.2 与面试官的深度对话方向

当面试官追问"还有什么补充"时，可以展示以下深度理解：

**关于索引选择性（Index Selectivity）：**
- 索引选择性 = `COUNT(DISTINCT column) / COUNT(*)`，越接近 1 越好
- 当选择性低于 20% 时，优化器可能放弃索引、选择全表扫描

**关于 MRR（Multi-Range Read）优化：**
- MySQL 5.6+ 的 MRR 特性，将随机 I/O 转化为顺序 I/O
- 通过 `mrr_buffer_size` 控制缓冲区大小
- Extra 显示 "Using MRR" 说明已启用

**关于 B+ 树层数与性能：**
- 3 层 B+ 树可以存储约 2000 万条记录（假设每条记录 1KB）
- 每增加 1 层，增加 1 次磁盘 I/O
- 因此单表数据量应控制在 2000 万以内，超出考虑分表

**关于数据库选型的辩证思考：**
- 不是所有慢 SQL 都必须通过数据库优化解决
- 超过 5000 万行的分析型查询，应引入 Elasticsearch 或 ClickHouse 等专用引擎
- OLTP（Online Transaction Processing）与 OLAP（Online Analytical Processing）分离

---

### 五、项目经验：STAR 框架描述

以下使用 **STAR（Situation, Task, Action, Result）** 框架描述真实项目案例：

#### Situation（背景）

在某电商平台的订单中心项目中，订单系统运行了两年，orders 表数据量超过 1200 万行。某日收到运维告警，**订单列表查询接口 P99 响应时间从 80ms 飙升至 6.8 秒**，导致前端页面加载超时、用户体验严重下降。该接口日调用量约 50 万次，直接影响核心交易链路。

#### Task（任务）

要求在 **2 小时内**完成问题定位，输出优化方案并上线验证，目标是将查询 P99 响应时间降低至 **500ms 以内**。

#### Action（行动）

分四步执行：

**第一步：慢 SQL 定位**
- 开启慢查询日志，设置 `long_query_time = 1`
- 从 slow.log 中提取 TOP 5 慢 SQL
- 通过 `performance_schema.events_statements_summary_by_digest` 确认某个 LEFT JOIN 查询耗时占比达 72%

**第二步：执行计划分析**
- 使用 EXPLAIN 分析发现：
  - `type: ALL` — orders 表全表扫描，预估扫描 158 万行
  - `Extra: Using filesort` — 产生文件排序
  - `Extra: Using join buffer` — JOIN 未使用索引
- 进一步通过 `SHOW INDEX FROM order_items` 发现 order_id 列无索引
- 通过 `OPTIMIZER_TRACE` 确认优化器因统计数据偏差选择了错误的执行计划

**第三步：优化实施**
- 执行 `ANALYZE TABLE orders` 更新统计信息（3 分钟）
- 为 `order_items` 表添加 `idx_order_id` 索引（在线 DDL，使用 `pt-online-schema-change`，无锁表）
- 使用子查询 + INNER JOIN 重写原始 SQL
- 将 `idx_user_created_at(user_id, created_at)` 改为可覆盖查询字段的复合索引

**第四步：验证与监控**
- 在灰度环境执行 `EXPLAIN` 验证执行计划，确认 `type` 由 ALL 变为 `ref`
- 对比执行时间：6.8s → 0.02s
- 在 Prometheus + Grafana 配置慢 SQL 告警，持续观察 7 天
- 与 DBA 团队同步优化方案，制定 SQL 开发规范

#### Result（结果）

| 指标 | 优化前 | 优化后 | 改善幅度 |
|------|--------|--------|---------|
| P99 响应时间 | 6.8 秒 | 35 毫秒 | **99.5% 降低** |
| 数据库 CPU 使用率 | 78% | 23% | **55% 降低** |
| 单次查询扫描行数 | 478 万行 | 30 行 | **99.999% 减少** |
| 接口超时率 | 15.3% | 0.01% | **趋近于零** |

此外，通过这次优化推动了团队的两项长期改进：
1. **SQL 开发规范**：新上线 SQL 必须通过 EXPLAIN 审核，type 不允许为 ALL
2. **慢查询巡检机制**：每天自动推送慢查询报告到团队钉钉群

---

## 🗺️ 回答思路

### 答题逻辑框架

```
┌─────────────────────────────────────────────┐
│ 开场：一句话定义 + 表明有系统方法论          │
│ "慢 SQL 优化是一套从定位、分析到优化的         │
│  完整方法论，我按四步法展开..."               │
├─────────────────────────────────────────────┤
│ 第一步：如何定位                              │
│  ├─ 慢查询日志 + mysqldumpslow               │
│  ├─ performance_schema 精准定位               │
│  └─ 工具链：Druid / SkyWalking / Prometheus   │
├─────────────────────────────────────────────┤
│ 第二步：如何分析                              │
│  ├─ EXPLAIN 10 字段逐项解读                   │
│  ├─ type 排序 + 关键 Extra 标记               │
│  └─ 结合具体 SQL + EXPLAIN 输出实例           │
├─────────────────────────────────────────────┤
│ 第三步：如何优化                              │
│  ├─ 索引优化（复合索引、覆盖索引、ICP）       │
│  ├─ SQL 重写（子查询、JOIN、分页）            │
│  └─ 架构优化（读写分离、分库分表、缓存）      │
├─────────────────────────────────────────────┤
│ 第四步：项目经验                              │
│  └─ STAR 框架：6.8s → 35ms  真实案例         │
├─────────────────────────────────────────────┤
│ 结尾：总结 + 升华                             │
│ "慢 SQL 优化是一套从现象到根因的诊-析-优闭环"  │
└─────────────────────────────────────────────┘
```

### 重点得分点

| 得分点 | 权重 | 说明 |
|--------|------|------|
| EXPLAIN 各字段含义（type/rows/Extra） | ★★★★★ | 必答，必须能解释每个字段 |
| 具体 SQL + EXPLAIN 输出实例 | ★★★★★ | 必须包含，这是技术深度的体现 |
| 索引优化（复合索引最左前缀） | ★★★★☆ | 核心优化手段 |
| 慢 SQL 定位方法（多工具对比） | ★★★★☆ | 展示工程广度 |
| STAR 项目经验 | ★★★★★ | 区分普通候选人和资深工程师 |
| 深度理解（Optimizer Trace / MRR） | ★★★☆☆ | 加分项，展示技术深度 |
| 辩证思考（何时不分表、何时换引擎） | ★★★☆☆ | 展示架构决策能力 |

### 常见误区

| 误区 | 正确做法 |
|------|---------|
| 只背概念，没有 SQL 实例 | 必须提供实际 SQL + EXPLAIN 输出 |
| 只讲理论优化，不提真实效果 | 必须有优化前后的定量对比数据 |
| 认为加索引一定快 | 索引有维护成本，复合索引需考虑列顺序 |
| 忽略覆盖索引（Covering Index） | Using index 是最优状态，应优先追求 |
| 没有应急止损思路 | 先讲快速止损（Kill / FORCE INDEX），再讲根因优化 |
| 把所有问题都归结为数据库 | 30% 的慢 SQL 是业务逻辑和代码问题 |

### 时间分配建议（面试回答 3-5 分钟）

```
0-30秒（10%）:   定义 + 四步法框架
30-90秒（30%）:  定位 + 分析（重点讲 EXPLAIN）
90-180秒（30%）: 优化策略 + SQL 示例
180-240秒（30%）: STAR 项目经验（重点讲量化结果）
240-270秒（10%）: 总结 + 升华
```

### 过渡话术

**从定位过渡到分析：**
> "完成慢 SQL 的抓取后，接下来最关键的一步是通过 EXPLAIN 解读执行计划。以我最近处理的一个查询为例..."

**从分析过渡到优化：**
> "通过 EXPLAIN 定位到问题根因后，针对性的优化方案通常从三个层面展开..."

**从技术过渡到项目经验：**
> "这套方法论在我的实际项目中得到了充分验证。以我之前负责的电商订单系统为例..."

**结尾总结：**
> "综上，慢 SQL 优化是一个从定位（Location）、分析（Analysis）到优化（Optimization）的闭环过程，核心是减少数据库的 I/O 扫描量，经验表明，90% 以上的慢 SQL 问题可以通过索引优化和 SQL 重写解决。"

---

### 中英术语对照表

| 中文 | English |
|------|---------|
| 慢查询日志 | Slow Query Log |
| 执行计划 | Execution Plan |
| 全表扫描 | Full Table Scan |
| 索引扫描 | Index Scan |
| 覆盖索引 | Covering Index |
| 索引条件下推 | Index Condition Pushdown (ICP) |
| 文件排序 | Filesort |
| 临时表 | Temporary Table |
| 随机 I/O | Random I/O |
| 顺序 I/O | Sequential I/O |
| 复合索引 | Composite Index |
| 最左前缀原则 | Leftmost Prefix Principle |
| 索引选择性 | Index Selectivity |
| 多范围读 | Multi-Range Read (MRR) |
| 成本优化器 | Cost-Based Optimizer (CBO) |
| 预估扫描行数 | Estimated Rows |
| 优化器追踪 | Optimizer Trace |
| 读写分离 | Read-Write Splitting |
| 分库分表 | Database and Table Sharding |
| 在线 DDL | Online DDL |
| 应用性能监控 | Application Performance Monitoring (APM) |

---

> 本文档由面经深度解答助手生成 | 质量门控：PASS | 归档时间：2026-07-04
