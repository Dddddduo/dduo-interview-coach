---
id: q0015
question: "Redis 常用数据结构；zset（有序集合）底层跳表原理"
category: redis
tags: ["Redis", "数据结构", "ZSet", "跳表", "Skip List", "压缩列表"]
difficulty: hard
created: 2026-07-04 12:50:00
source: /面经助手-20260704
---

# Redis 常用数据结构；zset（有序集合）底层跳表原理

### 🧠 联想记忆法

**记忆口诀："字列哈集位，超流地 Z 跳"**

取每种数据结构的首字或关键字：
- **字**（String）→ 字节/字符串
- **列**（List）→ 列表
- **哈**（Hash）→ 哈希/字典
- **集**（Set）→ 集合
- **位**（Bitmap）→ 位图
- **超**（HyperLogLog）→ 超低内存基数统计
- **流**（Stream）→ 消息流
- **地**（GEO）→ 地理位置
- **Z**（ZSet）→ 有序集合 → **跳**（Skip List）→ 跳表

**跳表记忆锚点："楼梯跳板"**
- 底层（Level 0）是所有人走楼梯 → 原始链表 O(N)
- 每隔一层（Level 1）只有一半人能走 → 一级索引
- 每隔四层（Level 4）只有精英能走 → 二级索引
- 查找时从顶层往下"跳"，一次跳过多个节点 → 平均 O(log N)

**ZSet 两种编码记忆："少拉链，多跳表"**
- 元素少（<128）且值小（<64B）→ **ziplist**（压缩列表，紧凑拉链）
- 元素多或值大 → **skiplist + dict**（跳表排序 + 字典加速）

---

### 📖 深度解答

#### 第一层：核心概念

**Redis** 是一个基于内存的键值存储系统（Key-Value Store），其"值"支持多种数据结构（Data Structures）。以下是 9 种常用数据结构概述：

| 数据结构 | 英文 | 用途概述 |
|---------|------|---------|
| **String** | 字符串 | 最基础类型，存文本、数字、二进制数据。支持自增自减，常用于计数器、分布式锁（SETNX）、缓存片段。最大 512MB。 |
| **List** | 列表 | 双向链表实现（quicklist）。支持头尾压入/弹出（LPUSH/RPOP），可用作消息队列（阻塞版 BLPOP）或时间线数据。 |
| **Hash** | 哈希 | field-value 映射表。适合存对象（如用户信息），相比 String 序列化，Hash 支持单独操作某个字段。 |
| **Set** | 集合 | 无序不可重复集合。支持交（SINTER）、并（SUNION）、差（SDIFF）运算。用于标签系统、共同好友等场景。 |
| **ZSet** | **有序集合** | 每个元素关联一个分数（score），按分数排序。底层用跳表+字典实现。用于排行榜、延时队列、滑动窗口限流。 |
| **Bitmap** | 位图 | 基于 String 的位操作。每个 bit 表示一个布尔值。用于用户签到、布隆过滤器、在线状态统计，内存极省。 |
| **HyperLogLog** | 超对数 | 近似基数统计（Cardinality Estimation）。用约 12KB 内存统计上亿唯一值（如 UV），误差率约 0.81%。 |
| **GEO** | 地理空间 | 存储经纬度坐标，底层用 ZSet 编码（GeoHash）。支持计算距离（GEODIST）、范围查询（GEORADIUS）、附近的人。 |
| **Stream** | 流 | Redis 5.0 引入的消息队列。支持消费者组（Consumer Group）、消息持久化、ACK 确认、消息回溯。类似 Kafka 的轻量实现。 |

---

#### 第二层：底层原理 —— ZSet 深入

##### 2.1 双编码机制

ZSet 根据数据规模选择两种底层编码，由配置参数控制：

```
zset-max-ziplist-entries 128    # 最大压缩列表元素数，默认 128
zset-max-ziplist-value    64    # 单个元素最大字节数，默认 64
```

**编码一：ziplist（压缩列表）** — 元素少时使用

