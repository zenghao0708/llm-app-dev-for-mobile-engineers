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

## 13.11 能力接口契约

跨平台端侧 AI 的接口契约应描述“能力”，而不是描述某个模型调用。一个稳定契约至少包含：

```text
capability_id
platform
supported
availability_reason
required_permissions
required_models
input_schema_version
output_schema_version
estimated_cost
fallback_modes
```

例如本地 OCR 能力可以返回：

```json
{
  "capability_id": "local_ocr",
  "supported": true,
  "availability_reason": "ready",
  "required_permissions": ["photo_library_read"],
  "required_models": [
    {"model_id": "ocr-lite", "version": "2.1.0", "status": "ready"}
  ],
  "input_schema_version": "image-input-v1",
  "output_schema_version": "ocr-output-v2",
  "fallback_modes": ["cloud_ocr", "manual_input"]
}
```

共享层根据契约决定入口展示、下载提示、权限引导和降级路径。平台层负责把系统差异转成契约字段。这样做可以避免 UI 层到处写 `if iOS`、`if Android`，也避免把平台差异伪装成不存在。

契约还应有版本。输入输出字段一旦变化，就要升级 schema，并提供兼容处理。跨平台项目最怕“某个平台偷偷多返回一个字段，另一个平台还是旧结构”。契约版本让这种变化可见、可测、可回滚。

## 13.12 Bridge 性能与数据传输

端侧 AI 经常处理大对象，跨平台 bridge 是性能风险点。原则是：大数据留在原生侧，跨层只传句柄、路径、结构化结果和小型元数据。

| 数据 | 推荐方式 | 避免方式 |
| --- | --- | --- |
| 大图片 | 原生文件 URI、asset id、临时文件句柄 | base64 字符串穿过 bridge |
| 音频 | 文件路径、分片句柄 | 一次性传完整二进制 |
| 长文本 | 分段、文件路径、摘要输入 | UI 层拼接超长字符串 |
| embedding | 原生索引查询 | 传大量向量到 JS/Dart |
| 进度 | 小型事件 | 高频大 payload 事件 |

bridge 还要控制事件频率。相册索引每处理一张图就发一次事件，可能让 UI 层过载。更好的方式是按时间窗口或批次上报：

```text
progress: processed=120, total=1000, stage="embedding"
```

跨平台性能优化不只看模型推理时间，还要看桥接复制、序列化、图片解码、线程切换和 UI 刷新。如果 profiling 只发生在原生 runtime 内部，团队会低估端到端延迟。

## 13.13 权限和隐私差异

iOS 和 Android 的权限、文件访问和后台限制差异很大。跨平台共享层不能直接假设“有权限”或“无权限”，而应处理平台返回的明确状态：

| 状态 | 含义 | UI 策略 |
| --- | --- | --- |
| `not_determined` | 尚未请求 | 展示功能价值后请求 |
| `granted` | 已授权 | 正常执行 |
| `limited` | 部分授权 | 展示可处理范围 |
| `denied` | 用户拒绝 | 提供设置入口或降级 |
| `restricted` | 系统或组织限制 | 说明不可用原因 |

相册、麦克风、文件和通知权限都可能影响端侧 AI。企业管理设备还可能通过策略禁用模型下载、云端上传或本地索引。共享层应把这些限制当成正常状态，而不是异常。

隐私文案也要按平台适配。系统权限弹窗文案、设置页说明、功能入口说明要保持一致语义，但不一定逐字相同。跨平台统一的是用户理解，而不是字符串完全一致。

## 13.14 多端配置治理

跨平台端侧 AI 通常需要远程配置控制模型版本、功能开关、灰度比例和降级策略。配置治理要避免一个平台误用另一个平台的配置。

建议配置结构包含平台维度：

```json
{
  "feature": "local_screenshot_assistant",
  "ios": {
    "enabled": true,
    "model_bundle": "screenshot-ios-v3",
    "min_app_version": "6.2.0"
  },
  "android": {
    "enabled": false,
    "fallback": "cloud_only",
    "reason": "runtime_not_ready"
  }
}
```

配置变更要有审计记录：谁改了、改了什么、影响哪些版本、回滚方式是什么。端侧模型和云端 API 不同，坏配置可能在用户设备上形成持久状态。配置平台必须支持快速关闭、分平台回滚和按版本冻结。

## 13.15 跨平台代码审查关注点

跨平台端侧 AI 的代码审查应特别关注：

- 是否把大图片或音频穿过 JS/Dart bridge。
- 是否在 UI 线程做预处理或后处理。
- 是否把平台错误字符串直接暴露给共享层。
- 是否缺少取消和资源释放。
- 是否缺少权限撤销处理。
- 是否假设两个平台模型版本一致。
- 是否缺少低端设备降级。
- 是否把原始输入写入跨平台日志。

这些问题在单平台开发中也会出现，但跨平台项目更隐蔽。因为共享层看起来很干净，真正的性能和隐私问题可能藏在平台实现里。代码审查要同时看共享接口和原生实现，不能只看 Dart、JS 或 Kotlin common 代码。

## 本章小结

跨平台不是抹平平台差异，而是把差异放到明确边界内管理。端侧 AI 的共享层应关注任务协议、状态机、错误模型和测试样本，平台层应负责 runtime、权限、硬件加速和资源管理。只有能力查询、错误模型、评测矩阵和灰度策略都设计好，跨平台端侧 AI 才能稳定发布。
