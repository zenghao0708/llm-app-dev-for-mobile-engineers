# AI Coding Mobile Refactor Example

这个示例工程配套《AI Coding 编程专家》第 14 章和附录 E。它用 Python 模拟移动端项目中的网络错误处理、Repository 和 ViewModel，便于读者在没有 Xcode、Android Studio 或真实模型 API Key 的情况下练习 AI coding 工作流。

## 目标

示例刻意保留两个页面级 ViewModel：`ProfileViewModel` 和 `SettingsViewModel`。它们都依赖统一的 `AppError` 和 `ErrorMapper`，读者可以让 agent 练习：

- 只读分析模块结构。
- 补充错误模型测试。
- 修复 ViewModel 状态问题。
- 输出 PR 描述和风险清单。
- 遵守禁止事项和验证命令。

## 目录

```text
src/ai_refactor/
  app_error.py       统一错误模型
  network_client.py  可注入结果的模拟网络层
  view_models.py     Profile/Settings 两个页面状态模型
tests/
  test_app_error.py
  test_view_models.py
docs/
  ai-task.md
  high-risk-files.md
  ci-equivalent.md
```

## 运行

```bash
cd examples/ai-coding-mobile-refactor
PYTHONPATH=src python3 -m unittest discover -s tests
```

## 推荐练习

1. 让 agent 只读分析 `ProfileViewModel` 的状态路径，不修改代码。
2. 让 agent 为新的业务错误码补测试。
3. 让 agent 修改 `ErrorMapper`，保持 ViewModel 外部行为不变。
4. 让 agent 输出修改文件、测试结果、风险和未验证项。

## 约束

- 不需要真实 API Key。
- 不访问网络。
- 不新增依赖。
- 所有测试应在干净 Python 环境中运行。
