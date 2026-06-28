# 大模型应用开发三部曲

面向移动端开发工程师的 Prompt、RAG、Agent、AI Coding 与端侧智能工程实践

本仓库用于维护面向移动端开发工程师的大模型应用开发系列书稿、EPUB 电子书和配套示例工程。系列目标是帮助具备 iOS、Android、Flutter 或 React Native 基础的开发者，快速理解大模型应用、AI coding 和端侧智能工程的关键机制，并完成可运行的入门与实战项目。

## 当前状态

- 系列目标篇幅：每册约 10 万字，合理区间为 9 万-11 万字。
- 第一册《大模型应用开发快速入门》：当前约 11.0 万字符；16 章和附录 A-E 已压缩为目标区间内的完整书稿。
- 第二册《AI Coding 编程专家》：当前约 10.0 万字符；14 章、附录 A-F 和配套示例工程已形成完整初稿，见 `books/02-ai-coding-mobile-engineers/`。
- 第三册《端侧大模型与移动智能工程》：当前约 10.0 万字符；14 章和附录 A-D 已形成完整初稿，见 `books/03-on-device-ai-mobile-engineers/`。
- 配套工程：`examples/mobile-knowledge-assistant/` 已包含可运行的 Python 服务端、开发环境检查、提示词契约检查、结构化输出与工具调用、RAG 检索、RAG 评测、答案质量评测、成本、性能与稳定性报表、多模态截图 payload、只读文件分析 Agent、周报工作流、SSE 流式输出、取消请求、RAG Trace 和自动化测试。
- 发布计划：见 `GITHUB_PUBLICATION_PLAN.md`。
- 三部曲总规划：见 `SERIES_PLAN.md`。

## 目录

```text
manuscript/
  front-matter/          前言、书名页和读者说明
  chapters/              全书章节正文
  back-matter/           附录
  assets/                图表、截图和配图素材
examples/
  mobile-knowledge-assistant/
                         可运行的移动端知识助手服务端示例
  ai-coding-mobile-refactor/
                         第二册配套 AI coding 重构训练示例
books/
  02-ai-coding-mobile-engineers/
                         第二册：面向移动端工程师的 AI coding 进阶书稿
  03-on-device-ai-mobile-engineers/
                         第三册：端侧大模型与移动智能工程书稿
```

## 本地验证

构建可打开的整本 Markdown 书稿：

```bash
python3 tools/manage_chapters.py validate
python3 tools/build_book.py
python3 -m unittest discover -s tests
```

输出文件为 `build/book.md`。这是由 `manuscript/` 源文件生成的审校稿，正式修改仍应回到章节和附录源文件中完成。

生成 EPUB 3 电子书：

```bash
python3 tools/build_epub.py
```

输出文件为 `build/ebooks/llm-app-dev-for-mobile-engineers.epub`。EPUB 产物包含阅读器目录、章节 XHTML 拆分、标题锚点和高清 PNG 图表资源，适合在 Apple Books、Calibre、Thorium Reader 等阅读器中做笔记、高亮和跳转。构建脚本会优先把 SVG 图表栅格化为 PNG，避免部分阅读器无法渲染 SVG 中文字体。

当前已提交的 EPUB 产物包括：

- `build/ebooks/llm-app-dev-for-mobile-engineers.epub`
- `build/ebooks/ai-coding-mobile-engineers.epub`
- `build/ebooks/on-device-ai-mobile-engineers.epub`

构建第二册书稿：

```bash
python3 tools/manage_chapters.py --manifest books/02-ai-coding-mobile-engineers/book-manifest.json validate
python3 tools/build_book.py \
  --manifest books/02-ai-coding-mobile-engineers/book-manifest.json \
  --output build/book-02-ai-coding-mobile-engineers.md
python3 tools/build_epub.py \
  --manifest books/02-ai-coding-mobile-engineers/book-manifest.json \
  --output build/ebooks/ai-coding-mobile-engineers.epub
```

构建第三册书稿：

```bash
python3 tools/manage_chapters.py --manifest books/03-on-device-ai-mobile-engineers/book-manifest.json validate
python3 tools/build_book.py \
  --manifest books/03-on-device-ai-mobile-engineers/book-manifest.json \
  --output build/book-03-on-device-ai-mobile-engineers.md
python3 tools/build_epub.py \
  --manifest books/03-on-device-ai-mobile-engineers/book-manifest.json \
  --output build/ebooks/on-device-ai-mobile-engineers.epub
```

运行第二册配套示例工程测试：

