# Redis 分布式锁如何实现

---

## 联想记忆法

### 记忆口诀/联想

**口诀：SET 一锁，Watchdog 续命，Lua 一脚本，Del 收工**

或者用 **"互死不重高，V 到 V3 走一遭，SET 配 Lua，Watchdog 把命保"** 来记忆整个知识体系：

- **互死不重高** = 互斥 (Mutual Exclusion)、防死锁 (Deadlock Prevention)、可重入 (Reentrancy)、高可用 (High Availability) —— 分布式锁四大需求
- **V 到 V3 走一遭** = V1(SETNX+EXPIRE) → V2(SET NX EX) → V3(Redisson/RedLock) 三种实现演进
- **SET 配 Lua** = 加锁用 SET 原子指令，释放用 Lua 脚本保证原子性
- **Watchdog 把命保** = Redisson Watchdog 自动续期机制

### 记忆原理

这个口诀采用 **"三字经+七言"的混合节奏**，押"ao"韵（高、遭、稿、保），朗朗上口。前三个字"互死不重高"提取了分布式锁四个核心需求的第一个字，形成易于回忆的线索链。V1→V2→V3 的版本演进像一个故事线，面试时顺着版本号就能回忆起每一步解决了什么问题。SET 和 Lua 对应加锁和解锁两个关键操作，是代码实现中最核心的两个动作。

### 关联知识

- **与数据库乐观锁关联**：Redis SET NX 类似于数据库的 `INSERT ... WHERE NOT EXISTS`，都是"不存在才写入"的互斥逻辑
- **与 CAS (Compare And Swap) 关联**：Lua 释放锁时的 GET+DEL 本质是 CAS 思想的实现——先比较持有者再删除
- **与 JVM 的 ReentrantLock 关联**：Redisson 的 RLock 实现了 JUC 的 Lock 接口，可重入机制类似 AQS 的状态计数
- **与 CAP 理论关联**：Redis 是 AP 系统（可用性+分区容忍性），Zookeeper 是 CP 系统（一致性+分区容忍性），选择哪种分布式锁本质是 CAP 的权衡

---

## 深度解答

### 第一层：核心概念

#### 什么是分布式锁

分布式锁 (Distributed Lock) 是一种跨多个进程/机器的互斥同步原语。在单机多线程场景下，我们使用 `synchronized` 或 `ReentrantLock` 来协调线程对共享资源的访问；但在分布式系统中，多个服务实例运行在不同 JVM 甚至不同物理机上，本地锁无法跨进程生效，因此需要一种**所有节点都能访问的第三方中间件**来协调互斥——这就是分布式锁。

#### 四大核心需求

| 需求 | 英文术语 | 说明 |
|------|----------|------|
| **互斥性** | Mutual Exclusion | 任何时刻只有一个客户端持有锁 |
| **防死锁** | Deadlock Prevention | 锁必须有过期时间 (TTL / Time-To-Live)，防止持有者宕机后锁永远不被释放 |
| **可重入** | Reentrancy | 同一个线程可以重复获取同一把锁，不会自己阻塞自己 |
| **高可用** | High Availability | 锁服务本身不能成为单点故障 (Single Point of Failure, SPOF) |

其他非必需但重要的需求还包括：

- **锁的自动续期** (Automatic Renewal / Lease Extension)：防止业务执行时间超过锁的过期时间
- **公平性** (Fairness)：是否按请求顺序分配锁
- **容错性** (Fault Tolerance)：节点宕机不影响锁服务的整体可用性

---

### 第二层：底层原理

#### Redis 为何适合做分布式锁

Redis 是基于内存的键值存储系统，具备以下优势：

1. **单线程模型 (Single-threaded Event Loop)**：所有命令串行执行，天然保证操作的原子性
2. **SET 命令的 NX 选项**：原子地执行"不存在才设置"(Set if Not eXists)，这是分布式锁互斥的核心
3. **EXPIRE/PEXPIRE 机制**：支持键过期，天然防止死锁
4. **Lua 脚本支持**：保证多个 Redis 命令的原子执行

#### 实现演进详解

##### V1：SETNX + EXPIRE（问题版本）

```java
// 第一步：尝试获取锁
long result = jedis.setnx("lock:order", "1");  // 返回 1 成功，0 失败
// 第二步：设置过期时间（防止死锁）
jedis.expire("lock:order", 30);
```

