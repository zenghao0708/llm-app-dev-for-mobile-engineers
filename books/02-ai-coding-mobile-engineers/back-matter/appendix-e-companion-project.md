# 附录 E 配套示例工程说明

本书第二册配套一个小型可运行示例工程：`examples/ai-coding-mobile-refactor/`。它不是完整 iOS 或 Android App，而是用 Python 模拟移动端项目中最常见的三层结构：网络结果、统一错误模型、页面 ViewModel。选择 Python 的原因是降低读者运行门槛，让练习重点放在 AI coding 工作流上，而不是安装平台 SDK。

## 示例工程目标

示例工程服务于第 10 章和第 14 章的练习，目标包括：

- 让读者能在本地运行测试。
- 让 agent 有真实代码可读、可改、可验证。
- 训练“先分析、再补测试、再最小修改”的流程。
- 训练统一错误模型迁移。
- 训练 PR 摘要、风险说明和未验证项输出。

它刻意保持小规模。真实移动端项目可能有更多页面、更多平台配置和更复杂的生命周期，但练习的工程原则相同：任务要小，边界要清，验证要明确。

## 目录结构

```text
examples/ai-coding-mobile-refactor/
  README.md
  docs/
    ai-task.md
    high-risk-files.md
    ci-equivalent.md
  src/
    ai_refactor/
      app_error.py
      network_client.py
      view_models.py
  tests/
    test_app_error.py
    test_view_models.py
```

`app_error.py` 定义统一错误模型。它包含 `ErrorKind`、`NetworkFailure`、`AppError` 和 `ErrorMapper`。读者可以把它类比为 Swift/Kotlin 项目中的错误枚举、sealed class 或 domain error。

`network_client.py` 定义可注入结果的 `FakeNetworkClient`。它不访问真实网络，避免测试依赖外部服务。

`view_models.py` 定义 `ProfileViewModel` 和 `SettingsViewModel`。它们模拟移动端页面状态：loading、title 和 error。

`tests/` 目录包含错误映射测试和页面状态测试。读者可以让 agent 运行这些测试，再根据失败结果调整实现。

## 运行命令

```bash
cd examples/ai-coding-mobile-refactor
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m py_compile src/ai_refactor/*.py
```

这两个命令已经进入仓库 CI。读者修改示例工程后，应至少运行测试命令。`py_compile` 只验证语法，不等价于行为测试。

## 练习一：只读分析

Prompt：

```text
请只读分析 examples/ai-coding-mobile-refactor。
不要修改代码。
输出：
- 模块职责。
- 错误模型如何映射。
- ProfileViewModel 和 SettingsViewModel 的状态路径。
- 测试覆盖了哪些错误。
- 还缺少哪些测试。
```

验收：

- Agent 能正确指出 `ErrorMapper` 是统一错误模型入口。
- Agent 不应声称项目访问真实网络。
- Agent 不应修改代码。

## 练习二：补充新业务错误码

任务：

```text
请为新的业务错误码 biz_profile_frozen 补充测试和映射。
约束：
- 只修改 app_error.py 和 test_app_error.py。
- 不修改 ViewModel。
- 不新增依赖。
验收：
- 新错误码 kind 为 BUSINESS_ERROR。
- retryable 为 false。
- message_key 为 error_biz_profile_frozen。
- 运行测试。
```

这个练习训练局部任务边界。Agent 如果修改了 ViewModel，就说明任务控制不够好。

## 练习三：修复页面状态

任务：

```text
请检查 ProfileViewModel 在 timeout 时的状态。
如果缺少测试，先补测试。
要求：
- timeout 后 loading=false。
- error.kind 为 TIMEOUT。
- error.retryable 为 true。
```

这个练习训练测试先行。读者可以要求 agent 先写失败测试，再做实现。

## 练习四：生成 PR 摘要

任务：

```text
请根据当前 diff 生成 PR 摘要。
必须包含：
- 背景。
- 修改范围。
- 测试命令和结果。
- 未验证项。
- 风险和回滚方式。
```

这个练习训练交付能力。AI coding 不只是改代码，最终还要让审查者快速理解变更。

## 如何映射到 iOS/Android

示例中的概念可以这样映射：

| 示例工程 | iOS | Android |
| --- | --- | --- |
| `AppError` | enum/struct domain error | sealed class/data class |
| `NetworkFailure` | URLSession/Alamofire error wrapper | Retrofit/OkHttp exception wrapper |
| `ErrorMapper` | mapper/service | mapper/use case |
| `ProfileViewModel` | ObservableObject/ViewModel | ViewModel + StateFlow |
| `ScreenState` | view state | ui state |
| unittest | XCTest | JUnit/coroutine test |

读者在真实项目中迁移时，要补充平台特定内容：生命周期、取消、主线程、协程、权限、本地化、埋点和 UI 验证。

## 示例工程的边界

这个示例有意不包含：

- 真实网络请求。
- 真实移动端 UI。
- 平台权限。
- 签名和发布配置。
- 模型 API 调用。

这些边界是为了让练习聚焦于 AI coding 方法。真实项目中，边界会更复杂，因此更需要本书讨论的 Prompt、Context、Harness 和 Loop。

## 推荐读者输出

完成练习后，读者应保存三类输出：

- 一份只读分析报告。
- 一份通过测试的代码 diff。
- 一份 PR 摘要和风险说明。

如果这三类输出都能稳定生成，说明读者已经掌握了本书第二册最核心的技能：把 agent 放进可验证的工程循环，而不是只让它生成代码片段。
