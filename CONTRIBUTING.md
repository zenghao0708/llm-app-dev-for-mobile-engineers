# 贡献说明

感谢关注《大模型应用开发快速入门》。本仓库主要接受以下类型贡献：

- 书稿错别字、术语不统一、表达不清楚。
- 大模型机制、RAG、Agent、评测、安全等技术表述问题。
- iOS、Android、Flutter、React Native 场景补充。
- 配套示例工程的运行问题、测试补充和注释改进。
- 图表、截图、箭头位置、高清渲染和图注问题。

## 提交 Issue

提交问题时，建议包含：

- 章节或文件路径。
- 具体段落、标题或代码位置。
- 当前问题是什么。
- 建议如何修改。
- 如果是代码问题，请附上运行命令、环境版本和错误输出。

## 提交 Pull Request

提交 PR 前请确认：

- 修改范围尽量小，不做无关格式化。
- 增删章节时，优先使用 `python3 tools/manage_chapters.py` 更新 `manuscript/book-manifest.json` 和章节文件。
- 章节结构变更后，同步审查 `manuscript/contents.md`、`manuscript/publication-length-plan.md`、`manuscript/README.md` 和 `CHANGELOG.md`。
- 修改配套代码时，补充或更新测试。
- 不提交真实 API Key、内部域名、用户数据、日志、Cookie、Session 或本地缓存。
- 不提交 `__pycache__/`、`.pyc`、`.env`、`.venv/`、`node_modules/` 等运行产物。

整书构建命令：

```bash
python3 tools/manage_chapters.py validate
python3 tools/build_book.py
python3 -m unittest discover -s tests
```

章节管理命令：

```bash
python3 tools/manage_chapters.py list
python3 tools/manage_chapters.py show 8
python3 tools/manage_chapters.py add --number 17 --slug on-device-llm --title '端侧大模型应用'
python3 tools/manage_chapters.py rename 17 --title '端侧模型与移动端部署'
python3 tools/manage_chapters.py remove 17
python3 tools/manage_chapters.py validate
```

配套工程测试命令：

```bash
cd examples/mobile-knowledge-assistant
PYTHONWARNINGS=error PYTHONPATH=src python3 -m unittest discover -s tests
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

SVG 图表检查命令：

```bash
xmllint --noout manuscript/assets/diagrams/*.svg examples/mobile-knowledge-assistant/data/multimodal/login_error.svg
```

## 写作要求

- 面向移动端开发工程师，不假设读者有机器学习背景。
- 先解释工程问题，再引入模型概念。
- 代码必须能在配套工程中找到对应实现，不能只给不可运行片段。
- 注释应解释设计意图、边界和移动端注意事项，避免逐行复述代码。
- 图表箭头应停在模块边框，不应进入文字框内部。
