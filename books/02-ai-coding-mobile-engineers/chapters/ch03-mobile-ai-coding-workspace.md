# 第 3 章 移动端 AI Coding 工作区

## 本章导读

同一个 agent，在不同仓库里的表现差异会非常大。干净的目录、明确的脚本、稳定的测试和清晰的约束，会让 agent 更容易完成任务；混乱的构建方式、缺失的 README、隐式环境变量和没有测试的模块，会让 agent 很快迷失。

移动端项目尤其需要工作区整理。服务端项目通常可以用一个命令启动、一个命令测试；移动端项目却经常同时包含 Xcode、Gradle、CocoaPods、Swift Package、Kotlin、Flutter、React Native、Node、Ruby、证书、模拟器、真机和 CI 配置。人类开发者可以靠经验记住这些隐式规则，agent 不能。它需要显式、结构化、可执行的工作区说明。

## 学习目标

- 建立适合 AI coding 的移动端工作区结构。
- 知道哪些信息应该写入 README、AGENTS.md、脚本和测试。
- 理解本地环境、CI 环境和云端 agent 环境的差异。
- 能够为 iOS、Android、Flutter、React Native 项目设计最小可用 AI coding harness。

## 3.1 为什么工作区比提示词更重要

很多团队第一次使用 AI coding 工具时，会把注意力放在提示词模板上。例如“你是资深 iOS 工程师，请帮我修复 bug”。这当然有用，但如果仓库里没有构建说明、测试脚本、架构边界和敏感文件规则，再好的 Prompt 也只能让 agent 更自信地猜。

一个好的工作区会把隐式经验变成显式信息：

- 如何安装依赖。
- 如何运行最小测试。
- 哪些目录是核心业务。
- 哪些文件不能修改。
- 哪些命令需要人工确认。
- 什么样的输出才算完成。

这些信息一旦写清楚，不只 agent 受益，新同事也受益，CI 和文档也更容易维护。

## 3.2 工作区组成

适合 AI coding 的移动端仓库至少应该包含六类信息。

| 类型 | 建议文件 | 作用 |
| --- | --- | --- |
| 项目入口 | `README.md` | 打开工程、安装依赖、运行主流程 |
| Agent 规则 | `AGENTS.md` 或工具专用规则文件 | 给 agent 的任务边界、命令和禁止事项 |
| 脚本入口 | `scripts/` | 把复杂命令封装成稳定接口 |
| 架构说明 | `docs/architecture.md` | 模块边界、依赖方向、平台差异 |
| 验证清单 | `docs/release-checklist.md` | 构建、测试、隐私、权限、发版检查 |
| Playbook | `docs/ai-coding-playbooks.md` | 常见任务的 agent 委托流程 |

目录示例：

```text
mobile-app/
  AGENTS.md
  README.md
  scripts/
    test_unit.sh
    lint.sh
    build_debug.sh
    check_privacy.sh
  ios/
  android/
  packages/
  docs/
    architecture.md
    release-checklist.md
    ai-coding-playbooks.md
    module-map.md
```

## 3.3 README：给人和 Agent 的入口

README 不应该只写项目介绍，而应该写最短可执行路径。对 AI coding 来说，README 中最有价值的是命令和边界。

一个移动端 README 至少应该回答：

- 这个仓库包含哪些平台和模块？
- 本地开发需要哪些工具版本？
- 如何安装依赖？
- 如何运行最小构建？
- 如何运行最快的测试？
- 如何只测试某个模块？
- 如何生成代码或资源？
- 哪些命令会修改大量文件？
- 哪些配置不能提交？

示例：

````markdown
## 本地验证

运行网络层单元测试：

```bash
./scripts/test_unit.sh NetworkTests
```

运行本地化检查：

```bash
./scripts/check_localization.sh
```

不要直接运行 Release 打包脚本；发布构建只能由 CI 执行。
````

