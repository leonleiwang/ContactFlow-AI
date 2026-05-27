# ContactFlow AI

ContactFlow AI 是一个面向企业客服与工单处理场景的 AI Contact Center 原型系统，采用 Java Spring Boot、Python AI Service 与 React 构建，围绕工单流转、坐席辅助、企业知识库检索、异步事件处理和服务治理，探索大模型能力在企业客服 SaaS 中的工程化落地。

项目不是单纯的 AI Chatbot 和 RAG 企业知识库，而是将 AI 能力嵌入真实客服工单流程：Java 服务负责工单状态机、并发领取、审计日志、幂等控制和业务一致性；Python AI Service 负责意图识别、转人工评估、RAG 检索、风险判断和建议回复；Redis 与 RabbitMQ / Kafka 用于缓存、幂等、事件解耦和异步处理；React 前端提供面向坐席的三栏工作台，用于展示工单详情、AI Assist、SLA 风险和处理状态。

在 V0.2 中，项目进一步扩展企业知识库 RAG 能力，重点从“能问答”升级到“可运营、可评估、可追溯”的知识检索系统：支持基于 Markdown / 段落结构和 NLP 句子边界的动态切分、token budget 与 overlap 控制、父子索引、Query Rewrite 语义校验、向量检索 + BM25 + FAQ / 手册多路召回、轻量重排序、证据引用、低置信转人工，以及 Context Recall、Faithfulness、幻觉率、Rewrite Accept Rate 和 Retrieval Latency 等评估指标。

该项目关注的核心问题是：如何在企业客服场景中，让大模型既能辅助坐席提升处理效率，又不直接越权修改业务事实；如何通过异步架构、证据约束、成本路由、风险检查和人工确认机制，将 AI 从“聊天能力”落到可控、可追踪、可评估的业务流程中。

## 项目定位

核心目标：

- 用 Java Spring Boot 承担工单、状态流转、审计日志、并发控制、OpenAPI 合同等企业后端职责。
- 用 Python AI Service 承担意图识别、转人工评估、AI 摘要、建议回复、SLA 风险检查、RAG 检索与成本路由。
- 用 Redis / MQ / MySQL 体现真实企业系统中的缓存、异步处理和事实数据一致性。
- 用 React 构建坐席工作台，而不是营销型 AI 页面。
- 用可落地的企业知识库 RAG 设计补齐多源异构数据、ETL、语义切分、混合检索、重排序、幻觉控制、权限隔离和反馈闭环。

## V0.1 范围

V0.1 只做一个高价值闭环：

> 工单创建后，Java 服务写入 MySQL 并发布 `ticket.created` 事件；Python AI Service 异步生成摘要、意图、SLA 风险、转人工建议和回复建议；Java 服务持久化 AI Assist；React 坐席台展示工单、AI Assist 和状态流转按钮。

不一开始做复杂分布式，是为了把业务边界讲清楚：

- 工单创建必须快，不能被 LLM 延迟阻塞。
- AI 分析可能慢、可能失败、可能需要重试，所以放到异步链路。
- Java 服务仍然是工单事实来源，Python AI 只返回建议，不直接修改业务状态。
- 即使 AI 服务不可用，客服仍然能接单、流转、关闭工单。

## 技术栈

| 层 | 技术 | 责任 |
| --- | --- | --- |
| 后端业务核心 | Java 17, Spring Boot 3, Spring Data JPA | 工单、状态机、并发抢单、审计、API 合同 |
| 数据库 | MySQL, Flyway | 业务事实、版本号、事件日志、AI Assist 结果 |
| 缓存 | Redis，V0.1 先预留接口 | 热工单详情、队列计数、可选抢单锁 |
| 消息队列 | RabbitMQ 或 Kafka，V0.1 用接口抽象 | 工单创建、状态变更、AI Assist 完成事件 |
| AI 服务 | Python 3.10, FastAPI | 意图识别、成本路由、RAG mock、转人工评估 |
| 前端 | React, Vite | 三栏坐席工作台、AI Assist、状态操作 |
| 测试 | JUnit 5, Spring Boot Test, pytest | 状态流转、并发抢单、AI 边界行为 |

## 目录结构

```text
contactflow-ai/
  backend/
    pom.xml
    src/main/java/com/contactflow/ticket/
    src/main/resources/db/migration/
    src/test/java/com/contactflow/ticket/
  ai-service/
    app/
    tests/
    requirements.txt
  frontend/
    package.json
    src/
  README.md
```

## 总体架构

