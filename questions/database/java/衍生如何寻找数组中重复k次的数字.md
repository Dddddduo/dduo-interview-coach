---
id: q0168
question: "衍生——如何寻找数组中重复k次的数字？"
category: java
tags: []
difficulty: medium
created: 2026-08-02 09:41:22
source: 用户输入
---

# 衍生——如何寻找数组中重复k次的数字？

# 衍生——如何寻找数组中重复 k 次的数字？

> 背景：本题是"数组中只出现一次/两次的数字"（k=2 经典题）的衍生追问。回答的关键在于展示**从特殊到一般的推广能力**：承认异或 (XOR) 的局限、给出通用计数解法、并区分"恰好 k 次"与"超过 n/k 次"两类问题。

## 🧠 联想记忆法

**一句话总纲**："k=2 靠异或（成对抵消），k 任意靠计数（模 k 统计），超过 n/k 靠投票（k-1 个擂台），位运算只认'唯一非 k 的倍数'。"

**记忆锚点 1——XOR 是"k=2 专享"**：异或 (XOR) 的数学本质是**按位模 2 加法**，它只认识"奇/偶"两种状态。把它想成"夫妻对拜"：两人互相抵消归零（a⊕a=0），所以 k=2（出现两次，偶数）恰好能被完美消去。但推广到 k=3：三人拜堂，两两抵消后还剩"自己"；k=4：四人拜堂，全部抵消归零。也就是说，**k 为偶数时重复 k 次的数字会把自己异或成 0**（与从未出现无法区分），**k 为奇数时它又留下"本体"**（与所有出现奇数次的数字混在一起）。所以异或这把钥匙只配 k=2 这把锁。

**记忆锚点 2——"三重钥匙"工具箱**：面试官从 k=2 追问到一般 k 时，工具箱里必须有且只有这几把钥匙：
- 第一把 **HashMap 计数**：数人头，O(n)/O(n)，万能，先亮出来；
- 第二把 **排序扫描**：排队点名，O(n log n)/O(1)，空间受限时顶替第一把；
- 第三把 **摩尔投票推广 (Boyer-Moore Majority Vote)**：擂台赛，k-1 个擂台，但只能找"超过 n/k 的擂主"，找不了"恰好 k 次"；
- 隐藏钥匙 **位运算逐位模 k**：查户口，逐位统计 1 的个数模 k，只适用于"唯一一个出现次数非 k 的倍数"的兄弟变体。

**记忆口诀**："偶 k 异或归零，奇 k 异或自留；恰好 k 次靠计数，超 n/k 靠投票；位运算模 k 找独苗，二次验证防虚警。"

**联想画面**：把数组想成一排学生报数——XOR 是"两两击掌消失"的游戏（只认成对），计数是"老师画正字点名"（数到 k 就圈出来），摩尔投票是"擂台车轮战"（k-1 个擂主守擂，被挑战就扣一滴血，血空下台，但最后擂主未必真赢——要重新数票验证）。记住这个画面，三个算法的区别就刻在脑子里了。

## 📖 深度解答

### 1. 核心概念

**问题定义**：给定长度 n 的整数数组，寻找"恰好重复 k 次"的数字（number appearing exactly k times）。

**与"重复两次"的本质差异（必答）**：
- k=2 经典题能用异或，是因为 XOR 是**自逆运算 (self-inverse)**：a⊕a=0、a⊕0=a，且满足交换律、结合律。全部异或一遍，成对元素两两抵消，剩下的就是落单者。
- 推广到一般 k，XOR 立即失效，原因有二：
  1. **k 为偶数时**：重复 k 次的数字异或 k 次后等于 0，与"从未出现"完全无法区分；
  2. **k 为奇数时**：重复 k 次的数字异或 k 次后等于自身，但数组里**所有出现奇数次的数字都会"残留"**，除非其他元素全部是偶数次——这种额外约束让 XOR 方案失去通用性。
- **本质区别一句话**：XOR 是"模 2 世界"的运算（只分奇偶），一般 k 需要"模 k 世界"的计数思想。k=2 恰好是"模 2 计数"，而 k≠2 时不存在同样简洁的等价位运算（除非有额外前提）。

**问题语义的三个变体（动手前先确认）**：
- **恰好 k 次 (exactly k times)**：固定阈值，判断条件 ==k；
- **至少 k 次 (at least k times)**：判断条件 >=k；
- **超过 n/k 次 (more than n/k times)**：阈值随 n 变化，判断条件 >n/k——这是摩尔投票的目标，不是本题"恰好 k 次"的目标。

### 2. 底层原理

#### 解法一：哈希表计数 (Hash Map Counting)——O(n) 时间，O(n) 空间，万能保底

