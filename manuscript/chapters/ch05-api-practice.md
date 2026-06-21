# 第 5 章 大模型 API 调用实践

## 本章导读

第 2 章解释了大模型为什么按 Token 逐步生成文本，也说明了首 Token 延迟、流式输出、上下文窗口和采样参数会影响移动端体验。本章把这些机制落到 API 调用层：移动端应用不应直接调用模型提供方，而应调用自有服务端；服务端负责保存密钥、构造 Prompt、控制上下文、调用模型、返回结构化事件，并把错误转换为移动端可以处理的状态。

本章图示如下。

- 图 5-1 大模型应用调用链路，对应 `../assets/diagrams/llm-call-flow.svg`。
- 图 5-2 同步调用与流式调用时序，对应 `../assets/diagrams/streaming-api.svg`。

配套代码：`examples/mobile-knowledge-assistant/`

## 学习目标

- 理解移动端接入大模型时为什么要经过自有服务端。
- 掌握消息列表、系统指令、用户输入和上下文资料的组织方式。
- 实现普通 JSON 响应和服务器发送事件（Server-Sent Events，SSE）流式响应。
- 使用 `request_id` 管理一次生成任务，并支持用户取消生成。
- 将模型错误、超时、限流和格式异常转换为稳定的业务错误。
- 能够运行并测试配套 Python 工程，而不是只停留在伪代码层面。

## 5.1 移动端不应直接调用模型提供方

很多入门示例会在客户端直接调用模型 API，这种写法适合课堂演示，却不适合 App 上线。移动端安装包会被反编译，网络请求也可能被抓包。如果把模型 API 密钥（API Key）写入 iOS、Android、Flutter 或 React Native 客户端，就等于把调用额度交给任何拿到安装包的人。

面向生产环境的调用链路应采用如下结构：

```text
移动端 App -> 自有服务端 API -> 模型提供方（Provider）/ 模型网关
```

自有服务端至少承担 6 类职责。

| 职责 | 服务端要做什么 | 移动端只需要做什么 |
| --- | --- | --- |
| 密钥保护 | 读取环境变量或密钥管理系统中的 API 密钥 | 永远不保存模型密钥 |
| Prompt 管理 | 维护系统指令、模板版本和安全边界 | 发送用户输入和必要业务上下文 |
| 权限控制 | 在检索资料和调用工具前检查用户权限 | 携带登录态或业务身份 |
| 成本控制 | 控制上下文长度、模型路由、限流和超时 | 显示加载、失败和重试入口 |
| 结果校验 | 校验 JSON、引用来源和工具调用结果 | 按协议渲染答案和状态 |
| 审计监控 | 记录请求 ID、耗时、错误码和成本 | 上报客户端页面状态和取消行为 |

配套工程中的 `load_settings()` 体现了这一点。模型密钥只从服务端环境变量读取，移动端不会接触真实 API 密钥：

```python
def load_settings() -> Settings:
    """Load runtime settings from environment variables.

    The model API key is intentionally read only on the server side. A mobile
    app should call this service, not the model vendor directly, because keys
    embedded in an app package can be extracted.
    """

    docs_dir = Path(os.getenv("DOCS_DIR", PROJECT_ROOT / "data" / "documents"))
    return Settings(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        provider=os.getenv("LLM_PROVIDER", "mock"),
        api_url=os.getenv("LLM_API_URL", "https://api.example.com/v1/chat/completions"),
        api_key=os.getenv("LLM_API_KEY", ""),
        model=os.getenv("LLM_MODEL", "example-chat-model"),
        docs_dir=docs_dir,
    )
```

这段代码不是为了演示环境变量语法，而是给出一个清晰边界：移动端只调用自己的服务端；模型提供方地址、模型名称和 API 密钥都属于服务端配置。

## 5.2 消息列表不是“聊天记录”

大多数聊天模型接口使用消息列表表示输入。常见角色包括：

