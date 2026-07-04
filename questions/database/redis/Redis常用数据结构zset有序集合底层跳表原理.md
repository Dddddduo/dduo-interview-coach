---
id: q0018
question: "Redis 常用数据结构；zset（有序集合）底层跳表原理"
category: redis
tags: ["Redis", "数据结构", "ZSet", "跳表", "Skip List", "压缩列表"]
difficulty: hard
created: 2026-07-04 12:50:00
source: /面经助手-20260704
---

# Redis 常用数据结构；zset（有序集合）底层跳表原理

### 🧠 联想记忆法

**记忆口诀："字列哈集有，位超地流跳"**

每个字对应一种数据结构，串联成故事方便回忆：

1. **字（String）** — 字符串，最基础，像"字"一样简单
2. **列（List）** — 列表，像"队列"排队
3. **哈（Hash）** — 哈希，像"哈"希表存对象
4. **集（Set）** — 集合，像"集"合去重
5. **有（ZSet / Sorted Set）** — 有序集合，带"有"序的集合
6. **位（Bitmap）** — 位图，像"位"运算
7. **超（HyperLogLog）** — 超低内存基数统计，"超"级省空间
8. **地（GEO）** — 地理位置，"地"理坐标
9. **流（Stream）** — 消息流，"流"式消息队列

**ZSet 跳表记忆："层塔跳查"**

想象一栋楼（跳表）：
- **层（Level）** — 楼层越高人越少（高层节点少）
- **塔（Tower）** — 每个节点像塔，高度随机（随机层数，P=1/4）
- **跳（Skip）** — 坐电梯跳跃，不用爬每层楼梯
- **查（Search）** — O(log N) 查到目标，比链表 O(N) 快得多

**为什么 Redis 用跳表不用红黑树？→ "简范并"**

- **简** — 实现简单，代码量少
- **范** — 范围查询友好，跳表双向遍历即可
- **并** — 并发加锁粒度更小（锁节点而非整棵树）

---

### 📖 深度解答

---

#### 第一层：核心概念 — Redis 九大数据结构概述

Redis（Remote Dictionary Server）是一个高性能的键值对（Key-Value）内存数据库，其成功很大程度上归功于丰富的数据结构。以下逐一概述每种数据结构的核心用途：

**1. String（字符串）**
最基础的数据结构，value 最大 512MB。底层实现为 SDS（Simple Dynamic String，简单动态字符串），相比 C 字符串具备 O(1) 长度获取、预分配空间、二进制安全等优势。用途：缓存（如验证码 123456）、计数器（如商品浏览量）、分布式锁（SETNX 命令）、对象序列化存储。

**2. List（列表）**
双向链表（linked list）或压缩列表（ziplist，元素少时），支持双端插入/弹出（LPUSH/RPOP）。用途：消息队列（BRPOP 阻塞消费）、最新消息列表（如微博时间线 LPUSH + LTRIM）。注意：Redis 官方已逐步转向 Stream 作为消息队列的首选。

**3. Hash（哈希）**
字典结构，类似 Java 的 HashMap，底层可用哈希表（hashtable）或压缩列表（ziplist，字段少时）。用途：存储对象（如用户信息 `HSET user:1001 name "Alice" age 25`），比 String 序列化整对象更灵活，支持单独修改某个字段。

**4. Set（集合）**
无序、不可重复的元素集合，底层用哈希表（hashtable）或整数集合（intset，全为整数时）。核心价值在集合运算：交集（SINTER）、并集（SUNION）、差集（SDIFF）。用途：标签系统（如文章标签）、共同好友、抽奖去重。

**5. ZSet / Sorted Set（有序集合）**
**本题重点**，见下文详细展开。每个元素关联一个 score（分值），按 score 排序。用途：排行榜（如游戏积分排名）、延时队列（score 存时间戳）、限流滑动窗口。

**6. Bitmap（位图）**
底层实际是 String，按位（bit）操作，8 个 bit = 1 字节。用途：用户签到（365 天只需 46 字节）、在线状态统计（SETBIT/GETBIT/BITCOUNT）。

