---
id: q0216
question: "升序数组，返回=target的元素下标，不存在返回-1。如果有重复元素，返回它首次出现的下标代码怎么改？"
category: java
tags: []
difficulty: medium
created: 2026-08-02 09:41:22
source: 用户输入
---

# 升序数组，返回=target的元素下标，不存在返回-1。如果有重复元素，返回它首次出现的下标代码怎么改？

# 升序数组，返回=target的元素下标，不存在返回-1。如果有重复元素，返回它首次出现的下标代码怎么改？

## 🧠 联想记忆法

**一句话口诀**：「砍一半、两边找；命中不停留，双墙夹到底。」

**三个记忆锚点：**

1. **猜数字游戏（Guessing Game）**：二分查找（Binary Search）本质就是"大了往左、小了往右"的猜数字游戏。面试时在纸上画一条数轴，比死背模板可靠得多。升序数组 + 随机访问（random access）是它的前提。

2. **"命中不返航"**：普通二分是"一击即中"——`nums[mid] == target` 立刻 `return`；左边界二分要"验明正身"——就算撞见 target 也不能停，必须追问一句"前面还有没有？"。联想火车站找人：找到第一个叫"张三"的人不能直接走，得继续往前翻，直到确认前面再无张三。**改动只有一行**：把 `return mid` 改成 `right = mid - 1`。

3. **双墙夹逼（Two Walls）**：把 `left`、`right` 想成两面墙，区间 `[left, right]` 是墙内"嫌疑人区域"。每轮必有一面墙往里推进，区域严格缩小，最终两面墙交错（`left > right`）循环结束，此时 `left` 恰好站在"第一个 ≥ target 的位置"——这正是 C++ `lower_bound`（下界）的落点。

**两个补充口诀**：「闭区间靠等号，开区间靠长度」（左闭右闭用 `left <= right`、`right = n-1`；左闭右开用 `left < right`、`right = n`）；「出界再看值」（循环结束后先查 `left` 是否越界，再查 `nums[left]` 是否等于 target，两步缺一不可）。

## 📖 深度解答

## 1. 核心概念（Core Concepts）

题目拆解：升序数组（sorted array），可能含重复元素（duplicates），返回等于 target 的元素下标，不存在返回 -1；有重复时返回**首次出现**（first occurrence）的下标，即最左边的那个。

三个关键概念串成一条线：**标准二分 → 左边界二分 → lower_bound 语义**。

- **标准二分**：每次把搜索区间（search interval）减半，时间复杂度 O(log n)。它回答的是"存在吗？在哪儿？"，遇到重复元素时命中即返回，得到的是"任意一个"匹配下标，不保证最左。
- **左边界二分**：把"存在性查找（existence search）"升级为"边界查找（boundary search）"，回答"最左边那个在哪儿"。
- **lower_bound**：C++ 标准库语义——返回第一个 ≥ target 的位置。左边界二分循环结束后 `left` 恰好就是这个位置，再补一次相等性检查即得"首次出现"。

## 2. 底层原理（Underlying Principles）

### 2.1 两种区间模板（面试必考）

**左闭右闭（inclusive interval）`[left, right]`**：
- 初始化 `left = 0, right = n - 1`；循环条件 `left <= right`（终止时 `left > right`，区间为空）；更新 `left = mid + 1` / `right = mid - 1`。
- 特征：区间内每个元素都"未被排除"，`right` 位置的元素也参与比较。

**左闭右开（half-open interval）`[left, right)`**：
- 初始化 `left = 0, right = n`；循环条件 `left < right`（终止时 `left == right`，区间为空）；更新 `right = mid`（**注意不是 `mid - 1`**）。
- 特征：`right` 是"不包含"的边界，天然允许初始化为 `n`，省去讨论"最后一个元素漏判"。

两个模板都能通过，关键是能说出**终止条件（termination condition）**的含义——这是区分"背模板"和"真懂"的分水岭。

### 2.2 为什么普通二分处理不了"首次出现"

普通二分 `nums[mid] == target` 立即返回 `mid`。有重复时 `mid` 是"随机命中"的，可能落在重复段的中间。例如 `[1,2,2,2,3]` 查 2，`mid` 可能落在下标 2，返回 2，而首次出现是 1。

### 2.3 改法：只改一行（本题核心得分点）

把命中分支从"返回"改成"收缩"：

```java
// 标准二分
if (nums[mid] == target) return mid;

// 左边界二分（首次出现）：找到了也不返回，右墙继续向左
if (nums[mid] == target) right = mid - 1;
```

此时"等于"与"大于"的处理完全一样，可合并为一个分支：