- `system`：系统指令，用来定义模型角色、约束、禁止事项和输出要求。
- `user`：用户输入，通常来自输入框、语音识别结果或业务页面。
- `assistant`：模型历史回复，需要由应用显式带回模型。
- `tool`：工具执行结果，例如检索结果、数据库查询结果或外部 API 结果。

需要特别强调：模型并不会自动记住某个用户的历史对话。每次请求时，服务端都要重新组织必要上下文。如果把完整历史无限追加，很快会超过上下文窗口，也会增加延迟和成本。因此服务端应根据任务决定保留哪些信息：最近几轮对话、会话摘要、当前页面状态、用户选中的对象、检索到的资料片段等。

在本书配套工程中，`build_rag_messages()` 把用户问题和检索资料合成消息列表：

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

这里有两个值得注意的设计。

第一，资料边界被显式标注为“来源 1”“来源 2”。这会帮助模型区分用户问题和参考资料，减少把资料内容误当成用户指令的风险。

第二，系统指令要求“只能根据参考资料回答”。这并不能彻底消除幻觉，但会让服务端更容易做后续校验：在生产系统中，如果没有检索到资料，服务端可以直接返回 `NO_CONTEXT`；如果模型仍然给出无引用判断，服务端也可以拦截。配套工程为了便于本地运行，暂时用文本说明“根据当前资料无法确定”，后续 RAG 章节会继续完善业务错误码。

## 5.3 普通 JSON 调用

同步调用适合短任务，例如标题生成、文本分类、权限说明摘要、短日志解释和表单字段抽取。移动端发送请求后等待完整 JSON 响应，再一次性刷新页面。

一个面向移动端的同步问答接口可以设计为：

```http
POST /api/ask
Content-Type: application/json
```

请求体示例：

```json
{
  "request_id": "req_20260621_001",
  "session_id": "s_mobile_001",
  "question": "移动端为什么不能直接保存模型 API 密钥？"
}
```

本章示例工程当前只读取 `question` 和 `request_id`。这里保留 `session_id` 是为了说明正式接口契约：会话持久化通常由服务端会话存储完成，不建议让移动端自行拼接完整历史。

响应体示例：

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

这段代码保留了完整链路：先检索资料，再构造 Prompt，最后调用模型提供方。读者可以直接运行测试验证该函数，而不是只阅读概念描述。注意，`KnowledgeAssistant.answer()` 属于业务服务层，只返回答案和引用；HTTP Handler 会在收到 `request_id` 时把它写回响应体。

同步调用的优点是实现简单，移动端页面状态也简单：`idle -> submitting -> done` 或 `idle -> submitting -> failed`。缺点是长回答会让用户在白屏或加载态中等待。如果任务可能生成数百字以上，或者需要让用户感知“正在工作”，就应该使用流式输出。

## 5.4 流式输出与 SSE

由于模型按 Token 逐步生成文本，服务端可以把部分结果持续发送给移动端。图 5-2 展示了同步调用和流式调用的差别：同步调用等待完整结果，流式调用则不断返回片段。图 5-1 则展示了移动端 App、自有服务端、Prompt 构造器、模型 API 和业务系统之间的调用链路。

在移动端场景中，SSE 是一种常见选择。它基于 HTTP，服务端可以持续发送文本事件，客户端按事件逐步更新 UI。与 WebSocket 相比，SSE 更适合单向“服务端到客户端”的生成场景；如果产品同时需要实时多人协作、双向消息或高频控制指令，再考虑 WebSocket。

| 方案 | 适合场景 | 注意事项 |
| --- | --- | --- |
| 普通 JSON | 短文本、分类、抽取、摘要 | 用户要等待完整结果 |
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

    # SSE clients on mobile often render each chunk immediately. Keep each
    # emitted event small and structured so the UI can update progressively.
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
data: {"type":"token","request_id":"req_20260621_001","content":"移动端安装包"}

event: token
data: {"type":"token","request_id":"req_20260621_001","content":"可能被反编译。"}

