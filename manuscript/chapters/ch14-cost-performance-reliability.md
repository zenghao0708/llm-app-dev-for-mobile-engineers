# 第 14 章 成本、性能与稳定性优化

## 本章导读

大模型应用能跑起来，只是第一步。真正上线后，团队很快会遇到三个更现实的问题：一次回答到底花多少钱，用户要等多久，模型服务异常时 App 会不会卡死或重复扣费。

对移动端开发工程师来说，这些问题不能只交给服务端同学处理。用户看到的是 App 页面：加载态是否及时出现，首个 Token 是否很快到达，离开页面后是否还能停止生成，弱网重试会不会重复追加旧文本，错误提示是否可恢复。服务端看起来是一次模型调用，落到移动端就是状态机、取消、缓存、埋点和兜底体验。

图 14-1 展示了成本、性能和稳定性的观测闭环。

![图 14-1 成本、性能与稳定性观测闭环](../assets/diagrams/ops-observability-loop.svg)

本章配套新增 `scripts/ops_report.py`、`data/observability/model_call_logs.json` 和 `data/observability/model_pricing.json`。脚本不会调用真实模型，而是读取模型网关日志样本和示例价格表，计算总成本、首 Token 延迟、P95 延迟、缓存命中率、错误率、重试率、降级率和告警。这样读者可以先掌握指标口径，再迁移到真实监控系统。

## 学习目标

- 理解大模型调用成本由输入 Token、输出 Token、模型单价、调用次数和附加链路组成。
- 区分首 Token 时间、完整回答耗时、P50、P95 和 SLO。
- 能够设计稳定且不泄露原文的缓存 Key。
- 能够区分可重试错误、不可重试错误和需要人工排查的异常。
- 能够运行 `ops_report.py`，读懂成本、性能和稳定性指标。
- 能把服务端指标映射到移动端加载、流式输出、取消和错误恢复体验。

## 核心内容

### 14.1 不要等账单出来才谈成本

大模型成本通常不只是一行“模型调用费”。一个 RAG 应用可能包含：

- 主模型输入 Token。
- 主模型输出 Token。
- Embedding 生成成本。
- 向量库查询和存储成本。
- 重排模型成本。
- 工具调用、文件解析和对象存储成本。
- 日志、评测、监控和告警成本。

早期原型阶段，团队容易只看单次调用是否成功；一旦接入真实用户，成本会随着调用次数、上下文长度和输出长度线性甚至放大增长。比如一个知识助手每次回答都塞入 8 段长文档，即使用户只问简单问题，也会为不必要的上下文付费。

降低成本不是简单地“换便宜模型”。更稳妥的顺序是：

1. 先减少无关上下文，避免把整篇文档都塞进 Prompt。
2. 再限制输出长度，让模型回答到业务需要的位置就停止。
3. 对稳定问题使用缓存，减少重复调用。
4. 用小模型处理分类、路由、标题生成等简单任务。
5. 把离线批处理和实时交互分开，避免在用户等待时做重任务。

对移动端 App 来说，还要特别注意“用户退出页面后仍然继续生成”的成本。取消按钮不只是体验控件，也是成本控制手段。如果 App 取消了请求，但服务端没有向上游模型网关传播取消，后台仍可能继续生成和计费。

### 14.2 Token 成本如何估算

`data/observability/model_pricing.json` 中保存了一份示例价格表：

```json
{
  "fast-chat": {
    "input_per_1k_usd": 0.0003,
    "output_per_1k_usd": 0.0009
  },
  "accurate-chat": {
    "input_per_1k_usd": 0.002,
    "output_per_1k_usd": 0.006
  }
}
```

这里的价格只是教学样例，不代表任何厂商的实时价格。真实项目必须以当前模型提供方的账单口径为准，并把价格配置放在独立文件或配置中心，而不是写死在代码里。

`ops_report.py` 的成本估算公式很直接：

```python
input_cost = record.prompt_tokens / 1000 * price.input_per_1k_usd
output_cost = record.completion_tokens / 1000 * price.output_per_1k_usd
```

