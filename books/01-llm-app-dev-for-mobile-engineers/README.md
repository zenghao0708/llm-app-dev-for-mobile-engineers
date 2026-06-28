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
- `../../examples/01-mobile-knowledge-assistant/`：可运行的移动端知识助手配套工程。
- `book-manifest.json`：整书源文件顺序清单，供构建脚本和章节管理工具读取。
- `contents.md`：正式目录。
- `style-guide.md`：写作风格、代码风格、图片规范。
- `publication-length-plan.md`：10 万字左右的出版篇幅规划。
- `image-plan.md`：全书配图总规划。
- `../../GITHUB_PUBLICATION_PLAN.md`：公开 GitHub 仓库、章节增删和发布节奏建议。

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

当前版本已完成 16 章正文和附录 A-E，并已压缩到目标篇幅区间。它适合进入出版社口径审校、技术审校、版式评估和读者测试。

正式书稿目标控制在 10 万字左右，合理区间为 9 万-11 万字。当前版本约 11.0 万字符；第 1 章至第 16 章和附录 A-E 已形成完整书稿。后续应以术语统一、技术审校、事实核验、截图补齐和读者测试为主。

后续建议按以下顺序处理：

1. 对第 1 章至第 16 章做出版社口径审校并统一术语。
2. 统一代码仓库与运行环境。
3. 根据最终模型提供方更新 API 示例。
4. 补齐真实移动端界面截图、运行结果和下载资源。
5. 做技术审校与事实核验。
