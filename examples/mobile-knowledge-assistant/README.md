# 移动端知识助手示例工程

本工程对应《大模型应用开发快速入门》的综合项目。它不是伪代码，而是一个可运行的最小工程闭环示例：移动端 App 调用自有服务端，自有服务端完成检索、提示词构造和模型调用。

默认使用 `mock` 模型提供方，因此不需要 API 密钥也能跑通。配置 OpenAI-compatible 接口后，可以切换到真实模型服务。

## 功能

- `POST /api/ask`：普通问答接口，返回答案和引用来源。
- `GET /api/ask/stream`：SSE 流式接口，适合移动端逐字渲染，事件类型包括 `token`、`done`、`error` 和 `cancelled`。
- `POST /api/ask/{request_id}/cancel`：取消正在进行的流式生成。示例默认 `mock` provider 可在分段间响应取消；真实模型是否能停止上游推理，取决于具体模型网关是否支持取消。
- `GET /health`：健康检查。
- 本地 Markdown 文档检索。
- 可测试的 mock LLM provider。
- 可运行的开发环境检查脚本，帮助确认 Python 版本、配置模板、文档目录和 mock 链路。
- 可运行的 temperature 采样实验，帮助理解模型输出稳定性。
- 可运行的提示词契约检查脚本，帮助检查任务、上下文、约束、输出格式、Few-shot 和敏感值边界。
- 可运行的日志和提示词上下文脱敏工具，帮助理解隐私保护边界。
- 可运行的 SSE 客户端模拟器，帮助理解移动端状态机和取消请求。
- 可运行的 RAG 链路追踪脚本，帮助检查检索片段、提示词和引用来源。
- 可运行的 RAG 检索评测脚本，帮助用黄金问题集检查 Top-K 召回和排序。
- 可运行的答案质量评测脚本，帮助检查答案要点覆盖、引用命中和风险表达。
- 可运行的结构化输出与工具调用路由器，帮助理解 Schema 校验、工具白名单、权限检查和移动端确认卡。
- 可运行的成本、性能与稳定性报表脚本，帮助检查 Token 成本、首 Token 延迟、P95 延迟、缓存命中、错误、重试和降级。
- 可运行的只读文件分析 Agent，帮助理解工具白名单、最大步数和执行轨迹。
- 可运行的周报工作流，帮助理解固定节点、校验、人工确认和发布门禁。
- 可运行的多模态截图工单 payload 生成器，帮助理解文件校验、图片输入和结构化输出。

## 运行

```bash
cd examples/mobile-knowledge-assistant
python3 -m venv .venv
source .venv/bin/activate
PYTHONPATH=src python3 -m mobile_llm.app
```

另开一个终端请求：

```bash
curl -s http://127.0.0.1:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"移动端为什么不能直接保存模型 API 密钥？"}' | python3 -m json.tool
```

流式接口：

```bash
curl -N --get http://127.0.0.1:8000/api/ask/stream \
  --data-urlencode 'question=如何处理移动端流式输出'
```

带请求 ID 的流式接口和取消接口：

```bash
curl -N --get http://127.0.0.1:8000/api/ask/stream \
  --data-urlencode 'question=如何处理移动端流式输出' \
  --data-urlencode 'request_id=req_stream_001'
curl -s -X POST http://127.0.0.1:8000/api/ask/req_stream_001/cancel | python3 -m json.tool
```

取消请求需要在流式请求尚未结束时另开终端执行；请求已结束时返回 `404 not_found` 是预期行为。

客户端模拟器：

```bash
python3 scripts/sse_client.py \
  --question '如何处理移动端流式输出' \
  --request-id req_client_001
```

## 测试

```bash
cd examples/mobile-knowledge-assistant
PYTHONPATH=src python3 -m unittest discover -s tests
```

## 开发环境检查

第 3 章使用下面的脚本检查本地开发环境是否准备好：

```bash
python3 scripts/dev_environment_check.py
```

脚本会检查 Python 版本、`requirements.txt`、`.env.example`、根目录 `.gitignore`、`data/documents/` 和 mock provider 本地链路。输出只包含 `api_key_set`，不会回显真实 API Key。

## 机制实验

第 2 章使用下面的脚本演示 temperature 如何改变候选 Token 的概率分布和采样结果：

