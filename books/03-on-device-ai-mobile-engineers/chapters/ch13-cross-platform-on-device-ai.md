# 第 13 章 跨平台端侧 AI 工程

## 本章导读

Flutter、React Native 和 Kotlin Multiplatform 等跨端技术会让端侧 AI 工程更复杂。跨平台框架可以复用 UI、业务逻辑和状态管理，但模型 runtime、硬件加速、权限、文件系统、后台任务、性能 profiling 和平台审核仍然需要分别处理。

端侧 AI 的跨平台工程不能简单理解为“封装一个统一 SDK”。真正可维护的方案，是把共享层和平台层的边界设计清楚：共享层负责任务协议、状态机、错误模型、评测和产品逻辑；平台层负责 runtime、模型加载、权限、硬件加速、资源管理和系统能力。

## 学习目标

- 理解跨平台端侧 AI 的分层。
- 设计共享层和平台层边界。
- 确保 iOS/Android 双平台验证。
- 能为 Flutter、React Native 或 KMP 项目设计端侧 AI 接入方案。

## 13.1 跨平台的真实边界

跨平台项目里，最容易犯的错误是把所有差异藏在一个抽象接口后面。例如定义一个 `runModel(input)`，然后希望 iOS 和 Android 都能一致工作。实际情况通常不是这样：

- iOS 和 Android 可用 runtime 不同。
- 硬件加速能力不同。
- 模型格式可能不同。
- 权限流程不同。
- 文件存储和备份策略不同。
- 后台任务限制不同。
- profiling 工具不同。
- 应用商店审核关注点不同。

因此，跨平台端侧 AI 的目标不是消灭差异，而是管理差异。共享层应定义稳定业务语义，平台层应暴露清楚的能力和限制。

## 13.2 推荐分层

建议使用四层：

```text
Product UI
  -> AiUseCase / StateMachine
  -> AiCapabilityBridge
  -> NativeRuntimeAdapter
```

其中：

| 层 | 责任 |
| --- | --- |
| Product UI | 展示入口、状态、结果、确认和降级 |
| AiUseCase / StateMachine | 定义任务流程、取消、重试、错误状态 |
| AiCapabilityBridge | 跨平台接口，暴露能力而非隐藏细节 |
| NativeRuntimeAdapter | iOS/Android 具体模型加载、推理、权限和资源管理 |

关键是 `AiCapabilityBridge` 不应只暴露一个“推理”方法，而应暴露能力查询：

```text
isAvailable(feature)
prepare(feature)
run(task)
cancel(taskId)
getDiagnostics()
```

这样共享层可以知道当前设备是否支持本地 OCR、是否需要下载模型、是否已授权麦克风、是否只能走云端兜底。

## 13.3 Flutter 项目接入

Flutter 项目通常用 MethodChannel、Pigeon 或 FFI 接入原生能力。端侧 AI 接入时要注意：

- 不要在 Dart UI isolate 中执行重任务。
- 大图片不要通过 channel 反复复制。
- 原生侧负责模型加载和资源释放。
- Dart 层负责状态机和 UI。
- 错误要转换成稳定的 Dart 枚举。

一个简化结构：

```text
lib/ai/
  ai_task.dart
  ai_state.dart
  ai_service.dart
ios/
  LocalAiRuntime.swift
android/
  LocalAiRuntime.kt
```

Flutter 层不应假设 iOS 和 Android 能力完全一致。可以通过 `getCapabilities()` 返回：

```json
{
  "localOcr": true,
  "localIntent": true,
  "localSpeechCommand": false,
  "requiresModelDownload": ["localOcr"]
}
```

UI 根据能力决定入口展示和降级。

## 13.4 React Native 项目接入

React Native 项目要特别注意 JS bridge 和原生模块边界。端侧 AI 任务可能处理大图片、音频或长文本，如果把大对象频繁穿过 bridge，会造成性能问题。

建议：

- 大文件用本地 URI 或句柄传递，不传 base64 大字符串。
- 原生模块负责图片解码、模型推理和临时文件清理。
- JS 层只拿结构化结果和状态。
- 长任务提供事件回调，例如 progress、cancelled、failed、done。
- TurboModule 或 JSI 接入要有明确生命周期管理。

错误模型应统一：

```typescript
type AiError =
  | { type: "permission_denied"; permission: string }
  | { type: "model_not_ready"; modelId: string }
  | { type: "device_unsupported"; reason: string }
  | { type: "timeout"; retryable: boolean }
  | { type: "native_failure"; code: string };
```