```java
if (nums[mid] < target) left = mid + 1;
else right = mid - 1;   // 命中或偏大，一律向左收缩
```

循环结束后 `left` 指向第一个 `nums[i] >= target` 的位置，再检查它是否越界且等于 target。**整个循环体从"找 target"变成"找第一个 ≥ target 的位置"**——这是最重要的思想升级，追问都从这里长出来。

### 2.4 循环不变量（Loop Invariant）

循环不变量是证明二分正确的核心工具，一句话表达：**在每次迭代开始前，答案（第一个 ≥ target 的位置）始终落在区间 `[left, right + 1]` 中**；更精确地说，`nums[left - 1] < target` 且 `nums[right + 1] >= target` 这个性质在循环中始终不变（循环结束时 `left == right + 1`，故 `left` 即答案落点）。

为什么成立？每次排除一半：若 `nums[mid] < target`，则 `mid` 及其左侧全部小于 target，答案必在 `[mid + 1, right + 1]`，故 `left = mid + 1`；若 `nums[mid] >= target`，则 `mid` 是候选位置（不保证是第一个），答案必在 `[left, mid]`，故 `right = mid - 1`。由于每轮区间长度严格减半，循环必然终止（不会死循环），结束时 `left` 即答案落点。**面试时把这段说出口，是最有力的加分项。**

### 2.5 mid 计算防溢出（overflow）

`(left + right) / 2` 在 `left + right` 超过 int 上限（2³¹ − 1）时溢出为负数，导致死循环或越界。改用 `left + (right - left) / 2`，数学上等价、绝对安全。虽是细节，主动说出来显功底。

### 2.6 复杂度分析

- 时间 **O(log n)**：每轮区间减半，最坏约 log₂n 轮。
- 空间 **O(1)**：只用了 `left`、`right`、`mid` 三个变量，原地完成。

## 3. 实践应用（Practical Application）

### 3.1 完整可运行 Java 代码

```java
/**
 * 升序数组二分查找全家桶：
 * 标准二分 + 首次出现（左边界）+ 最后一次出现（右边界）+ lower_bound/upper_bound
 * 题目：返回等于 target 的元素下标，不存在返回 -1；有重复元素时返回首次出现的下标。
 */
public class BinarySearchDemo {

    // ========== 模板一：左闭右闭 [left, right] ==========
    public int binarySearch(int[] nums, int target) {
        int left = 0, right = nums.length - 1;
        while (left <= right) {                    // 终止条件：left > right，区间为空
            int mid = left + (right - left) / 2;   // 防溢出，等价于 (left+right)/2
            if (nums[mid] == target) {
                return mid;
            } else if (nums[mid] < target) {
                left = mid + 1;                    // target 在右半边
            } else {
                right = mid - 1;                   // target 在左半边
            }
        }
        return -1;
    }

    // ========== 模板二：左闭右开 [left, right) ==========
    public int binarySearchHalfOpen(int[] nums, int target) {
        int left = 0, right = nums.length;         // 注意：right 初始化为 length
        while (left < right) {                     // 终止条件：left == right，区间为空
            int mid = left + (right - left) / 2;
            if (nums[mid] == target) {
                return mid;
            } else if (nums[mid] < target) {
                left = mid + 1;
            } else {
                right = mid;                       // 右开区间：right 不 -1
            }
        }
        return -1;
    }

    // ========== 找首次出现（左边界二分）——与标准二分只差一行 ==========
    // 关键：nums[mid] == target 时不 return，而是 right = mid - 1 继续向左收缩，
    // 循环结束后 left 是第一个 nums[i] >= target 的位置，检查相等性即可。
    public int firstOccurrence(int[] nums, int target) {
        int left = 0, right = nums.length - 1;
        while (left <= right) {
            int mid = left + (right - left) / 2;
            if (nums[mid] < target) {
                left = mid + 1;                    // 还太小，往右找
            } else {                               // nums[mid] >= target：
                right = mid - 1;                   // 命中或偏大，都向左收缩
            }
        }
        // 边界处理：先查越界，再查相等
        if (left < nums.length && nums[left] == target) {
            return left;                           // 首次出现的下标
        }
        return -1;                                 // 不存在
    }

    // ========== 找最后一次出现（右边界二分，对称写法）==========
    public int lastOccurrence(int[] nums, int target) {
        int left = 0, right = nums.length - 1;
        while (left <= right) {
            int mid = left + (right - left) / 2;
            if (nums[mid] > target) {
                right = mid - 1;                   // 还太大，往左找
            } else {                               // nums[mid] <= target：
                left = mid + 1;                    // 命中或偏小，都向右收缩
            }
        }
        if (right >= 0 && nums[right] == target) {
            return right;                          // 最后一次出现的下标
        }
        return -1;
    }

    // ========== C++ 语义：插入位置 ==========
    // lower_bound：第一个 >= target 的下标
    public int lowerBound(int[] nums, int target) {
        int left = 0, right = nums.length;
        while (left < right) {
            int mid = left + (right - left) / 2;
            if (nums[mid] < target) left = mid + 1;
            else right = mid;
        }
        return left;
    }

    // upper_bound：第一个 > target 的下标
    public int upperBound(int[] nums, int target) {
        int left = 0, right = nums.length;
        while (left < right) {
            int mid = left + (right - left) / 2;
            if (nums[mid] <= target) left = mid + 1;
            else right = mid;
        }
        return left;
    }

    public static void main(String[] args) {
        BinarySearchDemo s = new BinarySearchDemo();
        int[] a = {1, 2, 2, 2, 3, 5};

        System.out.println("binarySearch(2)          = " + s.binarySearch(a, 2));       // 任意命中下标(1/2/3)
        System.out.println("firstOccurrence(2)       = " + s.firstOccurrence(a, 2));    // 1
        System.out.println("lastOccurrence(2)        = " + s.lastOccurrence(a, 2));     // 3

        // 边界情况
        System.out.println("firstOccurrence(0)       = " + s.firstOccurrence(a, 0));    // 小于最小值 -> -1
        System.out.println("firstOccurrence(6)       = " + s.firstOccurrence(a, 6));    // 大于最大值 -> -1
        System.out.println("firstOccurrence(4)       = " + s.firstOccurrence(a, 4));    // 夹在中间不存在 -> -1
        System.out.println("firstOccurrence(空数组)  = "
                + s.firstOccurrence(new int[]{}, 1));                                   // 空数组 -> -1
        System.out.println("firstOccurrence([7,7,7,7],7) = "
                + s.firstOccurrence(new int[]{7, 7, 7, 7}, 7));                         // 全相同 -> 0

        // 插入位置 / 出现次数
        System.out.println("lowerBound(4)            = " + s.lowerBound(a, 4));         // 5（第一个 >= 4 的位置）
        System.out.println("upperBound(2)            = " + s.upperBound(a, 2));         // 4（第一个 > 2 的位置）
        System.out.println("2 的出现次数             = "
                + (s.upperBound(a, 2) - s.lowerBound(a, 2)));                           // 4 - 1 = 3
    }
}
```