event: done
data: {"type":"done","request_id":"req_20260621_001","citations":[...]}
```

移动端收到 `token` 就追加到当前消息气泡，收到 `done` 才展示引用来源、复制、反馈等操作。不要等所有 Token 都到齐后再统一刷新，否则流式输出的交互价值会消失。

SSE 的 HTTP 实现要注意 `flush()`。如果服务端把片段写入缓冲区却不刷新，移动端仍然要等缓冲区满或连接结束后才能看到结果：

```python
def _write_sse(self, event: dict) -> None:
    data = json.dumps(event, ensure_ascii=False)
    event_type = str(event.get("type", "message"))
    self.wfile.write(f"event: {event_type}\ndata: {data}\n\n".encode("utf-8"))
    # Flush each chunk so a mobile UI can render progressively.
    self.wfile.flush()
```

## 5.5 `request_id` 与取消生成

移动端用户经常会在生成过程中执行以下操作：退出页面、切换 Tab、收起 App、重新提问、点击“停止生成”。如果服务端没有请求标识，就很难区分到底要停止哪一次生成。

因此，每次生成都应有 `request_id`。这个 ID 可以由移动端生成，也可以由服务端生成并通过第一个事件返回。本书示例工程支持在流式请求中传入 `request_id`：

```bash
curl -N --get http://127.0.0.1:8000/api/ask/stream \
  --data-urlencode 'question=如何处理移动端流式输出' \
  --data-urlencode 'request_id=req_stream_001'