```text
React 坐席工作台
      |
      v
Spring Boot Ticket Service
      |
      +-- Ticket Domain
      |     - 工单 CRUD
      |     - 状态流转
      |     - 并发抢单
      |     - SLA 字段
      |     - 审计事件
      |
      +-- Integration Layer
      |     - OpenAPI DTO
      |     - Redis 缓存接口
      |     - MQ 事件发布接口
      |
      v
MySQL

ticket.created / ticket.status_changed
      |
      v
RabbitMQ / Kafka
      |
      v
Python AI Service
      |
      +-- Intent Detection
      +-- Handoff Evaluation
      +-- Suggested Reply
      +-- SLA Risk Check
      +-- Lightweight RAG
      +-- Cost Routing
      |
      v
AI Assist Callback
      |
      v
Spring Boot 持久化 ticket_ai_assists
```

## 企业后端关键设计

### 1. 并发抢单

场景：多个客服几乎同时点击“领取同一个工单”，系统只能允许一个人成功。

V0.1 采用 **数据库条件更新 + 乐观版本号**：

```sql
update support_tickets
set status = 'IN_PROGRESS',
    assigned_agent_id = ?,
    version = version + 1
where id = ?
  and status = 'OPEN';
```

设计考虑：

- `status = 'OPEN'` 是抢单成功的业务前置条件，天然保证只有未领取工单可以被领取。
- `version` 保留给后续复杂编辑场景，例如坐席编辑工单字段、主管改优先级、自动 SLA 任务同时更新。
- Redis 锁只能作为削峰优化，不能作为最终一致性来源；服务重启、锁超时、网络抖动都会让 Redis 锁不能代表业务事实。
- MySQL 是最终事实来源，抢单结果以数据库更新行数为准：`updatedRows = 1` 成功，`updatedRows = 0` 失败。

边界行为：

- 工单已经被别人领取：返回 `409 CONFLICT`。
- 工单不存在：返回 `404 NOT_FOUND`。
- 工单已关闭或取消：返回 `409 CONFLICT`。
- 重复点击领取：第一次可能成功，后续返回当前状态和负责人。

### 2. 状态流转

状态机：

```text
OPEN -> IN_PROGRESS -> WAITING_CUSTOMER -> RESOLVED -> CLOSED
  |          |                 |
  |          |                 +-> ESCALATED
  |          +-> ESCALATED
  +-> CANCELLED
```

设计考虑：

- 状态流转集中在领域服务里，不散落在 Controller。
- 每次流转写入 `ticket_events`，方便追踪是谁在什么时候做了什么。
- `CLOSED` 是终态，不允许继续改状态，除非未来显式设计“重开工单”动作。
- `ESCALATED` 必须带原因，避免只有状态没有上下文。

### 3. 事件异步处理

V0.1 的核心事件：

| 事件 | 生产者 | 消费者 | 作用 |
| --- | --- | --- | --- |
| `ticket.created` | Java Ticket Service | Python AI Service | 异步生成摘要、意图、SLA 风险和建议回复 |
| `ticket.status_changed` | Java Ticket Service | AI / Analytics | 后续可用于质检、SLA 统计和操作分析 |
| `ai_assist.completed` | Python AI Service | Java Ticket Service | AI 结果落库并通知前端刷新 |

设计考虑：

- 创建工单和 AI 分析解耦，避免 LLM 延迟影响主交易链路。
- AI 失败不影响工单主流程。
- AI 输出入库前由 Java 服务校验，避免 AI 直接改变业务事实。
- 事件使用 `eventId` 做幂等键，同一事件重复消费不会写出多条 Assist。

### 4. Redis / MQ 基础设施

V0.2 会把 V0.1 里的接口抽象接入真实 Redis 和 RabbitMQ。Kafka 保留为后续扩展选项，因为 V0.2 的核心是工单事件驱动和 AI 异步处理，RabbitMQ 的路由、确认、死信队列和延迟重试更贴合当前规模。

#### 4.1 Redis 缓存与幂等

Redis 在 V0.2 中不作为业务事实来源，只承担加速、削峰和短期幂等。

计划用途：

| 场景 | Key 设计 | 说明 |
| --- | --- | --- |
| 热工单详情缓存 | `ticket:{tenantId}:{ticketId}` | 缓存工单详情和 AI Assist 汇总，降低详情页反复查询 MySQL 的压力 |
| 队列计数 | `ticket_queue_count:{tenantId}:{status}` | 坐席台左侧队列需要快速显示不同状态数量 |
| AI 事件幂等 | `ai_event:{eventId}` | 防止 MQ 重复投递导致 AI Assist 重复处理 |
| 抢单削峰锁，可选 | `claim_lock:{tenantId}:{ticketId}` | 只用于减少同一工单的瞬时竞争，最终结果仍以 MySQL 条件更新为准 |

