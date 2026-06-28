# GitHub 公开仓库发布方案

## 目标

将面向移动端工程师的大模型应用开发三部曲维护为一个公开学习型仓库，兼顾 3 个目标：

1. 读者可以在线阅读书稿、运行配套代码并提交勘误。
2. 作者可以持续增删章节、调整结构和更新示例工程。
3. 后续正式出版时，仓库内容、授权和版本记录可与出版社要求对齐。

## 推荐仓库名称

优先使用英文仓库名，便于搜索和引用：

- `llm-app-dev-for-mobile-engineers`
- `mobile-llm-application-book`
- `llm-book-mobile-dev`
- `large-model-app-dev-book`

推荐首选：`llm-app-dev-for-mobile-engineers`。这个名称能直接表达“面向移动端工程师的大模型应用开发”。

## 推荐公开形态

采用 **Markdown 书稿 + 配套代码 + GitHub Pages 在线阅读** 的一体化仓库。

| 模块 | 建议路径 | 作用 |
| --- | --- | --- |
| 第一册书稿 | `manuscript/` | Prompt、RAG、Agent、多模态和综合项目 |
| 第二册书稿 | `books/02-ai-coding-mobile-engineers/` | AI coding、工程上下文、Agent 编程和自动化实践 |
| 第三册书稿 | `books/03-on-device-ai-mobile-engineers/` | 端侧模型、混合推理、隐私、性能和产品化 |
| 章节清单 | `*/book-manifest.json` | 维护各册构建顺序和章节元数据 |
| 章节管理工具 | `tools/manage_chapters.py` | 提供章节 list/show/add/rename/remove/validate |
| 配套代码 | `examples/` | 可运行示例工程和测试 |
| EPUB 产物 | `build/ebooks/` | 三册可下载电子书 |
| 在线阅读 | `docs/` 或 MkDocs 生成站点 | 对外提供稳定阅读入口 |
| 读者反馈 | `ERRATA.md`、GitHub Issues | 收集错别字、代码问题、内容建议 |
| 贡献规范 | `CONTRIBUTING.md` | 说明如何提交勘误、章节建议和代码修改 |
| 自动校验 | `.github/workflows/validate.yml` | 在 PR 中运行环境检查、单元测试、编译检查和 SVG 校验 |
| Issue 表单 | `.github/ISSUE_TEMPLATE/` | 分类收集文字、技术勘误、章节调整、代码和图表问题 |

后续如果使用 MkDocs Material，可以新增：

```text
mkdocs.yml
docs/
  index.md
  chapters/
  examples/
```

初期不必急着搬迁全部文件。可以先让 `manuscript/` 保持当前结构，等目录稳定后再生成 `docs/` 在线阅读目录。

## 版本策略

建议使用以下分支和版本：

| 类型 | 命名 | 用途 |
| --- | --- | --- |
| 主分支 | `main` | 当前稳定草稿 |
| 章节调整分支 | `chapter/ch08-rag-update` | 单章扩写或重写 |
| 代码示例分支 | `example/mobile-assistant-api` | 配套工程变更 |
| 发布标签 | `v0.1-draft`、`v0.2-readable`、`v1.0-publication` | 固定可引用版本 |

每次增删章节，应同步更新：

- `manuscript/book-manifest.json`，优先通过 `python3 tools/manage_chapters.py` 修改
- `manuscript/contents.md`
- `manuscript/publication-length-plan.md`
- `manuscript/README.md`
- GitHub Pages 导航配置，如 `mkdocs.yml`
- `.github/ISSUE_TEMPLATE/chapter-proposal.yml` 中的相关说明，如果章节调整流程发生变化

当前仓库已初始化 Git，并已推送到公开仓库 `zenghao0708/llm-app-dev-for-mobile-engineers` 的 `main` 分支。后续发布前仍应完成一次本地验证，并确认 GitHub Actions 通过。

## 章节增删流程

新增章节建议按以下流程执行：