原理：第一遍遍历统计"值→出现次数"，第二遍遍历哈希表找出计数恰为 k 的键。哈希表读写均摊 O(1)，总复杂度 O(n)/O(n)。

```java
import java.util.*;

public class FindKRepeated {
    // 通用版：返回所有恰好出现 k 次的元素（天然支持多解）
    public static List<Integer> findExactlyK(int[] nums, int k) {
        List<Integer> res = new ArrayList<>();
        if (nums == null || k <= 0) return res;
        Map<Integer, Integer> count = new HashMap<>();
        for (int x : nums) {
            count.put(x, count.getOrDefault(x, 0) + 1);
        }
        for (Map.Entry<Integer, Integer> e : count.entrySet()) {
            if (e.getValue() == k) res.add(e.getKey());
        }
        return res;
    }

    // 唯一解版：仅当恰好一个元素重复 k 次时返回它，否则返回 -1
    public static int findSingleExactlyK(int[] nums, int k) {
        Map<Integer, Integer> count = new HashMap<>();
        for (int x : nums) count.put(x, count.getOrDefault(x, 0) + 1);
        int ans = -1, found = 0;
        for (Map.Entry<Integer, Integer> e : count.entrySet()) {
            if (e.getValue() == k) { ans = e.getKey(); found++; }
        }
        return found == 1 ? ans : -1;
    }

    public static void main(String[] args) {
        int[] nums = {1, 1, 1, 2, 3, 3, 4, 4, 4, 5};
        System.out.println("恰好出现3次: " + findExactlyK(nums, 3));      // [1, 4]
        System.out.println("唯一重复3次: " + findSingleExactlyK(nums, 3)); // -1（有两个答案）
        int[] nums2 = {2, 2, 2, 3, 4};
        System.out.println("唯一重复3次: " + findSingleExactlyK(nums2, 3)); // 2
    }
}
```

#### 解法二：排序后扫描 (Sorting + Scan)——O(n log n) 时间，O(1) 空间

原理：排序后相同元素必然相邻，线性扫描统计每段长度，段长 ==k 即为答案。适合"允许修改数组 / 内存受限"的场景。

```java
import java.util.*;

public class FindKBySort {
    public static List<Integer> findExactlyK(int[] nums, int k) {
        List<Integer> res = new ArrayList<>();
        if (nums == null || k <= 0) return res;
        int[] a = nums.clone(); // 不修改原数组
        Arrays.sort(a);
        int i = 0, n = a.length;
        while (i < n) {
            int j = i;
            while (j < n && a[j] == a[i]) j++;
            if (j - i == k) res.add(a[i]);
            i = j;
        }
        return res;
    }

    public static void main(String[] args) {
        int[] nums = {1, 1, 1, 2, 3, 3, 4, 4, 4, 5};
        System.out.println(findExactlyK(nums, 3)); // [1, 4]
    }
}
```

#### 解法三：摩尔投票推广 (Generalized Boyer-Moore Majority Vote)——找"超过 n/k"的元素

原理（**k-1 个候选槽位法**）：维护一个最多 k-1 个候选 (candidates) 的池子，扫描数组时：
- x 命中候选 → 计数 +1；
- 未命中且池未满 → 入池，计数 1；
- 未命中且池已满 → **所有候选计数 -1，减到 0 的淘汰**。

正确性直觉：出现次数 > n/k 的元素，在每次"全体 -1"中至多损失 1 点，数学上可证明它永远不会被淘汰出池。但池中可能有**虚警 (false candidate)**——出现次数不够 n/k 却混进来的，因此必须**第二遍重新精确计数验证**。

```java
import java.util.*;

public class MajorityVoteK {
    // 找出所有出现次数严格大于 n/k 的元素（至多 k-1 个）
    public static List<Integer> moreThanNK(int[] nums, int k) {
        int n = nums.length;
        if (k <= 0) return new ArrayList<>();
        Map<Integer, Integer> cand = new HashMap<>(); // 候选池，最多 k-1 个
        for (int x : nums) {
            if (cand.containsKey(x)) {
                cand.put(x, cand.get(x) + 1);
            } else if (cand.size() < k - 1) {
                cand.put(x, 1);
            } else {
                Iterator<Map.Entry<Integer, Integer>> it = cand.entrySet().iterator();
                while (it.hasNext()) {
                    Map.Entry<Integer, Integer> e = it.next();
                    int c = e.getValue() - 1;
                    if (c == 0) it.remove();
                    else e.setValue(c);
                }
            }
        }
        List<Integer> res = new ArrayList<>();
        for (int key : cand.keySet()) {
            int c = 0;
            for (int x : nums) if (x == key) c++;
            if (c > n / k) res.add(key); // 二次验证，剔除虚警
        }
        return res;
    }

    public static void main(String[] args) {
        int[] nums = {1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4}; // n=11, 阈值 > 11/4=2
        System.out.println(moreThanNK(nums, 4)); // [2, 3, 4]
    }
}
```