```bash
cd examples/ai-coding-mobile-refactor
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m py_compile src/ai_refactor/*.py
```

## 章节维护

整书顺序由 `manuscript/book-manifest.json` 维护，构建脚本会按该清单合并前言、目录、章节和附录。常用命令：

```bash
python3 tools/manage_chapters.py list
python3 tools/manage_chapters.py show 8
python3 tools/manage_chapters.py add --number 17 --slug on-device-llm --title '端侧大模型应用'
python3 tools/manage_chapters.py rename 17 --title '端侧模型与移动端部署'
python3 tools/manage_chapters.py remove 17
python3 tools/manage_chapters.py validate
```

`remove` 默认只从清单移除章节，不删除 Markdown 文件；确需删除文件时再追加 `--delete-file`。新增、删除或重排章节后，应同步审查 `manuscript/contents.md`、`manuscript/publication-length-plan.md` 和 `CHANGELOG.md`。

运行配套工程测试：

```bash
cd examples/mobile-knowledge-assistant
PYTHONWARNINGS=error PYTHONPATH=src python3 -m unittest discover -s tests
```

检查脚本和服务端模块能否编译：

```bash
cd examples/mobile-knowledge-assistant
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

运行开发环境检查：

```bash
cd examples/mobile-knowledge-assistant
python3 scripts/dev_environment_check.py
```

该脚本检查 Python 版本、配置模板、`.gitignore`、示例文档目录和 mock provider 本地链路，不会输出真实密钥。

运行 RAG 检索评测：

```bash
cd examples/mobile-knowledge-assistant
python3 scripts/rag_eval.py --top-k 3
```

运行答案质量评测：

```bash
cd examples/mobile-knowledge-assistant
python3 scripts/answer_eval.py --min-score 0.8
```

默认情况下，任一答案样本未通过会返回非零退出码，适合 CI 门禁；早期只想观察报告时可追加 `--report-only`。

运行提示词契约检查：

```bash
cd examples/mobile-knowledge-assistant
python3 scripts/prompt_contract_check.py
```

该脚本检查提示词是否包含系统角色、任务、上下文边界、约束、输出格式、Few-shot 示例、敏感值边界和长度预算。

运行结构化输出与工具调用示例：

```bash
cd examples/mobile-knowledge-assistant
python3 scripts/structured_tool_router.py \
  --message '帮我查一下订单 A1024 到哪里了' \
  --user-id user_001
```

取消订单等高风险动作会先做权限和业务状态检查；检查通过后返回移动端确认卡，用户确认后再追加 `--confirm` 模拟二次提交。

运行成本、性能与稳定性报表：

```bash
cd examples/mobile-knowledge-assistant
python3 scripts/ops_report.py --latency-slo-ms 3000
```

该脚本支持 `--logs` 指定模型调用日志、`--pricing` 指定示例价格表、`--latency-slo-ms` 指定延迟目标，输出中包含 Token 成本、首 Token 延迟、P95 延迟、缓存命中率、错误率、重试率、降级率和告警。

运行只读文件分析 Agent：

```bash
cd examples/mobile-knowledge-assistant
python3 scripts/file_triage_agent.py \
  --goal '检查移动端知识库是否覆盖密钥、流式输出、权限和脱敏要求' \
  --keyword 'API Key' \
  --keyword '流式输出' \
  --keyword '权限' \
  --keyword '脱敏'
```

运行周报工作流：

```bash
cd examples/mobile-knowledge-assistant
python3 scripts/weekly_report_workflow.py
```

运行多模态截图工单 payload 生成器：

```bash
cd examples/mobile-knowledge-assistant
python3 scripts/image_ticket_payload.py --omit-image-data
```

检查 SVG 图表：

```bash
xmllint --noout manuscript/assets/diagrams/*.svg examples/mobile-knowledge-assistant/data/multimodal/login_error.svg
```

## 公开仓库说明

本仓库适合采用“书稿 Markdown + 可运行代码 + GitHub Pages 在线阅读”的方式公开。正式公开前，需要确认出版社合同、内容授权、示例代码授权和图片素材授权。

建议暂按以下原则维护：

- 书稿正文和示例代码分开授权，具体见 `LICENSE.md`。
- 真实 API Key、内部域名、真实用户数据不得进入仓库。
- 章节增删必须同步更新 `manuscript/contents.md` 和 `GITHUB_PUBLICATION_PLAN.md`。
- 章节顺序以 `manuscript/book-manifest.json` 为准，使用 `tools/manage_chapters.py` 做增删改查。
- 示例代码变更必须补充或更新测试。
