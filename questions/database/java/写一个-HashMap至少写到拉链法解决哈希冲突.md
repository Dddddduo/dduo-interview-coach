---
id: q0174
question: "写一个 HashMap，至少写到拉链法解决哈希冲突"
category: java
tags: []
difficulty: medium
created: 2026-08-02 09:41:22
source: 用户输入
---

# 写一个 HashMap，至少写到拉链法解决哈希冲突

# 写一个 HashMap，至少写到拉链法解决哈希冲突（Java）

## 🧠 联想记忆法

**记忆锚点：一个停车场 + 一条拖车链。**

把 HashMap 想象成一个大型停车场：车位就是桶数组（bucket array），每辆车（键值对 Entry）按车牌哈希值（hashCode）停到对应车位。车停满了怎么办？就在那个车位上挂一条拖车链（链表），冲突的车依次挂在链上。当某个车位的链上挂了太多车（≥ 8 辆），就把链换成树状立体停车架（红黑树）。当整场车位使用率达到 75%（负载因子 0.75）时，扩建停车场（扩容 resize），所有车重新分配车位（rehash）。

**数字口诀（一句话串起全部关键数字）：** "满七五扩容，长八转树，六退链，六十四才开门。"

- **0.75** —— 负载因子（load factor），扩容阈值，时间与空间的折中
- **8** —— 链表转红黑树（treeify）的节点数阈值
- **6** —— 红黑树退化为链表的节点数阈值
- **64** —— 允许树化的最小数组容量（不到 64 只扩容不树化）
- **16** —— 默认初始容量（2 的幂）

**定位公式口诀：** "减一相与，胜过取模；高位扰动，均匀分布" —— `(n-1) & hash` 代替 `hash % n`，`hash ^ (hash >>> 16)` 扰动高位。

## 📖 深度解答

### 1. 核心概念

**HashMap（哈希映射表）** 是 Java 集合框架（Java Collections Framework）中基于**哈希表（Hash Table）**实现的 Map 接口实现类，JDK 1.8 之后采用"**数组 + 链表 + 红黑树**"三合一的结构，是面试中出场率最高的容器类。

要理解 HashMap，先抓住**哈希表的三要素**：

1. **哈希函数（hash function）**：把任意长度的 key 映射成一个整数（哈希值，hash value），要求计算快、分布均匀。
2. **哈希冲突（hash collision）**：不同 key 算出相同哈希值（数学上必然存在，因为值域无限、桶域有限）。
3. **冲突解决策略**：教科书上有四种——**开放定址法（open addressing，线性探测/平方探测/双重散列）、再哈希法（rehashing）、链地址法（chaining，即拉链法）、公共溢出区法**。HashMap 选用的是**拉链法（chaining）**：每个桶（bucket）不再只存一个元素，而是存一条链表的头节点，冲突的元素全部挂在同一条链上。

**为什么 HashMap 选拉链法而不选开放定址法？** 因为拉链法对负载因子的容忍度高（开放定址法负载因子逼近 1 时几乎瘫痪），删除简单，且当链表过长时可以升级为红黑树——这是开放定址法做不到的。这就是本题目要求的"写一个 HashMap，至少写到拉链法"的由来：拉链法是 HashMap 的骨架，其余（树化、扩容优化）都是骨架上的装修。

### 2. 底层原理

**2.1 数据结构**：`Node<K,V>[] table` 桶数组 + 单向链表（1.8 起长链升级为红黑树 `TreeNode`）。每个 `Node` 持有四个字段：`hash`（存扰动后的哈希值，避免重复计算）、`key`、`value`、`next`（链表指针）。

**2.2 hash 扰动函数（perturbation function）**：JDK 源码中：

```java
static final int hash(Object key) {
    int h;
    return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}
```

**为什么扰动？** 因为数组初始只有 16 个桶，取模只用到 hash 的低 4 位，高 28 位的信息白白浪费；直接取低 4 位很容易让某些模式（比如低 4 位相同、高 4 位不同的 key）全部撞车。把 hash 右移 16 位后与自己异或，等于把高位信息"折叠"进低位——**让分布只取决于哈希函数本身，而不是取决于数组大小**。这是典型的"**低位折叠（low-bit folding）**"思想。