**7. HyperLogLog（超日志结构）**
基于概率算法（HyperLogLog 算法）的基数统计，标准误差约 0.81%。12KB 内存即可统计 2^64 个元素的基数（不重复元素数量）。用途：UV（独立访客）统计，如 `PFADD page:1 user1 user2 user3` + `PFCOUNT page:1`。

**8. GEO（地理空间）**
底层基于 ZSet 实现，将经纬度编码为 52 位整数作为 score。支持 GEOADD 添加位置、GEORADIUS 范围查询（附近的人）、GEODIST 距离计算。用途：附近的人、打车定位、地理围栏。

**9. Stream（流）**
Redis 5.0 引入的、类似 Kafka 的日志型消息队列。支持消息持久化、消费者组（Consumer Group）、ACK 确认机制。相比 List/发布订阅（Pub/Sub）更可靠。用途：消息队列、事件溯源（Event Sourcing）、日志采集。

---

#### 第二层：底层原理 — ZSet 编码机制与跳表原理

##### 2.1 ZSet 的两种底层编码

ZSet 根据数据量和元素大小自动选择底层编码：

| 编码方式 | 数据结构 | 适用条件 |
|---------|---------|---------|
| **ziplist（压缩列表）** | 连续内存块，元素按 score 排序紧密排列 | 元素少且元素值小时 |
| **skiplist + dict（跳表 + 字典）** | 跳表维护有序性 + 字典（哈希表）提供 O(1) 按成员查分值 | 元素多或元素值大时 |

**切换阈值（redis.conf 配置）：**
```
zset-max-ziplist-entries 128    # 元素数不超过 128
zset-max-ziplist-value 64       # 每个元素值（ele）不超过 64 字节
```
当元素个数 > 128 或任一元素值 > 64 字节时，自动从 ziplist 转换为 skiplist+dict，且**不可逆**（只能单向转换，从节省内存转向高性能）。

**为何 ziplist 在小数据量时更优？**
- ziplist 是连续内存，Cache Locality（缓存局部性）好，一个 CPU 缓存行（Cache Line）可加载多个元素
- skiplist 每个节点需独立 malloc，内存碎片 + 指针额外开销（约 20+ 字节/层）

##### 2.2 跳表（Skip List）核心原理

**什么是跳表？**
跳表由 William Pugh 在 1990 年提出，本质是在有序链表（Ordered Linked List）上建立多级索引（Multi-Level Index），通过"跳跃"跳过大量中间节点，实现近似二分查找的效率。

**形象理解：**
- **一级索引**：每隔一个节点取一个到上层（相当于高速公路的快车道）
- **二级索引**：再每隔一个节点取一个到更上层
- 查找时从最高层开始，快速定位区间，逐层下降找到目标

```
Level 3:  1 -----------------------------> 9
Level 2:  1 ------------> 5 ------------> 9
Level 1:  1 ---> 3 ---> 5 ---> 7 ---> 9
Level 0:  1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10
```

查找元素 8 的过程：Level 3 到达 9，发现 9 > 8 → 降 Level 2 从 1 跳到 5 → Level 1 从 5 跳到 7 → Level 0 从 7 遍历到 8。只需 4 步，而原始链表需要 8 步。

**层数（Level）与随机化：**
- 每个新节点插入时，随机决定其层数
- Redis 实现中，概率 P = 1/4（ZSKIPLIST_P = 0.25），最高层数限制为 64（ZSKIPLIST_MAXLEVEL = 64）
- 层数生成算法：
  ```
  层数 = 1
  while (random() < 0.25 and 层数 < 64):
      层数++
  ```
- 数学期望：平均层数 = 1 / (1 - P) = 1 / 0.75 ≈ 1.33 层
- 这使得跳表在空间和速度之间取得平衡：P=1/4 比 P=1/2 更节省内存（每层索引节点更少），但查找速度稍慢（层数更多）


