# 附录 C 资料来源与事实核验

本附录列出第二册初稿写作时使用的官方资料。正式出版前应重新打开链接核验工具版本、命令、截图和能力边界。

## OpenAI / Codex

- Introducing Codex：<https://openai.com/index/introducing-codex/>
- Codex CLI：<https://developers.openai.com/codex/cli>
- Codex Quickstart：<https://developers.openai.com/codex/quickstart>
- Codex MCP：<https://developers.openai.com/codex/mcp>
- Codex changelog：<https://developers.openai.com/codex/changelog>
- Codex Subagents：<https://developers.openai.com/codex/subagents>
- Codex Hooks：<https://developers.openai.com/codex/hooks>
- Codex Skills：<https://developers.openai.com/codex/skills>

## Anthropic / Claude Code

- Claude Code overview：<https://docs.anthropic.com/en/docs/claude-code/overview>
- Claude Code best practices：<https://www.anthropic.com/engineering/claude-code-best-practices>
- Effective context engineering for AI agents：<https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
- Building agents with the Claude Agent SDK：<https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk>
- Effective harnesses for long-running agents：<https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents>
- Claude Code hooks：<https://docs.anthropic.com/en/docs/claude-code/hooks-guide>
- Claude Code MCP：<https://docs.anthropic.com/en/docs/claude-code/mcp>
- Claude Code auto mode：<https://www.anthropic.com/engineering/claude-code-auto-mode>
- Claude Agent SDK：<https://docs.anthropic.com/en/docs/claude-code/sdk>

## 出版前核验清单

- 工具名称和产品定位是否变化。
- 命令行参数是否变化。
- 付费计划、模型、权限和沙箱说明是否变化。
- MCP、hooks、skills、SDK 等能力是否仍按文中描述存在。
- 官方文档是否新增安全限制或弃用说明。

## 核验流程建议

正式出版前，建议按下面流程核验全书事实：

1. 打开所有官方链接，确认页面仍然存在。
2. 记录访问日期。
3. 检查产品名称是否变化。
4. 检查命令、参数、配置文件位置是否变化。
5. 检查示例截图是否与当前版本一致。
6. 检查安全、权限、沙箱、数据保留说明是否变化。
7. 检查书中是否把推断写成了官方结论。
8. 对变化较大的段落做脚注或改写。

建议维护一个表格：

| 条目 | 来源 | 上次核验 | 状态 | 处理 |
| --- | --- | --- | --- | --- |
| Codex CLI 是否支持 MCP | OpenAI Developers | 待填 | 待核验 | 出版前确认 |
| Claude Code hooks 事件 | Claude Code Docs | 待填 | 待核验 | 对照命令和配置 |
| Context engineering 观点 | Anthropic Engineering | 待填 | 待核验 | 保留引用日期 |

## 引用原则

本书引用工具能力时遵守三个原则：

第一，优先引用官方文档、官方博客和工程团队文章。社区文章可以作为启发，但不作为事实依据。

第二，区分官方事实和作者推断。例如“Codex 支持 MCP”属于官方事实；“移动端团队应把 MCP 用于崩溃平台脱敏接入”是本书推断和建议，应在表述上区分。

第三，避免写死容易变化的界面细节。按钮位置、菜单名称、付费计划和模型名称都可能变化。正式出版时如果必须截图，应在图注中标明版本和访问日期。

## 截图核验清单

如果后续补充工具截图，建议每张截图记录：

- 工具名称。
- 版本或访问日期。
- 操作系统。
- 截图对应章节。
- 截图想说明的技术点。
- 是否包含账号、路径、token、内部仓库名。

截图应该服务于技术理解，而不是展示工具界面本身。对读者有帮助的截图通常包括：任务输入、上下文选择、权限确认、测试输出、diff 审查和 PR 摘要。

## 示例代码核验清单

本书强调示例代码真实可运行。出版前应检查：

- 是否能在干净环境安装依赖。
- 是否不需要真实 API key 即可跑通基础测试。
- `.env.example` 是否只包含占位符。
- README 命令是否与实际脚本一致。
- 测试是否稳定。
- 输出是否与书中描述一致。
- 是否有 CI 覆盖。

如果示例依赖模型服务，应提供 mock provider 或录制样例，避免读者因为没有账号而无法学习核心流程。