**2.3 桶定位公式**：`index = (n - 1) & hash`。见追问一，这是"位运算替代取模"的经典优化，前提是**容量 n 恒为 2 的幂**，这正是 JDK 用 `tableSizeFor` 强制把容量规整为 2 的幂的根本原因。

**2.4 核心流程**（以 JDK 1.8 为准）：

- **put**：① 算 `hash` → ② `(n-1)&hash` 定位桶 → ③ 桶空则直接占位；桶非空则沿链表遍历——**先比 hash 再比 equals**（快速失败），找到相同 key 就覆盖旧值并返回旧值；找不到就在**链表尾部插入**（尾插法）→ ④ `size++`，若 `size > 容量 × 负载因子` 则扩容。
- **get**：同样的定位 + 链表遍历查找，找不到返回 `null`（注意：value 本身为 null 时返回 null 无法区分"键不存在"与"值为 null"，需用 `containsKey` 区分）。
- **扩容 resize**：新建 2 倍容量数组，把旧元素全部**重新散列（rehash）**迁移。JDK 1.8 有个精妙优化：`(e.hash & oldCap) == 0` 的节点留在原位（lo 链），否则移到"原下标 + oldCap"（hi 链），**无需重新计算下标**，且能保持相对顺序，配合尾插彻底解决了 JDK 1.7 头插法在并发下链表成环、CPU 100% 的死循环问题。

**2.5 负载因子（load factor）0.75**：扩容阈值 `threshold = capacity × loadFactor`。0.75 是官方在**空间占用与查询效率之间**的经验折中——太小（如 0.5）则空间浪费、扩容频繁；太大（如 1.0）则冲突剧烈、链表边长。0.75 在 JDK 源码注释中有**泊松分布（Poisson distribution）**佐证：在 0.75 负载因子和随机哈希下，桶内节点数服从泊松分布，`k=8` 的概率约为 `0.00000006`（约六百万分之一）。

**2.6 树化与退化（8 / 64 / 6）**：树化条件有**两个必须同时满足**——① 链表长度 ≥ 8（`TREEIFY_THRESHOLD`）；② 数组容量 ≥ 64（`MIN_TREEIFY_CAPACITY`）。容量不足 64 时只扩容不树化（扩容本身就能让链表"摊薄"）。退化条件：树中节点数 ≤ 6（`UNTREEIFY_THRESHOLD`），发生在扩容拆分或 remove 之后。8 与 6 之间留了 1 的缓冲，避免元素在阈值附近反复横跳（链 ↔ 树抖动）。**为什么选 8？** 就是上面泊松分布算出的概率极低，说明树化只是极端情况下的兜底，平时链表（节点更省内存、遍历更快）才是常态。

**2.7 与 JDK 源码的对比（哪些简化了、为什么简化）**：

| JDK 源码 | 本实现简化 | 简化原因 |
|---|---|---|
| 支持红黑树 TreeNode | 只写链表，注释说明树化条件 | 红黑树约 500 行，手写不现实；说出 8/64/6 条件即得分 |
| 扩容用 `(e.hash & oldCap)` 拆分链表，无需重算下标 | 直接 `(n-1)&hash` 重算下标 | 逻辑直观、正确性等价，O(n) 重算可接受 |
| 懒加载：首次 put 才初始化数组 | 同上，复用 resize 初始化 | 省内存，且代码更少 |
| `tableSizeFor` 位运算找 2 的幂 | 保留（约 8 行） | 这是"为什么容量是 2 的幂"的答案，建议写出来 |
| 头插法（1.7）→ 尾插法（1.8） | 尾插 | 尾插避免并发扩容成环，是高分考点 |
| 独立实现 `remove`、`getNode` | 保留 | 展示对链表断链操作的理解 |

### 3. 实践应用（可运行完整实现）

