---
id: q0020
question: "Redisson 锁实现；看门狗机制原理"
category: redis
tags: ["Redis", "分布式锁", "Redisson", "Watch Dog", "Lua脚本", "可重入锁", "并发编程"]
difficulty: hard
created: 2026-07-04 23:30:00
source: 面经助手-20260704
---

# Redisson 锁实现；看门狗机制原理



## 🧠 联想记忆法

**核心记忆锚点：酒店行李寄存柜**

想象你走进一家**五星级酒店**，前台有一个**智能行李柜（Redis Hash）**。

- **锁 = 寄存柜**：柜子编号是锁的 key（锁名）
- **线程ID = 房卡号**：每个住客（线程）有唯一房卡号，写在柜台登记簿的"客人姓名"字段（Hash field）
- **重入次数 = 行李件数**：你可以多次往同一个柜子放行李（同一线程多次加锁），寄存单上写着"行李：3件"（Hash value = 3）

**看门狗机制**：酒店的**24小时值班保安（Watch Dog）**，每隔10分钟检查一次你的柜子。如果发现你的房间还亮着灯（业务还在执行），就自动把你的寄存时间再续30分钟。**保安只认你的房卡号**，别的人来续期，保安不理。

**释放锁**：你退房时，保安先查登记簿确认你是本人（field = 当前线程ID），然后清空柜子。如果你存了3件行李，每取走1件就减1次数，直到0才彻底关闭柜子（重入释放）。

**红锁（RedLock）**：你怕一家酒店不可靠，同时向 **5家酒店** 寄存同一个行李，超过3家确认寄存成功才算真正存好 —— 这就是多节点投票。

> 一句话记忆：**Hash存锁，Lua保原子，看门狗续命，红锁防脑裂。**

---

## 📖 深度解答

### 一、核心概念 —— Redisson 是什么

**Redisson** 是 Redis 官方推荐的 **Java 分布式工具集框架**，基于 Netty 实现高性能网络通信。它不像 Jedis 那样只是暴露 Redis API 的客户端，而是提供了丰富的**分布式数据结构**：RLock（分布式锁）、RCountDownLatch、RSemaphore、RQueue 等。

| 对比维度 | Jedis / Lettuce | Redisson |
|---------|----------------|----------|
| 定位 | Redis 原生客户端，操作基础数据结构 | 分布式工具集，封装高级场景 |
| 分布式锁 | 需手动 SETNX + Lua | 内置 RLock，开箱即用 |
| 锁续期 | 无，需自己写定时任务 | 内置 Watch Dog 自动续期 |
| 网络模型 | 阻塞 I/O / Netty | Netty NIO，异步驱动 |

**核心术语对照**：
- 分布式锁 = **Distributed Lock**
- 可重入锁 = **Reentrant Lock**
- 看门狗 = **Watch Dog (Auto-Renewal)**
- RedLock = **Redlock Algorithm**

---

### 二、底层原理 —— RLock 核心实现

#### 2.1 锁的数据结构：Redis Hash

Redisson 的锁不是简单用 String，而是用 **Hash 结构**：

```
KEY:   "myLock"                    ← 锁名（lockName）
FIELD: "UUID:threadId"            ← 线程唯一标识（客户端ID:线程ID）
VALUE: 2                          ← 重入次数（加锁几次就是几）
```

为什么用 Hash 而不用 String？
- Hash 天然支持**字段级操作**：HGET 查持有者、HINCRBY 计数
- 一个 key 下可以存多个 field，支持锁的**可重入**特性
- 相比 String 拼接"UUID:threadId:count"的臃肿做法，Hash 语义更清晰

#### 2.2 加锁 Lua 脚本（原子性保证）

Redisson 加锁的 Lua 脚本（简化版）：

```lua
-- KEYS[1] = lockName, ARGV[1] = leaseTime, ARGV[2] = threadId, ARGV[3] = UUID:threadId
-- 锁不存在，直接加锁
if (redis.call('exists', KEYS[1]) == 0) then
    redis.call('hset', KEYS[1], ARGV[3], 1)
    redis.call('pexpire', KEYS[1], ARGV[1])
    return nil
end
-- 锁已存在且是当前线程持有，重入+1
if (redis.call('hexists', KEYS[1], ARGV[3]) == 1) then
    redis.call('hincrby', KEYS[1], ARGV[3], 1)
    redis.call('pexpire', KEYS[1], ARGV[1])
    return nil
end
-- 锁被其他线程持有，返回剩余过期时间
return redis.call('pttl', KEYS[1])
```

**原子性**：整个脚本在 Redis 单线程模型内执行，中间不会被其他命令打断，**不存在竞态条件**。

#### 2.3 可重入的实现机制

