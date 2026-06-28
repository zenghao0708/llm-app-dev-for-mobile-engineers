# 第 11 章 MCP、工具、Hooks 与 Skills

## 本章导读

AI coding agent 的能力很大程度取决于它能连接哪些工具。MCP、hooks、skills、插件和自定义脚本，都是把 agent 放进工程体系的方式。没有工具的 agent 只能“猜代码”；有工具但没有边界的 agent 又会带来安全风险。工程化的关键，是把工具能力、权限模型和团队经验组织成稳定接口。

OpenAI Codex 文档把 MCP 描述为连接模型、工具和上下文的方式；Claude Code 文档也提供 MCP、hooks、SDK 等工程化入口。不同工具的具体命令会变化，但背后的模式相对稳定：让 agent 访问必要上下文，执行受控命令，并在关键节点触发自动校验。

## 学习目标

- 理解 MCP 的作用：连接模型、工具和上下文。
- 知道 hooks 如何把校验、格式化和通知自动接入 agent 流程。
- 掌握移动端团队可以沉淀哪些 skills/playbooks。
- 能够为移动端仓库设计一套最小 agent harness。

## 工具层次

| 层次 | 例子 | 作用 |
| --- | --- | --- |
| 本地命令 | test、lint、build、format | 验证代码 |
| 仓库工具 | rg、git、脚本、生成器 | 定位和修改 |
| 外部系统 | GitHub、Issue、CI、日志平台 | 连接协作流程 |
| MCP server | 设计稿、文档、数据库、内部平台 | 标准化上下文和工具 |
| Skills | 团队经验、任务模板、审查规则 | 复用高质量流程 |

这五层并不是越多越好。一个小团队可以先从本地命令和仓库脚本开始；当 agent 经常需要访问设计稿、接口文档、Issue 和监控系统时，再考虑 MCP 或插件化工具。

## MCP 的价值

MCP 的价值不是“让模型什么都能连”，而是把工具接入变成稳定协议。对移动端团队来说，常见 MCP 场景包括：

- 读取设计系统组件说明。
- 查询接口文档和错误码。
- 获取 Issue 或需求背景。
- 查询 CI 状态。
- 读取崩溃平台中的已脱敏堆栈。
- 查询内部文档中的发版规则。

这些上下文如果靠人工复制，很容易遗漏、过期或带入敏感信息。通过 MCP 接入后，团队可以控制可访问范围、返回格式和审计记录。

## 移动端 MCP 设计原则

为移动端团队设计 MCP 或工具接口时，应遵守四个原则：

1. 只暴露任务需要的最小字段。
2. 默认返回脱敏数据。
3. 对写操作做人工确认或禁用。
4. 让工具返回结构化结果，而不是大段不可控文本。

例如崩溃平台工具可以返回：

```json
{
  "crash_id": "CRASH-2026-001",
  "app_version": "5.8.0",
  "os": "iOS 18.5",
  "top_frame": "ProfileViewModel.handleError",
  "stack": ["..."],
  "recent_release": true,
  "sample_count": 128,
  "redacted": true
}
```

这比复制一整页监控系统 HTML 更适合 agent 使用，也更容易做安全审查。

## Hooks 的价值

Hooks 可以把人工提醒变成自动动作：

- 文件修改后运行格式化。
- 完成任务后运行测试。
- 修改权限文件时提示人工确认。
- 生成 PR 前检查敏感文件。
- 任务结束时生成变更摘要。
- 命中高风险目录时阻止自动执行。

Claude Code 文档中 hooks 的设计思路，就是在 agent 生命周期中的关键事件上运行 shell commands。不同工具的实现细节可能不同，但移动端团队可以抽象出自己的事件模型：

| 事件 | 动作 |
| --- | --- |
| 修改 Swift/Kotlin/Dart/TS 文件 | 运行格式化或 lint |
| 修改测试文件 | 运行相关测试 |
| 修改 Manifest/Info.plist/entitlements | 标记人工确认 |
| 修改依赖文件 | 要求输出升级说明 |
| 准备提交 | 扫描 secrets、缓存、构建产物 |

Hooks 的目标不是让每个改动都自动跑全量 CI，而是让高频低成本检查自动发生。

## Skills 与团队经验

Skills 可以理解为可复用的任务说明、流程约束和检查清单。它们比普通 prompt 更稳定，因为它们被放在仓库或团队工具中，可以版本化、审查和迭代。

移动端可沉淀的 Skills 包括：

- iOS 崩溃分析。
- Android Gradle 构建错误排查。
- Flutter Widget 拆分。
- React Native bridge 问题定位。
- 隐私权限变更审查。
- 发版前检查。
- 本地化文案同步。
- 网络错误模型迁移。

一个 skill 不需要很长，但必须包含：适用场景、输入要求、禁止事项、执行步骤、验收清单和输出格式。

## 示例：Android Gradle 构建错误 Skill

```text
适用场景：
- Android 项目 Gradle 构建失败。

输入要求：
- 完整失败日志。
- 执行命令。
- 最近修改文件。
- Gradle/AGP/Kotlin 版本。

禁止事项：
- 不允许自动升级 AGP、Kotlin、Gradle wrapper。
- 不允许删除 lockfile。
- 不允许修改签名配置。

执行步骤：
1. 先归类错误：依赖解析、编译、资源、R8、测试、环境。
2. 找到最小相关文件。
3. 提出不超过 2 个修复假设。
4. 做最小修改。
5. 运行原失败命令。

输出：
- 错误类型。
- 修改文件。
- 验证命令和结果。
- 仍需人工确认的风险。
```

这种 skill 能减少 prompt 随机性，也能降低新成员使用 agent 的门槛。

## 最小 Agent Harness

一个移动端仓库可以从下面的最小 harness 开始：

```text
docs/ai-coding/
  project-map.md
  high-risk-files.md
  commands.md
  prompt-templates.md
  review-checklist.md
scripts/
  check_secrets.sh
  changed_tests.sh
  mobile_ci_equivalent.sh
```

其中 `commands.md` 记录：

- iOS 单元测试命令。
- Android 单元测试命令。
- Flutter/RN 测试命令。
- lint/format 命令。
- 本地不建议运行的重命令。

`high-risk-files.md` 记录：

- 签名、证书、权限、发布配置。
- 支付、登录、风控、隐私相关模块。
- 禁止 agent 自动修改的路径。

有了这些文件，agent 不需要每次都问“怎么跑测试”“哪些文件危险”。团队经验被转化成可读上下文。

## 工具权限与审计

工具化之后必须做权限控制：

- 读权限和写权限分开。
- 本地命令和外部系统命令分开。
- 危险命令需要人工确认。
- 工具输出要避免泄露真实密钥和用户数据。
- 任务结束要保留变更摘要。

对移动端团队来说，尤其要注意设计稿、日志平台和发布系统。这些系统常包含商业信息和用户信息，不能因为 agent 需要上下文就无限开放。

## 本章小结

工具、hooks 和 skills 让 AI coding 从“个人提示词技巧”变成“团队工程能力”。MCP 负责连接上下文和工具，hooks 负责把校验嵌入流程，skills 负责沉淀团队经验。移动端团队不必一开始就建设复杂平台，但至少要有项目地图、高风险文件清单、标准命令和审查模板。
