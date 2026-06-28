# 第 9 章 Flutter 与 React Native 的跨端协作

## 本章导读

跨端项目让 AI coding 更有价值，也更容易犯错。一个改动可能同时影响 Dart/TypeScript、原生桥接、构建配置和两个平台的运行时行为。

## 学习目标

- 理解跨端项目的上下文组织方式。
- 掌握 Flutter/RN 中适合 agent 的任务类型。
- 知道跨端验证不能只看一个平台。

## Flutter 场景

Flutter 中适合 agent 处理：

- Widget 拆分和状态提升。
- Form 校验逻辑。
- Riverpod/Bloc 状态整理。
- 单元测试和 widget test。
- 平台通道调用参数检查。

风险点：

- iOS/Android 原生配置不一致。
- 资源和字体声明遗漏。
- 构建 flavor 差异。
- 平台通道异常没有统一兜底。

## React Native 场景

React Native 中适合 agent 处理：

- 组件拆分。
- TypeScript 类型补齐。
- hooks 依赖修复。
- 网络状态和错误状态整理。
- Jest 测试补充。

风险点：

- Native Module bridge。
- Hermes/JSC 差异。
- Metro 缓存和包管理。
- iOS pod 与 Android Gradle 同步。

## 本章小结

跨端 AI coding 的关键是双平台验证。一个 agent 任务的验收条件必须写清楚至少在哪些平台、哪些命令和哪些页面上验证。