**问题**：`SETNX` 和 `EXPIRE` 是两个独立命令，**非原子操作**。如果 `SETNX` 执行后程序崩溃或 `EXPIRE` 执行失败，锁将永不过期，形成死锁 (Deadlock)。这是经典的非原子性问题 (Non-atomic Operation Problem)。

##### V2：SET key value NX EX seconds（原子版本）

Redis 从 2.6.12 版本开始，`SET` 命令支持 `NX` 和 `EX` 选项的组合，将加锁和过期设置为**一条原子命令**：

```java
// 原子加锁：set key value NX EX seconds
String result = jedis.set("lock:order", threadId, "NX", "EX", 30);
// 返回 "OK" 表示获取成功，返回 null 表示获取失败
```

这里 `value` 存储的是客户端唯一标识（如 `UUID` 或 `Thread ID`），用于在释放锁时验证持有者身份——防止**误释放他人持有的锁** (Unlock by Mistake)。

**释放锁需要 Lua 脚本保证原子性**：

```lua
-- 释放锁的 Lua 脚本：先判断持有者再删除
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
```

```java
// Java 调用 Lua 脚本
String script = "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) else return 0 end";
jedis.eval(script, Collections.singletonList("lock:order"), Collections.singletonList(threadId));
```

如果不做持有者校验而直接 `DEL`，可能出现**时序问题**：

1. 线程 A 持有锁，业务执行超过 30 秒，锁自动过期
2. 线程 B 获取锁成功
3. 线程 A 执行完毕，调用 `DEL` —— 把线程 B 的锁释放了
4. 线程 C 又获取了锁，导致 B 和 C 同时执行临界区

这就是为什么释放锁必须用 Lua 脚本来保证 **GET（比较）和 DEL（删除）的原子性**。

##### V3：Redisson 框架（企业级方案）

Redisson 是一个基于 Redis 的 Java 分布式框架，提供了开箱即用的分布式锁实现，解决了 V2 方案的若干痛点。

###### Redisson RLock 的核心机制

```xml
<!-- Maven 依赖 -->
<dependency>
    <groupId>org.redisson</groupId>
    <artifactId>redisson</artifactId>
    <version>3.27.0</version>
</dependency>
```

```java
// 配置 Redisson 客户端
Config config = new Config();
config.useSingleServer().setAddress("redis://127.0.0.1:6379");
RedissonClient redisson = RedissonClient.create(config);

// 获取分布式锁（RLock 实现了 java.util.concurrent.locks.Lock 接口）
RLock lock = redisson.getLock("myLock");

try {
    // 尝试加锁，默认过期时间 30 秒
    lock.lock();
    
    // 业务逻辑
    processOrder();
    
} finally {
    // 释放锁
    lock.unlock();
}
```

###### Watchdog 自动续期机制

Redisson 的 Watchdog（看门狗）是 V2 方案中"锁过期时间难预估"问题的解决方案：

```
                ┌──────────────────────────────────────────────────┐
                │              Redisson Watchdog                   │
                │                                                  │
                │  lock() 时设定默认过期时间 30s                   │
                │  启动后台定时线程 (netty-timer)                   │
                │  每 10s（1/3 过期时间）检查一次                   │
                │  若锁仍被当前线程持有，执行 Lua 脚本重置过期时间  │
                │  释放锁时关闭 Watchdog                            │
                └──────────────────────────────────────────────────┘
```

```java
// Watchdog 的核心逻辑（简化示意）
lock.lock(30, TimeUnit.SECONDS);
// Redisson 自动启动一个定时任务，每 10 秒执行一次：
//   if (lock.exists()) { lock.expire(30, TimeUnit.SECONDS); }
// 业务无需关心过期时间是否足够
```

Watchdog 的设计解决了经典的两难问题：

- 锁过期时间设得太短 → 业务未完成锁就过期，其他线程闯入
- 锁过期时间设得太长 → 持有者宕机后锁一直不释放

###### 可重入实现

Redisson 的 RLock 支持可重入。其 Redis 数据结构采用 **Hash 类型**：

```
Key: "myLock"
Field: UUID:ThreadId      (客户端唯一标识)
Value: 重入次数计数器      (Reentrant Count)
```

- 加锁时：`EXISTS myLock == 0` → 创建 Hash，`HSET myLock UUID:ThreadId 1`
- 重入时：`HEXISTS myLock UUID:ThreadId == 1` → `HINCRBY myLock UUID:ThreadId 1`
- 解锁时：`HINCRBY myLock UUID:ThreadId -1` → 如果计数归零则 `DEL myLock`