输入 Token 和输出 Token 要分开看。RAG 应用常见的问题是输入成本过高：检索片段太长、重复片段太多、系统提示过于臃肿、历史会话没有裁剪。代码生成和长文总结则更容易输出成本高，因为模型会生成大量文本。

建议在模型网关层记录每次请求的字段：

| 字段 | 作用 |
| --- | --- |
| `request_id` | 串联移动端、服务端、模型网关和日志 |
| `route` | 区分普通问答、流式问答、批处理等入口 |
| `model` | 区分模型版本和路由策略 |
| `prompt_tokens` | 输入 Token 数 |
| `completion_tokens` | 输出 Token 数 |
| `first_token_ms` | 首段内容返回耗时 |
| `latency_ms` | 完整请求耗时 |
| `status_code` | 网关或上游返回状态 |
| `cache_hit` | 是否命中缓存 |
| `fallback_used` | 是否使用降级方案 |

没有这些字段，团队很难回答“成本上涨是因为用户变多、Prompt 变长、模型变贵，还是缓存失效”。

### 14.3 延迟要拆成用户能感知的阶段

大模型应用的延迟不是一个数字。一次 RAG 请求通常包含：

1. 移动端发起请求。
2. 服务端鉴权和参数校验。
3. 检索和重排。
4. Prompt 构造。
5. 模型排队和生成。
6. 流式片段返回。
7. 移动端渲染和状态更新。

对移动端用户来说，最重要的往往不是平均延迟，而是首 Token 时间和 P95 延迟。

| 指标 | 含义 | 适用判断 |
| --- | --- | --- |
| 首 Token 时间 | 从点击发送到第一段内容出现 | 用户是否觉得“有响应” |
| 完整回答耗时 | 从发送到 done 事件 | 长回答是否可接受 |
| P50 延迟 | 一半请求不超过该值 | 常规体验 |
| P95 延迟 | 95% 请求不超过该值 | 尾部体验和 SLO |
| SLO 违规率 | 超过目标阈值的请求比例 | 是否需要容量或降级 |

平均值很容易掩盖问题。比如平均延迟 2 秒，看起来不错，但如果 P95 是 10 秒，移动端仍会有大量用户看到长时间等待。书中脚本采用 nearest-rank 口径计算百分位，重点不是争论统计学细节，而是让团队用稳定口径持续比较。

运行报表：

```bash
cd examples/mobile-knowledge-assistant
python3 scripts/ops_report.py --latency-slo-ms 3000
```

典型输出节选：

```json
{
  "request_count": 8,
  "success_rate": 0.875,
  "error_rate": 0.125,
  "cache_hit_rate": 0.25,
  "retry_rate": 0.25,
  "fallback_rate": 0.125,
  "total_cost_usd": 0.012481,
  "latency_ms": {
    "avg": 2417.5,
    "p50": 1420,
    "p95": 5200,
    "slo_violation_rate": 0.375
  },
  "first_token_ms": {
    "p50": 680,
    "p95": 1450
  },
  "alerts": [
    "error_rate_above_5_percent",
    "latency_p95_above_slo",
    "fallback_used"
  ]
}
```

这份报告同时告诉我们三件事：成本可以估算，P95 已超过 3000ms 的目标，且出现了失败和降级。真实项目可以把这类 JSON 推送到监控系统，也可以在 CI 或发布前做静态样本检查。

### 14.4 缓存不是把问题字符串直接当 Key

缓存适合稳定问题、公开知识、低风险摘要和重复查询。不适合权限相关结果、实时状态、用户隐私内容和强时效答案。

一个常见错误是直接用用户问题作为缓存 Key。这样做有两个问题：

- Key 中可能包含隐私、手机号、订单号或内部信息。
- Prompt、知识库或模型版本变更后，旧缓存可能继续命中。

配套脚本提供了一个稳定缓存 Key 函数：

```python
def stable_cache_key(
    question: str,
    prompt_version: str,
    kb_version: str,
    tenant_id: str,
    permission_scope: str,
    locale: str = "zh-CN",
) -> str:
    payload = {
        "question": " ".join(question.split()),
        "prompt_version": prompt_version.strip(),
        "kb_version": kb_version.strip(),
        "tenant_id": tenant_id.strip(),
        "permission_scope": permission_scope.strip(),
        "locale": locale.strip(),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
```

