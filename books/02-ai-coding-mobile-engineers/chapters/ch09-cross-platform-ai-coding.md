# 第 9 章 Flutter 与 React Native 的跨端协作

## 本章导读

跨端项目让 AI coding 更有价值，也更容易犯错。一个改动可能同时影响 Dart/TypeScript、原生桥接、构建配置和两个平台的运行时行为。对于 Flutter 和 React Native 项目，agent 不能只看跨端层代码，还要理解 iOS/Android 原生目录、平台通道、包管理、资源声明和发布链路。

跨端项目经常出现一种误用：让 agent 在 macOS 上修改了 Dart 或 TypeScript 代码，运行了一个快速测试，然后就认为 iOS 和 Android 都没问题。实际情况往往不是这样。字体、权限、平台通道、原生模块、构建 flavor、Hermes/JSC、Gradle、Pods 都可能让一个看似简单的改动在另一端失败。

## 学习目标

- 理解跨端项目的上下文组织方式。
- 掌握 Flutter/RN 中适合 agent 的任务类型。
- 知道跨端验证不能只看一个平台。
- 能够设计一份双平台验收 prompt。

## 跨端项目的上下文地图

跨端项目至少有四层上下文：

| 层次 | Flutter 示例 | React Native 示例 | Agent 需要知道什么 |
| --- | --- | --- | --- |
| 业务 UI 层 | `lib/features/...` | `src/features/...` | 页面、状态、组件边界 |
| 跨端运行时 | Dart、pubspec | TS/JS、Metro、package.json | 包管理、测试命令、运行约束 |
| 原生桥接层 | MethodChannel、Pigeon | Native Module、TurboModule | 参数协议、错误处理、线程模型 |
| 平台工程层 | `ios/`、`android/` | `ios/`、`android/` | 权限、构建、资源、签名 |

Agent 在执行任务前，应该先判断任务涉及哪几层。如果只是拆分一个纯 UI 组件，可能只需要业务 UI 层和测试层。如果涉及相册、定位、推送或支付，就必须纳入原生桥接层和平台工程层。

## Flutter 场景

Flutter 中适合 agent 处理的任务包括：

- Widget 拆分和状态提升。
- Form 校验逻辑。
- Riverpod、Bloc、Provider 状态整理。
- 单元测试和 widget test。
- 平台通道调用参数检查。
- 本地化 ARB key 补齐。
- 简单 theme、spacing、design token 同步。

风险点包括：

- iOS/Android 原生配置不一致。
- 资源、字体、图片声明遗漏。
- build flavor 差异。
- 平台通道异常没有统一兜底。
- Widget test 过度依赖实现细节。
- 异步状态导致测试偶发失败。

### Flutter Prompt 模板

```text
你是 Flutter 项目的 AI coding 助手。请把 LoginForm 中的邮箱和密码校验逻辑抽取为可测试的 validator。

上下文：
- UI 在 lib/features/login/login_form.dart。
- 状态管理使用 Riverpod。
- 本地化文案在 lib/l10n/app_zh.arb 和 app_en.arb。
- 现有测试在 test/features/login/。

约束：
- 不修改 ios/ 和 android/ 目录。
- 不新增依赖。
- 不改变页面外部行为和路由。
- 每次只做一个小重构步骤。

验收：
- validator 有单元测试。
- LoginForm widget test 仍通过。
- 运行 `flutter test`。
- 如果未运行 iOS/Android 真机验证，需要明确说明。
```

这个任务适合 agent，因为边界清晰、可测试、风险低。相反，如果任务是“接入相机权限并上传照片”，就不能只让 agent 改 Dart 层。它必须检查 iOS `Info.plist`、Android Manifest、权限文案、平台差异和失败兜底。

### Flutter 平台通道审查

当 agent 修改 MethodChannel 或 Pigeon 接口时，审查重点包括：

- 参数名称和类型是否与原生端一致。
- 错误码是否可枚举，是否有 unknown 兜底。
- iOS/Android 是否都实现了同一协议。
- 是否处理权限拒绝、系统不可用和用户取消。
- 是否有超时或取消机制。
- 是否更新了调用方测试。

平台通道是跨端项目中最容易“单边成功”的地方。Dart 层编译通过，不代表 Android 原生方法存在；iOS 跑通，不代表 Android 权限声明正确。

## React Native 场景

React Native 中适合 agent 处理的任务包括：

- 组件拆分。
- TypeScript 类型补齐。
- hooks 依赖修复。
- 网络状态和错误状态整理。
- Jest 测试补充。
- 简单样式 token 统一。
- 文案和 i18n key 检查。

风险点包括：

- Native Module bridge。
- Hermes/JSC 差异。
- Metro 缓存和包管理。
- iOS Pods 与 Android Gradle 同步。
- 新架构开关、Fabric、TurboModule 差异。
- 原生依赖升级引发构建问题。

### React Native Prompt 模板

```text
你是 React Native 项目的 AI coding 助手。请修复 CheckoutButton 在重复点击时会触发多次提交的问题。

上下文：
- 组件在 src/features/checkout/CheckoutButton.tsx。
- 请求逻辑在 src/features/checkout/useSubmitOrder.ts。
- 测试在 src/features/checkout/__tests__/。
- 项目使用 TypeScript、Jest、React Native Testing Library。

约束：
- 不修改 ios/、android/、Podfile、Gradle 和 package manager lockfile。
- 不新增依赖。
- 不改变埋点字段。
- 修改前先说明状态机。

验收：
- 添加重复点击测试。
- 运行 `yarn test CheckoutButton` 或项目等价命令。
- 输出没有执行的 iOS/Android 验证项。
```

