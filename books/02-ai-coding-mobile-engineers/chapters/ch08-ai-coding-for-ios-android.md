# 第 8 章 iOS 与 Android 项目的 AI Coding 方法

## 本章导读

iOS 和 Android 项目都有完整的工程体系：构建工具、平台 SDK、权限模型、生命周期、UI 框架、测试工具和发布流程。AI coding 必须尊重这些平台边界。

## 学习目标

- 掌握 iOS/Android 项目中适合交给 agent 的任务类型。
- 知道哪些文件和操作需要人工确认。
- 学会把平台特定验证写入任务模板。

## iOS 任务模式

适合 agent 的任务：

- ViewModel 逻辑修复。
- 单元测试补充。
- SwiftUI 组件拆分。
- 网络错误映射。
- 本地化文案同步检查。

需要谨慎的任务：

- 签名、证书、entitlements。
- Info.plist 权限说明。
- App Store 隐私声明。
- Core Data migration。
- 大范围 UI 重构。

## Android 任务模式

适合 agent 的任务：

- Kotlin 协程错误处理。
- ViewModel 状态流整理。
- Retrofit/OkHttp 封装。
- Compose 组件拆分。
- 单元测试和 Robolectric 测试补充。

需要谨慎的任务：

- keystore 和签名配置。
- Manifest 权限和 exported 配置。
- ProGuard/R8 规则。
- Gradle 插件和 Kotlin 版本升级。
- 后台任务和电量策略。

## 本章小结

平台越成熟，隐性规则越多。AI coding 在 iOS/Android 项目中要强调最小改动、平台验证和高风险文件保护。