### 3.2 现场口述节奏

1. 先写标准二分（约 30 秒）；2. 指出"重复元素时返回的是任意下标"；3. 现场只改命中分支那两行；4. 循环结束后补越界检查 + 相等检查；5. 走查一个用例（如 `[1,2,2,2,3]` 查 2）。

真实场景：数据库 B+ 树索引范围查询、JDK `Arrays.binarySearch`（源码 `binarySearch0` 实际采用左闭右闭风格 `while (low <= high)`，未命中返回 `-(insertionPoint+1)`，语义与本文 `lowerBound` 对应）、区间统计——`upperBound - lowerBound` 即可 O(log n) 求出 target 出现次数。

## 4. 深入思考（Deep Dive）

### 4.1 边界情况逐一验证

- **target 小于最小值**：右墙（`right`）一路左移直到 `left = 0`（区间收缩到 `[0, -1]` 终止），`nums[0] != target` → 返回 -1。
- **target 大于最大值**：左墙（`left`）一路右移直到 `left == n`（越界）。**若忘记 `left < nums.length` 检查会抛 `ArrayIndexOutOfBoundsException`**，这是高频 bug。
- **空数组**：`right = -1`，循环不执行，`left = 0 == n`，安全返回 -1。
- **全相同元素 `[7,7,7,7]` 查 7**：每轮命中都收缩右墙，最终返回 0。
- **target 夹在中间但不存在**：`left` 停在第一个大于 target 的位置，相等检查失败 → -1。

### 4.2 追问 1：最后一次出现（last occurrence）

完全对称：命中时 `left = mid + 1` 继续向右收缩，循环结束后检查 `right` 是否越界且等于 target（代码见 `lastOccurrence`）。**"向左变向右"，一句话就能接住。**

### 4.3 追问 2：插入位置（insertion position）

直接返回 `lowerBound` 的结果，无需相等性检查。C++ 语义对照：`lower_bound` 返回第一个 ≥ target 的迭代器，`upper_bound` 返回第一个 > target 的迭代器，**两者之差就是 target 的出现次数**（count）。这也是"区间查找"问题的万能钥匙。