```java
import java.util.Objects;

/**
 * 手写 HashMap —— 数组 + 链表拉链法（单线程简化版）
 * 设计骨架与 JDK 1.8 一致，但省略了红黑树部分（注释中保留树化条件）。
 */
public class MyHashMap<K, V> {

    // ============ 1. Node 节点类：拉链上的一个结点 ============
    static class Node<K, V> {
        final int hash;      // 扰动后的哈希值。存起来避免查找/扩容时重复计算
        final K key;         // 键（final：hashCode 不可变是查找正确性的前提）
        V value;             // 值（可变）
        Node<K, V> next;     // 指向链表下一个节点，构成拉链结构

        Node(int hash, K key, V value, Node<K, V> next) {
            this.hash = hash;
            this.key = key;
            this.value = value;
            this.next = next;
        }
    }

    // ============ 2. 核心字段与常量 ============
    private Node<K, V>[] table;              // 桶数组（哈希表本体）
    private int size;                        // 已存储的键值对数量
    private final float loadFactor;          // 负载因子

    private static final int DEFAULT_CAPACITY = 16;   // 默认容量
    private static final float DEFAULT_LOAD_FACTOR = 0.75f; // 默认负载因子
    private static final int TREEIFY_THRESHOLD = 8;    // 链表转树阈值（未实现红黑树，仅注释）
    private static final int MIN_TREEIFY_CAPACITY = 64;// 允许树化的最小容量

    public MyHashMap() { this(DEFAULT_CAPACITY, DEFAULT_LOAD_FACTOR); }

    @SuppressWarnings("unchecked")
    public MyHashMap(int capacity, float loadFactor) {
        if (capacity <= 0) throw new IllegalArgumentException("capacity must > 0");
        this.loadFactor = loadFactor;
        // 关键：把容量规整为 2 的幂 —— 这是 (n-1)&hash 能替代 hash%n 的前提
        this.table = (Node<K, V>[]) new Node[tableSizeFor(capacity)];
    }

    /** 返回 >= cap 的最小 2 的幂（与 JDK tableSizeFor 一致） */
    private static int tableSizeFor(int cap) {
        int n = cap - 1;                 // 减 1 防止 cap 本身是 2 的幂时翻倍
        n |= n >>> 1;                    // 把最高位 1 向右传播，填满低位
        n |= n >>> 2;
        n |= n >>> 4;
        n |= n >>> 8;
        n |= n >>> 16;
        return (n < 0) ? 1 : (n >= 1 << 30) ? 1 << 30 : n + 1;
    }

    // ============ 3. hash 扰动函数 ============
    /**
     * 为什么扰动？数组小的时候 (n-1) 的高位全是 0，直接相与会丢掉 key 的高位信息，
     * 分布只取决于低位。把 hash 右移 16 位再异或自己（低位折叠），
     * 让高 16 位也参与定位 —— 高位散列的 key 不再容易撞车。
     * JDK 中 null key 的 hash 固定为 0，落在 table[0]。
     */
    private static int hash(Object key) {
        int h;
        return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
    }

    /**
     * 桶定位：为什么用 (n-1)&hash 而不是 hash%n？
     * 1) 位运算比取模快一个量级；2) n 为 2 的幂时两者结果完全等价
     *（n-1 的二进制是低位全 1 的掩码，与运算即取 hash 的低 log2(n) 位）；
     * 3) 代价是容量被强制为 2 的幂（tableSizeFor 保证）。
     */
    private int indexFor(int hash, int n) { return (n - 1) & hash; }

    // ============ 4. put：定位 → 拉链插入/覆盖 → 扩容 ============
    public V put(K key, V value) {
        if (table == null || table.length == 0) {
            resize();               // 懒加载：首次 put 才初始化数组
        }
        int n = table.length;
        int hash = hash(key);
        int i = indexFor(hash, n);

        if (table[i] == null) {
            // 情况一：桶位为空，直接占位
            table[i] = new Node<>(hash, key, value, null);
        } else {
            // 情况二：桶位非空，沿拉链查找
            Node<K, V> p = table[i];
            Node<K, V> prev = null; // 记录前驱节点，用于尾插
            while (p != null) {
                // 键相等判定：hash 相同 && (地址相同 || equals 相等)
                // 先比 hash 是"快速失败"：hash 不同直接跳过，避免昂贵的 equals 调用
                // 这背后是 equals/hashCode 契约：equals 相等则 hash 必相等
                if (p.hash == hash && (p.key == key || (key != null && key.equals(p.key)))) {
                    V oldValue = p.value;
                    p.value = value;   // 情况三：key 已存在 → 覆盖，返回旧值
                    return oldValue;
                }
                prev = p;
                p = p.next;
            }
            // 情况四：链表遍历完未找到 → 尾部插入
            // 为什么尾插？JDK 1.7 头插在并发扩容时会产生环形链表导致死循环，
            // 1.8 改尾插后并发下不再成环（但仍不安全，见追问五）。
            prev.next = new Node<>(hash, key, value, null);
        }
        size++;
        // 扩容时机：size 超过 容量 × 负载因子。
        // 为什么 0.75？时间与空间的折中：太大冲突变多，太小空间浪费、扩容频繁。
        if (size > table.length * loadFactor) {
            resize();
        }
        return null;
    }

    // ============ 5. get：定位 → 链表查找 ============
    public V get(Object key) {
        Node<K, V> e = getNode(key);
        return e == null ? null : e.value;
        // 注意：若 value 本身是 null，返回值也是 null，与"键不存在"无法区分；
        // 需要区分时用 containsKey（JDK 的 getOrDefault 也基于此语义）。
    }

    public boolean containsKey(Object key) { return getNode(key) != null; }

    private Node<K, V> getNode(Object key) {
        if (table == null || table.length == 0) return null;
        int hash = hash(key);
        Node<K, V> p = table[indexFor(hash, table.length)];
        while (p != null) {
            if (p.hash == hash && (p.key == key || (key != null && key.equals(p.key)))) {
                return p;           // 命中即返回
            }
            p = p.next;
        }
        return null;                // 遍历整条链未命中
    }

    // ============ 6. remove：定位 → 断链 ============
    public V remove(Object key) {
        if (table == null || table.length == 0) return null;
        int hash = hash(key);
        int i = indexFor(hash, table.length);
        Node<K, V> p = table[i];
        Node<K, V> prev = null;
        while (p != null) {
            if (p.hash == hash && (p.key == key || (key != null && key.equals(p.key)))) {
                if (prev == null) table[i] = p.next; // 删除的是链头：桶直接指向下一节点
                else prev.next = p.next;             // 删除中间/尾部节点：前驱跳过自己
                size--;
                return p.value;
            }
            prev = p;
            p = p.next;
        }
        return null;
    }

    public int size() { return size; }

    // ============ 7. 扩容 resize：翻倍容量 + rehash 迁移 ============
    @SuppressWarnings("unchecked")
    private void resize() {
        Node<K, V>[] oldTable = table;
        int oldCap = (oldTable == null) ? 0 : oldTable.length;
        int newCap = (oldCap == 0) ? DEFAULT_CAPACITY : oldCap << 1; // 容量翻倍
        Node<K, V>[] newTable = (Node<K, V>[]) new Node[newCap];

        if (oldTable != null) {
            for (Node<K, V> e : oldTable) {   // 遍历每个桶
                while (e != null) {
                    Node<K, V> next = e.next; // 先保存 next，否则断链后丢失
                    int j = indexFor(e.hash, newCap); // 重新散列定位（简化版）
                    e.next = newTable[j];     // 头插迁移
                    newTable[j] = e;
                    e = next;
                }
            }
        }
        table = newTable;
        // 与 JDK 的差异：JDK 1.8 用 (e.hash & oldCap)==0 把链表拆成"原位"和
        // "原位+oldCap"两条，避免重算下标；这里直接重算，代码更短、更易讲清 rehash 语义。
    }

    // ============ 8. toString：便于调试展示 ============
    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder("{");
        if (table != null) {
            boolean first = true;
            for (Node<K, V> e : table) {
                while (e != null) {
                    if (!first) sb.append(", ");
                    sb.append(e.key).append('=').append(e.value);
                    first = false;
                    e = e.next;
                }
            }
        }
        return sb.append('}').toString();
    }
}
```

