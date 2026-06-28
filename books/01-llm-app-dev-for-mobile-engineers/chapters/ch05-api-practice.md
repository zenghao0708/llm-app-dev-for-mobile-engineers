# 第 5 章 大模型 API 调用实践

## 本章导读

第 2 章解释了 Token、上下文窗口、首 Token 延迟和流式输出。本章把这些机制落到 API 层：移动端应用不直接调用模型提供方，而是调用自有服务端；服务端负责密钥、Prompt、上下文、模型调用、流式事件、取消和错误转换。

本章图示如下。

- 图 5-1 大模型应用调用链路，对应 `../assets/diagrams/llm-call-flow.svg`。
- 图 5-2 同步调用与流式调用时序，对应 `../assets/diagrams/streaming-api.svg`。

配套代码：`examples/01-mobile-knowledge-assistant/`

## 学习目标

- 理解移动端为什么必须经过自有服务端调用模型。
- 掌握消息列表、系统指令、用户输入和上下文资料的组织方式。
- 实现普通 JSON 响应和 SSE 流式响应。
- 使用 `request_id` 管理单次生成，并支持用户取消。
- 把模型错误、超时、限流和格式异常转换为稳定业务错误。
- 运行并测试配套 Python 工程。

## 5.1 服务端边界

很多入门示例会把模型 API Key 写进客户端。这只能用于课堂演示，不能用于上线 App。移动端安装包可能被反编译，网络请求也可能被抓包；模型密钥一旦进入 iOS、Android、Flutter 或 React Native 客户端，就等于把调用额度交给任何拿到安装包的人。

生产链路应保持为：

```text
移动端 App -> 自有服务端 API -> 模型提供方 / 模型网关
```

服务端至少承担以下职责。

| 职责 | 服务端做什么 | 移动端做什么 |
| --- | --- | --- |
| 密钥保护 | 从环境变量或密钥系统读取 API Key | 永远不保存模型密钥 |
| Prompt 管理 | 维护系统指令、模板版本和安全边界 | 发送用户输入和必要业务上下文 |
| 权限控制 | 在检索和工具调用前校验权限 | 携带登录态或业务身份 |
| 成本控制 | 控制上下文、模型路由、限流和超时 | 展示加载、失败和重试入口 |
| 结果校验 | 校验 JSON、引用来源和工具结果 | 按协议渲染答案 |
| 监控审计 | 记录请求 ID、耗时、错误码和成本 | 上报页面状态和取消行为 |

配套工程的 `load_settings()` 只在服务端读取 `LLM_API_KEY`。移动端只调用自己的 API，不接触模型提供方地址、模型名称和真实密钥。

## 5.2 消息列表与上下文

聊天模型接口通常使用消息列表表示输入。常见角色包括：

- `system`：定义模型角色、约束、禁止事项和输出要求。
- `user`：用户输入，来自输入框、语音识别结果或业务页面。
- `assistant`：历史回复，需要应用显式带回模型。
- `tool`：工具执行结果，例如检索片段、数据库查询或外部 API 结果。

模型不会自动记住用户历史。每次请求时，服务端都要重新组织必要上下文。如果把完整历史无限追加，会迅速拉高延迟和成本，也可能挤掉真正重要的资料。

本书示例工程用 `build_rag_messages()` 把用户问题和检索资料合成输入：

```python
def build_rag_messages(question: str, contexts: list[SearchResult]) -> list[dict[str, str]]:
    """Build a RAG prompt with explicit source boundaries."""

    context_text = "\n\n".join(
        f"[来源 {index}] {item.chunk.title} / {item.chunk.section}\n{item.chunk.text}"
        for index, item in enumerate(contexts, start=1)
    )
    return [
        {
            "role": "system",
            "content": (
                "你是移动端知识助手。只能根据参考资料回答；"
                "如果资料不足，请明确说明无法确定。"
            ),
        },
        {
            "role": "user",
            "content": f"问题：{question}\n\n参考资料：\n{context_text}",
        },
    ]
```