当 ZSet 的元素数量小于 128 **且** 每个元素的字符串长度小于 64 字节时，Redis 使用 **ziplist** 存储。ziplist 是一块连续内存，所有元素按 score 有序排列，每对相邻条目（member + score）紧挨在一起。

```
内存布局示意：
[zlbytes][zltail][zllen][entry1_member][entry1_score][entry2_member][entry2_score]...[zlend]
```

- 优点：内存极度紧凑，无指针额外开销，缓存友好
- 缺点：插入/删除需要内存重分配和数据移动，O(N) 复杂度
- 转换：一旦元素数 > 128 或任一元素 > 64 字节，自动升级为 skiplist + dict（不可逆降级）

**编码二：skiplist + dict（跳表 + 字典）** — 元素多时使用

##### 2.2 双底层结构

ZSet 的 skiplist+dict 编码同时维护两个底层结构：

1. **zskiplist**（跳表）：按 score 有序组织所有元素，支持 O(log N) 的范围查询和排序操作
2. **dict**（字典）：维护 member → score 的映射，支持 O(1) 的按成员查分操作

```c
// Redis 源码 server.h 中的定义（示意）
typedef struct zset {
    dict *dict;          // key=member, value=score → O(1)查分
    zskiplist *zsl;      // 跳表 → 按score有序
} zset;
```

两个结构共享同一份 member 和 score 数据（通过指针），无冗余存储浪费。

---

#### 第三层：实践应用 —— 跳表（Skip List）核心原理

##### 3.1 什么是跳表

**跳表**（Skip List）是由 William Pugh 在 1990 年提出的概率性平衡数据结构。它在有序链表（Linked List）的基础上建立多级索引（Index Layer），通过"跳跃式"前进加速查找。

**核心思想**：
- 底层（Level 0）：完整有序链表，包含所有节点
- 上层（Level 1, 2, ...）：每层是下一层的"快速通道"，只包含部分节点
- 查找时从最高层开始，水平前进直到遇到大于目标值的节点，然后降一层继续
- 每步跳过的节点数呈指数级增长，达到 O(log N) 的平均查找时间

##### 3.2 层数（Level）生成算法

每个新插入节点的层数通过随机函数决定，这是跳表"概率平衡"的关键：

```c
// Redis 源码定义
#define ZSKIPLIST_MAXLEVEL 64   // 最高 64 层
#define ZSKIPLIST_P 0.25        // 晋升概率 1/4

int zslRandomLevel(void) {
    int level = 1;
    while ((random() & 0xFFFF) < (ZSKIPLIST_P * 0xFFFF))
        level += 1;
    return (level < ZSKIPLIST_MAXLEVEL) ? level : ZSKIPLIST_MAXLEVEL;
}
```

- 层数期望值：E[level] = 1/(1-P) = 1/0.75 ≈ 1.33
- P 选择 1/4 是 Redis 在内存和速度之间的权衡（P 越小，层数越低，内存越省）

##### 3.3 为什么用跳表不用红黑树/AVL树？

| 维度 | 跳表（Skip List） | 红黑树 / AVL 树 |
|------|-------------------|----------------|
| **实现复杂度** | 简单，约 200 行 C 代码 | 复杂，需处理旋转（左旋/右旋/变色） |
| **范围查询** | 天然支持：找到起点后沿链表遍历即可 | 需要中序遍历或额外维护线索 |
| **并发锁粒度** | 可以只锁定局部节点，锁粒度更细 | 树平衡操作需要全局同步 |
| **最坏情况** | O(N) —— 但概率极低（1/4^63） | O(log N) —— 严格保证 |

---

#### 第四层：深入思考 —— Redis 跳表源码级实现

##### 4.1 zskiplistNode（跳表节点）

```c
typedef struct zskiplistNode {
    sds ele;                      // 成员
    double score;                 // 分值
    struct zskiplistNode *backward; // 后退指针
    struct zskiplistLevel {
        struct zskiplistNode *forward; // 前进指针
        unsigned long span;           // 跨度
    } level[];
} zskiplistNode;
```