**为什么不用红黑树/AVL树？**

| 维度 | 跳表 | 红黑树 / AVL树 |
|------|------|---------------|
| 实现复杂度 | 实现简单，约 200 行 C 代码 | 复杂，需处理旋转（Rotation）、染色（Coloring），约 500+ 行 |
| 范围查询 | 天然支持：找到起点后沿 backward/forward 指针遍历区间，无需回溯 | 需中序遍历，需维护栈或 parent 指针，实现复杂 |
| 并发控制 | 仅需锁住受影响的节点，细粒度锁 | 需锁住整棵子树，锁粒度大 |
| 调试难度 | 可视化简单，插入/删除不破坏全局结构 | 旋转操作导致结构突变，调试困难 |
| 内存占用 | 约 N * avgLevel 个指针（额外 ~1.33N 指针） | 每个节点 2 个子节点指针 + 1 个 parent 指针 + 颜色位 |
| 查找效率 | 平均 O(log N)，最坏 O(N)（几乎不发生） | 严格 O(log N) |

**总结：Redis 作者 antirez 的原话 — "跳表实现起来更简单，调试更容易，而且范围查询操作（ZRANGE）更高效。"**

---

#### 第三层：实践应用 — Redis 跳表具体实现分析

##### 3.1 核心数据结构（C 语言，Redis 源码 t_zset.c）

```c
/* 跳表节点 */
typedef struct zskiplistNode {
    sds ele;                          // 成员（member），SDS 字符串
    double score;                     // 分值（score），排序依据
    struct zskiplistNode *backward;   // 后退指针，指向上一个节点（用于反向遍历）
    struct zskiplistLevel {
        struct zskiplistNode *forward; // 前进指针，指向同层的下一个节点
        unsigned long span;            // 跨度，从当前节点到 forward 节点跨越了多少个元素
    } level[];                        // 层级数组（柔性数组，C99 特性）
} zskiplistNode;

/* 跳表 */
typedef struct zskiplist {
    struct zskiplistNode *header, *tail; // 头节点（哨兵）+ 尾节点
    unsigned long length;                // 节点总数（不含头节点）
    int level;                           // 当前最大层数（不含头节点）
} zskiplist;
```

**关键理解：**
- **header（头节点）** — 哨兵节点（Sentinel），不存储实际数据，level 数组固定 64 层，所有 forward 初始化为 NULL，span 初始化为 0
- **level[]（层级数组）** — 柔性数组，每个节点实际占用的层数是随机生成的，level[0] 总是存在
- **span（跨度）** — 精髓设计！用于快速计算元素的排名（Rank），ZRANK 命令无需遍历就可知道元素排第几
- **backward（后退指针）** — 仅 level[0] 有 backward，用于 ZREVRANGE 反向遍历

**辅助结构 — dict（字典）：**
```c
/* ZSet 整体结构 */
typedef struct zset {
    dict *dict;            // 字典：key=成员(ele), value=分值(score)
    zskiplist *zsl;        // 跳表：按 score 排序
} zset;
```
- **dict 的作用**：ZSCORE 命令 O(1) 按成员查分值；ZSet 的成员唯一性检查通过 dict 完成
- **数据冗余**：ele（成员）和 score（分值）在跳表和字典中各存一份指针，不复制数据

##### 3.2 查找过程（O(log N)）

```
查找 score=8.0 的元素：
1. 从 header 的最高层（当前 level-1）开始
2. 在每一层向前移动，直到下一节点的 score > 目标 score
3. 降一层继续
4. 最终在 level[0] 找到目标
```

**ZRANK 排名计算：**
查找过程中累加经过节点的 span 值，即可得到排名。无需额外遍历，这就是 span 字段的妙用。

##### 3.3 插入过程（O(log N)）