这里有两个关键点。第一，资料被显式标注为“来源”，帮助模型区分用户问题和参考资料。第二，系统指令要求只根据参考资料回答，便于服务端在后续做引用和资料不足校验。

## 5.3 普通 JSON 调用

同步调用适合短任务，例如标题生成、文本分类、短摘要、表单字段抽取和权限说明。移动端发送请求后等待完整 JSON 响应，再一次性刷新页面。

请求示例：

```http
POST /api/ask
Content-Type: application/json
```

```json
{
  "request_id": "req_20260621_001",
  "session_id": "s_mobile_001",
  "question": "移动端为什么不能直接保存模型 API 密钥？"
}
```

响应示例：

```json
{
  "request_id": "req_20260621_001",
  "answer": "移动端安装包可能被反编译，API 密钥应只保存在服务端。",
  "citations": [
    {
      "source": "mobile_ai_api.md",
      "title": "移动端 AI API 接入规范",
      "section": "密钥管理",
      "score": 0.4217
    }
  ]
}
```

服务端主流程在 `KnowledgeAssistant.answer()` 中完成：

```python
def answer(self, question: str, top_k: int = 3) -> dict:
    contexts = self.retriever.search(question, top_k=top_k)
    messages = build_rag_messages(question, contexts)
    answer = self.provider.generate(messages, contexts, question)
    return {
        "answer": answer,
        "citations": [_citation(item) for item in contexts],
    }
```

这段代码保留了完整链路：先检索资料，再构造 Prompt，最后调用模型提供方。同步调用的优点是实现简单；缺点是长回答会让用户长时间停留在加载态。只要任务可能生成较长内容，或需要让用户看到“正在工作”，就应使用流式输出。

## 5.4 SSE 流式输出

模型按 Token 逐步生成文本，服务端可以把部分结果持续发送给移动端。SSE 基于 HTTP，适合单向“服务端到客户端”的生成场景；如果产品需要双向实时协作或高频控制指令，再考虑 WebSocket。

| 方案 | 适合场景 | 注意事项 |
| --- | --- | --- |
| 普通 JSON | 短文本、分类、抽取、摘要 | 用户等待完整结果 |
| SSE | 聊天、长文生成、代码建议、日志分析 | 要处理页面退出、断线和取消 |
| WebSocket | 双向实时交互、多路任务控制 | 协议和连接管理更复杂 |

配套工程的流式服务方法如下：

```python
def stream_answer(
    self,
    question: str,
    top_k: int = 3,
    request_id: str = "",
    is_cancelled: Callable[[], bool] | None = None,
) -> Iterable[dict]:
    contexts = self.retriever.search(question, top_k=top_k)
    messages = build_rag_messages(question, contexts)

    for chunk in self.provider.stream_generate(messages, contexts, question):
        if is_cancelled and is_cancelled():
            yield _event("cancelled", request_id)
            return
        yield _event("token", request_id, content=chunk)
    yield _event("done", request_id, citations=[_citation(item) for item in contexts])
```

事件协议保持简单：

```text
event: token
data: {"type":"token","request_id":"req_001","content":"移动端安装包"}

event: done
data: {"type":"done","request_id":"req_001","citations":[...]}
```

移动端收到 `token` 就追加到当前消息气泡，收到 `done` 后再展示引用来源、复制、反馈等操作。服务端写 SSE 时必须及时 `flush()`，否则客户端仍可能等连接结束后才看到内容。

## 5.5 `request_id` 与取消

移动端用户可能在生成过程中退出页面、切换 Tab、收起 App、重新提问或点击“停止生成”。没有请求标识，服务端很难判断要停止哪一次生成。

推荐使用两个 ID：

- `session_id`：一段对话或一个页面任务。
- `request_id`：一次模型生成。

一个 `session_id` 下可以有多次 `request_id`。取消生成时，应取消具体 `request_id`，而不是取消整个会话。