设计考虑：

- Redis 缓存失效不能影响工单主流程，缓存未命中时回源 MySQL。
- 工单状态、负责人、SLA 等业务事实必须以 MySQL 为准。
- 抢单不能只依赖 Redis 锁，锁超时或服务重启都可能造成业务语义不完整。
- AI 幂等 key 需要设置 TTL，避免长期堆积；最终落库仍依赖 `source_event_id` 唯一约束。

#### 4.2 RabbitMQ / Kafka 事件处理

V0.2 默认接 RabbitMQ，Kafka 作为 V0.3 或更高吞吐场景的替换实现。

事件流：

```text
Ticket Service
  -> ticket.created exchange
  -> ai.assist.request queue
  -> Python AI Service
  -> ai.assist.completed callback
  -> Ticket Service 落库
```

队列设计：

| 队列 | 作用 | 失败策略 |
| --- | --- | --- |
| `ai.assist.request` | 工单创建后触发 AI 摘要、意图、SLA 检查 | 失败进入延迟重试 |
| `ai.assist.retry` | AI 临时失败后的重试队列 | 超过次数进入死信 |
| `ai.assist.dlq` | 保存不可恢复失败事件 | 后台人工排查或重放 |
| `ticket.audit.events` | 状态流转和操作日志事件 | 后续用于统计、质检和审计 |

设计考虑：

- 事件消息必须带 `eventId`、`tenantId`、`ticketId`、`eventType`、`occurredAt` 和 `schemaVersion`。
- 消费者按 `eventId` 做幂等，允许 MQ 至少一次投递。
- AI 服务失败不能影响客服处理工单，前端展示 AI Assist pending / failed 状态。
- RabbitMQ 适合当前的任务派发、重试和死信处理；Kafka 更适合后续大规模事件流、报表分析和多消费者订阅。

### 5. RAG 知识库

V0.1 先用轻量 RAG mock，V0.2 升级为真实企业知识库。

RAG-Anything 可以作为 V0.2 的工程参考，重点借鉴它在多模态文档解析、版式结构保留、上下文感知处理、向量/图结构融合检索上的思路。它适合处理 PDF、Office、图片、表格、公式等复杂文档，也提供 page/chunk 级上下文窗口、header/caption 保留和 hybrid 查询模式。ContactFlow AI 不直接照搬整个框架，而是把企业客服场景最需要的链路拆出来实现，避免 MVP 被重型依赖和模型配置拖慢。

参考：<https://github.com/HKUDS/RAG-Anything>

V0.2 目标设计：

```text
多源文档
  -> 原始文件存储
  -> 版式解析
  -> ETL 清洗
  -> NLP 动态切分
  -> 父子索引
  -> 向量索引 + BM25 索引 + FAQ/手册索引
  -> Query Rewrite 与语义校验
  -> 分级策略路由
  -> 混合检索
  -> 重排序
  -> 证据组装
  -> 大模型生成
  -> 引用校验、幻觉控制与低置信转人工
  -> 反馈池与评估指标
```

设计考虑：

- 不用固定长度切片作为主策略。企业知识往往包含条件、例外、生效时间和适用范围，切坏了会直接造成错误回答。
- 父子索引保留上下文：子块用于精准召回，父块用于回答时补足政策上下文。
- 混合检索解决只靠向量召回容易漏掉订单号、产品型号、政策编号、人名、机构名和专有术语的问题。
- 所有回答必须能追溯到证据；证据不足时输出坐席摘要和转人工建议，而不是编造答案。
- 未解决问题和坐席修改记录进入反馈池，但不能自动污染正式知识库，需要审核后发布。

#### 5.1 NLP 动态切分

V0.2 会实现结构优先的动态切分，而不是简单按字符数切片。

切分顺序：

```text
Markdown / 标题 / 表格 / 列表结构识别
  -> 段落边界识别
  -> NLP 句子边界检测
  -> token budget 合并
  -> 约 100 token overlap
  -> 生成 child chunk
  -> 绑定 parent section
```

设计考虑：