这里有几个工程要点：

- 使用稳定哈希，而不是 Python 内置 `hash()`；内置 `hash()` 在不同进程中可能不同。
- 把 `prompt_version` 和 `kb_version` 放进 Key，避免 Prompt 或知识库更新后继续使用旧答案。
- 把 `tenant_id` 和 `permission_scope` 放进 Key，避免不同租户或不同权限范围复用同一份答案。
- 不把原始问题直接作为 Key 名称，减少日志和缓存系统暴露隐私的风险。
- 同一问题在不同语言、租户或权限范围下，应该使用不同 Key。

移动端侧也可以做轻量缓存，但不要缓存服务端没有授权的内容。推荐做法是：移动端缓存最近一次已授权响应、引用和状态；服务端缓存模型结果或检索结果，并由服务端控制过期和权限。

### 14.5 重试要克制，降级要明确

模型 API 调用失败时，不能一律重试。错误类型不同，处理方式也不同：

| 状态 | 建议动作 | 原因 |
| --- | --- | --- |
| 408、425、429、500、502、503、504 | 可重试 | 可能是临时超时、限流、上游故障或过早请求 |
| 400、401、403、404、422 | 快速失败 | 参数、认证、权限或资源不存在，重试无意义 |
| 其他未知状态 | 人工排查或降级 | 避免自动重试放大问题 |

配套脚本中的分类函数：

```python
def classify_status(status_code: int) -> str:
    if not 100 <= status_code <= 599:
        raise ValueError("status_code must be a valid HTTP status code")
    if 200 <= status_code < 300:
        return "success"
    if status_code in {408, 425, 429, 500, 502, 503, 504}:
        return "retry"
    if status_code in {400, 401, 403, 404, 422}:
        return "fail_fast"
    return "manual_review"
```

重试也不能无限做。常见做法是指数退避：

```python
def retry_schedule(max_retries: int, base_ms: int = 200, cap_ms: int = 3000) -> list[int]:
    return [min(cap_ms, base_ms * 2**attempt) for attempt in range(max_retries)]
```

生产项目还应增加 jitter，避免大量请求在同一时间再次打到模型网关。重试应发生在服务端或模型网关的受控层，移动端弱网重连不能直接重复创建生成任务。对于移动端长回答，重试还要考虑幂等性：如果前一次请求已经生成了部分 Token，新请求不能把旧 Token 重复追加到当前消息里。建议每次请求携带 `request_id`，页面状态只接受当前 request_id 的事件。

降级策略要提前设计，而不是异常发生时临时拼接：

- 命中缓存结果。
- 使用较小或更便宜的模型。
- 关闭重排或减少 Top-K。
- 返回“稍后重试”并保留用户输入。
- 创建工单或转人工处理。

移动端页面也要区分这些状态。限流可以提示“稍后再试”；权限错误应提示用户无权访问；模型暂时不可用可以提供重试按钮；用户取消则应保留已生成片段并显示“已停止”。

### 14.6 从日志生成可读报表

`data/observability/model_call_logs.json` 是一份最小模型调用日志样本。每条记录包含路由、模型、Token、延迟、状态码、缓存、重试和降级信息。`ops_report.py` 会把这些日志聚合为报告：

```bash
python3 scripts/ops_report.py --latency-slo-ms 3000
```

报告中的几个字段尤其重要：

| 字段 | 如何解读 |
| --- | --- |
| `success_rate` | 请求是否大体成功 |
| `error_rate` | 错误是否超过发布阈值 |
| `cache_hit_rate` | 缓存是否真正发挥作用 |
| `retry_rate` | 是否存在上游抖动或策略过度重试 |
| `fallback_rate` | 是否已经触发降级 |
| `total_cost_usd` | 当前样本的估算成本 |
| `latency_ms.p95` | 尾部延迟是否超过 SLO |
| `first_token_ms.p95` | 用户等待首段内容的尾部体验是否过慢 |
| `by_route` | 哪个接口贡献了最多成本或延迟 |
| `alerts` | 需要优先排查的问题 |