React Native 项目中，TypeScript 类型和测试很适合 agent 发挥。但当修改进入原生目录时，必须切换到更严格的 harness：限制命令、记录环境、要求双平台构建结果。

## 双平台验收不能省

跨端任务至少要明确三类验证：

| 验证类型 | 目的 | 示例 |
| --- | --- | --- |
| 快速测试 | 证明核心逻辑正确 | `flutter test`、`yarn test` |
| 平台构建 | 证明原生工程没有坏 | iOS build、Android assemble |
| 关键路径运行 | 证明用户路径可用 | 登录、支付、上传、权限弹窗 |

不是每个任务都必须在每轮跑完整双平台构建，但 prompt 必须要求 agent 说明“哪些验证已执行，哪些没有执行”。这比假装全部验证过更重要。

## 跨端 AI Coding 的上下文包

建议为跨端仓库准备一个上下文包，放在 `docs/ai-coding/` 或类似目录中：

```text
docs/ai-coding/
  project-map.md
  flutter-testing.md
  react-native-testing.md
  platform-bridge-rules.md
  high-risk-files.md
  release-checklist.md
```

其中 `platform-bridge-rules.md` 应该说明：

- 哪些接口必须 iOS/Android 同步修改。
- 错误码如何命名。
- 用户取消、权限拒绝、系统不可用如何表达。
- 是否允许跨端层直接拼接平台错误文案。
- 修改桥接后必须运行哪些测试。

这些上下文越清楚，agent 越不容易在错误范围内发挥。

## 常见失败模式

跨端 AI coding 常见失败包括：

- 只修改跨端层，忘记原生桥接。
- 只跑一个平台，另一个平台构建失败。
- 修复测试时改坏真实行为。
- 引入新依赖但没有更新 lockfile 或 Pods。
- 文案只补中文，遗漏英文或其他语言。
- 忽略平台权限和商店审核要求。
- 把缓存问题误判为代码问题。

这些失败通常不是模型“不会写代码”，而是任务上下文不完整、验收条件不清楚、harness 没有覆盖跨端差异。

## 跨端案例：相册选择能力接入

相册选择是跨端项目中典型的高风险任务。它看起来只是“选择图片并返回 URI”，实际涉及权限、系统 API、平台差异、用户取消、文件大小、隐私文案和上传链路。

正确的 agent 工作流应拆成三轮。

第一轮，只读分析：

```text
请分析当前项目是否已有相册或文件选择能力。
不要修改代码。
输出：
- Flutter/RN 调用入口。
- iOS 原生实现位置。
- Android 原生实现位置。
- 当前权限声明。
- 已有测试。
- 需要人工确认的隐私文案。
```

第二轮，协议设计：

```text
请设计跨端返回结构，不要实现。
要求包含：
- success。
- userCancelled。
- permissionDenied。
- fileTooLarge。
- unknown。
说明 iOS/Android 如何映射。
```

第三轮，受限实现：

```text
只实现跨端层和 mock 测试。
不要修改 Info.plist、AndroidManifest.xml 和原生权限文件。
如果发现必须修改权限文件，请停止并输出原因。
```

这个流程看似慢，但它把权限和平台差异提前暴露出来。跨端项目最怕 agent 直接改完 Dart/TypeScript 层，然后在原生端留下隐性缺口。

## 跨端桥接协议表

建议为每个平台通道维护协议表：

| 字段 | 类型 | iOS 来源 | Android 来源 | 备注 |
| --- | --- | --- | --- | --- |
| `status` | string | enum 映射 | sealed class 映射 | success/cancel/denied/error |
| `uri` | string? | file URL | content URI | 不直接暴露真实本地路径 |
| `errorCode` | string? | NSError code | Exception code | 需要统一枚举 |
| `messageKey` | string? | 本地化 key | 本地化 key | 跨端层不拼接最终文案 |

协议表的价值是让 agent 有明确目标。否则它可能在 iOS 返回 `path`，在 Android 返回 `uri`，跨端层再做大量兼容判断，最终形成新的技术债。

## Flutter 与 React Native 的测试差异

Flutter 和 React Native 的测试工具不同，agent 任务中要写清楚：

| 项目 | Flutter | React Native |
| --- | --- | --- |
| 单元测试 | `flutter test` | `yarn test` 或 `npm test` |
| UI 测试 | widget test | React Native Testing Library |
| 静态检查 | `flutter analyze` | TypeScript、ESLint |
| 原生构建 | Xcode/Gradle | Pods/Gradle/Metro |
| 常见缓存问题 | pub、build cache | Metro、Pods、node_modules |

如果任务只涉及纯逻辑，快速测试足够。如果涉及原生模块，必须记录是否执行了原生构建。Agent 输出中要明确：“本轮只运行了 JS/Dart 测试，未验证 iOS/Android 原生构建。”这不是缺点，而是诚实的工程记录。

## 跨端发版前检查

跨端项目发版前可以让 agent 做只读检查：

- 查找本轮是否修改 `ios/` 或 `android/`。
- 查找是否新增权限。
- 查找是否新增依赖和 lockfile 变化。
- 查找是否有平台特定代码只覆盖一端。
- 检查本地化 key 是否双端一致。
- 汇总未运行的验证。

这类任务适合 agent，因为它以搜索、归纳和清单输出为主，不需要自动修改高风险文件。

## 本章小结

跨端 AI coding 的关键是双平台验证和上下文分层。Flutter 与 React Native 项目可以让 agent 高效处理 UI、状态、类型和测试，但原生桥接、权限、构建和发布配置必须提高审查级别。一个合格的跨端 prompt，不只说明“改什么”，还要说明“涉及哪些层、哪些平台必须验证、哪些文件不能自动改”。
