# 第 6 章 Harness Engineering：为 Agent 准备工程护栏

## 本章导读

Agent 想要完成真实编程任务，不能只靠模型。它需要一个 harness：文件系统、命令、工具、权限、沙箱、测试、日志和检查点共同构成的执行环境。

Anthropic 在 long-running agents 的 harness 研究中指出，长任务 agent 的问题不只是上下文窗口限制。即使有压缩，agent 仍可能试图一次做太多、在半成品状态中断、或者看到已有进展后过早宣布完成。解决思路不是“给一个更长 Prompt”，而是设计环境：初始化任务清单、进度文件、可恢复的 Git 状态、清晰的测试和逐步交付机制。

对移动端团队来说，Harness Engineering 是把 AI coding 从个人技巧变成团队能力的关键。

## 学习目标

- 理解 harness 是 agent 能力稳定输出的基础。
- 能够为移动端项目设计最小可用 harness。
- 掌握权限、测试、脚本、沙箱和检查点的边界设置。
- 知道如何避免 agent 一次做太多、浅层验证和过早完成。

## 6.1 Harness 是什么

Harness 可以理解为 agent 的工程运行环境。它不是单个工具，而是一组约束和接口。

一个 AI coding harness 通常包括：

- 入口规则：AGENTS.md、README、任务模板。
- 工具集合：文件读写、搜索、构建、测试、Git、Issue、PR。
- 权限模型：只读、可写、可执行、需要确认、禁止执行。
- 沙箱环境：依赖隔离、网络限制、敏感文件排除。
- 验证命令：单元测试、lint、类型检查、格式化、构建。
- 进度机制：任务清单、检查点、进度文件、提交记录。
- 交付协议：diff、commit、PR、变更摘要、风险说明。

Prompt 告诉 agent “做什么”；harness 决定 agent “能做什么、怎么验证、做错了怎么停下来”。

## 6.2 最小可用 Harness

并不是所有团队都需要一开始建设复杂平台。移动端团队可以先做最小可用 harness。

```text
mobile-app/
  AGENTS.md
  scripts/
    test_unit.sh
    lint.sh
    build_debug.sh
    check_localization.sh
  docs/
    module-map.md
    ai-progress.md
```

最小可用 harness 应该满足：

1. agent 知道哪些文件不能改。
2. agent 知道常用测试命令。
3. agent 能用一个脚本验证局部任务。
4. agent 必须输出运行过的命令和结果。
5. 长任务有进度文件。

做到这五点，agent 的可控性会明显提高。

## 6.3 权限模型

移动端项目的权限模型可以分为五层。

| 权限级别 | 允许动作 | 适用任务 |
| --- | --- | --- |
| 只读 | 搜索、阅读、解释 | 代码理解、方案评审 |
| 受限写 | 修改指定目录 | 小 bug、测试、文档 |
| 受限执行 | 运行白名单命令 | 测试、lint、Debug 构建 |
| 人工确认 | 依赖、权限、签名、发布 | 高风险变更 |
| 禁止 | 密钥、证书、删除历史、生产发布 | 不应交给 agent |

不要把所有命令都放进同一个权限级别。`./scripts/test_unit.sh` 和 `./scripts/release_prod.sh` 都是脚本，但风险完全不同。

## 6.4 命令白名单

建议为 agent 准备白名单命令。

安全命令示例：

```text
./scripts/test_unit.sh <TestName>
./scripts/lint.sh
./scripts/check_localization.sh
./scripts/build_debug.sh ios
./scripts/build_debug.sh android
```

需要确认的命令：

```text
pod update
./gradlew wrapper --gradle-version ...
npm install <package>
bundle update
```

禁止命令：

```text
rm -rf
git reset --hard
git push --force
./scripts/release_prod.sh
security find-identity
printenv
```

实际项目中不一定用文本白名单，也可以通过工具权限、CI、pre-commit hook 或 sandbox 实现。

## 6.5 测试 Harness

没有测试 harness，agent 很容易产生“看起来合理”的代码。测试 harness 不一定要全量，它应该提供分层验证：

| 层级 | 移动端例子 | 适用场景 |
| --- | --- | --- |
| 快速单测 | ViewModel、Repository、ErrorMapper | bug 修复、小重构 |
| 静态检查 | SwiftLint、ktlint、dart analyze、TypeScript | 格式和基础质量 |
| Debug 构建 | iOS/Android/Flutter/RN Debug | 验证编译和依赖 |
| UI/截图测试 | Snapshot、Compose UI、Flutter widget test | UI 结构变更 |
| 人工真机 | 权限、相机、通知、弱网、支付 | 高风险体验 |

Prompt 中应告诉 agent 运行哪个层级。不要让 agent 默认选择最省事的验证。