流式请求示例：

```bash
curl -N --get http://127.0.0.1:8000/api/ask/stream \
  --data-urlencode 'question=如何处理移动端流式输出' \
  --data-urlencode 'request_id=req_stream_001'
```

取消接口示例：

```http
POST /api/ask/{request_id}/cancel
```

示例工程用 `CancellationRegistry` 记录活跃请求。取消只对活跃请求返回 `202 Accepted`；不存在或已结束的请求返回 `404 not_found`，避免客户端误以为无效任务已被成功取消。

真实系统中的取消通常分两层：先停止向客户端转发，让页面立即进入 `cancelled`；如果模型网关、推理服务或任务队列支持取消，再继续把取消信号传下去释放计算资源。关闭页面不等于取消成功，成本敏感业务应在页面退出时主动调用取消接口。

## 5.6 错误处理与重试

模型提供方的原始错误不应直接透传给移动端。服务端应转换为稳定错误码，再由客户端映射成产品文案。

| 错误类型 | 服务端错误码 | 是否自动重试 | 移动端处理 |
| --- | --- | --- | --- |
| 网络抖动 | `NETWORK_ERROR` | 可退避重试 | 保持生成中或显示正在重试 |
| 模型超时 | `MODEL_TIMEOUT` | 可有限重试 | 提供重新生成入口 |
| 请求过多 | `RATE_LIMITED` | 不立即重试 | 提示稍后再试 |
| 无可用资料 | `NO_CONTEXT` | 不重试 | 告知资料不足 |
| 无权限 | `PERMISSION_DENIED` | 不重试 | 引导申请权限或切换账号 |
| 输出格式异常 | `OUTPUT_INVALID` | 可重试一次 | 多次失败后人工处理 |
| 配置错误 | `SERVER_CONFIG_ERROR` | 不重试 | 记录日志并提示服务异常 |

流式输出中的错误也用事件返回：

```text
event: error
data: {"type":"error","request_id":"req_001","code":"MODEL_TIMEOUT","message":"分析超时，请稍后重试"}
```

重试要避免两个错误。第一，不要无条件重试：认证失败、权限不足、参数错误和资料不足通常不会因重试恢复。第二，不要让移动端绕过服务端直接重试模型提供方；重试次数、退避间隔、幂等控制和模型切换都应由服务端处理。

## 5.7 上下文长度与会话管理

移动端聊天界面容易让人以为历史消息可以无限保存。实际上每次请求都要把必要上下文重新放进窗口。历史越长，首 Token 延迟越高，成本越高，也越容易挤掉当前任务真正需要的资料。

服务端可以用 4 种方式控制上下文：

| 方法 | 适合场景 | 风险 |
| --- | --- | --- |
| 保留最近 N 轮 | 普通聊天、低风险问答 | 早期关键约束可能丢失 |
| 会话摘要 | 长对话、客服助手 | 摘要错误会被继续放大 |
| RAG 检索 | 知识库问答、文档助手 | 检索召回不足会影响答案 |
| 结构化状态 | 订单、工单、配置页面 | 依赖业务系统提供可靠字段 |

移动端应把“页面状态”和“历史文本”区分开。例如崩溃日志分析助手不需要记录用户每次点击，但需要传递 `app_version`、`platform`、`os_version`、附件对象 ID 和当前问题。服务端再根据这些字段构造 Prompt 和检索条件。

## 5.8 OpenAI-compatible Provider

配套工程默认使用 `mock` Provider，读者不用申请模型 API Key 也能运行服务和测试。切换真实模型时，可以使用 OpenAI-compatible 接口。实现放在 `OpenAICompatibleProvider` 中，使用 Python 标准库 `urllib` 发起请求，并对网络错误、`429` 和部分 `5xx` 状态做有限重试。

生产代码可以替换为团队采用的官方 SDK 或内部模型网关客户端，但边界不应改变：Provider 层负责模型网关差异，业务服务层只依赖 `generate()` 和 `stream_generate()`。

