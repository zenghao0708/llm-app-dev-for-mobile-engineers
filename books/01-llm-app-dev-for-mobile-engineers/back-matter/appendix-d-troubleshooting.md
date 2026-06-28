# 附录 D 常见故障排查清单

本附录用于读者运行配套工程或接入移动端时快速定位问题。排查顺序建议从本地环境、服务端接口、移动端网络、模型配置、RAG 质量和安全边界逐层推进。

## D.1 本地环境

| 现象 | 可能原因 | 检查命令 | 处理方式 |
| --- | --- | --- | --- |
| `python3` 命令不存在 | 系统未安装 Python 或 PATH 不正确 | `python3 --version` | 安装 Python 3.10+，重新打开终端 |
| 启动时报 `ModuleNotFoundError` | 未设置 `PYTHONPATH=src` | `echo $PYTHONPATH` | 使用 `PYTHONPATH=src python3 -m mobile_llm.app` |
| 端口被占用 | 8000 已被其他服务使用 | `lsof -nP -iTCP:8000 -sTCP:LISTEN` | 改用 `PORT=8010` |
| 自检失败 | 文档目录、配置模板或 `.gitignore` 不完整 | `python3 scripts/dev_environment_check.py` | 按报告中的失败项修复 |

## D.2 服务端接口

| 现象 | 可能原因 | 检查方式 | 处理方式 |
| --- | --- | --- | --- |
| `/health` 无响应 | 服务端未启动或端口不一致 | `curl -s http://127.0.0.1:8000/health` | 重新启动服务，确认 `PORT` |
| `/api/ask` 返回 400 | 请求体不是 JSON 或缺少 `question` | 查看响应中的 `error` | 按 README 示例发送请求 |
| `/api/ask` 返回 401 / 403 | 自有服务端鉴权失败或用户无权限访问资料 | 检查登录态、用户 ID、资料权限过滤 | 重新登录，确认服务端权限规则 |
| `/api/ask` 返回 429 | 模型网关或自有服务端限流 | 查看响应头、网关日志和重试策略 | 使用退避重试，移动端提示稍后再试 |
| `/api/ask` 返回 502 | 模型 provider 调用失败 | 检查 `LLM_PROVIDER`、`LLM_API_URL`、`LLM_API_KEY` | 先切回 `mock`，再排查真实网关 |
| 请求超时 | 模型生成太慢、网络代理异常或服务端阻塞 | 对比 `/health`、模型网关日志和客户端超时设置 | 增加流式输出、取消按钮和服务端超时 |
| TLS 或代理错误 | 证书链、企业代理或网关域名配置异常 | 用 `curl -v` 检查握手和代理路径 | 修复证书、代理白名单或网关域名 |
| 返回没有引用来源 | 文档目录为空或检索未命中 | `python3 scripts/rag_trace.py` | 检查 `data/documents/` 与问题表达 |

## D.3 移动端网络

| 现象 | iOS / Android 线索 | 处理方式 |
| --- | --- | --- |
| 模拟器无法访问本机服务 | iOS Simulator 通常用 `127.0.0.1`，Android Emulator 用 `10.0.2.2` | 按平台改请求地址 |
| 真机无法访问 Mac | 服务端只绑定了 `127.0.0.1` 或不在同一局域网 | 使用 `HOST=0.0.0.0`，确认防火墙和局域网 IP |
| App 内 HTTP 请求失败 | ATS 或 Android cleartext HTTP 策略阻止 | 只在 Debug 配置 HTTP 例外，生产使用 HTTPS |
| 流式输出卡住 | 代理、网关或客户端未逐块读取 | 用 `curl -N` 或 `scripts/sse_client.py` 先验证服务端 |

## D.4 RAG 与答案质量

| 现象 | 可能原因 | 检查命令 | 处理方式 |
| --- | --- | --- | --- |
| 答案泛泛而谈 | 检索片段不相关或 Prompt 未要求引用 | `python3 scripts/rag_trace.py` | 调整文档切分、标题、Top-K 和回答模板 |
| 正确资料没有召回 | 关键词差异、Chunk 太大或太小 | `python3 scripts/rag_eval.py --top-k 3` | 增加同义词、重切文档或加入重排 |
| 答案格式不稳定 | 缺少结构化输出约束 | `python3 scripts/answer_eval.py --min-score 0.8` | 使用 JSON Schema 和服务端校验 |
| 幻觉版本号或接口名 | 模型脱离资料补全 | 检查引用来源 | 要求“不知道就说不知道”，并展示来源 |

## D.5 安全与隐私

| 风险 | 检查点 | 处理方式 |
| --- | --- | --- |
| API Key 泄露 | `.env`、日志、终端输出、移动端包体 | 只提交 `.env.example`，真实密钥只放服务端环境变量 |
| 日志包含隐私 | 邮箱、手机号、Token、Cookie、身份证号 | 运行 `scripts/privacy_redaction.py`，日志默认脱敏 |
| Prompt Injection | 外部资料要求“忽略系统规则” | 把外部资料标记为不可信上下文，工具调用走白名单 |
| 高风险工具误执行 | 删除、退款、取消订单、发通知 | 服务端做权限检查，移动端展示确认页 |

## D.6 公开仓库前检查

```bash
PYTHONWARNINGS=error PYTHONPATH=src python3 -m unittest discover -s tests
python3 scripts/dev_environment_check.py
xmllint --noout books/01-llm-app-dev-for-mobile-engineers/assets/diagrams/*.svg examples/mobile-knowledge-assistant/data/multimodal/login_error.svg
```

提交前还要确认没有 `.env`、真实 Key、真实用户日志、`__pycache__/`、`.pyc`、`node_modules/` 或本地打包产物。