### 4.4 追问 3：缺失数字（missing number）

剑指 Offer 53-II：长度为 n−1 的升序数组，本应包含 0~n−1 的全部整数，求缺失的那个。二分判断 `nums[mid] == mid`：相等说明缺失在右侧，不等说明缺失在左侧（含 mid）。**这是"不变量从值的大小变成下标与值的关系"的变体**，展示二分思维的迁移能力。

### 4.5 追问 4：旋转数组（rotated sorted array，LeetCode 33 / 153）

先判断 `mid` 落在左升序段还是右升序段（比较 `nums[mid]` 与 `nums[left]`），再根据 target 与端点的关系决定排除哪一半；找旋转点（最小值）同理。核心依然是"每轮证明可以排除哪一半"，模板形式不重要，判断逻辑才重要。

### 4.6 常见 bug 清单（自查表）

- **死循环（infinite loop）**：左闭右开模板把 `right` 写成 `mid - 1`，或闭区间更新分支不收敛。检查方法：每轮区间长度是否严格减小。
- **越界（out of bounds）**：循环结束后直接访问 `nums[left]` 前没查越界；或右开区间把 `right` 初始化为 `n - 1` 导致漏掉最后一个元素。
- **溢出（overflow）**：`(left + right) / 2`。
- **语义错误**：把 `left` 直接返回给"不存在"场景，忘记相等性检查——把"不存在"错返成插入位置。
- **模板混用**：闭区间配 `right = mid`、开区间配 `right = mid - 1`，左右不搭。

## 🗺️ 回答思路

## 答题逻辑框架（四步走）

1. **复述题意 + 确认假设**（30 秒）："升序数组、可能有重复，返回首次出现的下标，不存在返回 -1，对吗？"——确认需求本身就是得分点。
2. **先给标准二分**（2-3 分钟）：选最熟的模板（推荐左闭右闭），边说循环不变量边写。
3. **现场改造成左边界二分**（2 分钟）：指出"只改命中分支一行"，解释 `right = mid - 1` 的收缩含义与循环结束后的双重检查。
4. **收尾**（2 分钟）：走查边界（空数组、全重复、小于最小值、大于最大值）、报复杂度、主动抛出两个追问展示深度。

## 重点得分点

- **循环不变量说得清**（"答案（第一个 ≥ target 的位置）始终落在 `[left, right+1]`，结束时 `left` 即答案落点"）——最大加分项。
- 主动指出"普通二分返回的是任意下标"这一痛点。
- `mid` 防溢出写法主动说明。
- 循环结束后的双重检查（越界 + 相等）。
- 能同时写出左闭右闭与左闭右开两种模板。
- 复杂度 O(log n) / O(1) 脱口而出。

## 常见误区

- 只会背模板，说不出终止条件为什么成立（"背模板 vs 真懂"的判据）。
- 找左边界却忘了最后检查 `nums[left] == target`，把"不存在"错返成插入位置。
- `right` 初始化为 `n` 却用 `left <= right`（越界或死循环风险）。
- 认为二分只适合"查找"，看不到它能做边界、计数、缺失值。
- 复杂度答成 O(n)，或画蛇添足说"最好情况 O(1)"（二分严格 O(log n)）。

## 时间分配建议

思考 0.5-1 分钟（确认假设）→ 标准二分 2-3 分钟 → 左边界改造 2 分钟 → 边界走查 + 复杂度 2 分钟 → 追问延伸 1-2 分钟。总时长控制在 8-10 分钟，末尾留 1 分钟自查代码。

## 过渡话术

- **从标准到变形**："如果数组里有重复元素，普通二分返回的可能不是首次出现的位置——比如 `[1,2,2,2,3]` 查 2，mid 可能落在下标 2，而首次出现是 1。怎么改？其实只差一行：命中时不返回，`right = mid - 1` 继续向左收缩。"
- **被追问最后一次出现**："跟左边界完全对称，把收缩方向反过来：命中时 `left = mid + 1` 继续向右，循环结束检查 `right` 是否越界且等于 target。"
- **被追问插入位置**："把 `left` 的结果直接返回就是 C++ `lower_bound` 的语义；再求 `upper_bound`，两者相减就能 O(log n) 数出 target 的出现次数。"
- **遇到不会的变体**："这个方向我可以现场推一推：二分的关键是每轮排除一半，只要能证明被排除的那一半绝不含答案，具体判断逻辑可以现想，模板形式并不重要。"

---

> 📋 **分类**: Java
> 🏷️ **标签**: 
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-08-02 09:41:22
