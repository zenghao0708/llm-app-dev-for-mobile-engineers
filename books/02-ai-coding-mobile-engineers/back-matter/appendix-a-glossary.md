# 附录 A AI Coding 术语表

| 术语 | 简要解释 | 移动端工程关注点 |
| --- | --- | --- |
| AI coding | 使用大模型辅助软件开发的总称。 | 不只生成代码，还包括调试、测试、评审和文档。 |
| Agentic coding | agent 能读写文件、运行命令、调用工具并循环验证的编程方式。 | 必须设置权限、沙箱和验证命令。 |
| Prompt Engineering | 设计任务表达、约束和输出格式。 | 任务要包含平台、模块、禁止事项和验收命令。 |
| Context Engineering | 选择、组织、压缩和更新上下文。 | 移动端项目上下文大，必须分层提供。 |
| Harness Engineering | 为 agent 准备执行环境、工具、权限和检查点。 | 签名、证书、生产配置要保护。 |
| Loop Engineering | 设计 agent 的反馈循环。 | 每轮修改后要运行测试或检查。 |
| MCP | Model Context Protocol，用于连接模型、工具和上下文。 | 可接入设计稿、Issue、日志和内部文档。 |
| Hooks | 在 agent 生命周期中自动运行命令。 | 可用于格式化、测试、敏感文件检查。 |
| Skills | 可复用的任务流程和经验包。 | 适合沉淀平台专项能力。 |
| Sandbox | 限制 agent 可访问资源和命令的执行环境。 | 防止误删、泄露和危险命令。 |

## 扩展术语

| 术语 | 简要解释 | 移动端工程关注点 |
| --- | --- | --- |
| Worktree | Git 中同一仓库的独立工作区。 | 多 agent 并行时可隔离修改，避免互相覆盖。 |
| Subagent | 面向特定任务的子代理。 | 可让一个 agent 做实现，另一个 agent 做审查或测试补充。 |
| Tool call | 模型调用外部工具或本地命令的动作。 | 要限制命令范围并记录结果。 |
| Context window | 模型一次可处理的上下文容量。 | 长任务需要压缩摘要和进度文件。 |
| Context compression | 把长历史压缩成摘要。 | 保留决策、风险、待办和测试结果，避免丢失关键事实。 |
| Checkpoint | 任务过程中的可恢复状态。 | 可用 Git commit、stash、进度文件或测试结果记录。 |
| CI equivalent | 本地等价于 CI 的验证命令。 | 让 agent 在本地运行与 CI 接近的检查。 |
| High-risk file | 修改后风险较高的文件。 | 如 `Info.plist`、`AndroidManifest.xml`、签名配置、依赖文件。 |
| Redaction | 脱敏处理。 | 提供日志、崩溃和用户反馈前必须删除隐私和密钥。 |
| Mock provider | 本地模拟模型或后端服务。 | 让示例代码可运行，避免读者必须配置真实 API key。 |
| Golden test | 基于快照或黄金文件的回归测试。 | 适合 UI 状态、结构化输出和文档生成校验。 |
| Flaky test | 偶发失败测试。 | Agent 生成异步测试时容易引入，需要避免 sleep 和真实网络。 |
| Human-in-the-loop | 人在关键节点介入确认。 | 权限、支付、登录、发版等任务必须人工确认。 |
| PR summary | Pull Request 变更摘要。 | Agent 应输出修改范围、验证结果、风险和未验证项。 |
| Rollback plan | 回滚方案。 | 移动端回滚通常依赖开关、灰度、远程配置和后续版本。 |

## 易混概念

### Prompt 与 Context

Prompt 是任务表达，Context 是任务所需信息。Prompt 写得再好，如果缺少错误日志、相关文件和验证命令，agent 仍然会猜。移动端任务中，Context 往往包括平台、模块、构建变体、复现设备、系统版本和最近变更。

### Harness 与 Tool

Tool 是单个工具或命令，Harness 是把工具、权限、验证和检查点组合起来的执行环境。一个 `flutter test` 是工具；一套“允许命令、禁止命令、测试脚本、高风险文件检查、进度记录”才是 harness。

### Loop 与 Retry

Retry 只是重复尝试。Loop 是有目标、有证据、有停止条件的反馈循环。好的 loop 会在失败后缩小问题范围；坏的 retry 会在没有新证据的情况下不断改代码。

### Agent 与资深工程师

Agent 可以执行、总结、搜索和修改，但不承担业务责任。资深工程师需要判断任务优先级、用户体验、合规风险和发版节奏。AI coding 的目标是放大工程能力，不是取消工程判断。
