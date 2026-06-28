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