**测试代码（验证拉链、覆盖、扩容、冲突）：**

```java
public class MyHashMapTest {
    public static void main(String[] args) {
        MyHashMap<String, Integer> map = new MyHashMap<>();
        map.put("apple", 1);
        map.put("banana", 2);
        map.put("cherry", 3);
        map.put("apple", 100);                       // 覆盖旧值
        System.out.println(map.get("apple"));        // 100
        System.out.println(map.get("banana"));       // 2
        System.out.println(map.containsKey("cherry")); // true
        System.out.println(map.size());              // 3
        System.out.println(map);                     // {banana=2, apple=100, cherry=3}

        for (int i = 0; i < 1000; i++) map.put("key" + i, i); // 触发多次扩容
        System.out.println(map.size());              // 1003
        System.out.println(map.get("key999"));       // 999

        // 验证拉链法：自定义类固定 hashCode，20 个元素全部冲突进同一桶
        MyHashMap<BadHash, String> m2 = new MyHashMap<>();
        for (int i = 0; i < 20; i++) m2.put(new BadHash(i), "v" + i);
        System.out.println(m2.get(new BadHash(19))); // v19 —— 链式查找正确
    }

    static class BadHash {                           // 合法但糟糕的哈希类
        int id;
        BadHash(int id) { this.id = id; }
        @Override public int hashCode() { return 42; } // 故意制造冲突
        @Override public boolean equals(Object o) {
            return o instanceof BadHash && ((BadHash) o).id == id;
        }
    }
}
```