###### RedLock（红锁）算法

Redis 官方提出的 RedLock 算法用于解决**单点故障问题**。基本原理：

```
N = 5 (奇数个 Redis 节点，相互独立，不需要主从复制)

1. 客户端获取当前时间戳 T1
2. 依次向 N 个节点发送 SET NX EX 请求，设置一个较短的超时时间（如 10ms）
3. 计算成功获取锁的节点数 M
4. 判断条件：
   - M >= N/2 + 1（即多数节点加锁成功）
   - 总耗时 < 锁过期时间
   同时满足则加锁成功，否则向所有节点发送解锁请求
```

**关于 RedLock 的争议**：分布式系统领域权威 Martin Kleppmann 曾撰文批评 RedLock 存在根本性问题（依赖时间假设、GC pause 导致锁失效等），Redis 作者 antirez 进行了回应。实践中，**大多数业务场景不需要 RedLock**——保证 Redis 主从高可用（哨兵/Cluster）通常已足够。

---

### 第三层：实践应用

#### 原生 Jedis 完整实现

```java
public class RedisDistributedLock {
    
    private final JedisPool jedisPool;
    private final String lockKey;
    private final String lockValue;  // UUID:ThreadId
    private final int expireTime;    // 过期时间（秒）
    
    private static final String LOCK_SUCCESS = "OK";
    private static final String UNLOCK_SCRIPT = 
        "if redis.call('GET', KEYS[1]) == ARGV[1] then " +
        "    return redis.call('DEL', KEYS[1]) " +
        "else " +
        "    return 0 " +
        "end";
    
    public RedisDistributedLock(JedisPool jedisPool, String lockKey, int expireTime) {
        this.jedisPool = jedisPool;
        this.lockKey = lockKey;
        this.lockValue = UUID.randomUUID().toString() + ":" + Thread.currentThread().getId();
        this.expireTime = expireTime;
    }
    
    /**
     * 尝试获取锁（非阻塞）
     */
    public boolean tryLock() {
        try (Jedis jedis = jedisPool.getResource()) {
            String result = jedis.set(lockKey, lockValue, SetParams.setParams()
                .nx()    // 不存在才设置
                .ex(expireTime));  // 过期时间
            return LOCK_SUCCESS.equals(result);
        }
    }
    
    /**
     * 尝试获取锁（带超时阻塞）
     */
    public boolean tryLock(long waitTime, TimeUnit unit) throws InterruptedException {
        long deadline = System.currentTimeMillis() + unit.toMillis(waitTime);
        while (System.currentTimeMillis() < deadline) {
            if (tryLock()) {
                return true;
            }
            Thread.sleep(100);  // 自旋间隔
        }
        return false;
    }
    
    /**
     * 释放锁（Lua 脚本保证原子性）
     */
    public void unlock() {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.eval(UNLOCK_SCRIPT, 
                Collections.singletonList(lockKey),
                Collections.singletonList(lockValue));
        }
    }
}
```

**使用示例**：

```java
RedisDistributedLock lock = new RedisDistributedLock(jedisPool, "lock:pay:12345", 30);

if (lock.tryLock()) {
    try {
        // 执行支付业务逻辑
        processPayment();
    } finally {
        lock.unlock();  // 务必在 finally 中释放
    }
} else {
    // 获取锁失败，返回提示或重试
    return "操作过于频繁，请稍后重试";
}
```

#### Redisson 生产级使用

```java
@Configuration
public class RedissonConfig {
    
    @Bean
    public RedissonClient redissonClient() {
        Config config = new Config();
        config.useClusterServers()
            .addNodeAddress("redis://node1:6379", "redis://node2:6379")
            .setPassword("xxx")
            .setMasterConnectionPoolSize(64)
            .setSlaveConnectionPoolSize(64);
        return Redisson.create(config);
    }
}

@Service
public class OrderService {
    
    @Autowired
    private RedissonClient redissonClient;
    
    public void createOrder(OrderDTO order) {
        String lockKey = "lock:order:" + order.getUserId();
        RLock lock = redissonClient.getLock(lockKey);
        
        // 等价于 tryLock(10s, 30s, TimeUnit.SECONDS)
        // waitTime: 等待锁的时间
        // leaseTime: 锁持有时间（-1 则启用 Watchdog）
        boolean acquired = lock.tryLock(10, 30, TimeUnit.SECONDS);
        
        if (!acquired) {
            throw new BusinessException("请稍后重试");
        }
        
        try {
            // 业务处理：订单创建、库存扣减
            orderService.createOrderInternal(order);
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }
}
```