1. 使用 `python3 tools/manage_chapters.py add --number 17 --slug on-device-llm --title '端侧大模型应用'` 创建章节文件和 manifest 条目。
2. 在 `manuscript/contents.md` 中说明章节位置和标题。
3. 在 `publication-length-plan.md` 中调整目标字数。
4. 如果新增代码示例，同步放入 `examples/` 并补充测试。
5. 如果新增图表，同步放入 `manuscript/assets/diagrams/`，确保 SVG 不遮挡、不重叠、可高清渲染。
6. 运行 `python3 tools/manage_chapters.py validate` 和 `python3 tools/build_book.py`。
7. 更新 `CHANGELOG.md` 或 Release Notes，说明本次结构调整。

删除或合并章节时，不建议直接丢失内容。可以先在 PR 中说明：

- 删除原因。
- 内容是否迁移到其他章节。
- 对全书字数和目录编号的影响。
- 是否影响配套代码或图片引用。

## 授权建议

正式公开前需要确认出版社合同。建议把“内容授权”和“代码授权”分开处理：

| 对象 | 推荐授权 | 原因 |
| --- | --- | --- |
| 书稿正文、图表、配图说明 | CC BY-NC-SA 4.0 或出版社许可范围内的自定义声明 | 允许学习传播，同时限制商业再利用 |
| 示例代码 | MIT 或 Apache-2.0 | 方便读者在项目中学习、修改和复用 |
| 截图与第三方素材 | 单独标注来源和授权 | 避免版权风险 |

如果出版社要求完整书稿不公开，可以采用折中方案：

- 公开完整目录、前言、样章和配套代码。
- 公开勘误、更新日志和运行说明。
- 非样章正文只保留摘要或学习路线。

当前仓库采用分开授权声明：

- 示例代码、测试和工具脚本：MIT License，见 `LICENSE-CODE`。
- 书稿正文、图表和配图规划：CC BY-NC-SA 4.0，见 `LICENSE-CONTENT.md`。
- 第三方截图、商标、外部引用资料和未来出版社正式版本不自动纳入上述授权。

## Issue 分类建议

GitHub Issues 可以使用以下标签：

| 标签 | 用途 |
| --- | --- |
| `typo` | 错别字、标点、格式 |
| `errata` | 技术错误或表述错误 |
| `chapter-proposal` | 新增、删除或重排章节建议 |
| `code-example` | 配套代码问题 |
| `diagram` | 图表、箭头、截图和高清渲染问题 |
| `mobile-ios` | iOS 相关补充 |
| `mobile-android` | Android 相关补充 |
| `rag` | RAG、检索、引用来源相关问题 |
| `agent` | Agent、工具调用、工作流相关问题 |

## 发布优先级

建议分 4 个阶段公开：

1. `v0.1-draft`：公开目录、前言、样章、第 16 章综合项目和配套代码。
2. `v0.2-readable`：补齐所有章节到可读草稿，开放勘误。
3. `v0.3-review`：完成技术审校、图表检查、代码测试和字数控制。
4. `v1.0-publication`：与正式出版稿对齐，冻结主要章节结构。

当前项目已形成三册初稿：第一册约 11 万字符，第二册和第三册接近 10 万字目标区间。配套工程具备环境自检和自动化测试，三册 EPUB 已可生成并提交；更适合按 `v0.3-review` 候选来准备公开。进入 `v1.0-publication` 前，需要重点完成技术审校、截图补齐、授权确认和发布标签冻结。

## 公开前检查清单

- 初始化 Git 仓库并创建 `main` 分支。
- 运行 `python3 tools/manage_chapters.py validate`，确认章节清单没有重复、缺失或越界路径。
- 确认正文、图表和代码的授权边界，必要时增加单独的内容授权说明。
- 运行 `.github/workflows/validate.yml` 中的本地等价命令，确保示例工程和 SVG 图表可验证。
- 检查 `manuscript/contents.md`、`books/*/contents.md`、`README.md`、`SERIES_PLAN.md`、`CHANGELOG.md` 和 `GITHUB_PUBLICATION_PLAN.md` 中的章节状态一致。
- 重新生成并抽检 `build/ebooks/*.epub`，确认目录、锚点、图片和中文字体正常。
- 检查仓库中没有真实 API Key、`.env`、本地缓存、打包产物或第三方未授权素材。