不要让 JS 层解析平台私有错误字符串。

## 13.5 Kotlin Multiplatform 项目接入

KMP 更适合共享业务逻辑、状态机、数据模型和测试。端侧 AI 中，KMP 可以共享：

- 任务协议。
- 错误模型。
- 路由策略。
- 本地索引规则。
- 评测样本解析。
- 端云协同状态机。

但 runtime 和系统能力仍然需要 expect/actual 或平台实现：

```kotlin
interface LocalAiRuntime {
    suspend fun capabilities(): AiCapabilities
    suspend fun run(task: AiTask): AiResult
    suspend fun cancel(taskId: String)
}
```

iOS actual 实现可以调用 Core ML 或原生 runtime，Android actual 实现可以调用对应 Android runtime。共享层只依赖接口和能力描述。

## 13.6 双平台一致性

跨平台端侧 AI 必须定义一致性边界。并不是所有输出都要完全一致，但业务语义要一致。

例如本地意图识别：

| 项目 | 一致性要求 |
| --- | --- |
| 支持命令列表 | 必须一致 |
| 错误枚举 | 必须一致 |
| 置信度分层 | 必须一致 |
| 模型格式 | 可不同 |
| 推理耗时 | 可不同，但都要满足预算 |
| 低端设备降级 | 可不同，但体验要清楚 |

如果 iOS 支持本地语音命令，而 Android 暂不支持，产品层应明确显示，而不是让 Android 用户点击后失败。

## 13.7 跨平台测试矩阵

测试矩阵至少包括：

| 测试 | iOS | Android |
| --- | --- | --- |
| 能力查询 | 主力设备、老系统 | 主力设备、低端设备 |
| 模型下载 | Wi-Fi、蜂窝、断点续传 | Wi-Fi、蜂窝、断点续传 |
| 本地推理 | 小输入、大输入 | 小输入、大输入 |
| 权限拒绝 | 麦克风、相册、文件 | 麦克风、相册、文件 |
| 生命周期 | 前后台、锁屏、来电 | 前后台、省电、进程回收 |
| 降级 | 模型失败、云端超时 | 模型失败、云端超时 |

跨平台项目常见问题是只在一个平台验证核心路径，另一个平台直到发版前才发现 runtime、权限或性能问题。

## 13.8 共享评测样本

为了保证双平台行为一致，建议把评测样本放在共享目录：

```text
testdata/ai/
  intent_commands.jsonl
  screenshot_privacy_cases.jsonl
  retrieval_queries.jsonl
  expected_errors.json
```

同一套样本在 iOS、Android 和共享层测试中使用。这样可以发现平台实现差异，而不是依赖人工试用。

样本不要包含真实用户数据。使用脱敏样本或合成样本，并覆盖边界情况。

## 13.9 跨平台发布策略

跨平台端侧 AI 不一定要双平台同时全量发布。更稳妥的策略是：

1. 两个平台都接入能力查询和降级框架。
2. 先在一个平台打开低风险功能。
3. 另一个平台保持云端或传统逻辑兜底。
4. 双平台都完成设备矩阵后再统一入口。
5. 模型版本和配置按平台独立灰度。

如果平台能力差异明显，不要为了“产品一致”强行开放。用户更需要稳定可用，而不是名义一致。

## 13.10 检查清单

跨平台端侧 AI 上线前建议检查：

| 项目 | 问题 |
| --- | --- |
| 分层 | 共享层和平台层责任是否清楚？ |
| 能力 | 是否有能力查询，而不是盲目调用？ |
| 错误 | 错误模型是否跨平台一致？ |
| 数据 | 大图片、音频是否避免跨 bridge 复制？ |
| 权限 | iOS/Android 权限拒绝体验是否一致？ |
| 测试 | 是否使用共享评测样本？ |
| 性能 | 双平台是否都有 profiling 数据？ |
| 灰度 | 是否能按平台独立开关和回滚？ |

## 本章小结

跨平台不是抹平平台差异，而是把差异放到明确边界内管理。端侧 AI 的共享层应关注任务协议、状态机、错误模型和测试样本，平台层应负责 runtime、权限、硬件加速和资源管理。只有能力查询、错误模型、评测矩阵和灰度策略都设计好，跨平台端侧 AI 才能稳定发布。