```

这里使用 `--data-urlencode` 是为了避免中文 query 在不同终端中出现编码差异。还要注意，`GET /api/ask/stream?question=...` 是本地教学工程的简化写法。生产环境不建议把用户原文放入 URL，因为 URL 可能进入代理、网关和访问日志。更稳妥的设计是使用 `POST` 创建生成任务，再通过 `request_id` 拉取流式结果，或使用支持流式响应的 `POST` 接口。

取消接口如下：

```http
POST /api/ask/{request_id}/cancel
```

服务端用一个很小的内存注册表记录取消状态：

```python
class CancellationRegistry:
    """Tracks user-initiated cancellations by request ID.

    The registry is intentionally small and in-memory because the example server
    runs as a single process. A production service should store equivalent state
    in the request worker, gateway or task queue that owns the model call.
    """

    def __init__(self) -> None:
        self._active: set[str] = set()
        self._cancelled: set[str] = set()
        self._lock = threading.Lock()

    def register(self, request_id: str) -> bool:
        with self._lock:
            if request_id in self._active:
                return False
            self._active.add(request_id)
            self._cancelled.discard(request_id)
            return True

    def cancel(self, request_id: str) -> bool:
        with self._lock:
            if request_id not in self._active:
                return False
            self._cancelled.add(request_id)
            return True

    def unregister(self, request_id: str) -> None:
        with self._lock:
            self._active.discard(request_id)
            self._cancelled.discard(request_id)

    def is_cancelled(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._cancelled
```

真实代码还会限制 `request_id` 的长度和字符集，避免把任意路径片段或超长字符串写入取消表。示例工程在流式请求开始时调用 `register()`，结束时调用 `unregister()`；取消接口只对活跃请求返回 `202 Accepted`，对不存在或已结束的请求返回 `404 not_found`。

在真实系统中，取消可能分为两层。

第一层是“停止向客户端转发”。即使底层模型提供方不能真正中断生成，服务端也应停止继续写入 SSE，让移动端立即进入 `cancelled` 状态。这个语义是 best-effort：它保证客户端体验可控，但不一定意味着上游推理已经释放资源。

第二层是“停止底层任务”。如果模型网关、推理服务或任务队列支持取消，应继续把取消信号传下去，释放计算资源。

移动端不要把关闭页面等同于取消成功。关闭页面只说明当前连接断开；是否停止任务，需要看服务端是否收到取消请求或连接断开回调。对于成本敏感的业务，建议页面退出时主动调用取消接口。

## 5.6 错误处理与重试

大模型 API 的错误不能直接暴露给移动端。模型提供方返回的原始错误可能包含内部字段、英文消息、限流细节或不稳定状态码。服务端应转换为稳定的业务错误码，再由移动端映射成产品文案。

| 错误类型 | 服务端错误码 | 是否自动重试 | 移动端处理 |
| --- | --- | --- | --- |
| 网络抖动 | `NETWORK_ERROR` | 可以，使用退避 | 保持生成中或显示“正在重试” |
| 模型超时 | `MODEL_TIMEOUT` | 可以有限重试 | 提供“重新生成”入口 |
| 请求过多 | `RATE_LIMITED` | 不立即重试 | 提示稍后再试 |
| 无可用资料 | `NO_CONTEXT` | 不重试 | 告知资料不足 |
| 无权限 | `PERMISSION_DENIED` | 不重试 | 引导用户申请权限或切换账号 |
| 输出格式异常 | `OUTPUT_INVALID` | 可重新生成一次 | 多次失败后进入人工处理 |
| 服务端配置错误 | `SERVER_CONFIG_ERROR` | 不重试 | 记录日志并提示服务异常 |

流式输出中的错误也应通过事件返回：

```text
event: error
data: {"type":"error","request_id":"req_20260621_001","code":"MODEL_TIMEOUT","message":"分析超时，请稍后重试"}
```

配套工程实现了基础请求错误、SSE `error` 事件和模型调用有限重试。生产错误码表中的 `NO_CONTEXT`、`OUTPUT_INVALID`、`PERMISSION_DENIED` 等需要结合权限系统、结构化输出校验和检索链路继续扩展。

下面是模型提供方层的有限重试逻辑。它只对网络错误、`429` 和部分 `5xx` 状态重试，不对 `401`、`403`、`400` 等确定性错误重试：

```python
for attempt in range(MAX_PROVIDER_ATTEMPTS):
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as exc:
        if not _should_retry_http_status(exc.code, attempt):
            raise RuntimeError(f"LLM request failed with HTTP {exc.code}") from exc
        _sleep_before_retry(attempt)
    except urllib.error.URLError as exc:
        if attempt == MAX_PROVIDER_ATTEMPTS - 1:
            raise RuntimeError(f"LLM request failed: {exc}") from exc
        _sleep_before_retry(attempt)
```

移动端收到 `error` 后，应停止追加 Token，把状态切到 `failed`，并保留已生成内容或显示失败占位。是否保留部分输出取决于任务类型：闲聊和写作可以保留，财务、医疗、审批和权限相关任务不建议展示未完成结果。

重试策略要避免两个常见错误。

第一，不要无条件重试。认证失败、权限不足、参数错误、资料不足通常不会因为重试而恢复，重复请求只会浪费成本。

第二，不要让移动端绕过服务端直接重试模型提供方。重试次数、退避间隔和幂等控制应放在服务端，移动端只表达用户意图。例如用户点击“重新生成”时，客户端可以带上新的 `request_id` 和原始问题，由服务端决定是否复用检索结果、是否切换模型、是否降低输出长度。

## 5.7 上下文长度与会话管理

移动端聊天界面天然会让人以为历史消息可以无限保存。但对模型来说，每次请求都要把必要上下文重新放进上下文窗口。历史越长，首 Token 延迟越高，成本越高，越容易挤掉真正重要的资料。

服务端可以采用 4 种方式控制上下文。

| 方法 | 适合场景 | 风险 |
| --- | --- | --- |
| 保留最近 N 轮 | 普通聊天、低风险问答 | 早期关键约束可能丢失 |
| 会话摘要 | 长对话、客服助手 | 摘要错误会被继续放大 |
| RAG 检索 | 知识库问答、文档助手 | 检索召回不足会影响答案 |
| 结构化状态 | 订单、工单、配置页面 | 需要业务系统提供可靠字段 |

移动端应把“页面状态”和“历史文本”区分开。例如崩溃日志分析助手不需要把用户每次点击都写入聊天历史，但需要传递 `app_version`、`platform`、`os_version`、附件对象 ID 和当前问题。服务端再根据这些字段构造 Prompt 和检索条件。

对于多轮会话，推荐使用 `session_id` 管理会话，用 `request_id` 管理单次生成。两者职责不同：

- `session_id` 表示一段对话或一个页面任务。
- `request_id` 表示一次模型生成。
- 一个 `session_id` 下可以有多次 `request_id`。
- 取消生成时，应取消具体 `request_id`，而不是取消整个 `session_id`。

## 5.8 OpenAI-compatible 模型提供方示例

本书配套工程默认使用 `mock` 模型提供方，读者不用申请模型 API 密钥也能运行完整服务和测试。切换到真实模型时，可以使用 OpenAI-compatible 接口。下面是配套工程中的最小实现：

```python
class OpenAICompatibleProvider:
    """Minimal OpenAI-compatible chat-completions client.

    The code uses urllib from the standard library to keep the example
    dependency-free. Production code can replace this class with the official
    SDK used by the team.
    """

    def __init__(self, settings: Settings):
        if not settings.api_key:
            raise ValueError("LLM_API_KEY is required when LLM_PROVIDER=openai_compatible")
        self.settings = settings

    def generate(self, messages: list[dict[str, str]], contexts: list[SearchResult], question: str) -> str:
        del contexts, question
        body = json.dumps(
            {
                "model": self.settings.model,
                "messages": messages,
                "temperature": 0.2,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.settings.api_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        for attempt in range(MAX_PROVIDER_ATTEMPTS):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    return payload["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as exc:
                should_retry = _should_retry_http_status(exc.code, attempt)
                exc.close()
                if not should_retry:
                    raise RuntimeError(f"LLM request failed with HTTP {exc.code}") from exc
                _sleep_before_retry(attempt)
            except urllib.error.URLError as exc:
                if attempt == MAX_PROVIDER_ATTEMPTS - 1:
                    raise RuntimeError(f"LLM request failed: {exc}") from exc
                _sleep_before_retry(attempt)

        raise RuntimeError("LLM request failed after retries")
```

这段实现有意保持简单：只使用 Python 标准库，避免读者还没理解 API 边界就陷入 SDK 安装和版本差异。生产代码可以替换为团队采用的官方 SDK 或内部模型网关客户端，但边界不应改变：模型提供方层负责模型网关差异，业务服务层只依赖 `generate()` 和 `stream_generate()`。

需要特别说明：当前 `OpenAICompatibleProvider.stream_generate()` 是同步请求后的单块 fallback，用来保证服务端 SSE 协议仍然可运行；它不等于真正的上游逐 Token 流式解析。生产环境要获得真实流式效果，需要在模型提供方层启用模型网关的流式模式，并解析上游增量事件。

还要注意，`temperature`、`top_p`、`max_tokens` 等参数不是越多越好。移动端知识问答、故障分析和权限说明通常更需要稳定性，温度可以设置得较低；创意写作、营销文案和头脑风暴可以适当提高温度。第 2 章的采样实验已经说明了温度如何影响输出分布。

## 5.9 移动端消费流式接口

移动端页面可以按以下状态机处理一次生成任务：

```text
idle -> submitting -> waiting_first_token -> streaming -> done
                         |                 |
                         v                 v
                      failed           cancelled
```

每个状态对应清晰的 UI 行为。

| 状态 | 客户端行为 |
| --- | --- |
| `idle` | 输入框可编辑，发送按钮可用 |
| `submitting` | 禁止重复提交，创建本地消息占位 |
| `waiting_first_token` | 显示“正在分析”或骨架屏 |
| `streaming` | 逐步追加 `token` 内容，停止按钮可用 |
| `done` | 展示引用、复制、反馈、重新生成 |
| `cancelled` | 停止追加，保留已生成片段或显示已停止 |
| `failed` | 展示错误文案和重试入口 |

移动端实现时还应处理 5 个边界情况。

第一，页面退出。页面销毁时应关闭 SSE 连接，并视业务需要调用取消接口。

第二，App 进入后台。短任务可以继续等待，长任务建议转为后台任务或提示用户稍后查看。

第三，弱网重连。断线后不要直接把同一段内容重复追加。客户端应根据 `request_id` 判断当前事件是否仍属于正在展示的任务。

第四，多次快速提问。新问题发出后，旧请求应取消或标记为过期，旧事件到达时不能写入新消息气泡。

第五，引用来源展示。`done` 事件到达前不要过早展示引用，因为引用通常依赖完整检索结果和最终回答。

配套工程提供了一个可运行的客户端模拟器 `scripts/sse_client.py`。它运行在命令行中，但刻意按移动端状态机组织：先进入 `submitting`，连接建立后进入 `waiting_first_token`，收到 `token` 后进入 `streaming`，收到 `done`、`cancelled` 或 `error` 后进入终态。核心处理逻辑如下：

```python
for event in parse_sse_events(response):
    event_type = event.get("type")
    if event_type == "token":
        state = ClientState.STREAMING
        print(event.get("content", ""), end="", flush=True)
    elif event_type == "done":
        print(f"citations: {len(event.get('citations', []))}")
        return ClientState.DONE
    elif event_type == "cancelled":
        return ClientState.CANCELLED
    elif event_type == "error":
        print(f"error: {event.get('code')} {event.get('message')}")
        return ClientState.FAILED
```

真实移动端项目可以把这段逻辑迁移为 Swift、Kotlin、Dart 或 TypeScript 中的状态更新函数。关键不是语言，而是保持一个原则：网络层只解析事件，状态层负责决定 UI 如何变化，避免在网络回调里直接散落页面更新代码。

## 5.10 运行与验证

进入示例工程目录：

```bash
cd examples/mobile-knowledge-assistant
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

取消请求需要在流式请求尚未结束时另开终端执行。如果 `req_stream_001` 已经完成或从未注册，服务端会返回 `404 not_found`，这是为了避免客户端误以为一个不存在的任务被成功取消。

运行客户端模拟器：

```bash
python3 scripts/sse_client.py \
  --question '如何处理移动端流式输出' \
  --request-id req_client_001
```

运行测试：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

这些命令覆盖了启动、同步问答、流式事件、取消接口和自动化测试。对于一本面向工程实践的入门书，示例代码必须达到这个标准：读者可以复制命令运行，可以看到稳定输出，也可以通过测试确认自己改动没有破坏主流程。

## 本章小结

大模型 API 调用不是把用户输入转发给模型那么简单。面向移动端的工程实现需要把模型调用封装在自有服务端中，并围绕 `request_id`、`session_id`、流式事件、取消接口、错误码、上下文控制和密钥保护建立稳定协议。普通 JSON 调用适合短任务；SSE 适合长回答和逐步渲染；取消和错误事件决定了移动端体验是否可控。完成本章后，读者应能看懂并运行配套 Python 工程，为后续结构化输出、RAG 和 Agent 章节打好基础。

## 实践练习

1. 为 `OpenAICompatibleProvider` 的有限重试加入随机抖动（jitter），避免大量客户端同时重试。
2. 为 `POST /api/ask` 增加输入长度限制，超过限制时返回稳定错误码 `INPUT_TOO_LONG`。
3. 在移动端页面设计中区分 `waiting_first_token` 和 `streaming`，分别给出加载文案。
4. 为 SSE 事件增加服务端耗时字段，例如 `elapsed_ms`，并在测试中验证字段存在。
5. 将 `CancellationRegistry` 替换为团队内部任务队列或缓存服务中的取消状态。