##### 4.2 zskiplist（跳表结构）

```c
typedef struct zskiplist {
    struct zskiplistNode *header, *tail;
    unsigned long length;
    int level;
} zskiplist;
```

##### 4.3 Java 实现简化版跳表

```java
import java.util.*;

public class SkipList {
    private static final int MAX_LEVEL = 64;
    private static final double P = 0.25;
    
    static class Node {
        int score;
        String member;
        Node[] forward;
        int level;
        
        Node(int score, String member, int level) {
            this.score = score;
            this.member = member;
            this.level = level;
            this.forward = new Node[MAX_LEVEL];
        }
    }
    
    private final Node header = new Node(Integer.MIN_VALUE, "", MAX_LEVEL);
    private int currentLevel = 1;
    
    private int randomLevel() {
        int level = 1;
        while (Math.random() < P && level < MAX_LEVEL) level++;
        return level;
    }
    
    public void insert(int score, String member) {
        Node[] update = new Node[MAX_LEVEL];
        Node cur = header;
        for (int i = currentLevel - 1; i >= 0; i--) {
            while (cur.forward[i] != null && cur.forward[i].score < score)
                cur = cur.forward[i];
            update[i] = cur;
        }
        int newLevel = randomLevel();
        if (newLevel > currentLevel) {
            for (int i = currentLevel; i < newLevel; i++)
                update[i] = header;
            currentLevel = newLevel;
        }
        Node newNode = new Node(score, member, newLevel);
        for (int i = 0; i < newLevel; i++) {
            newNode.forward[i] = update[i].forward[i];
            update[i].forward[i] = newNode;
        }
    }
    
    public Node search(int score) {
        Node cur = header;
        for (int i = currentLevel - 1; i >= 0; i--) {
            while (cur.forward[i] != null && cur.forward[i].score < score)
                cur = cur.forward[i];
        }
        cur = cur.forward[0];
        return (cur != null && cur.score == score) ? cur : null;
    }
    
    public boolean delete(int score) {
        Node[] update = new Node[MAX_LEVEL];
        Node cur = header;
        for (int i = currentLevel - 1; i >= 0; i--) {
            while (cur.forward[i] != null && cur.forward[i].score < score)
                cur = cur.forward[i];
            update[i] = cur;
        }
        cur = cur.forward[0];
        if (cur == null || cur.score != score) return false;
        for (int i = 0; i < currentLevel; i++) {
            if (update[i].forward[i] == cur)
                update[i].forward[i] = cur.forward[i];
        }
        while (currentLevel > 1 && header.forward[currentLevel - 1] == null)
            currentLevel--;
        return true;
    }
    
    public List<Node> rangeQuery(int minScore, int maxScore) {
        List<Node> result = new ArrayList<>();
        Node cur = header;
        for (int i = currentLevel - 1; i >= 0; i--) {
            while (cur.forward[i] != null && cur.forward[i].score < minScore)
                cur = cur.forward[i];
        }
        cur = cur.forward[0];
        while (cur != null && cur.score <= maxScore) {
            result.add(cur);
            cur = cur.forward[0];
        }
        return result;
    }
}
```

---

### 🗺️ 回答思路

**Step 1：总览全局** — 概述 9 种数据结构，自然过渡到 ZSet 的跳表。
**Step 2：ZSet 双编码** — ziplist vs skiplist+dict，阈值 128/64。
**Step 3：跳表原理** — 多级索引、P=0.25 随机层数、对比红黑树。
**Step 4：源码解析** — zskiplistNode 和 zskiplist 结构体字段。
**Step 5：代码落地** — Java 版 randomLevel()、insert、search 实现。
**Step 6：升华** — 并发优化、与 B+ 树的对比话题方向。

---

> 📋 **分类**: Redis / 缓存
> 🏷️ **标签**: `Redis` `数据结构` `ZSet` `跳表` `Skip List` `压缩列表`
> 📊 **难度**: 进阶
> 📅 **归档时间**: 2026-07-04 12:50:00
