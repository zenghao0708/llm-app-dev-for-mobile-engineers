# 《大模型应用开发快速入门》书稿项目

书名：大模型应用开发快速入门  
副标题：Prompt、RAG、Agent 与工程实践  
定位：面向移动端开发工程师的入门与实战型计算机图书  
技术主线：Python 服务端示例为主，兼顾 iOS、Android、Flutter、React Native 的接入思维  

## 目录结构

- `front-matter/`：书名页、前言、读者对象、配套资源说明。
- `chapters/`：16 章正文初稿。
- `back-matter/`：附录 A-E，包括术语表、Prompt 模板、项目结构、排查清单和延伸阅读。
- `assets/diagrams/`：可用于排版的高清 SVG 矢量示意图。
- `assets/image-prompts/`：每章高清配图、截图和示意图制作提示。
- `../examples/mobile-knowledge-assistant/`：可运行的移动端知识助手配套工程。
- `book-manifest.json`：整书源文件顺序清单，供构建脚本和章节管理工具读取。
- `contents.md`：正式目录。
- `style-guide.md`：写作风格、代码风格、图片规范。
- `publication-length-plan.md`：10 万字左右的出版篇幅规划。
- `image-plan.md`：全书配图总规划。
- `../GITHUB_PUBLICATION_PLAN.md`：公开 GitHub 仓库、章节增删和发布节奏建议。

## 章节维护

增删改查章节统一使用根目录下的脚本：

```bash
python3 tools/manage_chapters.py list
python3 tools/manage_chapters.py show 8
python3 tools/manage_chapters.py add --number 17 --slug on-device-llm --title '端侧大模型应用'
python3 tools/manage_chapters.py rename 17 --title '端侧模型与移动端部署'
python3 tools/manage_chapters.py remove 17
python3 tools/manage_chapters.py validate
```

脚本会维护 `book-manifest.json` 和章节 Markdown 文件。目录正文、篇幅规划和修订日志仍需要人工审阅，避免章节名称、目标字数和出版说明不一致。

## 当前版本说明

当前版本已完成 16 章样章级扩写，并补齐附录 A-E。它适合进入出版社口径审校、技术审校、版式评估和读者测试。

正式书稿目标控制在 10 万字左右，合理区间为 9 万-11 万字。当前版本约 18.6 万字符，其中章节正文约 16.6 万字符；第 1 章至第 16 章已经按样章标准扩写，附录 A-E 已补齐。由于当前版本已经高于目标区间，后续应以压缩重复段落、统一术语和强化读者测试为主，并在全书统稿阶段控制篇幅。

后续建议按以下顺序处理：

1. 对第 1 章至第 16 章做出版社口径审校，压缩重复段落并统一术语。
2. 统一代码仓库与运行环境。
3. 根据最终模型提供方更新 API 示例。
4. 补齐真实移动端界面截图、运行结果和下载资源。
5. 做技术审校与事实核验。
