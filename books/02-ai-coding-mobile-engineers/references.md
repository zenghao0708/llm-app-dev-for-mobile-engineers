# 资料来源与事实核验记录

本文件记录第二册写作时用到的主要官方资料。由于 AI coding 工具更新速度很快，正式出版前需要重新核验版本、命令、截图和功能边界。

## OpenAI / Codex

- OpenAI：Introducing Codex，说明 Codex 作为云端软件工程 agent，可以在独立云沙箱中并行执行任务、写功能、修 bug、回答代码库问题和提出 PR。<https://openai.com/index/introducing-codex/>
- OpenAI Developers：Codex CLI，说明 Codex CLI 是可在本地终端运行的 coding agent，可以在选定目录中读取、修改和运行代码。<https://developers.openai.com/codex/cli>
- OpenAI Developers：Codex Quickstart，说明 Codex 默认以 Agent mode 启动，可以读文件、运行命令并写入项目目录。<https://developers.openai.com/codex/quickstart>
- OpenAI Developers：Codex MCP，说明 MCP 可用于把模型连接到工具和上下文，Codex CLI 和 IDE extension 均支持 MCP servers。<https://developers.openai.com/codex/mcp>
- OpenAI Developers：Codex changelog，记录插件、skills、app integrations 和 MCP server configuration 等能力变化。<https://developers.openai.com/codex/changelog>
- OpenAI Developers：Codex Subagents，说明可以把复杂任务拆给专门的子代理处理，适合代码审查、测试、文档和专项分析等场景。<https://developers.openai.com/codex/subagents>
- OpenAI Developers：Codex Hooks，说明可以在 agent 生命周期中触发命令，用于校验、格式化、通知和流程约束。<https://developers.openai.com/codex/hooks>
- OpenAI Developers：Codex Skills，说明 skills 可把可复用流程、说明和脚本打包成 agent 可调用能力。<https://developers.openai.com/codex/skills>

## Anthropic / Claude Code

- Claude Code Docs：Overview，说明 Claude Code 是 agentic coding tool，可以读取代码库、编辑文件、运行命令并与开发工具集成。<https://docs.anthropic.com/en/docs/claude-code/overview>
- Anthropic Engineering：Claude Code best practices，强调上下文窗口会被消息、文件和命令输出快速填满，性能会随着上下文填充而下降。<https://www.anthropic.com/engineering/claude-code-best-practices>
- Anthropic Engineering：Effective context engineering for AI agents，说明 Claude Code 会压缩历史上下文并保留关键架构决策、未解决 bug 和实现细节，同时携带最近访问文件。<https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
- Anthropic Engineering：Building agents with the Claude Agent SDK，说明 Claude Code 常见反馈循环是 gather context -> take action -> verify work -> repeat。<https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk>
- Anthropic Engineering：Effective harnesses for long-running agents，讨论长任务 agent 的 harness 和环境管理。<https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents>
- Claude Code Docs：Hooks，说明可以在 Claude Code 编辑文件、完成任务或需要输入时自动运行 shell commands，用于格式化、通知、校验命令和执行规则。<https://docs.anthropic.com/en/docs/claude-code/hooks-guide>
- Claude Code Docs：MCP，说明 Claude Code 可通过 MCP 连接本地或远程工具与数据源。<https://docs.anthropic.com/en/docs/claude-code/mcp>
- Anthropic Engineering：Claude Code auto mode，说明 permission prompts 的自动化和安全边界。<https://www.anthropic.com/engineering/claude-code-auto-mode>
- Claude Code Docs：Agent SDK overview，说明 Agent SDK 提供与 Claude Code 相同的 tools、agent loop 和 context management，可用 Python/TypeScript 编程。<https://docs.anthropic.com/en/docs/claude-code/sdk>

## 概念来源

- Prompt Engineering：来自大模型提示词工程实践，在本书中收敛到“任务表达、输出格式、约束、示例和验收标准”。
- Context Engineering：来自 agent 长上下文实践，在本书中收敛到“仓库地图、上下文预算、摘要、索引、最近文件和错误现场”。
- Harness Engineering：来自长任务 agent 环境管理，在本书中收敛到“工具、权限、测试、沙箱、检查点和自动化脚手架”。
- Loop Engineering：来自 agent feedback loop，在本书中收敛到“理解-修改-验证-复盘”的可收敛循环。
