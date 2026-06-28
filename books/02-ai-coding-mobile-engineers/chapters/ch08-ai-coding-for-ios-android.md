# 第 8 章 iOS 与 Android 项目的 AI Coding 方法

## 本章导读

iOS 和 Android 项目都有完整的工程体系：构建工具、平台 SDK、权限模型、生命周期、UI 框架、测试工具和发布流程。AI coding 在这些项目中不是“会写 Swift 或 Kotlin 就可以”，而是要尊重平台边界、工程约束和团队发版规则。

移动端项目的一个特点是：许多问题无法只靠静态阅读代码判断。例如一个 SwiftUI 状态更新是否导致页面闪烁，一个 Android 后台任务是否受系统电量策略影响，一个权限说明是否会影响商店审核，这些都需要平台经验和真实验证。因此，本章讨论的重点不是让 agent 替代移动端工程师，而是让它在移动端工程体系中承担合适的任务，并把风险控制在可审查、可回滚的范围内。

## 学习目标

- 掌握 iOS/Android 项目中适合交给 agent 的任务类型。
- 知道哪些文件和操作需要人工确认。
- 学会把平台特定验证写入任务模板。
- 能够为移动端仓库设计一份“agent 可做/不可做”边界表。

## 移动端项目中的任务分层

把 AI coding 引入移动端项目时，首先要做任务分层。不要一上来就要求 agent “重构整个首页”或“升级所有依赖”。更稳妥的做法是把任务分成四类：

| 任务类型 | 适合程度 | 示例 | 验证方式 |
| --- | --- | --- | --- |
| 局部逻辑修改 | 高 | ViewModel 状态修复、错误码映射、表单校验 | 单元测试、局部 UI 测试 |
| 重复性工程任务 | 高 | 本地化 key 补齐、测试样板生成、接口模型整理 | 静态检查、快照测试 |
| 跨文件小重构 | 中 | 拆分组件、抽取 mapper、迁移两个调用方 | 分批测试、人工审查 |
| 平台敏感改动 | 低 | 签名、权限、证书、发布配置、数据库迁移 | 必须人工确认 |

这张表背后的原则很简单：越靠近业务核心、用户隐私、支付登录、发布签名和平台审核，越不能让 agent 自动决定。越是局部、重复、可测试、可回滚的任务，越适合交给 agent。

## iOS 任务模式

iOS 项目的技术栈通常包含 Swift/Objective-C、UIKit/SwiftUI、Combine 或 async/await、Xcode 工程配置、Info.plist、entitlements、签名证书、单元测试和 UI 测试。Agent 需要理解这些上下文，但不应该默认拥有所有改动权限。

适合 agent 的 iOS 任务包括：

- ViewModel 逻辑修复。
- SwiftUI 组件拆分和状态绑定整理。
- UIKit ViewController 中重复逻辑抽取。
- 网络错误映射和本地化文案同步。
- 单元测试补充。
- Snapshot 测试或 Preview 数据整理。
- 简单 SwiftLint 违规修复。

需要谨慎的任务包括：

- 修改签名、证书和 provisioning profile。
- 修改 entitlements。
- 修改 Info.plist 权限说明。
- Core Data migration。
- Keychain、支付、登录、风控相关逻辑。
- 大范围 UI 重构。
- 影响 App Store 隐私声明的改动。

### iOS Prompt 模板

下面是一份适合 iOS 小范围修复任务的 prompt 模板。它不是为了写得漂亮，而是为了让 agent 拿到足够边界。

```text
你是 iOS 项目的 AI coding 助手。请修复 ProfileViewModel 中弱网错误提示不准确的问题。

上下文：
- 项目使用 Swift、SwiftUI、async/await。
- 错误模型在 Sources/AppCore/Network/AppError.swift。
- Profile 页面入口在 Sources/Profile/ProfileView.swift。
- 现有测试在 Tests/ProfileTests/ProfileViewModelTests.swift。

约束：
- 只允许修改 Profile 模块、AppError 映射和对应测试。
- 不允许修改 Info.plist、entitlements、签名、构建配置和依赖版本。
- 不允许改变登录、支付和用户数据上报逻辑。
- 先解释问题和修复计划，再修改代码。

验收：
- 新增或修改单元测试覆盖 timeout、offline、serverError 三类错误。
- 运行 `xcodebuild test` 或项目已有等价测试命令。
- 输出修改文件列表、测试结果和仍需人工确认的问题。
```

这个模板体现了四个要点：范围、禁止事项、测试命令和交付格式。移动端工程师应该把这些内容写进团队 playbook，而不是每次临时补充。

### iOS 代码审查重点

Agent 生成 iOS 代码后，人工审查要重点看下面几类问题：

- 生命周期：是否在 `viewDidLoad`、`onAppear`、`task` 或 `deinit` 中引入重复请求或未取消任务。
- 并发：是否正确处理 `Task` 取消、主线程更新和 actor 隔离。
- UI 状态：loading、empty、error、success 状态是否互斥，是否存在闪烁。
- 本地化：新增文案是否进入 strings 文件，是否硬编码。
- 无障碍：按钮、图片、动态文本是否保留 accessibility label。
- 隐私：日志、埋点和错误上报是否带出用户敏感信息。

这些问题有些可以通过测试发现，有些只能通过审查发现。AI coding 的价值在于减少重复劳动，不是取消审查。

## Android 任务模式