```
插入 (ele="Bob", score=8.0)：
1. 查找插入位置，同时记录每层需要更新的节点（update[] 数组）和累积排名（rank[] 数组）
2. 随机生成新节点的层数 level
3. 如果新 level > 当前跳表 level，更新 update[] 中更高层指向 header
4. 逐层插入：调整每层 forward 指针和 span 值
5. 设置 backward 指针
6. 更新跳表 level 和 length
7. 同步更新 dict（ZADD 同时操作 dict + skiplist）
```

##### 3.4 删除过程（O(log N)）

与插入对称，逐层调整 forward 指针和 span 值，释放节点内存，同步删除 dict 中的键值对。

---

#### 第四层：深入思考

##### 4.1 跳表 vs B+ 树：为什么 MySQL 用 B+ 树，Redis 用跳表？

| 维度 | Redis 跳表 | MySQL B+ 树 |
|------|-----------|------------|
| 存储介质 | **内存**（随机访问无成本） | **磁盘**（需最小化 I/O） |
| 节点大小 | 小粒度节点（1 个元素） | 大粒度页（通常 16KB，读一批数据） |
| 扇出（Fan-out） | 低（平均 1/(1-P) 个指针） | 高（一个页存几百个 key） |
| 树高 | O(log N)，~20 层（百万级数据） | 通常 3~4 层（千万级数据） |
| 范围查询 | 双向链表遍历 | 叶节点链表遍历 |

**结论：** 内存场景下跳表更灵活；磁盘场景下 B+ 树通过高扇出降低树高，减少 I/O 次数。

##### 4.2 跳表最坏情况分析

- 最坏情况：所有节点都只生成 1 层（概率极低：0.75^N），此时退化为链表，查找 O(N)
- 但概率指数级衰减：N=1000 时，概率约为 10^-125，实际几乎不可能发生
- 随机化算法保证的是"期望性能"而非"最坏性能保证"

##### 4.3 ZSet 的应用场景深度解析

**场景 1：实时排行榜**
```bash
# 玩家积分更新
ZADD game:scores 1500 "player:1001"
ZADD game:scores 2000 "player:1002"
# 获取 Top 10
ZREVRANGE game:scores 0 9 WITHSCORES
# 查看自己排名
ZRANK game:scores "player:1001"
```

**场景 2：延时队列**
```bash
# 任务到期时间戳作为 score
ZADD delay:queue 1690000000 "task:send_email"
# 消费线程轮询到期的任务
ZRANGEBYSCORE delay:queue 0 <current_timestamp> LIMIT 0 10
```

**场景 3：滑动窗口限流**
```bash
# 每个请求的时间戳作为一个成员，score 也设为时间戳
ZADD rate:limit:user:1001 1690000000 1690000000
# 删除窗口外的请求
ZREMRANGEBYSCORE rate:limit:user:1001 0 <window_start>
# 统计窗口内请求数
ZCARD rate:limit:user:1001
```

---

##### 4.4 Java 简化版跳表实现

以下代码展示跳表的核心机制（查找/插入/删除），仅用于理解原理：