**实际应用场景**：本地缓存（如 Redis 客户端本地缓存）、去重（`HashSet` 本质就是"值为固定对象"的 HashMap）、词频统计、数据库索引的哈希索引实现思想、以及 LRU 缓存（`LinkedHashMap` 继承 HashMap）。面试中若时间紧张，可以只写 `Node` + `put` + `get` + `resize` 四个核心方法，再用几句话补充扩容与树化逻辑——骨架完整就是 80 分。

### 4. 深入思考（面试追问）

**追问一：为什么用 `(n-1)&hash` 而非 `hash % n`？**
三点：① 位运算（AND）比取模（除法指令）快；② n 为 2 的幂时两者结果**严格等价**——`n-1` 是低位全 1 的掩码，与运算即"取 hash 的低 log₂n 位"，而 `hash % 2^k` 本就等于 hash 的低 k 位；③ 反过来说，这个优化**强制容量必须是 2 的幂**，所以扩容一律翻倍、`tableSizeFor` 必须存在。若 n 不是 2 的幂，`(n-1)&hash` 会浪费部分桶位且不等价于取模。

**追问二：为什么负载因子是 0.75？**
空间与时间的折中，且并非拍脑袋——官方注释给出泊松分布推导：随机哈希下桶内节点数 k 的概率为 `(e^(-λ)λ^k)/k!`（λ=0.75），k=8 时概率约 `0.00000006`。0.75 附近"容量 x 0.75"恰好让哈希冲突概率处在一个可接受的平坦区。太小频繁扩容浪费内存，太大连表变长拖慢查询。

**追问三：为什么"链表长度 ≥ 8 且容量 ≥ 64"才树化？6 又是什么？**
单条件不成立的原因：长度 ≥ 8 但容量 < 64 时，先扩容——把链表"摊薄"成短链，比建树更省事（树节点是链表节点内存的约 2 倍）。阈值 8 对应泊松分布中几乎不可能的自然冲突，说明树化只针对**哈希函数被恶意或缺陷性破坏**的极端情况。退化为链表选 6 而非 8，是为了在 8/6 之间留缓冲，避免元素在阈值附近频繁"链↔树"抖动。树化后最坏查找从 O(n) 降到 O(log n)。

**追问四：equals 与 hashCode 的契约？违反的后果？**
契约：**equals 相等的两个对象，hashCode 必须相等**（逆命题不成立）。HashMap 查找先比 hash（快速失败）再比 equals，若违反契约——equals 相等但 hash 不同——同一个逻辑 key 会被散列到不同桶，`put` 能存进去但 `get` 永远找不到，表现为"幽灵数据丢失"。反面推论：**已放入 Map 的 key 必须是不可变的**（常用 String/Integer），否则修改 key 字段导致其 hashCode 变化后，旧桶位再也定位不到。此外，写自己的类做 key 时，`equals` 必须保证对称性、自反性、传递性。

**追问五：HashMap 并发下有什么问题？ConcurrentHashMap 如何改进？**
HashMap 本身非线程安全（未做任何同步）。JDK 1.7 的**头插法 + 并发扩容**会导致两个线程同时迁移同一链表时把节点互相指向，形成**环形链表**，随后 `get` 无限循环、CPU 飙到 100%——这是历史上著名的生产事故。JDK 1.8 改**尾插法**后不再成环，但并发 `put` 仍会**互相覆盖丢数据**、`size` 不准。`ConcurrentHashMap` 的改进：1.7 用**分段锁（Segment）**，锁粒度是段（默认 16 段，每个段是一把 ReentrantLock）；1.8 放弃分段锁，改 **CAS + synchronized 锁桶头**——桶为空时用 CAS 原子插入（乐观锁），桶非空时只锁住**单个桶的链表头/树根**（悲观锁），并发度提升到桶的数量级；读操作不加锁，靠 volatile 保证可见性。一句话总结：**"锁粒度从段细化到桶，乐观 CAS + 悲观 synchronized 结合"**。