读者要注意，样本报表不是生产监控替代品。它的价值在于帮助团队统一口径：成本怎么算，P95 怎么看，什么算错误，什么算降级。等真实系统上线后，可以把同样字段接入 Prometheus、Grafana、Datadog、OpenTelemetry 或公司内部监控平台。

### 14.7 移动端如何配合服务端优化

移动端不直接持有模型 Key，也不直接面对模型提供方，但它对成本、性能和稳定性仍有明显影响。

首先是状态机。页面至少应区分：

- `idle`：没有请求。
- `submitting`：请求已发出，还没有首 Token。
- `streaming`：正在接收片段。
- `completed`：收到 done。
- `failed`：收到 error 或请求失败。
- `cancelled`：用户停止或页面退出。

其次是取消。用户点击停止、页面退出、App 进入后台、发起新问题时，都可能需要取消旧请求。取消要同时发生在三层：页面停止追加文本，服务端标记 request_id 取消，上游模型网关尽量停止生成。即使某些模型网关不能真正中断推理，服务端也要避免继续把旧片段推给移动端。

再次是埋点。移动端要把关键时间点带上同一个 `request_id`：

- 点击发送。
- 请求到达服务端。
- 首 Token 到达。
- 用户点击停止。
- 收到 done、error 或 cancelled。
- 页面退出、App 后台、网络切换。
- 引用展开、复制、反馈和重新生成。

这些埋点和服务端日志合在一起，才能定位问题究竟发生在 App 网络层、服务端检索、模型网关还是上游模型。

### 14.8 发布前的成本与稳定性检查

一次大模型功能发布前，建议至少完成下面的检查：

1. 跑完整单元测试和接口测试。
2. 跑 `rag_eval.py` 和 `answer_eval.py`，确认质量没有退化。
3. 跑 `ops_report.py` 或真实监控查询，确认成本、首 Token 延迟和 P95 延迟没有明显异常。
4. 检查 Prompt、Top-K、模型和知识库版本是否写入日志。
5. 检查缓存 Key 是否包含版本信息，是否避免暴露原始隐私。
6. 检查 429、5xx、超时、取消和降级路径。
7. 检查移动端弱网、后台、页面退出和重复发送。

这些检查不需要一开始全部做成阻断门禁。早期可以先生成报告，等指标稳定后再把关键项接入 CI 或发布系统。例如：单元测试和质量评测必须阻断；P95 延迟、错误率和成本先进入发布报告；当线上指标连续几周稳定后，再把严重回归设为发布门禁。

## 本章小结

大模型应用上线后，成本、性能和稳定性会直接决定产品能否持续运行。控制成本要从 Token、上下文、缓存和取消开始；优化性能要关注首 Token 和 P95，而不是只看平均值；提高稳定性要区分可重试错误、不可重试错误和降级路径。

对移动端开发工程师来说，本章最重要的结论是：大模型体验不是服务端一个接口的事。App 的状态机、取消逻辑、弱网恢复、埋点和错误展示，都会影响模型调用成本和用户体验。配套工程中的 `ops_report.py` 给出了一个最小可运行的观测样例，读者可以把它迁移到真实日志和监控系统中。

## 实践练习

1. 修改 `data/observability/model_call_logs.json`，把某条请求的 `latency_ms` 改大，再观察 `alerts` 如何变化。
2. 修改 `stable_cache_key()` 的 `tenant_id` 和 `permission_scope`，观察缓存 Key 如何变化，并说明为什么两者都不能省略。
3. 把 `retry_schedule(4)` 改成带 jitter 的版本，并解释为什么可以减轻上游压力。
4. 设计移动端消息状态对象，包含 `request_id`、`state`、`first_token_at`、`finished_at`、`error_code` 和 `cancelled_by_user`。
5. 为一个真实或模拟的模型接口设计降级策略：缓存、小模型、减少 Top-K、转人工分别在什么条件下触发。