- Markdown 标题、列表、表格和段落先于 NLP 句子边界，因为企业手册、SOP、FAQ 的结构本身就是语义边界。
- spaCy 或 NLTK 用于句子边界检测，主要解决长段落里多个条件句被切坏的问题。
- 100 token 左右的 overlap 用于保留跨句指代、例外条件和补充说明，但 overlap 不能过大，否则会扩大召回噪音和存储成本。
- child chunk 负责召回精度，parent section 负责生成答案时的上下文完整性。
- 每个 chunk 保存 `tenant_id`、`doc_id`、`section_path`、`source_uri`、`effective_from`、`effective_to`、`acl_tags` 和 `checksum`，方便权限隔离、引用溯源和增量更新。

#### 5.2 Query Rewrite 与语义校验

V0.2 可以做 query rewrite，但必须加防噪音机制。

流程：

```text
原始问题
  -> 意图识别
  -> 小模型生成 2-3 个改写问题
  -> Embedding 相似度校验
  -> Sim(original, rewrite) >= 0.8 的改写进入检索
  -> Sim < 0.8 的改写丢弃
```

设计考虑：

- query rewrite 适合把用户的口语化问题补全为更具体的业务问题，例如“这个还能退吗”扩写为“订单签收超过 7 天是否支持退货”。
- 改写会带来额外召回能力，也可能引入原问题没有的条件，所以必须做语义相似度校验。
- `0.8` 作为 V0.2 默认阈值，后续根据评测集调参；低于阈值直接舍弃，避免系统自己制造检索噪音。
- 高风险意图、投诉、法务、赔偿承诺类问题默认减少或关闭自由扩写，只允许结构化补全，避免改变用户诉求。

#### 5.3 混合检索、重排序与策略路由

V0.2 会实现多路召回，但重排序按问题复杂度分级开启。

召回通道：

| 通道 | 作用 | 适合问题 |
| --- | --- | --- |
| Vector Search | 语义召回 | 口语化问题、近义表达、政策理解 |
| BM25 | 关键词召回 | 人名、机构名、产品型号、政策编号、专有名词 |
| FAQ Index | 高频问答补充 | 标准客服问题、固定话术、低成本直答 |
| Manual Index | 手册/SOP 补充 | 流程型、条件型、规则型问题 |
| Graph Index，V0.3 | 关系增强 | 多实体、多条件、跨文档关联问题 |

重排序策略：

```text
简单问题
  -> Vector Top3 / FAQ Top1
  -> 不启用重排序

中等问题
  -> Vector Top10 + BM25 Top10 + FAQ Top5
  -> 轻量 cross-encoder 或特征打分
  -> Top3 进入生成

复杂问题
  -> Vector Top30 + BM25 Top30 + Manual Top10
  -> LambdaMART / Learning-to-Rank 特征统一打分
  -> Top3-5 进入生成
```

设计考虑：

- 所有问题都重排会拖慢响应，客服场景更需要稳定延迟，所以按意图、问题长度、实体数量、风险等级和首轮召回分数做策略路由。
- V0.2 先实现可解释的轻量重排序：BM25 分、向量相似度、FAQ 命中、文档新鲜度、权限匹配、source priority、chunk/parent 匹配度。
- LambdaMART 适合 V0.3 做成训练化重排：先用坐席采纳、用户追问、人工改写、答案是否解决作为弱标签积累训练数据，再训练轻量排序模型。
- 如果 V0.2 没有足够标注数据，直接上 LambdaMART 只是形式完整，实际效果未必稳定。

#### 5.4 幻觉控制与评估指标

V0.2 不只做“能回答”，还要做“回答是否有证据、是否可靠、是否能被运营改进”。

核心指标：

| 指标 | 含义 | 用途 |
| --- | --- | --- |
| Context Recall | 标准答案所需证据是否被召回 | 判断检索链路是否漏召回 |
| Faithfulness | 回答是否被上下文支持 | 判断是否存在幻觉 |
| Answer Relevance | 回答是否真正回应用户问题 | 判断生成是否跑题 |
| Citation Coverage | 关键结论是否带引用 | 判断答案是否可追溯 |
| First Contact Resolution | 首轮是否解决问题 | 衡量客服业务效果 |
| Handoff Rate | 转人工比例 | 衡量自动化边界 |
| Rewrite Accept Rate | 改写通过语义校验比例 | 监控 query rewrite 是否制造噪音 |
| Retrieval Latency | 检索耗时 | 控制坐席台响应体验 |
| Rerank Latency | 重排序耗时 | 判断策略路由是否合理 |

设计考虑：