- **同线程首次加锁**：Hash field 不存在，hset value = 1
- **再次加锁**：hexists 发现 field 存在 → hincrby value +1
- **解锁**：hincrby value -1，若减到 0 则 hdel field；若 field 删完后 Hash 为空，del key

#### 2.4 解锁 Lua 脚本

```lua
-- KEYS[1] = lockName, KEYS[2] = channelName, ARGV[1] = UUID:threadId
if (redis.call('hexists', KEYS[1], ARGV[1]) == 0) then
    return nil  -- 锁不属于当前线程，无权释放
end
local counter = redis.call('hincrby', KEYS[1], ARGV[1], -1)
if (counter > 0) then
    redis.call('pexpire', KEYS[1], ARGV[2])
    return 0   -- 重入未完全释放
else
    redis.call('del', KEYS[1])
    redis.call('publish', KEYS[2], ARGV[3])
    return 1   -- 完全释放
end
```

---

### 三、深度机制 —— 看门狗（Watch Dog）原理

#### 3.1 为什么要看门狗？

分布式锁面临的核心矛盾：**锁的过期时间设置多大才合理？**

- 设小了：业务还没执行完，锁自动过期了 → 其他线程拿到锁 → **数据竞争**
- 设大了：持有锁的线程挂了，锁迟迟不释放 → **死锁**

看门狗（Watch Dog）的答案是：**动态续期，过期时间设一个合理默认值（30s），每 1/3 过期时间（10s）续一次，业务一直执行就一直续；业务/线程挂了，续期停止，锁自然释放。**

#### 3.2 看门狗触发条件

```java
// === 场景一：看门狗生效 ===
lock.lock();            // 不传过期时间 → 默认 30s → 看门狗启动
lock.lock(30, TimeUnit.SECONDS);  // 显式传了 30s → 看门狗也启动

// === 场景二：看门狗不生效 ===
lock.lock(10, TimeUnit.SECONDS);  // 传了自定义过期时间 → 看门狗不启动
lock.tryLock(100, 10, TimeUnit.SECONDS);  // tryLock 传了 leaseTime → 不启动
```

**核心规则**：只有不传 `leaseTime` 或传的 `leaseTime` 等于默认值（INTERNAL_LOCK_LEASE_TIME = 30000ms）时，看门狗才启动。

#### 3.3 看门狗的底层实现

看门狗基于 **Netty 的 Timeout + TimerTask** 实现：

```java
// Redisson 源码核心逻辑（概念层面）
private void renewExpiration() {
    // 创建一个 Netty 定时任务，延迟 internalLockLeaseTime / 3 后执行
    Timeout task = commandExecutor.getConnectionManager()
        .newTimeout(new TimerTask() {
            @Override
            public void run(Timeout timeout) throws Exception {
                // 执行 Lua 续期脚本
                RFuture<Boolean> future = renewExpirationAsync(threadId);
                future.onComplete((res, e) -> {
                    if (res) {
                        // 续期成功 → 递归调用自己，形成循环续期
                        renewExpiration();
                    }
                });
            }
        }, internalLockLeaseTime / 3, TimeUnit.MILLISECONDS);
    // 将 Timeout 对象存入 EXPIRATION_RENEWAL_MAP 供解锁时取消
    EXPIRATION_RENEWAL_MAP.put(entryName, task);
}
```

**续期 Lua 脚本**：

```lua
-- KEYS[1] = lockName, ARGV[1] = UUID:threadId, ARGV[2] = leaseTime
if (redis.call('hexists', KEYS[1], ARGV[1]) == 1) then
    redis.call('pexpire', KEYS[1], ARGV[2])
    return 1
end
return 0
```

**续期分三步**：
1. 检查 Hash 的 field 是否等于当前线程 ID（`hexists`）
2. 是 → 将锁的过期时间重新设为 30s（`pexpire`）
3. 递归调用自己，10s 后再来续

#### 3.4 线程挂了的场景

如果业务线程突然崩溃（OOM、Kill -9、机器宕机）：

- 看门狗任务和业务线程在**同一个 JVM 进程**中
- 进程挂了 → Netty 的 EventLoop 也停了 → **定时任务不再执行**
- 锁的 30s 过期时间自然倒计时 → 到期自动释放
- 新的等待线程正常获取锁

> 这解决了一个经典问题：**锁持有者挂了，锁不释放怎么办？**

#### 3.5 看门狗风险点

看门狗有一个**微妙的竞态窗口**：如果业务线程在 Watch Dog 续期后的 10s 间隔内 GC STW（Stop-The-World）超过 30s → 锁过期了 → 其他线程拿到锁 → GC 恢复后业务线程以为还有锁 → 数据不一致。

**应对**：实际场景中 Full GC 几十秒不常见，但如果严格要求，可以用 RedLock 降低概率。

---

### 四、实践应用 —— 完整代码示例