这些说明可以显著减少 agent 的试错成本。agent 不需要猜 `xcodebuild` 参数，也不需要自己拼 Gradle 命令，而是调用团队认可的脚本。

## 3.4 AGENTS.md：把团队规则写给 Agent

`AGENTS.md` 是面向 agent 的规则文件。它不应该写成口号，而应该写成可执行约束。

差的写法：

```text
请保持代码质量，注意安全，写出优雅代码。
```

更好的写法：

```text
## 修改边界

- 不要修改 `ios/Signing/`、`android/keystore.properties`、`.env`。
- 不要新增第三方依赖，除非任务明确要求并说明原因。
- UI 文案变更必须同步更新 `Localizable.strings` 或 Android string resources。
- 修改网络层必须运行 `./scripts/test_unit.sh NetworkTests`。
- 修改权限配置必须在最终摘要中标记“需要人工确认”。

## 输出要求

- 列出修改文件。
- 列出运行过的命令和结果。
- 标记没有验证的部分。
```

这类规则比“请小心”更有效，因为它能直接影响 agent 的计划、文件选择和最终报告。

## 3.5 脚本：给 Agent 一个稳定接口

移动端命令往往复杂。与其让 agent 拼长命令，不如提供脚本：

```bash
./scripts/test_unit.sh LoginTests
./scripts/lint.sh
./scripts/build_debug.sh ios
./scripts/build_debug.sh android
./scripts/check_privacy.sh
```

脚本的价值有三点：

1. 稳定：命令变化时只改脚本，不需要更新所有 Prompt。
2. 安全：脚本内部可以限制危险参数。
3. 可审计：agent 运行了什么命令，日志更清楚。

对移动端团队来说，建议至少提供：

- 单元测试脚本。
- 静态检查脚本。
- Debug 构建脚本。
- 本地化检查脚本。
- 权限/隐私检查脚本。
- 依赖变更检查脚本。

## 3.6 架构文档：减少 Agent 误改

Agent 最容易犯的工程错误之一，是破坏依赖方向。例如把 UI 层逻辑写进网络层，把平台逻辑写进共享层，把业务状态放进工具模块。

架构文档不需要长，但要明确：

- 模块列表。
- 依赖方向。
- 重要接口。
- 不允许跨越的边界。
- 平台差异。
- 常见扩展位置。

示例：

```text
网络层依赖方向：

UI -> ViewModel -> Repository -> ApiClient -> NetworkSession

禁止：
- UI 直接调用 NetworkSession。
- ApiClient 依赖 UI 文案。
- Repository 读取平台权限状态。
```

这类架构说明会直接影响 agent 的修改路径。

## 3.7 本地环境、CI 环境与云端 Agent 环境

移动端 AI coding 要区分三种环境。

| 环境 | 能做什么 | 不能假设什么 |
| --- | --- | --- |
| 本地环境 | 访问模拟器、真机、私有缓存、本地证书 | 不应暴露密钥给 agent |
| CI 环境 | 稳定运行构建、测试、lint、产物检查 | 不能做交互式调试 |
| 云端 agent 环境 | 并行处理任务、生成 PR、隔离运行 | 不一定有 Xcode、模拟器、私有依赖 |

如果 agent 在云端完成了代码修改，本地仍可能需要做真机验证。如果 agent 在本地运行了测试，CI 仍需要复跑，保证没有依赖个人机器状态。

## 3.8 敏感文件与危险命令

移动端仓库中常见敏感文件包括：

- `.env`、`.env.local`。
- iOS 证书、profile、签名配置。
- Android keystore 和密码文件。
- 内部 API 域名和 token。
- 崩溃日志中的用户信息。
- 发布脚本和上传脚本。

危险命令包括：

- 删除大量文件。
- 重置 Git 历史。
- 修改远端分支。
- 上传产物。
- 触发生产发布。
- 打印环境变量。

这些内容应该写进 `.gitignore`、`AGENTS.md` 和工具权限配置中。agent 可以读取规则，但不能凭自觉保护你的仓库。