**边界说明（重点讲）**：摩尔投票只保证找到"出现次数 > n/k"的元素，**不能**保证找到"恰好出现 k 次"的元素——"恰好 k 次"是固定阈值，可能与 n/k 毫无交集。例：n=10、k=3 时，恰好出现 3 次的元素并不满足 > 10/3（3 < 3.33），投票法根本锁不住它。这是两类不同的问题：投票法解决"多数派"问题，本题解决"固定重复次数"问题。面试时主动讲清这个区别，是重要加分项。

#### 解法四：位运算逐位模 k (Bit Manipulation with mod k)——O(32n) 时间，O(1) 空间

适用前提：数组中**除一个数字 x 外，其余数字的出现次数均为 k 的整数倍**（经典 LeetCode 137 即 k=3 版本）。此时对每个二进制位独立统计"1 的总个数模 k"：所有整 k 组的元素贡献的 1 都是 k 的倍数，模 k 后消去，只剩 x 在该位的贡献（0 或 1），从而逐位还原 x。

```java
public class FindSingleByBit {
    // 前提：唯一一个数字出现次数不是 k 的倍数，其余均为 k 的整数倍
    public static int findNonMultipleOfK(int[] nums, int k) {
        if (nums == null || nums.length == 0 || k <= 0) return 0;
        int result = 0;
        for (int b = 0; b < 32; b++) {          // Java int 为 32 位补码
            int bitSum = 0;
            for (int x : nums) {
                bitSum += (x >> b) & 1;
            }
            if (bitSum % k != 0) result |= (1 << b);
        }
        return result;
    }

    public static void main(String[] args) {
        int[] nums = {3, 3, 3, 5, 5, 5, 7};     // 7 出现 1 次(非3倍数)，其余 3 次
        System.out.println(findNonMultipleOfK(nums, 3)); // 7
        int[] nums2 = {1, 1, 2, 2, 2};          // 2 出现 3 次(非2倍数)
        System.out.println(findNonMultipleOfK(nums2, 2)); // 2
    }
}
```

注意：若目标正是"恰好 k 次"而其余元素是"各出现 < k 次"（不构成 k 的倍数关系），非 k 倍数次的元素会在每个含 1 的位上残留非零余数，结果沦为"垃圾值"（可能碰巧正确，但无任何保证）——仅当所有元素出现次数均为 k 的整数倍时模 k 才恒为 0。此方法只适用于上述兄弟变体，务必说清前提。

### 3. 实践应用

**复杂度对比表**：

| 方法 | 时间复杂度 | 空间复杂度 | 能否解"恰好 k 次" | 适用前提 |
|---|---|---|---|---|
| XOR 异或 | O(n) | O(1) | 仅 k=2（或其余元素全偶数次） | 模 2 计数：k 偶数自抵消、k 奇数留本体 |
| HashMap 计数 | O(n) | O(n) | 完全通用 | 无，最稳妥的首选 |
| 排序 + 扫描 | O(n log n) | O(1) | 完全通用 | 允许排序 / 空间受限 |
| 摩尔投票推广 | O(n) | O(k) | 否（只找 > n/k） | 需二次精确验证防虚警 |
| 位运算逐位模 k | O(32n) | O(1) | 否（只找唯一"非 k 倍数次"） | 其余元素出现次数均为 k 的整数倍 |

**面试现场推理过程（从 k=2 推广到一般 k 的思考路径）**：
1. **先复述已知**：k=2 经典题（如 LeetCode 136 Single Number）用异或，全部异或一遍，成对抵消，剩下答案；
2. **主动质疑**："k 变成 3、4、任意 k，异或还行吗？"——验证两个反例：k=4（偶数）异或归零；k=3（奇数）且其余元素为奇数次时残留混淆。结论：**异或只属于 k=2**；
3. **退而求稳**：计数是"重复次数"问题的通解 → HashMap 两遍扫描，报出 O(n)/O(n)；
4. **追问优化**："空间能省吗？"→ 排序扫描 O(n log n)/O(1)；"要 O(n)/O(1)？"→ 诚实回答："恰好 k 次"没有已知的通用线性 O(1) 解，但近亲"超过 n/k 次"可用摩尔投票推广做到 O(n)/O(k)；
5. **展示二进制功底**：若题目是"其余元素均为 k 的整数倍次"，补上逐位模 k 的位运算解法；
6. **收尾**：对比表总结 + 边界覆盖。

**工程落点**：HashMap 计数就是 MapReduce 中 word count 的原型；摩尔投票是流式数据 (streaming data) 里单遍常数空间找多数元素的经典武器；位运算逐位统计是硬件/极简环境下的优化手段。面试题 = 工程场景的抽象，点出这一层更显功力。