```bash
python3 scripts/sampling_temperature_experiment.py --temperature 0.2 --rounds 50 --seed 7
python3 scripts/sampling_temperature_experiment.py --temperature 1.2 --rounds 50 --seed 7
```

低温度会让高概率候选更集中，高温度会让分布更平、更容易采到其他候选。这个脚本不调用真实模型服务，适合读者先理解概率采样机制。

## 提示词契约检查

第 4 章使用下面的脚本检查提示词是否具备工程化结构：系统角色、任务块、上下文边界、约束、输出格式、Few-shot 示例、敏感值边界和长度预算。

```bash
python3 scripts/prompt_contract_check.py
```

测试用例位于 `data/prompt/prompt_contract_cases.json`。默认样例覆盖移动端 API 接入说明、用户反馈分类和提示词注入上下文隔离。脚本不调用真实模型服务，任一案例失败时默认返回非零退出码；只想观察报告时可以追加 `--report-only`。

第 7 章使用下面的脚本演示 TF-IDF 向量检索、归一化和余弦相似度排序：

```bash
python3 scripts/tfidf_vector_search.py \
  --question '移动端为什么不能直接保存模型 API Key？' \
  --top-k 2
```

这个脚本会真实读取 `data/documents/` 下的 Markdown 文档并返回 Top-K 片段。它不是神经网络 Embedding 服务，但能帮助读者先看清向量化、相似度和引用来源的关系。

第 15 章使用下面的脚本演示日志和提示词上下文脱敏：

```bash
python3 scripts/privacy_redaction.py \
  --text 'user=a@example.com token=abc123 phone=13800138000 api_key=test-secret-value'
```

脚本只输出脱敏文本和命中类型计数，不会把原始敏感值写回报告。

## 结构化输出与工具调用

第 6 章使用下面的脚本演示模型结构化输出进入业务工具前的服务端边界：JSON Schema 校验、工具白名单、订单归属检查、高风险动作确认和审计字段。

```bash
python3 scripts/structured_tool_router.py \
  --message '帮我查一下订单 A1024 到哪里了' \
  --user-id user_001
```

示例订单数据位于 `data/tools/orders.json`。查询或取消他人订单会返回 `forbidden`；取消不可取消订单会返回 `not_cancellable`；只有通过权限和状态前置检查的高风险动作才会返回 `confirmation_required` 和移动端确认卡：

```bash
python3 scripts/structured_tool_router.py \
  --message '我要取消订单 P3001' \
  --user-id user_001
```

用户确认后再提交确认态请求：

```bash
python3 scripts/structured_tool_router.py \
  --message '我要取消订单 P3001' \
  --user-id user_001 \
  --confirm
```

脚本默认不写回订单文件。生产系统应把确认态、权限、审计日志和业务写入放在服务端完成，移动端只负责展示确认卡和提交用户选择。

## RAG 链路追踪

第 8 章使用下面的脚本观察一次 RAG 请求的完整输入：用户问题、检索到的片段、构造出的提示词消息和 `MockLLMProvider` 生成的答案。

```bash
python3 scripts/rag_trace.py --question '移动端为什么不能直接保存模型 API Key？'
```

Trace 输出会包含完整提示词上下文。只对已脱敏的本地文档运行该脚本，不要把真实用户日志、内部密钥或未脱敏资料直接打印到终端。

## RAG 检索评测

第 9 章使用下面的脚本检查检索器是否能把期望文档章节召回到 Top-K 中：

```bash
python3 scripts/rag_eval.py --top-k 3
```

评测用例位于 `data/eval/rag_eval_cases.json`。脚本输出 `hit_rate` 和 `mrr`，只评估检索层，不调用模型，也不评价最终答案质量。这样可以先判断“资料有没有给对”，再决定是否需要优化提示词或模型参数。

## 答案质量评测

第 13 章使用下面的脚本运行完整本地知识助手链路，并用确定性规则检查最终答案是否覆盖关键要点、是否命中指定引用、是否包含禁止出现的风险表达：

```bash
python3 scripts/answer_eval.py --min-score 0.8
```

评测用例位于 `data/eval/answer_eval_cases.json`。脚本默认使用 `MockLLMProvider`，因此不需要真实模型 API Key。它不是模型评审器，而是一个快速回归门禁：任一样本未通过时进程会返回非零退出码，方便 CI 阻断；早期只想观察报告时可以追加 `--report-only`，再把高风险样本交给人工复核。

