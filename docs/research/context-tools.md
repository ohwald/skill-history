# 调研:AI coding agent 的上下文监控与上下文修改工具

调研日期:2026-10-24。范围:Claude Code / ZCode 类 CLI coding agent 生态中「监控 context(观察用量/内容)」与「修改 context(注入/改写/删除)」的工具。所有事实均对着一手资料核实(官方 docs、GitHub 仓库本体);无法核实的明确标注「未核实」。star 数为 2026-10-24 当日快照,会漂移,仅用于量级判断。

## TL;DR

这个生态可以分成两大类、八个细分:

- **监控类**(只读):① CLI 内建命令(`/context`、`/usage`、`/insights`);② statusline 定制(官方开放 stdin JSON 接口,token/上下文余量都是官方字段);③ OTEL/遥测导出(面向企业后端);④ 第三方 JSONL 后处理(ccusage、claude-code-log 等,读本地 transcript);⑤ 第三方 GUI 面板(opcode 等)。
- **修改类**(写入):① hooks 注入与改写(官方最重要、能力最强的杠杆);② 规则文件与 system prompt(CLAUDE.md / AGENTS.md / rules / output styles / `--append-system-prompt`);③ 压缩(`/compact`、auto-compact、API 层 context editing);④ 记忆类第三方(MCP memory server);⑤ 检索换 context(Serena、Context7);⑥ 仓库打包注入(repomix 等)。

总体观察:**官方已经把「改上下文」的主要杠杆全部内建化**(hooks + rules + auto memory + compact + MCP Tool Search),第三方的修改类工具大多不再对抗官方机制,而是「用检索和持久记忆换 context」或做规则文件的跨工具同步;而监控类第三方几乎全部依附于两个官方数据源——本地 transcript JSONL 和 statusline stdin JSON——因此其健壮性上限就是官方格式的稳定性。

---

## 一、上下文监控类

### 1.1 官方内建(Claude Code)

