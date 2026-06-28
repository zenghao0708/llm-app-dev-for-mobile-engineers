# 发布前检查清单

本清单用于本地模拟 GitHub Actions，并在公开发布前确认仓库没有明显的构建、测试、图表或清单问题。

## 本地验证

```bash
python3 tools/manage_chapters.py validate
python3 tools/build_book.py
python3 tools/build_epub.py
python3 -m unittest discover -s tests

cd examples/mobile-knowledge-assistant
python3 scripts/dev_environment_check.py
PYTHONPATH=src PYTHONWARNINGS=error python3 -m unittest discover -s tests
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

cd ../..
python3 -m py_compile tools/build_book.py tools/build_epub.py tools/manage_chapters.py
xmllint --noout books/01-llm-app-dev-for-mobile-engineers/assets/diagrams/*.svg examples/mobile-knowledge-assistant/data/multimodal/login_error.svg
```

## 章节结构检查

- `books/01-llm-app-dev-for-mobile-engineers/book-manifest.json` 是构建顺序的唯一机器清单。
- `books/01-llm-app-dev-for-mobile-engineers/contents.md` 是面向读者的正式目录，需要人工审阅。
- 新增章节用 `python3 tools/manage_chapters.py add`。
- 修改章节标题或文件 slug 用 `python3 tools/manage_chapters.py rename`。
- 删除章节默认只从 manifest 移除；确认不再需要源文件时才使用 `--delete-file`。

## GitHub 发布检查

- 确认 `.env`、真实 API Key、Cookie、Session、本地日志、缓存、`__pycache__/`、`.pyc`、`node_modules/` 没有进入提交。
- 确认 `README.md`、`CONTRIBUTING.md`、`GITHUB_PUBLICATION_PLAN.md`、`CHANGELOG.md` 与当前章节状态一致。
- 首次公开建议使用仓库名 `llm-app-dev-for-mobile-engineers`。
- 首次标签建议使用 `v0.2-readable`，表示全书进入可读草稿并开放勘误。
