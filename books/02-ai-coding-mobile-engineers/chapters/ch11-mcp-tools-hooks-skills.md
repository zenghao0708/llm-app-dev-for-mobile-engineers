# 第 11 章 MCP、工具、Hooks 与 Skills

## 本章导读

AI coding agent 的能力很大程度取决于它能连接哪些工具。MCP、hooks、skills、插件和自定义脚本，都是把 agent 放进工程体系的方式。

## 学习目标

- 理解 MCP 的作用：连接模型、工具和上下文。
- 知道 hooks 如何把校验、格式化和通知自动接入 agent 流程。
- 掌握移动端团队可以沉淀哪些 skills/playbooks。

## 工具层次

| 层次 | 例子 | 作用 |
| --- | --- | --- |
| 本地命令 | test、lint、build、format | 验证代码 |
| 仓库工具 | rg、git、脚本、生成器 | 定位和修改 |
| 外部系统 | GitHub、Issue、CI、日志平台 | 连接协作流程 |
| MCP server | 设计稿、文档、数据库、内部平台 | 标准化上下文和工具 |
| Skills | 团队经验、任务模板、审查规则 | 复用高质量流程 |

## 移动端可沉淀的 Skills

- iOS 崩溃分析。
- Android Gradle 构建错误排查。
- Flutter Widget 拆分。
- React Native bridge 问题定位。
- 隐私权限变更审查。
- 发版前检查。

## Hooks 的价值

Hooks 可以把人工提醒变成自动动作：

- 文件修改后运行格式化。
- 完成任务后运行测试。
- 修改权限文件时提示人工确认。
- 生成 PR 前检查敏感文件。

## 本章小结

工具、hooks 和 skills 让 AI coding 从“个人提示词技巧”变成“团队工程能力”。它们也是移动端团队规模化使用 agent 的基础。
