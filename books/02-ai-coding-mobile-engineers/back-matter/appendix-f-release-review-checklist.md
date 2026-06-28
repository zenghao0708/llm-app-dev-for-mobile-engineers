# 附录 F 发版前审稿与质量检查清单

本附录用于第二册进入正式发布前的自检。它既适用于 GitHub 公开仓库，也适用于后续整理成正式出版稿。AI coding 领域变化很快，书稿发布前不能只检查错别字，还要检查事实、命令、示例代码、截图、术语、读者练习和授权边界。

## 一、内容完整性检查

全书应覆盖以下主线：

- AI coding 从代码补全、聊天辅助、仓库感知到 agentic coding 的演进。
- Claude Code、Codex 等工具代表的工程化变化。
- Prompt Engineering、Context Engineering、Harness Engineering、Loop Engineering 四类能力。
- iOS、Android、Flutter、React Native 等移动端场景。
- 调试、重构、测试、工具接入、安全治理、效果评测和综合项目。
- 面向读者的练习、Playbook 和可运行示例。

检查方式：

| 检查项 | 标准 |
| --- | --- |
| 技术演进 | 不只讲工具名称，要讲能力变化 |
| 工程能力 | 四类 Engineering 都有定义、案例、失败模式和清单 |
| 移动端定位 | 每篇都能落回移动端项目，而不是泛泛谈 AI |
| 实战性 | 有 prompt 模板、任务拆分、测试命令、风险清单 |
| 读者路径 | 从只读分析到团队治理有练习路线 |

如果某章只有概念，没有案例或检查清单，应补充。专业计算机书的价值不只是观点，还在于读者能照着做。

## 二、章节质量检查

每一章至少应回答五个问题：

1. 本章解决什么问题？
2. 读者为什么需要这个能力？
3. 移动端项目中的典型场景是什么？
4. 具体应该怎么做？
5. 常见失败和风险是什么？

章节结构建议：

```text
本章导读
学习目标
核心概念
移动端案例
Prompt/清单/模板
常见失败
本章小结
```

不是每章都必须完全一致，但读者应该能快速判断本章的入口、方法和输出。对于教程类书籍，章节内部的“可执行材料”很重要，例如表格、模板、流程和验收清单。

## 三、术语一致性检查

AI coding 领域术语混杂，书稿中要保持一致。

| 术语 | 推荐写法 | 避免写法 |
| --- | --- | --- |
| AI coding | AI coding | AI 编码、智能编码混用 |
| agentic coding | agentic coding | 自动编程、智能体编程随意切换 |
| Prompt Engineering | Prompt Engineering | 提示词工程、Prompt 工程混乱切换 |
| Context Engineering | Context Engineering | 上下文工程、上下文管理不区分 |
| Harness Engineering | Harness Engineering | 工具工程、环境工程随意替换 |
| Loop Engineering | Loop Engineering | 循环工程、反馈循环混用但不解释 |
| MCP | MCP | 第一次出现不解释 |

中英文混排可以保留，但首次出现应解释。后续章节尽量使用同一写法，避免读者以为是不同概念。

## 四、事实核验检查

正式发布前，应打开附录 C 中所有链接重新核验。重点检查：

- Codex、Claude Code 等产品名称是否变化。
- CLI 命令、配置文件、MCP、hooks、skills、subagents 是否仍存在。
- 官方文档中对权限、沙箱、安全边界的描述是否变化。
- 书中是否把某个工具的临时功能写成长期承诺。
- 是否引用了非官方资料作为事实依据。

建议为每条事实加上核验状态：

| 事实 | 来源 | 核验日期 | 状态 |
| --- | --- | --- | --- |
| Codex 支持 MCP | OpenAI Developers | 待填 | 待核验 |
| Claude Code 支持 hooks | Claude Code Docs | 待填 | 待核验 |
| Agent SDK 提供工具和循环能力 | Anthropic Docs | 待填 | 待核验 |

如果无法确认，应改写为更稳妥的表述。例如把“某工具一定支持某能力”改成“截至核验日期，官方文档说明该工具支持某能力”。

## 五、示例代码检查

本书强调示例代码真实可运行。所有示例工程应满足：