## 3.9 工作区成熟度自检

可以用下面的清单评估一个移动端仓库是否适合引入 agentic coding。

| 检查项 | 达标标准 |
| --- | --- |
| 入口说明 | 新人和 agent 都能根据 README 跑起最小验证 |
| 脚本封装 | 常用测试和构建有稳定脚本 |
| 架构说明 | 核心模块和依赖方向写清楚 |
| 禁止事项 | 敏感文件和危险命令明确列出 |
| 测试入口 | 至少有模块级快速测试 |
| 任务模板 | bug 修复、重构、测试补充有标准流程 |
| 审查要求 | agent 输出必须包含修改、验证和风险 |

如果这些都没有准备好，建议先不要让 agent 大范围改代码。可以从只读分析、文档整理和测试补充开始。

## 3.10 把 AGENTS.md 写成工程契约

`AGENTS.md` 不应该只是几句礼貌提示。它应该像工程契约一样，告诉 agent 如何在仓库中工作。

建议包含：

- 项目类型：iOS、Android、Flutter、React Native 或混合项目。
- 常用命令：测试、lint、构建、格式化。
- 禁止命令：删除、强推、发布、打印环境变量。
- 高风险文件：签名、权限、依赖、发布配置。
- 输出要求：每轮说明修改、验证和风险。
- 失败处理：最多尝试几轮，什么时候停止并请求人工确认。

示例：

```text
本仓库是 Android + Flutter 混合项目。

允许：
- 修改 lib/、app/src/main/、app/src/test/ 中与任务相关的文件。
- 运行 flutter test、./gradlew testDebugUnitTest。

禁止：
- 修改 keystore、signing、release、gradle.properties。
- 执行 git reset --hard、git push --force、release 脚本。
- 打印环境变量或读取 .env.local。

输出：
- 修改文件列表。
- 执行过的命令和结果。
- 未验证项。
- 需要人工确认的风险。
```

这类规则越具体，agent 越容易遵守。模糊的“注意安全”没有工程价值。

## 3.11 为移动端准备快速验证入口

很多移动端项目验证很慢。完整 iOS 构建可能需要数分钟，Android 多 flavor 测试可能更久，React Native 还可能受到包管理和缓存影响。如果没有快速验证入口，agent 往往会跳过测试，或者只运行最方便但不相关的命令。

建议为每类任务准备快速命令：

| 任务 | 快速验证 |
| --- | --- |
| ViewModel 修改 | 对应单元测试 |
| 网络 mapper 修改 | mapper 测试 + 少量 repository 测试 |
| UI 组件拆分 | snapshot/widget/Compose test |
| 本地化修改 | key 检查脚本 |
| 依赖修改 | 最小 debug build |
| 权限修改 | 配置检查 + 人工确认 |

这些命令应写进 README 或 `docs/ai-coding/commands.md`。Agent 不应该猜测试命令，团队也不应该每次人工重复解释。

## 3.12 工作区反模式

不适合 agent 的工作区通常有几个特征：

- README 过期，命令跑不通。
- 测试依赖个人机器状态。
- 构建脚本会读取真实生产凭据。
- 高风险文件没有清单。
- 模块边界只存在于老同事脑子里。
- CI 和本地命令不一致。
- 文档没有日期，无法判断是否过期。

这些问题对人类工程师也不好，但 agent 会把它们放大。人类遇到不确定性会停下来问同事，agent 可能会根据局部信息继续修改。因此，引入 AI coding 前整理工作区，本质上也是在提升团队基础工程质量。

## 本章小结

AI coding 的第一项工程准备不是选择工具，而是整理工作区。一个对人类清楚、对脚本友好、对权限敏感的仓库，通常也更容易被 agent 正确理解。移动端团队应该把 README、AGENTS.md、脚本、架构文档和验证清单看作 AI coding harness 的一部分，而不是附属文档。