**追问六：复杂度分析。**
- **平均（均匀散列）**：`put/get/remove` 均摊 **O(1)**——定位 O(1)，链表长度期望 O(1)；
- **最坏（全部撞进一个桶）**：无树化时 O(n)，树化后 O(log n)；
- **扩容**：单次 O(n)（重散列全部元素），但均摊到每次 put 上是 **O(1)**（平摊分析，amortized）；
- **空间**：O(n)，桶数组 + n 个节点。

## 🗺️ 回答思路

**答题逻辑框架（四步走，15 分钟左右）：**

1. **先画骨架（2 分钟）**：不急着写代码，先讲设计——"HashMap 是数组 + 链表拉链法，JDK 1.8 加红黑树；定位用 hash 扰动 + `(n-1)&hash`；负载因子 0.75 决定扩容时机；链表 ≥ 8 且容量 ≥ 64 树化，≤ 6 退化"。先给全貌，证明你不是只会背代码，而是理解设计。
2. **再写核心（8-10 分钟）**：`Node` 类 → `put`（定位→拉链插入→覆盖→扩容检查）→ `get`（定位→遍历→equals 契约）→ `resize`（翻倍 + rehash）。写的时候**边写边说理由**，尤其三处：扰动函数、`(n-1)&hash`、0.75。
3. **补刀细节（2 分钟）**：`remove` 断链的两种分支、null key 放桶 0、尾插与头插的区别、懒加载初始化。
4. **主动挖坑引追问（1 分钟）**：写完主动说"我这个是单线程简化版，并发下会丢数据，JDK 的 ConcurrentHashMap 用 CAS + 锁桶头解决"——把面试官想问的问题自己抛出来，掌握节奏。

**重点得分点（按权重排序）：**
- hash 扰动函数 `h ^ (h >>> 16)` 及"低位折叠"原理（多数人漏讲，讲出来即加分）
- `(n-1)&hash` 与取模等价的前提是"容量为 2 的幂"，并顺势讲 `tableSizeFor`
- 精确报出 0.75 / 8 / 64 / 6 四个数字及各自理由（含泊松分布佐证）
- 尾插 vs 头插与并发死循环的演进（1.7 成环 → 1.8 尾插防环）
- `equals`/`hashCode` 契约及"key 必须不可变"的结论
- 复杂度：平均 O(1)、最坏 O(log n)、扩容均摊 O(1)

**常见误区（务必避开）：**
- 只写数组不写拉链（题目明说"至少写到拉链法"）
- 用 `hash % n` 取模——暴露你没理解位运算优化的前提
- 说"扩容要重新计算所有 hash"——**hash 值不变，变的是下标**（因为 n 变了）
- 忘了树化的**双条件**（≥8 且容量 ≥64），只说 8
- 说"HashMap 线程安全"或只说"不安全"不给方案——追问五的内容要能接住
- 手写代码时忘记 `if (key == null)` 的防护（真实面试里 key 可能为 null）

**时间分配建议：** 若面试官说"写一个简化版"（最常见），控制在 10 分钟：1 分钟讲设计，7 分钟写代码，2 分钟收尾讲复杂度；若说"写完整版"，最多 15 分钟，树化部分用口述（"红黑树代码量太大，我讲清条件"）替代，不要埋头写 300 行树代码。写完后留 30 秒通读检查：`hash` 变量、空指针、`next` 断链这三处最容易写错。

**过渡话术（背熟三句）：**
- 从设计到代码："我先花 30 秒讲一下我的设计骨架，然后直接写核心的 put、get 和 resize，这样您能最快看到重点。"
- 从代码到追问："我这个版本为了可读性做了两处简化——扩容直接重算下标、没实现红黑树；JDK 1.8 里扩容是用 `(e.hash & oldCap)` 拆链避免重算的，树化的条件是链表到 8 且容量到 64，我可以展开讲。"
- 从单线程到并发（主动收尾）："最后补充一点，这个实现和 JDK 的 HashMap 一样不是线程安全的；如果并发场景我会用 ConcurrentHashMap，它是 CAS 加锁桶头的实现——这是它和 HashMap 最大的区别。"

---

> 📋 **分类**: Java
> 🏷️ **标签**: 
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-08-02 09:41:22