```java
import java.util.*;

/**
 * 简化版跳表 — 用于理解 Redis ZSet 底层原理
 * 特点：
 *  - 泛型，支持任意可比较类型
 *  - 随机层数（P=0.25，同 Redis）
 *  - 支持查找、插入、删除、范围查询
 */
public class SkipList<K extends Comparable<? super K>, V> {

    private static final double P = 0.25;        // 概率因子，同 Redis ZSKIPLIST_P
    private static final int MAX_LEVEL = 64;     // 最大层数，同 Redis

    private final Node<K, V> header;            // 哨兵头节点
    private int level;                           // 当前最大层数
    private int size;                            // 元素个数

    static class Node<K, V> {
        K key;
        V value;
        Node<K, V>[] forward;   // 每层的前进指针
        int nodeLevel;          // 该节点的层数

        @SuppressWarnings("unchecked")
        Node(K key, V value, int level) {
            this.key = key;
            this.value = value;
            this.nodeLevel = level;
            this.forward = new Node[level];
        }
    }

    public SkipList() {
        this.header = new Node<>(null, null, MAX_LEVEL);
        this.level = 1;
        this.size = 0;
    }

    /**
     * 随机生成层数（同 Redis 算法）
     * 层数从 1 开始，每次概率为 P 时加一层，不超过 MAX_LEVEL
     */
    private int randomLevel() {
        int lvl = 1;
        Random rand = new Random();
        while (rand.nextDouble() < P && lvl < MAX_LEVEL) {
            lvl++;
        }
        return lvl;
    }

    /**
     * 查找 — O(log N) 平均
     * 返回与 key 关联的 value，不存在返回 null
     */
    public V search(K key) {
        Node<K, V> current = header;
        // 从最高层向下查找
        for (int i = level - 1; i >= 0; i--) {
            while (current.forward[i] != null
                    && current.forward[i].key.compareTo(key) < 0) {
                current = current.forward[i];
            }
        }
        // 到达第 0 层，检查下一个节点
        current = current.forward[0];
        if (current != null && current.key.compareTo(key) == 0) {
            return current.value;
        }
        return null;
    }

    /**
     * 插入 — O(log N) 平均
     * 如果 key 已存在，更新 value；否则插入新节点
     */
    public void insert(K key, V value) {
        // update[] 记录每层需要更新的节点
        Node<K, V>[] update = new Node[MAX_LEVEL];
        Node<K, V> current = header;

        // 1. 查找插入位置，记录每层的前驱
        for (int i = level - 1; i >= 0; i--) {
            while (current.forward[i] != null
                    && current.forward[i].key.compareTo(key) < 0) {
                current = current.forward[i];
            }
            update[i] = current;
        }
        current = current.forward[0];

        // 2. 如果 key 已存在，更新 value
        if (current != null && current.key.compareTo(key) == 0) {
            current.value = value;
            return;
        }

        // 3. 随机生成新节点层数
        int newNodeLevel = randomLevel();

        // 4. 如果新层数 > 当前跳表层数，更新 update 数组
        if (newNodeLevel > level) {
            for (int i = level; i < newNodeLevel; i++) {
                update[i] = header;
            }
            level = newNodeLevel;
        }

        // 5. 创建新节点并逐层插入
        Node<K, V> newNode = new Node<>(key, value, newNodeLevel);
        for (int i = 0; i < newNodeLevel; i++) {
            newNode.forward[i] = update[i].forward[i];
            update[i].forward[i] = newNode;
        }

        size++;
    }

    /**
     * 删除 — O(log N) 平均
     * 返回被删除节点的 value，不存在返回 null
     */
    public V delete(K key) {
        Node<K, V>[] update = new Node[MAX_LEVEL];
        Node<K, V> current = header;

        // 1. 查找待删除节点，记录每层的前驱
        for (int i = level - 1; i >= 0; i--) {
            while (current.forward[i] != null
                    && current.forward[i].key.compareTo(key) < 0) {
                current = current.forward[i];
            }
            update[i] = current;
        }
        current = current.forward[0];

        // 2. 未找到
        if (current == null || current.key.compareTo(key) != 0) {
            return null;
        }

        // 3. 逐层删除
        for (int i = 0; i < level; i++) {
            if (update[i].forward[i] != current) {
                break;  // 更高层不包含此节点
            }
            update[i].forward[i] = current.forward[i];
        }

        // 4. 更新跳表层数（可能降低）
        while (level > 1 && header.forward[level - 1] == null) {
            level--;
        }

        size--;
        return current.value;
    }

    /**
     * 范围查询 — 跳表的核心优势
     * 返回 key 在 [from, to] 范围内的所有键值对
     */
    public List<Map.Entry<K, V>> rangeQuery(K from, K to) {
        List<Map.Entry<K, V>> result = new ArrayList<>();
        Node<K, V> current = header;

        // 找到 from 的起始位置
        for (int i = level - 1; i >= 0; i--) {
            while (current.forward[i] != null
                    && current.forward[i].key.compareTo(from) < 0) {
                current = current.forward[i];
            }
        }

        // 沿第 0 层遍历
        current = current.forward[0];
        while (current != null && current.key.compareTo(to) <= 0) {
            result.add(new AbstractMap.SimpleEntry<>(current.key, current.value));
            current = current.forward[0];
        }

        return result;
    }

    public int size() {
        return size;
    }

    // 测试
    public static void main(String[] args) {
        SkipList<Integer, String> sl = new SkipList<>();

        sl.insert(3, "Alice");
        sl.insert(1, "Bob");
        sl.insert(4, "Charlie");
        sl.insert(2, "David");
        sl.insert(5, "Eve");

        System.out.println("查找 key=3: " + sl.search(3));     // Alice
        System.out.println("查找 key=6: " + sl.search(6));     // null

        System.out.println("\n范围查询 [2, 4]: ");
        for (Map.Entry<Integer, String> e : sl.rangeQuery(2, 4)) {
            System.out.println("  " + e.getKey() + " -> " + e.getValue());
        }

        System.out.println("\n删除 key=3: " + sl.delete(3));   // Alice
        System.out.println("删除后查找 key=3: " + sl.search(3)); // null
        System.out.println("当前元素数: " + sl.size());         // 4
    }
}
```