#### 最佳实践清单

1. **始终在 finally 中解锁**：确保异常时锁不被遗漏
2. **锁的粒度要细**：锁的 Key 尽量精确到具体资源（如 `lock:order:${orderId}`），不要用全局锁
3. **设置合理的等待超时**：`tryLock(waitTime)` 避免无限等待
4. **统一锁的 Key 命名规范**：建议格式 `业务域:资源类型:资源ID`
5. **监控锁的持有时间**：超过阈值输出告警日志
6. **选择合适的部署模式**：大多数业务 Redis 哨兵/Cluster 足够，RedLock 仅在强一致性场景下考虑

---

### 第四层：深入思考

#### 1. 主从切换的锁丢失问题

**问题描述**：

```
Redis 主从采用异步复制 (Asynchronous Replication)：

  客户端 A → Master 加锁成功 (SET NX EX)
  Master 在将数据同步到 Slave 前宕机
  Sentinel 选举 Slave 升级为新的 Master
  此时新 Master 没有锁的数据
  客户端 B 对新 Master 加锁成功！
  → 客户端 A 和 B 同时持有锁，互斥性被破坏
```

**解决方案及权衡**：

| 方案 | 原理 | 代价 |
|------|------|------|
| **WAIT 命令** | 等待至少 N 个 Slave 完成复制后才返回 | 增加延迟，降低吞吐 |
| **RedLock** | 多数节点写入 | 部署复杂，有理论争议 |
| **Zookeeper** | 强一致性（ZAB 协议） | 性能低于 Redis |
| **业务层兜底** | 用数据库乐观锁做防重/幂等 | 增加代码复杂度 |

实践中，对于**绝大多数的互联网业务场景**（如秒杀库存、重复支付防护），允许极短时间窗口内的锁丢失，通过数据库层面的唯一约束或乐观锁做兜底即可。这也是为什么 Redis 分布式锁是主流选型——它在**一致性（Consistency）和可用性（Availability）之间取得了工程上可接受的平衡**。

#### 2. 时钟漂移问题 (Clock Drift)

**问题影响**：RedLock 依赖时间判断（比较当前时间与锁获取时间），如果 Redis 节点间的系统时钟不同步（Clock Drift），可能导致：

- 节点 A 时间比实际快 → 锁提前过期，互斥性失效
- 节点 B 时间比实际慢 → 锁过期时间延长，死锁风险增大

**应对策略**：

- 使用 NTP (Network Time Protocol) 保证节点间时钟偏差在合理范围
- Redisson 的实现不依赖本地时间（使用 Redis 的 TTL 机制），天然避免了此问题
- 如果使用 RedLock，设置较短的时间超时和宽松的时钟漂移容忍度

#### 3. Zookeeper vs Redis 对比

| 维度 | Zookeeper | Redis |
|------|-----------|-------|
| **一致性模型** | **CP** (强一致) | **AP** (最终一致) |
| **实现原理** | 临时顺序节点 + Watcher | SET NX EX + Lua |
| **锁丢失** | ZAB 协议保证不丢失 | 主从切换可能丢失 |
| **性能** | 写入 O(n)（ZAB 投票），QPS ~数万 | 内存操作，QPS 可达十万+ |
| **客户端复杂度** | Curator 封装了锁实现 | Redisson 封装了锁实现 |
| **适用场景** | 配置中心、分布式协调等强一致场景 | 高并发、允许短暂不一致的场景 |
| **死锁预防** | 临时节点（Session 断开自动删除） | TTL 过期自动删除 |
| **可重入** | Curator 支持 | Redisson 支持 |

**选择建议**：

- **优先 Redis**：大部分业务场景（秒杀、防重、幂等）允许极小概率的锁丢失，Redis 的高性能是关键优势
- **选择 ZK**：金融交易、分布式任务调度等**锁丢失不可接受**的场景，ZK 的强一致性更重要

#### 4. 其他值得思考的问题

**GC Pause 导致的锁失效**：Java 应用发生 Stop-The-World GC 时，锁持有者暂停，锁可能在此期间过期。解决思路：

- Redisson Watchdog 在 GC 期间也会暂停，续期会失败，锁自然过期——是一种"安全失效"
- 业务层做幂等设计 (Idempotency)，即使锁失效也能保证数据最终一致