## 6.6 长任务 Harness

长任务最容易失败在三个地方：

- 一次做太多。
- 中断后丢失状态。
- 表面通过后过早宣布完成。

长任务 harness 可以借鉴“初始化 + 增量执行”的结构。

初始化阶段生成：

- 任务清单。
- 风险清单。
- 验证命令清单。
- 进度文件。
- 初始提交或检查点。

执行阶段要求：

- 每轮只推进一个小目标。
- 每轮结束更新进度文件。
- 每轮结束让仓库保持可运行状态。
- 每轮输出测试结果和未完成项。

移动端重构任务尤其适合这种模式。例如迁移网络错误模型时，不要让 agent 一次迁移 30 个页面，而是每轮迁移 2 个低风险页面，并保留剩余清单。

## 6.7 MCP 和外部工具

MCP 的价值是让 agent 不再只依赖本地文件，而能通过标准协议连接外部工具和上下文。OpenAI Agents SDK 文档将 MCP 描述为一种标准化方式，让应用把工具和上下文提供给 LLM。

移动端团队可以考虑接入：

- GitHub Issue 和 PR。
- CI 运行结果。
- 崩溃平台。
- 日志平台。
- 设计系统。
- 内部接口文档。
- 测试设备农场。

但外部工具接入要先做权限和脱敏。不要把用户日志、真实 token、内部证书直接交给 agent。

## 6.8 Harness 失败模式

| 失败模式 | 表现 | 解决方式 |
| --- | --- | --- |
| 工具太少 | agent 只能猜，不能验证 | 提供测试、lint、构建脚本 |
| 权限太大 | agent 改敏感文件或跑危险命令 | 分级权限和禁止清单 |
| 验证太慢 | agent 不愿运行测试 | 提供模块级快速验证 |
| 任务太大 | agent 半途耗尽上下文 | 拆分任务和进度文件 |
| 状态丢失 | 下一轮不知道做过什么 | 使用进度文件和 Git 检查点 |
| 过早完成 | agent 看到部分功能就宣称完成 | 使用明确任务清单和验收项 |

## 6.9 CI 等价命令清单

Harness 的一个重要目标，是让本地验证和 CI 尽量一致。移动端项目的 CI 往往很复杂，但可以为 agent 提供“CI 等价命令清单”。

示例：

```text
docs/ai-coding/ci-equivalent.md

Android:
- ./gradlew testDebugUnitTest
- ./gradlew ktlintCheck
- ./gradlew assembleDebug

iOS:
- xcodebuild test -scheme App -destination 'platform=iOS Simulator,name=iPhone 16'
- swiftlint

Flutter:
- flutter analyze
- flutter test

React Native:
- yarn typecheck
- yarn test
- cd ios && pod install --repo-update  # 仅人工确认后执行
```

清单中应标注命令成本和风险：

| 命令 | 成本 | 是否允许 agent 自动运行 |
| --- | --- | --- |
| 单元测试 | 低 | 是 |
| lint | 低 | 是 |
| debug build | 中 | 可按任务运行 |
| pod install | 中 | 需要确认 |
| release build | 高 | 默认禁止 |
| 上传商店 | 高 | 禁止 |

这样 agent 不会为了省事只跑最轻的测试，也不会误触发发布流程。

## 6.10 Harness 与开发者体验

Harness 如果太重，团队不会用。一个实用的 harness 应该满足：

- 命令少而稳定。
- 输出清楚。
- 失败时能指向下一步。
- 不依赖个人机器秘密状态。
- 能在 CI 中复跑。

例如，与其要求 agent 记住十条 Gradle 命令，不如提供一个脚本：

```bash
./scripts/check_mobile_change.sh --module profile
```

脚本内部可以运行对应 lint、单测和轻量构建。对 agent 和人类来说，入口都更简单。移动端项目中，构建链路本身已经够复杂，harness 应该降低复杂度，而不是制造新的复杂度。

## 6.11 Harness 的演进路线

团队可以按三步建设 harness：

第一步，文档化。写清项目地图、命令、高风险文件和任务模板。

第二步，脚本化。把常用验证、敏感文件检查、格式化和测试选择封装成脚本。

第三步，平台化。通过 MCP、hooks、CI、Issue 模板和内部工具，把上下文、权限和验证接入统一流程。

不要跳过前两步。没有文档和脚本，直接平台化会把混乱自动化。好的 harness 往往从几个稳定脚本开始，而不是从宏大的平台设计开始。

## 本章小结

Harness Engineering 是 AI coding 从个人玩具走向团队能力的关键。它让 agent 的能力进入可控边界：知道能看什么、能改什么、能跑什么、怎么验证、什么时候停。下一章会进一步讨论如何把这些能力组织成反馈循环。