## 成本、性能与稳定性报表

第 14 章使用下面的脚本读取本地模型调用日志样本和示例价格表，输出成本、首 Token 延迟、P95 延迟、缓存命中、错误率、重试率、降级率和告警：

```bash
python3 scripts/ops_report.py --latency-slo-ms 3000
```

日志样本位于 `data/observability/model_call_logs.json`，示例价格位于 `data/observability/model_pricing.json`。价格只用于教学，不代表任何模型厂商的实时价格；真实项目应接入模型网关日志、移动端埋点、崩溃监控和当前账单配置。可以用 `--logs` 指定日志文件、`--pricing` 指定价格文件、`--latency-slo-ms` 指定延迟目标。

## 只读文件分析 Agent

第 10 章使用下面的脚本演示 Agent 的 Observe、Plan、Act、Tool Result、Reflect 循环，以及工具白名单、路径限制、最大步数和执行轨迹：

```bash
python3 scripts/file_triage_agent.py \
  --goal '检查移动端知识库是否覆盖密钥、流式输出、权限和脱敏要求' \
  --keyword 'API Key' \
  --keyword '流式输出' \
  --keyword '权限' \
  --keyword '脱敏'
```

脚本默认读取 `data/documents/` 下的 Markdown 文档；如果显式传入 `--docs-dir`，会读取该目录下的 Markdown 文件，并在输出中包含命中的行片段。脚本不调用外部模型服务，也不会执行写文件、删除文件或网络请求。生产系统可以把确定性规划器替换成模型规划器，但工具白名单和参数校验仍应保留在服务端代码中。

## 周报工作流

第 11 章使用下面的脚本演示固定工作流如何收集输入、生成草稿、校验章节，并在发布前停在人工确认节点：

```bash
python3 scripts/weekly_report_workflow.py
```

默认输出 `waiting_confirmation`，不会写文件。显式传入 `--approve --out <path>` 后才会写入本地文件；只传 `--approve` 会返回 `dry_run`：

```bash
python3 scripts/weekly_report_workflow.py --approve
```

```bash
python3 scripts/weekly_report_workflow.py \
  --approve \
  --out /tmp/mobile-ai-weekly.md
```

示例中的发布动作只是写入本地文件，用来模拟发送周报、创建工单或通知团队频道。真实项目应在发布前重新校验用户权限、接收对象和内容风险。

## 多模态截图工单 payload

第 12 章使用下面的脚本演示移动端截图进入多模态模型前的服务端处理：文件类型、大小、尺寸校验，图片摘要，模型请求 payload 和结构化输出 schema。

```bash
python3 scripts/image_ticket_payload.py --omit-image-data
```

`--omit-image-data` 只省略完整 base64 图片内容，便于阅读终端输出；去掉该参数即可看到完整数据 URI。示例图片位于 `data/multimodal/login_error.svg`，用于本地学习和测试。当前脚本只做文件类型、大小、尺寸和摘要校验；生产环境应优先使用移动端导出的 PNG 或 JPEG，并在服务端补充 EXIF 剥离、可见隐私识别/遮挡和人工确认后再调用模型网关。

## 切换真实模型

复制 `.env.example` 中的变量到本地环境。不要把真实密钥提交到仓库。

```bash
export LLM_PROVIDER=openai_compatible
export LLM_API_URL=https://api.example.com/v1/chat/completions
export LLM_API_KEY=replace-with-real-key
export LLM_MODEL=example-chat-model
PYTHONPATH=src python3 -m mobile_llm.app
```

移动端客户端只应调用本工程暴露的自有服务端接口，不应直接持有 `LLM_API_KEY`。

当前 `OpenAICompatibleProvider.stream_generate()` 是同步请求后的单块 fallback，用来保持服务端协议可运行。生产环境要获得真正逐 Token 返回，需要在 provider 层实现模型网关的流式协议解析。

本工程默认绑定 `127.0.0.1`，用于本地学习和调试。如果将 `HOST` 改为 `0.0.0.0` 并接入真实模型服务，必须先增加登录认证、限流、受控 CORS 来源和访问日志脱敏，避免被任意网页跨域调用消耗模型额度。