- 在干净环境中可运行。
- 不需要真实 API key 才能完成基础练习。
- 不访问真实网络。
- 测试命令写在 README 中。
- CI 会运行测试。
- `.env.example` 只包含占位符。
- 不提交缓存、虚拟环境、构建产物和本地凭据。

配套示例工程 `examples/ai-coding-mobile-refactor/` 应检查：

```bash
cd examples/ai-coding-mobile-refactor
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m py_compile src/ai_refactor/*.py
```

如果未来增加 Swift、Kotlin、Flutter 或 React Native 示例，也应提供最小可运行命令。不要只在书中贴无法执行的片段。

## 六、EPUB 检查

EPUB 发布前应检查：

- 目录是否完整。
- 章节标题是否正确。
- 锚点跳转是否可用。
- 代码块是否保留缩进。
- 表格是否可读。
- 中文显示是否正常。
- 图片是否清晰且不乱码。
- 文件大小是否合理。
- Apple Books、Calibre 或 Thorium Reader 至少打开验证一次。

本仓库的 EPUB 构建命令：

```bash
python3 tools/build_epub.py \
  --manifest books/02-ai-coding-mobile-engineers/book-manifest.json \
  --output build/ebooks/ai-coding-mobile-engineers.epub
```

如果后续增加 SVG 图表，应确认 EPUB 构建是否会栅格化，避免阅读器中文字体渲染失败。

## 七、GitHub 发布检查

公开仓库发布前检查：

- README 是否说明三部曲定位。
- 第二册目录是否清晰。
- EPUB 下载链接是否有效。
- LICENSE 是否区分代码和内容授权。
- CONTRIBUTING 或勘误入口是否存在。
- GitHub Actions 是否通过。
- 不包含真实密钥、日志、缓存、依赖目录。
- 构建命令可复制运行。

提交前建议执行：

```bash
git status --short
git diff --check
python3 tools/manage_chapters.py --manifest books/02-ai-coding-mobile-engineers/book-manifest.json validate
python3 tools/build_book.py --manifest books/02-ai-coding-mobile-engineers/book-manifest.json --output build/book-02-ai-coding-mobile-engineers.md
python3 tools/build_epub.py --manifest books/02-ai-coding-mobile-engineers/book-manifest.json --output build/ebooks/ai-coding-mobile-engineers.epub
python3 -m unittest discover -s tests
```

如果提交 EPUB 产物，因为 `build/` 可能被 `.gitignore` 忽略，需要显式确认文件已被纳入版本库。

## 八、安全与隐私检查

必须检查：

- `.env`、`.env.local`、token、cookie、session 是否被提交。
- 示例日志是否脱敏。
- 截图是否包含账号、内部路径、仓库名、token。
- 示例代码中是否有真实域名、真实密钥、真实用户数据。
- 书中 prompt 是否鼓励读者复制敏感日志给 agent。

高风险词扫描只是辅助，不能替代人工检查。尤其要注意截图和二进制文件，因为普通文本搜索不能发现图片里的敏感信息。

## 九、出版风格检查

面向软件开发工程师的技术书，需要避免两类问题。

第一，避免过度营销。不要把 AI coding 写成万能工具，也不要把某个产品写成唯一答案。要讲清边界、失败模式和人工责任。

第二，避免过度抽象。每章都应有移动端场景、任务模板或检查清单。读者读完后应知道下一步怎么做。

文字风格建议：

- 用短段落解释复杂概念。
- 表格服务于比较和决策。
- Prompt 模板要有约束和验收。
- 小结要回到本章核心能力。
- 示例不要只展示成功，也要展示失败恢复。

## 十、终审问题清单

最终发布前，逐项回答：

- 这本书是否明确面向移动端工程师？
- 是否解释了 AI coding 的技术演进？
- 是否覆盖 Prompt、Context、Harness、Loop？
- 是否有 Claude Code/Codex 等工具演进的事实依据？
- 是否强调挑战、边界和解决方案？
- 是否有真实可运行代码？
- 是否有 EPUB？
- 是否能在 GitHub 上持续维护章节？
- 是否通过 CI？
- 是否还有明显短章节或空洞段落？

如果这些问题都能用当前文件和命令结果证明，第二册才算达到公开发布的基本标准。