**`/context`** — 会话内运行,显示当前 context 空间被什么占用(system prompt、tools、MCP、memory files 等)。官方在多篇文档中将其作为排查 context 占用的入口。来源:[How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)、[Manage costs](https://code.claude.com/docs/en/costs)。

**`/usage`** — Session 区块显示当前会话 token 统计与成本估算(本地按标价估算,权威账单在 Console);订阅用户还能看到套餐进度条、用量归因(按 skill/子代理/MCP 服务器)、prompt cache 命中率统计。`/insights` 可分析最近最多 200 个会话并生成 HTML 报告(`~/.claude/usage-data/report.html`)。来源:[Manage costs](https://code.claude.com/docs/en/costs)。

**context-left 指示** — 接近 auto-compact 窗口时会出现警告;spinner 旁显示当前回合 token 计数(如 `↓ 5.5k tokens`)。"Context left until auto-compact" 这一 UI 字符串出现在 changelog(2.1.14 修复其 `/compact` 后不消失的问题)。来源:[Manage costs](https://code.claude.com/docs/en/costs)、[CHANGELOG.md](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)。

**statusline 定制** — `settings.json` 中 `statusLine` 字段(仅 `type: "command"`),Claude Code 把会话 JSON 写入脚本 **stdin**,脚本 stdout 即状态栏。token/上下文字段是官方一等公民:`context_window.used_percentage` / `remaining_percentage` / `current_usage`(input/output/cache_read/cache_creation)、`context_window_size`(200k,扩展模型 1M)、`exceeds_200k_tokens`,另有 `cost.total_cost_usd`、`rate_limits`(Pro/Max)、`prompt_cache` 对象。官方甚至提供 `/statusline` 命令用自然语言生成脚本。**这就是所有第三方 statusline 工具的数据来源**。来源:[Statusline docs](https://code.claude.com/docs/en/statusline)。

**`--verbose`** — 显示完整逐轮输出(会覆盖 `viewMode` 设置)。来源:[CLI reference](https://code.claude.com/docs/en/cli-reference)。

**OTEL/OpenTelemetry 导出** — 设 `CLAUDE_CODE_ENABLE_TELEMETRY=1` + `OTEL_METRICS_EXPORTER=otlp|prometheus|console` 即可导出到任意 OTLP 后端或 Prometheus。关键指标:`claude_code.token.usage`(按 `type=input/output/cacheRead/cacheCreation`、`model`、`query_source=main/subagent` 归因)、`claude_code.cost.usage`、`session.count`、`active_time.total`;events 走 logs 协议(`user_prompt`、`tool_result` 等,prompt 文本默认脱敏);Traces 处于 beta(`CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`)。可视化靠接入的 Grafana/Datadog 等自建 dashboard。来源:[Monitoring usage](https://code.claude.com/docs/en/monitoring-usage)。

**其它工具有无对应物(一句话)**:Gemini CLI 有 `/stats`(会话 token 统计,`/stats model` 看配额)与 GEMINI.md 记忆体系,来源:[Gemini CLI commands](https://geminicli.com/docs/reference/commands)、[gemini-cli quota docs](https://github.com/google-gemini/gemini-cli/blob/main/docs/resources/quota-and-pricing.md);Cursor 的用量查看主要在账号 Dashboard,无等价的 `/context` 分解命令(未核实其最新版本细节)。

### 1.2 第三方监控工具

**ccusage**([ccusage/ccusage](https://github.com/ccusage/ccusage),★19.2k,活跃,最近推送 2026-10-24)
做什么:`npx ccusage` 即出 daily / monthly / blocks(5 小时计费块)/ session 四种 token 与费用报表,支持 JSON/CSV 导出,还内置 statusline 子命令(beta)。机制:**纯本地解析** `~/.claude/projects/` 等 transcript JSONL,按消息里的 usage 字段聚合,离线可用、不调 API;费用是按标价的本地估算。生态位:事后分析/统计的首选,事实上的行业标准。

**Claude Monitor**([Maciek-roboblog/Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor),★8.8k,活跃,PyPI 包名 `claude-monitor`)
做什么:终端实时监控,Rich live UI,对 5 小时计费块做耗尽时间预测与告警。机制:早期靠本地建模;现版本强调「official-limit trust layer」——通过 `--statusline` 捕获 Claude Code 官方 `rate_limits` 数据,过期则回退到带标注的本地估算。注意与 npm 上一个同名的无关小包(`claude-monitor` 0.1.0,指向 aistackhq)区分,认准 PyPI/GitHub 本仓。

**ccstatusline**([sirmalloc/ccstatusline](https://github.com/sirmalloc/ccstatusline),★13.4k,活跃)
做什么:statusline 格式化器,widget 化配置(model、git 分支、token 用量、context 余量等),带 TUI 配置器(`npx ccstatusline@latest`)与 powerline 主题。机制:读官方 statusline stdin JSON(`context_window.*` 字段直接可用),零依赖运行时。生态位:不想自己写脚本的用户的标准选择。

**CCometixLine**([Haleclipse/CCometixLine](https://github.com/Haleclipse/CCometixLine),★3.5k,活跃,Rust)
做什么:Rust 高性能 statusline,显示 Model | Directory | Git | **Context Window 信息** 段,带 TUI 配置。机制:同样读 stdin JSON + 解析 transcript;附带实用工具如「Context warning disabler」(去掉 "Context low" 提示)。生态位:在意性能与默认美观的用户。

**claude-powerline**([Owloops/claude-powerline](https://github.com/Owloops/claude-powerline),★1.2k,活跃)
做什么:vim 风格 powerline statusline,段可配置,token 段支持 `cost | tokens | both | breakdown` 显示格式。机制:官方 stdin JSON;`npx owloops/claude-powerline` 即用。

**claude-code-log**([daaain/claude-code-log](https://github.com/daaain/claude-code-log),★1.25k,活跃,Python)
做什么:把 transcript JSONL 转成可读 HTML / Markdown / JSON,逐消息与全会话的 token 用量统计、会话列表表格。机制:解析 `~/.claude/projects` JSONL(私有格式)。生态位:审计和归档会话内容。

**claude-conversation-extractor**([ZeroSumQuant/claude-conversation-extractor](https://github.com/ZeroSumQuant/claude-conversation-extractor),★683,**维护放缓**,最近推送 2026-01-02)
做什么:一条命令把对话导出为干净 Markdown。机制:读取 `~/.claude/projects` 下「undocumented JSONL」(README 原话)。因为官方格式无兼容承诺,长期停更风险较高。

**opcode**([winfunc/opcode](https://github.com/winfunc/opcode),★22.4k,最近推送 2026-09-18,约 5 周前)
做什么:Claude Code 的 GUI 管理面板(Tauri):会话历史浏览与恢复、按模型/项目/时间段的 token 分析、MCP server 注册表管理、自定义 agent。机制:读本地会话数据 + 驱动 CLI。前身是 getAsterisk/claudia(原 Claudia),后改名 opcode 并迁移到 winfunc 组织——引用旧链接会失效。

**其它收录**:
- [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates)(★32.9k,活跃):官方文档推荐的模板 CLI,含 agents/skills/MCP 配置生成与 **usage analytics** 监控面板,横跨监控与配置两类。
- [hoangsonww/Claude-Code-Agent-Monitor](https://github.com/hoangsonww/Claude-Code-Agent-Monitor)(★1.1k,活跃):SQLite + Node/React 的实时监控 dashboard,自建 Web UI。
- [cobra91/better-ccusage](https://github.com/cobra91/better-ccusage)(★92,活跃):ccusage 的多 CLI 分支,宣称同时支持 Claude Code/OpenCode/ZCode/Codex 等(对 ZCode 的支持程度未核实)。

---

## 二、上下文修改类

### 2.1 Hooks:官方最核心的注入/改写杠杆

官方 [Hooks reference](https://code.claude.com/docs/en/hooks) 核实结论,能「改上下文」的事件列全如下:

| 事件 | 能力 | 注入位置 |
|---|---|---|
| `SessionStart` / `SubagentStart` | `additionalContext`(+ `initialUserMessage`、`watchPaths`) | 对话开头 |
| `UserPromptSubmit` / `UserPromptExpansion` | `additionalContext`(不能改写 prompt 本身,exit 2 可拦截) | 随本条 prompt 注入,**每轮都触发** |
| `PreToolUse` | `permissionDecision`(allow/deny/ask)+ **`updatedInput` 重写工具参数** | 工具调用前 |
| `PostToolUse` | **`updatedToolOutput` 替换工具结果**(适合脱敏/裁剪大输出) | 工具结果处 |
| `Stop` / `SubagentStop` | `additionalContext` + 阻止停止 | 轮次结束 |
| `PostModelSwitch` | `additionalContext` | 切换模型后的下一请求 |
| `PreCompact` | 可 exit 2 **阻止压缩**(matcher 区分 `manual`/`auto`) | 压缩前 |

要点:`additionalContext` 超过 10,000 字符会被落盘,Claude 只收到文件路径 + 前 2,000 字符预览(防止 hooks 自己把 context 撑爆);exit 2 是最强阻塞信号;handler 支持 `command`/`http`/`mcp_tool`/`prompt`/`agent` 五种;配置在 settings 的 `hooks` 字段与插件的 `hooks/hooks.json`。

### 2.2 规则文件与 system prompt(声明式注入)

- **CLAUDE.md 体系**([Memory docs](https://code.claude.com/docs/en/memory)):企业/用户(`~/.claude/CLAUDE.md`)/项目/`CLAUDE.local.md` 四层,全部拼接注入;`@path` import 语法(递归 4 层);**`.claude/rules/`** 目录支持 frontmatter `paths` 按路径条件加载(只有操作相关文件时才进 context)。CLAUDE.md 以用户消息形式注入,单文件建议 ≤200 行、超 4 MiB 跳过。
- **AGENTS.md**:v2.1.277+ 通过内建插件支持,`/config` 的 Project instructions 可选「只读 CLAUDE.md / 只读 AGENTS.md / 两者都读」(默认:无 CLAUDE.md 时才读 AGENTS.md)。同仓库本仓即用 AGENTS.md。
- **Auto memory(内建)**:`/memory` 可开关;Claude 自动维护 `~/.claude/projects/<project>/memory/` 下的 `MEMORY.md` 索引 + 主题文件(user/feedback/project/reference 四类),每次会话加载索引前 200 行或 25KB,其余按需读——官方版的持久记忆,无需第三方。
- **`--append-system-prompt`**(CLI 参数):在默认 system prompt 后追加文本(保留工具指引与安全指令);`--system-prompt` 则整段替换。支持 `--append-system-prompt-file`。来源:[CLI reference](https://code.claude.com/docs/en/cli-reference)。
- **Output styles**([docs](https://code.claude.com/docs/en/output-styles)):`/output-style` 切换,自定义样式默认**替换**内建软件工程指令(`keep-coding-instructions: true` 可保留),存放于 `.claude/output-styles/`,随每次请求发送。

### 2.3 压缩与 context editing(删除类)

- **`/compact` + auto-compact**([How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)):`/compact` 可带自定义指令(如 `/compact focus on the API changes`);接近上限时先清除较早工具输出、再总结对话;CLAUDE.md 里可写 "Compact Instructions" 段控制保留什么;压缩可能丢失早期详细指令,且官方有 anti-thrashing 保护(反复塞满几次后停止 auto-compact 并报错)。changelog 证实还有 `autoCompactWindow`/`CLAUDE_CODE_AUTO_COMPACT_WINDOW`(可调压缩窗口)、idle compaction(2.1.300:200K+ 会话闲置约 54 分钟自动压缩)、subagent frontmatter `autoCompactWindow`(2.1.296)。「microcompact」这个术语(先清旧工具输出的那一层)**当前官方 docs 不再使用,仅描述机制**;社区逆向分析(如 [Inside Claude Code](https://y-agent.github.io/inside-claude-code/04-context-compaction.html))称其为 Tier-1 microcompact——细节属逆向,未核实。
- **API 层 context editing**([Context editing docs](https://platform.claude.com/docs/en/build-with-claude/context-editing)):beta header `context-management-2025-06-27`,`context_management.edits` 配置服务端策略:`clear_tool_uses_20250919`(trigger 默认 100,000 input tokens、keep 默认最近 3 个 tool use、`clear_at_least` 保证清除量以摊薄缓存失效、`exclude_tools` 白名单、`clear_tool_inputs` 连参数一起清)、`clear_thinking_20251015`(清旧 thinking 块)。响应 `applied_edits` 报告清除量;`count_tokens` 可预览节省。注意清除会使 prompt cache 前缀失效。
- **Memory tool**([Memory tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)):`{"type": "memory_20250818"}`,**客户端执行**的文件式记忆工具(view/create/str_replace/insert/delete/rename,映射到你的 `/memories` 存储),与 context editing 组合使用:接近阈值时模型先把关键信息写入记忆再被清除。API 文档还明确:服务端 compaction 是长对话首选,context editing 适合精细控制。
- **与 Claude Code 内建机制的关系**:memory tool / context editing 是 Anthropic API 平台侧原语,面向自建 agent 的开发者;Claude Code 的 auto memory 与 auto-compact 是产品化的独立实现,并不直接暴露这些 API 配置。两者是「同一思路在不同层的官方实现」,不要混淆。

### 2.4 MCP 对 context 的占用(官方机制)

[MCP docs](https://code.claude.com/docs/en/mcp) 核实:MCP 工具以 `mcp__server__tool` 名字注册,**工具定义与 server 说明占 context**;输出超 10k token 警告、默认 25k token 截断(`MAX_MCP_OUTPUT_TOKENS` 可调),文本结果超 50k 字符落盘。**Tool Search 现默认开启**——工具定义不再全量注入,Claude 按需用 `ToolSearch` 检索,大幅缓解 MCP 吃 context 的老问题;另有 discovery cache(首次调用才真正连接)。MCP 规范本身允许 server 提供 `instructions` 字段随握手注入 context(见 [MCP spec](https://modelcontextprotocol.io));Claude Code 对该字段的具体处理方式未核实。

### 2.5 第三方修改类工具

**记忆类(持久记忆换 context)**

- **mcp-memory-service**([doobidoo/mcp-memory-service](https://github.com/doobidoo/mcp-memory-service),★2.0k,活跃):自托管记忆后端,一个服务多通道接入(MCP + REST API + CLI + dashboard + OAuth),agent 存决策/知识、语义检索取回(宣称毫秒级),含知识图谱。生态位:想给多个 agent/会话共享一份长期记忆。
- **memory-bank-mcp**([alioshr/memory-bank-mcp](https://github.com/alioshr/memory-bank-mcp),★921,**停更约 14 个月**,最近推送 2025-08-20):把 Cline 社区的「Memory Bank」模式(markdown 文件层级:projectbrief/activeContext 等)做成 MCP server,跨会话维持项目状态。机制是「结构化 markdown 文件 + MCP 工具读写」。
- **claude-memory-compiler**([coleam00/claude-memory-compiler](https://github.com/coleam00/claude-memory-compiler),★1.3k,最近推送 2026-04-06):**hooks 管线**——复制其 `.claude/settings.json` 后,hooks 自动把会话捕获成 daily logs,再用 Claude Agent SDK 编译成知识库供后续注入。是「hooks 注入 + 记忆」组合的代表实现(半年未推送,依赖较新的 Agent SDK 行为,使用前先验证)。
- 相关:[lucasrosati/claude-code-memory-setup](https://github.com/lucasrosati/claude-code-memory-setup)(★1.0k,活跃):基于 Obsidian + Graphify 的持久记忆方案搭建器。Claude Code 内建 auto memory 之后,此类方案的必要性在下降。

**检索类(用检索换 context)**

- **Serena**([oraios/serena](https://github.com/oraios/serena),★30.7k,活跃):MCP toolkit,提供 LSP 级语义检索与编辑(符号查找、引用定位、精确编辑),核心思路是**让 agent 按符号取代码而非整文件塞 context**;内建 memory 系统(记忆跨会话持久化并注入 onboarding)。既省 token 又提升大库导航精度,是检索类的事实标杆。
- **Context7**([upstash/context7](https://github.com/upstash/context7),★63.6k,活跃,Upstash 官方):MCP server,`resolve-library-id` 解析库 ID 后拉取该库**最新文档与代码片段**注入 context,替代模型训练数据里过时的 API 知识。本质是「按需注入外部文档」,对快速演进的框架尤其有用。
- **ConPort(context-portal)**([GreatScottyMac/context-portal](https://github.com/GreatScottyMac/context-portal),★765,**维护放缓**,最近推送 2026-01-27):SQLite 后端的 memory bank MCP,把项目决策/进度/术语存成结构化知识图谱,配合 RAG 取回,并提供自定义指令注入引导 agent 使用。

**规则管理(跨工具同步)**

- **rulesync**([dyoshikawa/rulesync](https://github.com/dyoshikawa/rulesync),★1.55k,活跃,Node CLI):从统一的规则源自动生成各工具的配置文件——rules、commands、MCP、ignore、subagents、skills,覆盖 Claude Code、Cursor、Codex、Gemini CLI 等(支持的完整矩阵见其文档)。解决「一个团队同时用多个 agent CLI 时 CLAUDE.md/.cursorrules/AGENTS.md 各写一份」的同步问题,与 Claude Code `/init` 的规则迁移能力互补。

**仓库打包进 context(人工喂料)**

- **repomix**([yamadashy/repomix](https://github.com/yamadashy/repomix),★29.0k,活跃):把整个仓库打包成单个 AI 友好文件;逐文件 token 计数;`--compress` 用 Tree-sitter 抽取关键代码结构以降低 token;支持 `--remote` 直接打 GitHub 仓库。
- **gitingest**([coderamp-labs/gitingest](https://github.com/coderamp-labs/gitingest),★16.0k,活跃):把 GitHub URL 中 `hub` 换成 `ingest` 即得 prompt-friendly 文本摘要(含 token 计数);也有 CLI 与浏览器扩展,私有库走 PAT。
- **code2prompt**([mufeedvh/code2prompt](https://github.com/mufeedvh/code2prompt),★7.7k,活跃):代码库 → 单个 LLM prompt,Jinja2 模板、token 估算、git diff 整合,自称「context engineering 工具」。

**hooks 注入模板/教学**

- **claude-code-hooks-mastery**([disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery),★3.9k,教学仓库,最近推送 2026-03-04):hooks 模式的教学库,含大量可直接抄的注入/拦截配置模板。此外 [claude-code-templates](https://github.com/davila7/claude-code-templates) 也提供 hooks/agents/skills 的一键生成。

---

## 三、汇总对比表

| 工具 | 类别 | 机制 | 适用场景 | 维护状态(2026-10-24) |
|---|---|---|---|---|
| `/context` `/usage` `/insights` | 监控·官方 | 内建命令,官方数据 | 快速查看占用与用量 | 随 Claude Code 活跃 |
| statusline 接口 | 监控·官方 | settings.json `statusLine` 命令,stdin JSON(含 `context_window.*`) | 自定义常驻余量显示 | 活跃,字段持续演进 |
| OTEL 导出 | 监控·官方 | OTLP/Prometheus 指标+events+traces(beta) | 企业级用量/成本面板 | 活跃 |
| ccusage | 监控·第三方 | 本地解析 transcript JSONL | 事后 token/费用统计 | 活跃 ★19.2k |
| Claude Monitor | 监控·第三方 | 终端实时 UI + 捕获官方 `rate_limits` | 5 小时块配额预警 | 活跃 ★8.8k |
| ccstatusline | 监控·第三方 | statusline stdin JSON 格式化,TUI 配置 | 常驻状态栏(context 余量) | 活跃 ★13.4k |
| CCometixLine | 监控·第三方 | Rust statusline,context window 段 | 高性能美观状态栏 | 活跃 ★3.5k |
| claude-powerline | 监控·第三方 | statusline stdin JSON,powerline 段 | vim 风格状态栏 | 活跃 ★1.2k |
| claude-code-log | 监控·第三方 | JSONL → HTML/MD 转换 | 会话审计/归档 | 活跃 ★1.25k |
| claude-conversation-extractor | 监控·第三方 | JSONL → Markdown 导出 | 导出对话备份 | 放缓(2026-01)★683 |
| opcode | 监控·第三方 | Tauri GUI 读本地会话数据 | 图形化管理/分析 | 活跃 ★22.4k |
| Hooks(UserPromptSubmit 等) | 修改·官方 | `additionalContext` / `updatedInput` / `updatedToolOutput` | 每轮注入规范、改写工具调用与结果、脱敏 | 随 Claude Code 活跃 |
| CLAUDE.md / rules / AGENTS.md | 修改·官方 | 声明式文件注入(层级拼接/条件加载) | 项目规范进 context | 活跃 |
| auto memory(内建) | 修改·官方 | Claude 自维护 memory 目录,索引按需加载 | 跨会话记忆(免第三方) | 活跃 |
| `--append-system-prompt` / output styles | 修改·官方 | system prompt 追加/替换 | 会话级行为定制 | 活跃 |
| `/compact` + auto-compact | 修改·官方 | 清旧工具输出 + 总结压缩 | 长会话续命 | 活跃 |
| Context Editing API | 修改·官方(API) | 服务端 `clear_tool_uses` 等策略 | 自建 agent 的精细清除 | beta,活跃 |
| Memory tool(API) | 修改·官方(API) | 客户端执行的 `/memories` 文件工具 | 自建 agent 的持久记忆 | 活跃 |
| mcp-memory-service | 修改·第三方 | 自托管记忆服务,语义检索 | 多 agent 共享长期记忆 | 活跃 ★2.0k |
| memory-bank-mcp | 修改·第三方 | Memory Bank markdown 文件 + MCP | Cline 式项目状态 | 停更(2025-08)★921 |
| claude-memory-compiler | 修改·第三方 | hooks 捕获会话 → Agent SDK 编译知识库 | 会话知识沉淀 | 半年未推送 ★1.3k |
| Serena | 修改·第三方 | LSP 语义检索 + memories(MCP) | 大库导航省 context | 活跃 ★30.7k |
| Context7 | 修改·第三方 | MCP 按需注入最新库文档 | 过时 API 知识纠偏 | 活跃 ★63.6k |
| ConPort | 修改·第三方 | SQLite 知识图谱 memory bank(MCP) | 结构化项目上下文 + RAG | 放缓(2026-01)★765 |
| rulesync | 修改·第三方 | 单一规则源 → 各工具配置文件生成 | 多 CLI 团队规则同步 | 活跃 ★1.55k |
| repomix | 修改·第三方 | 仓库打包单文件 + token 计数 + Tree-sitter 压缩 | 人工喂整库给任意 LLM | 活跃 ★29.0k |
| gitingest | 修改·第三方 | URL 变换即得 repo 文本摘要 | 快速给网页端 LLM 喂库 | 活跃 ★16.0k |
| code2prompt | 修改·第三方 | 模板化代码库 → prompt | 定制化喂料 | 活跃 ★7.7k |

## 四、局限与注意点

1. **Transcript JSONL 是私有格式**。`~/.claude/projects/*.jsonl` 无官方 schema、无兼容承诺(第三方 README 自己也称 undocumented),Claude Code 版本迭代随时可能变字段——所有读 JSONL 的第三方(ccusage、claude-code-log、extractor、opcode 的部分功能)都建立在这个脆弱地基上,升级后失效是常态,issue 区常见「新版本解析不出」。
2. **statusline stdin JSON 同样在演进**。官方文档明确列出多个「可能缺失/为 null」的字段(`current_usage` 首次 API 调用前为 null、`rate_limits` 仅订阅用户等),statusline 脚本必须做回退;字段增删也会导致第三方 statusline 偶发显示错误。
3. **hooks 注入是逐轮重复计费**。`UserPromptSubmit` 的 `additionalContext` **每一轮 prompt 都会重新注入**,10KB 的注入 = 每轮多付 10KB 输入 token(还要考虑缓存命中);官方为此加了 >10,000 字符落盘机制,自己写 hooks 时同样要克制。`SessionStart` 只注入一次,语义不同。
4. **压缩有损**。auto-compact 明确可能丢失会话早期的详细指令;`/compact` 的自定义指令只能引导不能保真;context editing 的 `clear_tool_uses` 清除后不可逆(占位文本替代),且清除会使 prompt cache 前缀失效——官方用 `clear_at_least` 让「省下的 token > 重写缓存的成本」,自行调参时要算这笔账。
5. **microcompact 属灰色地带**。当前官方文档只描述「先清旧工具输出再总结」的机制而不用该词;具体分层细节来自社区逆向(Inside Claude Code 等),不应作为稳定依赖。
6. **监控数字都是估算**。ccusage/Claude Monitor 的费用是本地标价估算,不含订阅折扣/企业费率;权威数字只在 Console 账单与官方 `rate_limits`。
7. **memory tool 的安全责任在客户端**。API memory tool 完全由你的代码执行文件操作,路径遍历防护(`../`、URL 编码绕过)是文档明示的实现者义务;第三方 memory MCP server 同理,接进 Claude Code 前评估其写入范围。
8. **仓库改名/迁移风险**。opcode(原 getAsterisk/claudia → winfunc/opcode)证明了 star 高的项目也会换组织,引用旧 URL 会 404。
9. **star 数与活跃度是快照**。本文所有 star/推送日期为 2026-10-24 经 GitHub API 核实的数值,阅读时请以仓库现状为准。