### 4. 深入思考

**边界与坑（必讲）**：
1. **k=1**："恰好出现 1 次"退化为去重问题；摩尔投票在 k=1 时"超过 n 次"不存在，返回空集；
2. **k>n**：任何元素最多出现 n 次，结果必为空——代码仍需防御（k<=0 直接返回空），防止除零/无意义计算；
3. **"恰好" vs "至少" vs "超过 n/k"**：判断条件分别是 ==k、>=k、>n/k，语义完全不同，动手前必须与面试官确认；
4. **多个元素同时重复 k 次**：HashMap 法天然支持多解；若题意限定唯一解，用"唯一解版"并校验 found==1，否则返回 -1；
5. **摩尔投票虚警**：候选池元素不一定真满足条件，必须二次验证——这是面试官最爱追问的细节；
6. **位运算陷阱**：要求"其余元素是 k 的整数倍次"；对"恰好 k 次"硬套会失败（总和是 k 的倍数、模 k 恒 0）；Java int 固定 32 位、long 需 64 位，负数的补码表示不受逐位统计影响。

**再进一步**：k=2 经典题（其余元素各 1 次）有 O(n)/O(1) 的 XOR 解；但推广到"唯一数字重复 k 次、其余各 1 次"，除 k=2 和位运算模 k 的特殊前提外，目前没有同样简洁的确定性线性 O(1) 解法——这从反面说明"模 2 世界"的运算天然特殊，一般 k 必须付出哈希空间或排序时间的代价。能在回答中点到这一层，说明你对算法边界有真正的理解。

## 🗺️ 回答思路

**答题逻辑框架**（五步走）：
1. **确认题意**（30 秒）：k 的含义、恰好/至少/超过 n/k、唯一解/多解、能否修改数组；
2. **从已知切入**：k=2 用异或，随即主动指出其失效原因（k 的奇偶性）——直接命中追问意图；
3. **给通用解**：HashMap 计数（完整代码 + 复杂度），排序扫描作为空间优化备选；
4. **展示深度**：摩尔投票推广（k-1 槽位 + 二次验证）+ 位运算模 k（讲清适用前提）；
5. **收尾总结**：复杂度对比表 + 边界情况 + "两类问题"的区分。

**重点得分点**：
- 主动讲出"XOR 为什么失效"，且区分 k 偶/奇两种情形；
- 明确区分"恰好 k 次"与"超过 n/k 次"两类问题，说明摩尔投票为何不能硬套；
- 摩尔投票候选池的二次精确验证；
- 位运算模 k 的适用前提（k 的整数倍次，而非恰好 k 次）；
- 随手报出每个解的时间/空间复杂度；
- 边界情况（k=1、k>n、多解、空输入）的防御处理。

**常见误区**：
- 误以为异或可以任意推广，把 k 当"成对处理"；
- 用摩尔投票硬套"恰好 k 次"，忽略阈值语义不同；
- 忘记摩尔投票的二次验证（虚警）；
- 位运算模 k 前提记错（把"其余元素恰好 k 次"当成"k 的整数倍次"）；
- 忽略 k>n、k<=0、多个答案等边界；
- 上来就写代码，没先确认"恰好 vs 至少"。

**时间分配建议**（若总时长 5–8 分钟）：
- 0–1 分钟：确认题意 + 复述 k=2 异或方案并指出局限；
- 1–4 分钟：HashMap 版完整代码 + 复杂度（主体，务必扎实）；
- 4–6 分钟：排序 / 摩尔投票 / 位运算扩展（按面试官兴趣取舍）；
- 6–7 分钟：对比表总结 + 边界情况收尾。

**过渡话术**：
- 从 k=2 过渡："XOR 能解 k=2，靠的是 a⊕a=0 的成对抵消；但 k 一变化这性质就失效了——k 为偶数时重复 k 次的数字会把自己异或成 0，k 为奇数时又会和所有奇数次出现的数字混在一起，所以必须换成'记录次数'的思路。"
- 从哈希到摩尔投票："如果继续追问空间能不能压到 O(1)，要分情况说：'恰好 k 次'没有已知的通用线性 O(1) 解；但它的近亲'超过 n/k 次'可以用摩尔投票的推广做到 O(n) 时间、O(k) 空间，代价是它解决的是另一类问题。"
- 收尾："总结一下，这道衍生题真正考的是从特殊到一般的推广能力：异或只是模 2 世界的特例，通用武器是计数，摩尔投票和位运算模 k 各自带着严格的前提条件——讲清前提，比背下解法更重要。"

---

> 📋 **分类**: Java
> 🏷️ **标签**: 
> 📊 **难度**: 中级
> 📅 **归档时间**: 2026-08-02 09:41:22
