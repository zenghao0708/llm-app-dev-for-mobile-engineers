# 附录 E 延伸阅读与资料来源

本附录列出适合继续学习和事实核验的资料。API、平台安全策略和模型能力会变化，正式出版前应以官方网站为准重新核对。本清单中的链接于 2026-06-21 核对过。

## E.1 大模型 API 与结构化输出

- OpenAI API Overview：<https://developers.openai.com/api/reference/overview/>  
  用于了解 OpenAI API 的主要接口形态，包括 Responses、Realtime 和管理类接口。
- OpenAI Developer Quickstart：<https://developers.openai.com/api/docs/quickstart>  
  用于核对 Python / JavaScript SDK 的入门安装和首次调用方式。
- OpenAI Text Generation Guide：<https://developers.openai.com/api/docs/guides/text>  
  用于核对文本生成、消息输入和结构化文本输出的基础用法。
- OpenAI Structured Outputs Guide：<https://developers.openai.com/api/docs/guides/structured-outputs>  
  用于核对 JSON Schema 约束输出的能力边界。
- OpenAI Function Calling Guide：<https://developers.openai.com/api/docs/guides/function-calling>  
  用于核对工具调用、工具结果回传和参数结构化的官方说明。

## E.2 Python 工程与测试

- Python `venv` 文档：<https://docs.python.org/3/library/venv.html>  
  用于核对虚拟环境创建、隔离和目录结构。
- Python `unittest` 文档：<https://docs.python.org/3/library/unittest.html>  
  用于核对标准库测试框架、测试发现和断言方式。

## E.3 移动端网络与安全

- Apple `NSAppTransportSecurity` 文档：<https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity>  
  用于核对 iOS / iPadOS / macOS App 的 ATS 配置项。
- Apple Preventing Insecure Network Connections：<https://developer.apple.com/documentation/security/preventing-insecure-network-connections>  
  用于核对 Apple 平台对不安全网络连接的建议。
- Android Network Security Configuration：<https://developer.android.com/privacy-and-security/security-config>  
  用于核对 Android 的明文流量、证书信任和域名级网络安全配置。
- OWASP Mobile Application Security：<https://owasp.org/www-project-mobile-app-security/>  
  用于移动端安全测试方法和风险分类的延伸学习。
- OWASP MASTG：<https://mas.owasp.org/MASTG/>  
  用于核对移动端安全测试指南、测试技术和安全控制。

## E.4 流式输出与客户端体验

- MDN Server-sent events：<https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events>  
  用于理解 SSE 的浏览器 API、事件流和适用场景。
- MDN Using server-sent events：<https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events>  
  用于核对 `text/event-stream`、事件块格式和客户端处理方式。
- WHATWG HTML Standard: Server-sent events：<https://html.spec.whatwg.org/multipage/server-sent-events.html>  
  用于查阅 EventSource 与事件流格式的标准文本。

## E.5 本书配套工程核验路径

读者阅读外部资料后，可以回到配套工程做 4 类验证：

1. 用 `scripts/sampling_temperature_experiment.py` 理解采样参数。
2. 用 `scripts/prompt_contract_check.py` 检查 Prompt 契约。
3. 用 `scripts/rag_trace.py` 和 `scripts/rag_eval.py` 检查 RAG 链路。
4. 用 `scripts/privacy_redaction.py`、`scripts/structured_tool_router.py` 和 `scripts/ops_report.py` 检查上线边界。