```java
import org.redisson.Redisson;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.redisson.config.Config;

public class RedissonLockDemo {

    private static final RedissonClient redisson;

    static {
        Config config = new Config();
        config.useSingleServer()
              .setAddress("redis://127.0.0.1:6379");

        // 设置看门狗相关参数（可选，默认即可）
        config.setLockWatchdogTimeout(30_000); // 默认 30s，可不配

        redisson = Redisson.create(config);
    }

    public static void main(String[] args) {
        RLock lock = redisson.getLock("order:pay:12345");

        try {
            // === 方案一：看门狗自动续期（推荐） ===
            // 不传过期时间 → Watch Dog 启动，每 10s 续期到 30s
            lock.lock();
            System.out.println("获取到锁，threadId=" 
                + Thread.currentThread().getId());

            // 模拟耗时业务操作（超过 30s 也能保住锁）
            Thread.sleep(60_000); // 执行 60s
            // 看门狗会在第 10s、20s、30s、40s、50s 各续期一次

            // === 方案二：可重入验证 ===
            // 同一线程再次加锁（value 从 1 → 2）
            lock.lock();
            try {
                System.out.println("可重入成功，重入次数=" 
                    + lock.getHoldCount());
            } finally {
                lock.unlock(); // value 从 2 → 1
            }

        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            // === 释放锁并停止看门狗 ===
            // 看门狗任务从 EXPIRATION_RENEWAL_MAP 中移除
            lock.unlock();
            // Lua 脚本检查 field == threadId，匹配则 del
            // 看门狗停止续期
        }

        // === 方案三：tryLock 手动控制 ===
        RLock lock2 = redisson.getLock("order:refund:67890");
        try {
            // waitTime=100ms, leaseTime=10s → 看门狗不启动
            boolean acquired = lock2.tryLock(100, 10, 
                TimeUnit.SECONDS);
            if (acquired) {
                try {
                    // 业务必须在 10s 内完成，否则锁自动释放
                    doBusiness();
                } finally {
                    lock2.unlock();
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private static void doBusiness() {
        System.out.println("执行业务逻辑...");
    }
}
```

---

### 五、深入思考 —— 对比与延伸

#### 5.1 普通 Redis 锁 vs Redisson 锁

| 对比项 | SETNX + EXPIRE | Redisson RLock |
|--------|---------------|----------------|
| 加锁 | SET NX + EXPIRE 两条命令 | Lua 脚本单次原子执行 |
| 可重入 | 不支持（需自行实现计数） | Hash 结构原生支持 |
| 过期时间 | 固定值，难预估 | 看门狗动态续期 |
| 释放安全 | 每人都能 del（除非自己设随机值） | Lua 脚本验证 field 匹配 |
| 等待队列 | 无，需循环 sleep 重试 | 内置信号量订阅，阻塞等待 |
| 极端情况 | 业务超时 → 锁误释放 | 续期机制防止误释放 |

#### 5.2 RedLock 红锁算法

**为什么需要 RedLock？**

在 Redis 主从架构（Master-Slave）中：

1. 客户端 A 在 Master 上加锁成功
2. Master 在同步到 Slave 之前宕机
3. Slave 升为 Master
4. 客户端 B 上来对这个新 Master 加锁成功
5. **两个客户端同时持有了同一个锁** → 分布式锁失效

**RedLock 算法步骤**：

1. 准备 N 个（通常 **5 个**）完全独立的 Redis 节点（不主从、不集群）
2. 客户端按顺序向所有节点发送加锁请求
3. 每个请求设置超时时间（远小于锁过期时间）
4. 如果成功获得超过 **N/2 + 1**（即 3/5）个节点的锁，且总耗时小于锁过期时间 → **加锁成功**
5. 否则，向所有节点发起解锁（撤销已获得的锁）

```java
// Redisson RedLock 使用示例
RedissonClient redisson1 = Redisson.create(config1);
RedissonClient redisson2 = Redisson.create(config2);
RedissonClient redisson3 = Redisson.create(config3);
RedissonClient redisson4 = Redisson.create(config4);
RedissonClient redisson5 = Redisson.create(config5);

RLock lock1 = redisson1.getLock("lockKey");
RLock lock2 = redisson2.getLock("lockKey");
RLock lock3 = redisson3.getLock("lockKey");
RLock lock4 = redisson4.getLock("lockKey");
RLock lock5 = redisson5.getLock("lockKey");

RedissonRedLock redLock = new RedissonRedLock(lock1, lock2, 
    lock3, lock4, lock5);

try {
    // RedLock 内部自动完成多数投票机制
    if (redLock.tryLock(100, 30, TimeUnit.SECONDS)) {
        // 加锁成功，执行业务
        doBusiness();
    }
} finally {
    redLock.unlock();
}
```