---

### 🗺️ 回答思路

面试中遇到 "Redis 数据结构与 ZSet 跳表" 时，建议按以下思路组织回答，层层递进，体现深度和广度：

**第 1 步：总览全局（展示广度）**
先快速过一遍 9 种数据结构，每种一句话说出核心用途和典型命令。让面试官知道你全面掌握 Redis。如果你有实战经验，结合具体业务举例（如"我们用 Bitmap 做签到，HyperLogLog 做 UV"）。

**第 2 步：聚焦 ZSet 编码（展示深度切入点）**
说清楚 ZSet 有两种底层编码：
- 小数据用 ziplist（连续内存，缓存友好）
- 大数据用 skiplist+dict（跳表加速查找 + 字典 O(1) 查分值）
- 提到阈值 128/64 并解释单向转换原因

**第 3 步：跳表原理（核心考点）**
- 画图说明多级索引如何加速查找
- 解释随机层数（P=1/4, Max=64）
- 比较红黑树/AVL：强调"简（实现简单）范（范围查询）并（并发友好）"

**第 4 步：Redis 源码实现（体现源码阅读能力）**
说出 zskiplistNode 和 zskiplist 的结构，特别强调 span 字段用于排名计算，backward 用于反向遍历。这让面试官感受到你读过源码。

**第 5 步：手写代码（让面试官无可挑剔）**
主动提出用 Java 实现一个简化版跳表。面试官通常不会要求写完整的 Redis 实现，能写出 search/insert/delete 的核心逻辑即可。

**第 6 步：升华（拉开差距的关键）**
- 对比 B+ 树：内存 vs 磁盘的存储介质差异
- 最坏情况分析及概率论证
- 实际项目中的 ZSet 应用场景

**避坑指南：**
- ❌ 不要说跳表和 B+ 树谁更"好"——要说明它们适用不同场景
- ❌ 不要混淆 ziplist 和 skiplist 的"list"——完全是两回事
- ❌ 不要认为跳表比红黑树"快"——O(log N) 同级，区别在实现难度和范围查询
- ✅ 主动提 span 字段和 ZRANK 的关系，这是加分项
- ✅ 提到 Redis 官方也在考虑引入新的数据结构（如 listpack 替代 ziplist），展现你关注前沿

**复杂度总结：**
| 操作 | 平均时间复杂度 | 最坏时间复杂度 |
|------|--------------|--------------|
| 查找（search） | O(log N) | O(N) |
| 插入（insert） | O(log N) | O(N) |
| 删除（delete） | O(log N) | O(N) |
| 范围查询（range） | O(log N + M) | O(N) |
| ZRANK（排名） | O(log N) | O(N) |

*注：M 为返回的元素数；最坏情况几乎不会发生（概率指数级小）*
