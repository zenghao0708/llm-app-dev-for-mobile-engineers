# 附录 C Python 与移动端项目结构建议

## C.1 配套代码原则

本书的核心示例应满足以下要求：

- 可以在本地直接启动。
- 不需要真实模型 Key 也能通过 mock provider 跑通主流程。
- 配置真实模型服务后，可以切换到真实 Provider。
- 包含测试命令，读者能验证代码是否可用。
- 不在移动端客户端保存模型 API Key。
- 不提交真实密钥、真实用户数据或内部配置。

## C.2 推荐项目结构

```text
examples/01-mobile-knowledge-assistant/
  README.md
  .env.example
  requirements.txt
  data/
    documents/
    eval/
    multimodal/
    observability/
    prompt/
    tools/
    workflow/
  scripts/
    dev_environment_check.py
    rag_trace.py
    rag_eval.py
    answer_eval.py
  src/
    mobile_llm/
      app.py
      config.py
      prompts.py
      providers.py
      retriever.py
      service.py
  tests/
```

其中，`src/mobile_llm/` 放服务端代码，`data/documents/` 放可公开的示例文档，`data/eval/` 放评测样本，`data/multimodal/` 放多模态示例素材，`data/observability/` 放观测日志样本，`data/prompt/` 放 Prompt 契约样例，`data/tools/` 放工具调用示例数据，`data/workflow/` 放工作流示例数据，`scripts/` 放分章可运行脚本，`tests/` 放自动化测试。移动端客户端代码可以在后续扩展为 `ios/`、`android/`、`flutter/` 或 `react-native/` 目录。

## C.3 注释原则

注释应该帮助读者理解工程决策，而不是重复代码本身。推荐注释以下内容：

- 为什么模型 API Key 只放在服务端。
- 为什么默认使用 mock provider。
- 为什么 SSE 每个事件都要 flush。
- 为什么日志不能记录完整隐私文本。
- 为什么权限过滤必须在检索前完成。

不推荐写这类注释：

```python
# 给变量赋值
answer = service.answer(question)
```

推荐写这类注释：

```python
# 移动端只发送用户问题和状态，模型密钥、检索细节和 Prompt 模板都留在服务端。
result = service.answer(question)
```

## C.4 验收命令

示例工程至少应通过：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m py_compile \
  src/mobile_llm/*.py \
  scripts/answer_eval.py \
  scripts/dev_environment_check.py \
  scripts/image_ticket_payload.py \
  scripts/file_triage_agent.py \
  scripts/ops_report.py \
  scripts/prompt_contract_check.py \
  scripts/privacy_redaction.py \
  scripts/rag_eval.py \
  scripts/sampling_temperature_experiment.py \
  scripts/structured_tool_router.py \
  scripts/tfidf_vector_search.py \
  scripts/weekly_report_workflow.py \
  scripts/sse_client.py \
  scripts/rag_trace.py
```

如果新增接口，还应补充一次真实 HTTP 请求验证，确认 README 中的命令可以得到预期响应。