**RedLock 的争议**：分布式系统专家 Martin Kleppmann 曾发文质疑 RedLock，认为它依赖**严格的时间假设**（时钟漂移会导致问题）。但 RedLock 仍是业界使用最广泛的**跨节点容错锁方案**。

#### 5.3 锁的粒度考虑

在实践中，除了锁的实现机制，还需要思考：
- **锁粒度**：锁订单 `order:123` 还是锁用户 `user:456`？粒度越细，并发越高
- **热点 Key**：秒杀场景下，同一个 key 可能被大量线程争抢，需要分段加锁（sharding）
- **锁超时兜底**：即使有看门狗，也应该在业务代码中设置**全局超时**，防止死循环无限续期

---

## 🗺️ 回答思路

### 答题逻辑框架

```
第一层（30s）：Redisson 是什么，和 Jedis/Lettuce 的区别
  → 一句话定位：Redis 分布式工具集，不只是客户端

第二层（2min）：RLock 核心实现
  → Hash 结构（key/field/value）
  → Lua 脚本保证原子性
  → 可重入原理（+1/-1 计数）

第三层（3min）：看门狗机制 ← 这是面试官最想听的
  → 为什么需要（业务超时 vs 死锁的矛盾）
  → 怎么实现（Netty TimerTask + Lua 续期）
  → 触发条件（不传 leaseTime）
  → 线程挂了怎么办

第四层（30s）：解锁流程
  → 先检查 field 匹配
  → 重入减到 0 才真正释放
  → 同时停止看门狗

第五层（1min）：对比与延伸
  → 普通 Redis 锁的问题（SETNX + EXPIRE 非原子、不可重入、无续期）
  → RedLock 解决了主从切换的脑裂问题
  → RedLock 的争议
```

### 重点得分点（按权重排序）

1. **⭐⭐⭐ Lua 脚本保证原子性** — 每次提到锁操作都要强调原子性
2. **⭐⭐⭐ 看门狗续期周期 = 1/3 过期时间** — 默认 30s/10s 这个数字要准确
3. **⭐⭐⭐ 看门狗续期前检查 field = threadId** — 不检查直接续期会有安全问题
4. **⭐⭐ 可重入用 Hash 的 value 计数** — 体现出数据结构选择的思考
5. **⭐⭐ 解锁时停止看门狗** — 防止解锁后空转浪费资源
6. **⭐ RedLock 多数投票机制** — 至少知道主从切换会导致什么问题

### 常见误区

| 误区 | 正确理解 |
|------|---------|
| "Redisson 和 Jedis 一样，都是 Redis 客户端" | Redisson 是分布式工具集，封装了大量高级分布式数据结构，远不止是客户端 |
| "看门狗是无限续期的" | 看门狗续期依赖于业务线程存活，线程/进程挂了就不会再续 |
| "RedLock 保证绝对安全" | 任何分布式锁都有时钟漂移等隐患，只能降低概率 |
| "tryLock 不启动看门狗" | 准确说是：传了 `leaseTime` 的 tryLock 不启动 |

### 时间分配建议（5分钟回答）

| 阶段 | 时间 | 内容 |
|------|------|------|
| 开头 | 20s | Redisson 一句话定位（分布式工具集） |
| 核心机制 | 90s | Hash + Lua + 可重入（重点展开） |
| 看门狗 | 2min | 作用→触发条件→实现→线程挂了的场景 |
| 解锁流程 | 30s | 三步走：检查→减数→释放+停看门狗 |
| 对比 | 30s | 普通 Redis 锁的缺陷，为什么需要 Redisson |
| 延伸 | 30s | RedLock 解决什么问题 |
| 结尾 | 10s | 总结：原子性、续期、容错 |

### 过渡话术

**从 Redisson 定位到锁实现**：
> "Redisson 最核心的功能就是分布式锁，下面我详细拆解它的 RLock 实现..."

**从锁结构到看门狗**：
> "不过光有 Hash 和 Lua 还不够 —— 怎么解决锁过期时间设置的问题？这就引出了看门狗机制..."

**从看门狗到解锁**：
> "看门狗是保障业务执行期锁不释放的，那业务正常结束后的解锁流程是怎样的？..."

**从 Redisson 到 RedLock**：
> "以上讨论的都是单 Redis 节点场景，但在主从架构下有一个经典的问题 —— 如果 Master 挂了怎么办？这时候就需要 RedLock 了..."

---

> **一句话终结论**：Redisson RLock 通过 **Lua 脚本 + Hash 结构** 保证了锁的**原子性**和**可重入性**，**看门狗**机制解决了**过期时间难以预估**的核心痛点，**RedLock** 则进一步在**跨节点场景**下提供了容错保障。面试中重点突出"如何解决分布式锁的三个核心问题"：原子性、自动续期、安全性。