需要特别说明：当前示例中的 `stream_generate()` 是同步请求后的单块 fallback，用来保证服务端 SSE 协议可运行；它不等于真正的上游逐 Token 流式解析。生产环境要获得真实流式效果，需要在 Provider 层启用模型网关的流式模式，并解析上游增量事件。

采样参数也应按任务设置。移动端知识问答、故障分析和权限说明通常更需要稳定性，温度可以较低；创意写作、营销文案和头脑风暴可以适当提高温度。

## 5.9 移动端状态机

移动端页面可以按以下状态机处理一次生成任务：

```text
idle -> submitting -> waiting_first_token -> streaming -> done
                         |                 |
                         v                 v
                      failed           cancelled
```

| 状态 | 客户端行为 |
| --- | --- |
| `idle` | 输入框可编辑，发送按钮可用 |
| `submitting` | 禁止重复提交，创建本地消息占位 |
| `waiting_first_token` | 显示“正在分析”或骨架屏 |
| `streaming` | 逐步追加 `token` 内容，停止按钮可用 |
| `done` | 展示引用、复制、反馈、重新生成 |
| `cancelled` | 停止追加，保留已生成片段或显示已停止 |
| `failed` | 展示错误文案和重试入口 |

还要处理页面退出、App 进入后台、弱网重连、多次快速提问和引用来源展示。旧请求的事件不能写入新消息气泡；`done` 到达前不要过早展示引用。

配套工程提供了命令行客户端模拟器 `scripts/sse_client.py`。它按移动端状态机解析 `token`、`done`、`cancelled` 和 `error` 事件。真实 iOS、Android、Flutter 或 React Native 项目可以把这段逻辑迁移为状态更新函数。关键原则是：网络层只解析事件，状态层决定 UI 如何变化。

## 5.10 运行与验证

进入示例工程目录：

```bash
cd examples/01-mobile-knowledge-assistant
```

启动服务：

```bash
PYTHONPATH=src python3 -m mobile_llm.app
```

普通 JSON 请求：

```bash
curl -s http://127.0.0.1:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"request_id":"req_json_001","question":"移动端为什么不能直接保存模型 API 密钥？"}' \
  | python3 -m json.tool
```

流式请求：

```bash
curl -N --get http://127.0.0.1:8000/api/ask/stream \
  --data-urlencode 'question=如何处理移动端流式输出' \
  --data-urlencode 'request_id=req_stream_001'
```

取消请求：

```bash
curl -s -X POST http://127.0.0.1:8000/api/ask/req_stream_001/cancel \
  | python3 -m json.tool
```

客户端模拟器：

```bash
python3 scripts/sse_client.py \
  --question '如何处理移动端流式输出' \
  --request-id req_client_001
```

运行测试：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

这些命令覆盖启动、同步问答、流式事件、取消接口和自动化测试。示例代码必须达到这个标准：读者可以复制命令运行，可以看到稳定输出，也可以通过测试确认改动没有破坏主流程。

## 本章小结

大模型 API 调用不是把用户输入转发给模型。面向移动端的工程实现需要把模型调用封装在自有服务端中，并围绕 `request_id`、`session_id`、流式事件、取消接口、错误码、上下文控制和密钥保护建立稳定协议。普通 JSON 调用适合短任务；SSE 适合长回答和逐步渲染；取消和错误事件决定移动端体验是否可控。

## 实践练习

1. 为 Provider 的有限重试加入随机抖动，避免大量客户端同时重试。
2. 为 `POST /api/ask` 增加输入长度限制，超过限制时返回 `INPUT_TOO_LONG`。
3. 在移动端页面中区分 `waiting_first_token` 和 `streaming`。
4. 为 SSE 事件增加服务端耗时字段 `elapsed_ms`，并在测试中验证字段存在。
5. 将 `CancellationRegistry` 替换为团队内部任务队列或缓存服务中的取消状态。
