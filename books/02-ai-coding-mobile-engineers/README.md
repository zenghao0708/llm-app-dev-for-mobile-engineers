# 《AI Coding 编程专家：移动端工程师进阶实战》书稿项目

本目录维护三部曲第二册书稿，主题是面向移动端开发工程师的 AI coding 编程专家提升教程。

## 定位

- 系列位置：三部曲第二册。
- 目标篇幅：约 10 万字，合理区间 9 万-11 万字。
- 目标读者：有 iOS、Android、Flutter、React Native 或移动端架构经验的工程师。
- 前置基础：已理解大模型调用、Prompt、RAG、Agent 的基本概念，或读过第一册《大模型应用开发快速入门》。
- 核心问题：如何把 Claude Code、Codex 等 AI coding agent 变成可控、可验证、可复用的工程能力，而不是把它们当成一次性聊天工具。

## 推荐书名

主书名：AI Coding 编程专家
副标题：面向移动端工程师的 Agent 编程、工程上下文与自动化实践

备选书名：

- AI Coding 工程化实战：移动端开发者的智能编程进阶
- Agentic Coding 实战：从 Prompt 到工程闭环
- AI 辅助编程专家教程：移动端工程师版

## 目录结构

```text
books/02-ai-coding-mobile-engineers/
  front-matter/          书名页、前言
  chapters/              第二册章节正文
  back-matter/           附录、术语、资料来源
  book-manifest.json     构建顺序和章节元数据
  contents.md            面向读者的目录
  style-guide.md         写作风格和案例规范
  publication-plan.md    10 万字篇幅规划
  references.md          官方资料和事实核验来源
```

## 写作主线

本书不把 AI coding 简化为“写提示词让模型写代码”。真正的能力链条分为四层：

1. Prompt Engineering：把任务说清楚，让模型知道要做什么。
2. Context Engineering：把仓库、需求、约束、历史决策和错误现场组织成可执行上下文。
3. Harness Engineering：为 agent 准备工具、权限、测试、脚本、沙箱、检查点和交付边界。
4. Loop Engineering：设计“理解-修改-验证-复盘”的反馈循环，让 agent 能做长任务、多轮任务和跨模块任务。

## 当前状态

当前版本已扩写为接近 10 万字的完整初稿，覆盖 14 章正文和附录 A-F。书稿已包含移动端真实工程案例、prompt 模板、检查清单、读者练习和配套可运行示例工程。后续出版前仍需继续做事实核验、截图补充、语言精修和示例工程扩展。

配套示例工程位于 `examples/ai-coding-mobile-refactor/`，用于训练统一网络错误模型迁移、ViewModel 状态测试、PR 摘要和风险说明。
