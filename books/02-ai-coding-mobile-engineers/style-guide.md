# 写作风格指南

## 读者假设

- 读者具备移动端项目经验，但不一定了解 agentic coding 的系统设计。
- 读者知道 Git、CI、单元测试、构建脚本和代码评审。
- 读者可能使用 Swift、Kotlin、Dart、TypeScript 或 Python，但本书示例应尽量语言中立，并在必要时给出移动端平台差异。

## 写法要求

- 先讲工程问题，再讲 AI 工具能力。
- 少写“神奇自动化”，多写输入、上下文、工具、验证和失败处理。
- 每章至少包含一个移动端场景，例如崩溃修复、UI 重构、网络层迁移、权限说明、Flutter 组件拆分、React Native bridge 问题。
- 不把 Claude Code、Codex、Cursor、Copilot 等工具写成非此即彼；重点比较工具背后的工程能力。
- 涉及最新工具能力时必须标注资料来源和日期，避免把快速变化的产品状态写成长期事实。

## 术语约定

- AI coding：泛指使用大模型和 agent 辅助软件开发。
- Agentic coding：强调 agent 可以读写文件、运行命令、调用工具、循环验证的编程方式。
- Prompt Engineering：任务表达和输出约束。
- Context Engineering：上下文选择、压缩、分层和更新。
- Harness Engineering：执行环境、工具接口、权限、测试、脚本和沙箱。
- Loop Engineering：反馈循环、检查点、失败恢复和多轮收敛。

## 案例格式

每个案例尽量包含：

1. 任务背景。
2. 仓库结构和限制。
3. 给 agent 的输入。
4. agent 允许使用的工具。
5. 验证命令。
6. 人类审查点。
7. 失败模式和修正方式。