**锁的粒度优化**：对于热点资源，可以使用分段锁 (Segmented Lock)——将单个锁拆分为 N 个锁段，降低锁竞争。例如库存为 1000 件，拆分为 10 个段，每段 100 件。

---

## 回答思路

### 答题逻辑框架

面试时建议按以下层次递进回答，总时长控制在 **3-5 分钟**：

```
┌─────────────────────────────────────────────────┐
│  第一层（20秒）：一句话定义                       │
│  "分布式锁是分布式系统中协调多节点互斥访问         │
│   共享资源的一种机制"                             │
├─────────────────────────────────────────────────┤
│  第二层（60秒）：核心需求 + 版本演进              │
│  四大需求（互斥/防死锁/可重入/高可用）→          │
│  V1(V2)的缺陷 → V2(SET NX EX)的改进 →           │
│  V3(Redisson)的完善                             │
├─────────────────────────────────────────────────┤
│  第三层（60秒）：关键代码                         │
│  SET NX EX 加锁 + Lua 脚本解锁                   │
│  强调 value 存储唯一标识防止误删                   │
├─────────────────────────────────────────────────┤
│  第四层（30秒）：Watchdog + 可重入               │
│  演示对 Redisson 原理的理解深度                   │
├─────────────────────────────────────────────────┤
│  第五层（40秒）：深入思考                         │
│  主从切换锁丢失 + RedLock + ZK对比               │
│  展示技术视野和架构思维                           │
└─────────────────────────────────────────────────┘
```

### 重点得分点（面试官考察意图）

1. **原子性意识**（核心得分点）：能指出 V1 的 `SETNX + EXPIRE` 非原子问题，并给出 V2 的 `SET NX EX` 解决方案——这考察对 Redis 命令原子性的理解深度

2. **Lua 脚本的理解**：能解释为什么释放锁需要 Lua 脚本，以及误删他人锁的场景——考察分布式编程中的"检查再执行"(Check-Then-Act)竞态条件意识

3. **Watchdog 原理**：能说出 Redisson 自动续期的具体时间间隔（10s 续 30s）——区分"用过 Redisson"和"读过 Redisson 源码"的分水岭

4. **CAP 取舍**：能对比 ZK 的 CP 和 Redis 的 AP，并给出选型建议——考察架构决策能力

### 常见误区（扣分点）

| 错误说法 | 正确理解 |
|----------|----------|
| "SETNX 本身就是原子操作" | SETNX 是原子的，但 SETNX+EXPIRE 的组合不是原子操作 |
| "直接用 DEL 删除锁" | 必须先比较持有者再删除，否则可能删除他人持有的锁 |
| "过期时间设长一点就安全了" | Watchdog 才是正确的解决方案，静态过期时间无法应对业务波动 |
| "RedLock 能完美解决锁丢失" | RedLock 也有时钟漂移问题，且 Martin Kleppmann 提出过质疑 |
| "分布式锁保证数据绝对一致" | 分布式锁不是银弹，需要业务层幂等做兜底 |

### 过渡话术建议

- **从需求到实现**："针对这四个核心需求，我们来看 Redis 分布式锁的三种实现演进..."
- **从 V2 到 V3**："V2 方案解决了原子性问题，但在生产环境中还有几个痛点：过期时间难以预估、不支持可重入。Redisson 框架正是为了解决这些问题而诞生的。"
- **从 Redis 到 ZK 对比**："Redis 分布式锁在大多数场景下够用，但需要注意到主从异步复制导致的锁丢失问题。如果对一致性要求极其严格，可以考虑 Zookeeper 实现——接下来我想简单对比一下两者的差异..."
- **总结过渡**："以上就是我对 Redis 分布式锁的理解，总的来说，它是在可用性和一致性之间取得平衡的工程方案，核心是原子操作加锁和 Lua 脚本解锁这两个关键点。"

### 时间分配建议

- **面试总时长 45 分钟的场景**：此问题回答控制在 5 分钟内，留出 40 分钟给面试官追问（如 RedLock 细节、ZK 对比、Redis Cluster 模式下的锁行为等）
- **如果面试官打断**：说完 V2 原子命令和 Lua 脚本可暂停，这是最重要的两个点。Watchdog 和 ZK 对比是加分项，如果时间紧可以一句带过说"Redisson 提供了更完善的解决方案，包括自动续期和可重入"
- **遇到追问如何应对**：如果被问到未准备的知识点，可以说"这部分我没有深入研究过，不过我的理解是..."，展示思考过程比直接说"不知道"要好得多