- Context Recall 低说明问题通常在检索和切分，不应该先调 prompt。
- Faithfulness 低说明生成器越过证据说话，需要收紧提示词、引用校验或触发转人工。
- 首轮解决率比单次回答相似度更贴近客服业务，因为客服系统最终看的是问题是否被解决。
- 评估数据来自三部分：人工标注集、历史 FAQ、坐席采纳/修改/转人工行为。
- 线上链路需要记录 trace：query、rewrite、retrieved chunks、rerank score、final context、answer、citations、latency、fallback reason。

## API 初版

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/tickets` | 创建工单 |
| `GET` | `/api/tickets` | 查询工单队列 |
| `GET` | `/api/tickets/{id}` | 查询工单详情 |
| `POST` | `/api/tickets/{id}/claim` | 领取工单，包含并发控制 |
| `POST` | `/api/tickets/{id}/transitions` | 状态流转 |
| `GET` | `/api/tickets/{id}/events` | 查询操作日志 |
| `GET` | `/api/tickets/{id}/ai-assists` | 查询 AI Assist |
| `POST` | `/api/ai-assists` | AI 结果回写 |

## 前端设计方向

前端是客服工作台，不是 AI landing page。

设计原则：

- 首屏直接进入三栏工作区：队列、工单详情、AI Assist。
- 信息密度偏企业工具，不做大标题、大渐变、大卡片堆叠。
- 状态、SLA、风险、转人工理由要可扫读。
- AI 建议必须显示置信度、依据、风险和可操作按钮。
- 空状态、加载中、AI 失败、权限不足、工单已被领取等边界都要有 UI。

## 测试策略

Java：

- 状态流转规则单元测试。
- 并发抢单集成测试：多个线程抢同一工单，只允许一个成功。
- AI Assist 幂等写入测试。
- Controller 边界测试：不存在、状态冲突、非法流转。

Python：

- 意图识别测试。
- 成本路由测试。
- 高风险转人工测试。
- RAG 无证据时禁止生成确定答案。

前端：

- 队列、详情、AI Assist 状态展示。
- 工单已被别人领取时的冲突提示。
- AI Assist pending / completed / failed 三种状态。

## 本地运行

当前仓库提供代码骨架、测试命令和 Docker Compose 部署文件。V0.1.0 可以本地三端分别启动，也可以用 Compose 拉起 MySQL、Redis、RabbitMQ、后端、AI 服务和前端。

```bash
# Java tests, after Maven is available
cd backend
mvn test

# Python AI Service tests
cd ai-service
python -m pytest

# Frontend, after npm install
cd frontend
npm install
npm run build
```

三端本地启动：

```bash
cd backend
mvn spring-boot:run

cd ai-service
python -m uvicorn app.main:app --reload

cd frontend
npm run dev
```

Docker Compose：

```bash
cp .env.example .env
docker compose up --build
```

默认端口：

| 服务 | 地址 |
| --- | --- |
| Frontend | <http://localhost:5173> |
| Backend OpenAPI | <http://localhost:8080/docs> |
| AI Service health | <http://localhost:8000/health> |
| RabbitMQ Management | <http://localhost:15672> |

## 当前实现状态

- [x] 中文项目架构文档。
- [x] Spring Boot 工单领域模型、状态机、并发抢单设计。
- [x] Flyway MySQL 表结构。
- [x] Java 测试用例。
- [x] Python AI Service 规则引擎和测试。
- [x] React 三栏坐席台原型。
- [x] V0.1.0 工程化文件：Makefile、Dockerfile、docker-compose、CI、LICENSE、`.env.example`。
- [ ] V0.2 接入真实 RabbitMQ broker：事件发布、消费、重试、死信队列、幂等消费。
- [ ] V0.2 接入真实 Redis 缓存：热工单、队列计数、AI 事件幂等、可选抢单削峰锁。
- [ ] V0.3 Kafka 事件流扩展：面向统计、审计、质检和多消费者订阅。
- [ ] V0.2 企业知识库 ingestion：多源文档解析、ETL 清洗、NLP 动态切分、父子索引。
- [ ] V0.2 Query Rewrite：小模型改写、Embedding 相似度校验、低相似改写丢弃。
- [ ] V0.2 Hybrid Retrieval：向量召回、BM25、FAQ/手册多源召回、分级重排序。
- [ ] V0.2 RAG 评估：Context Recall、Faithfulness、首轮解决率、幻觉率和链路 trace。
- [ ] V0.3 图谱增强检索与 LambdaMART 训练化重排序。