Android 项目的上下文通常包含 Kotlin/Java、Jetpack Compose 或 XML、ViewModel、Coroutine/Flow、Room、Retrofit/OkHttp、Gradle、多 flavor、多 ABI、Manifest、ProGuard/R8 和不同 Android 版本兼容性。

适合 agent 的 Android 任务包括：

- Kotlin 协程错误处理。
- ViewModel 状态流整理。
- Retrofit/OkHttp 封装。
- Compose 组件拆分。
- 单元测试和 Robolectric 测试补充。
- sealed class 错误模型整理。
- 简单 Detekt/Ktlint 问题修复。

需要谨慎的任务包括：

- keystore 和签名配置。
- Manifest 权限和 exported 配置。
- ProGuard/R8 规则。
- Gradle 插件、AGP、Kotlin 版本升级。
- 后台任务、电量策略和通知权限。
- 支付、登录、风控、加密存储。

### Android Prompt 模板

```text
你是 Android 项目的 AI coding 助手。请修复 OrderViewModel 在接口超时时仍显示“未知错误”的问题。

上下文：
- 项目使用 Kotlin、Coroutine、StateFlow、Jetpack Compose。
- 错误模型在 app/src/main/java/.../network/AppError.kt。
- 页面状态在 app/src/main/java/.../order/OrderUiState.kt。
- 测试在 app/src/test/java/.../order/OrderViewModelTest.kt。

约束：
- 只允许修改订单模块、网络错误映射和测试。
- 不允许修改 AndroidManifest.xml、签名配置、Gradle 版本和 ProGuard/R8 规则。
- 不允许引入新依赖。
- 修改前先列出修复计划。

验收：
- 为 timeout、offline、http 5xx 增加测试。
- 运行 `./gradlew testDebugUnitTest`。
- 输出测试结果、修改文件和潜在风险。
```

Android 的 prompt 要特别强调构建变体和命令。很多仓库的默认 `./gradlew test` 并不能覆盖目标 variant，agent 如果不知道项目约定，容易跑了错误的测试命令。

## 高风险文件保护

移动端仓库中有一批文件应默认进入高风险清单。Agent 可以阅读它们，但不能在没有人工确认的情况下修改。

| 平台 | 高风险文件或目录 | 风险 |
| --- | --- | --- |
| iOS | `.xcodeproj`、`.xcworkspace`、`project.pbxproj` | 工程结构和构建配置易被破坏 |
| iOS | `Info.plist`、entitlements | 权限、审核、系统能力 |
| iOS | signing、profile、证书脚本 | 发布安全 |
| Android | `AndroidManifest.xml` | 权限、组件暴露、深链 |
| Android | `build.gradle`、version catalog | 依赖、插件、构建链路 |
| Android | ProGuard/R8 规则 | 混淆、反射、线上崩溃 |
| 通用 | `.env`、证书、keystore、配置中心 | 密钥和生产配置 |

团队可以把这张清单固化到 harness 中。例如在提交前检查 staged files，如果命中高风险文件，就要求 agent 输出原因，并把 PR 标记为“需要平台负责人确认”。

## 平台验证清单

移动端 AI coding 的验收不能只写“测试通过”。更好的验收清单应该包含平台特定项：

- 是否运行了目标模块的单元测试。
- 是否运行了至少一个 UI 或快照测试。
- 是否检查了暗黑模式、本地化、动态字体或屏幕尺寸。
- 是否确认没有修改签名、权限、发布配置。
- 是否确认日志和埋点没有泄露用户数据。
- 是否说明了未覆盖的设备和系统版本。

如果任务涉及网络、权限、后台任务、推送或相机相册等系统能力，还要补充真机验证说明。模拟器和单元测试不能覆盖全部平台行为。

## 一个完整的 iOS 小任务示例

假设需求是“设置页保存昵称失败时，应该显示服务端返回的业务错误文案，而不是统一显示保存失败”。合理的 agent 流程如下：

1. 阅读 `SettingsViewModel`、`ProfileRepository`、错误模型和现有测试。
2. 输出问题假设：业务错误码被映射成通用错误。
3. 新增失败测试：当 repository 返回 `nickname_too_long` 时，UI 状态应显示指定文案。
4. 修改 mapper 或 ViewModel，保持外部接口不变。
5. 运行测试。
6. 输出修改说明和人工审查点。

注意，这里没有要求 agent 顺手重构整个设置页，也没有要求它调整接口协议。任务越小，成功率越高，审查成本越低。

## 一个完整的 Android 小任务示例

假设需求是“商品详情页在弱网下会一直 loading”。合理流程如下：

1. 阅读 `ProductDetailViewModel`、repository、network client 和测试。
2. 确认 loading 状态是否在异常路径退出。
3. 增加 coroutine test，模拟 timeout。
4. 修复状态机，让 timeout 后进入 error 状态。
5. 检查 Compose 页面是否正确显示重试按钮。
6. 运行 `testDebugUnitTest`。

这类任务特别适合 agent，因为它有明确的失败路径和可写测试。但如果修复方案要求升级 OkHttp、调整全局拦截器或修改所有网络层调用，就应该拆成后续任务。

## 本章小结

平台越成熟，隐性规则越多。AI coding 在 iOS/Android 项目中要强调最小改动、平台验证和高风险文件保护。移动端工程师使用 agent 的成熟标志，不是让它一次改很多文件，而是能把任务拆成平台边界清晰、测试信号明确、人工审查可控的小循环。
