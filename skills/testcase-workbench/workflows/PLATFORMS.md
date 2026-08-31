# 跨平台接入说明

本 skill 的**核心资产**（脚本 + 规则 + 模板）**平台无关**，可在任意 Agent / 智能体平台使用。以下是各平台的接入方式和差异说明。

## 资产分层

| 资产 | 位置 | 平台相关度 | 说明 |
|---|---|---|---|
| 脚本层 | `scripts/*.py` | ✅ 完全无关 | 纯 Python stdlib，零第三方依赖，任何环境可跑 |
| 规则层 | `references/用例规则.md` | ✅ 完全无关 | 用例结构/优先级/格式规范，纯文本 |
| 模板层 | `templates/用例参考.xmind` | ✅ 完全无关 | 层级结构参考 |
| 工作流（提示词） | `workflows/*.md` | ⚠️ 通用提示词 | 提炼成平台无关的系统提示词，可直接粘贴 |

## 接入通用步骤

1. **此时上传脚本**：把 `scripts/*.py` 上传到平台（或让平台运行时能访问到）
2. **挂载知识**：把 `references/用例规则.md` + `templates/用例参考.xmind` 挂到平台知识库/检索
3. **创建智能体**：复制 `workflows/generate.md`（生成）或 `workflows/supplement.md`（补充优化）全文到系统提示词/人设框
4. **配置连接器**：庄周/禅道/Walle/17work/Baymax（或允许用户粘贴文档内容）
5. **确保 Python 可执行**：`md2xmind.py` / `xmind-edit.py` 需平台能执行 Python 3.8+，才能产出 XMind

## 平台兼容矩阵

> 以下是常见场景的判断。是否原生支持请以目标平台官方文档为准。

| 平台 | SKILL.md 识别 | workflows/ 通用提示词 | Python 脚本执行 | `.claude/agents/` subagent |
|---|---|---|---|---|
| **Claude Code** | ✅ | ✅（可作参考/内联） | ✅ | ✅（本 skill 已移除，改用提示词） |
| **通用 AI 应用平台**（自研/Coze/百炼等） | — | ✅ 直接粘贴到人设 | 🔶 视平台是否支持代码沙箱 | ❌ 不识别（已移除） |
| **Cursor / Windsurf 等 IDE Agent** | 🔶 各自格式 | ✅ 可放 rules/提示词 | ✅ | ❌ |
| **任意 Agent 框架** | 🔶 | ✅ | ✅ | ❌ |

**关键结论**：本 skill 已把能力从 Claude 专属的 `.claude/agents/` **降级为通用提示词（`workflows/`）+ 平台无关脚本**。因此：
- 依赖数据连接器（庄周/禅道等）的平台 → 提示词照抄 + 平台侧配连接器
- 平台能跑 Python → 三样产物（测试点/用例/XMind）全部可落地
- 平台不能跑 Python → 只能产出 Markdown，XMind 由支持 Python 的环境离线补跑

## 依赖降级策略

- 平台没有庄周/禅道/Walle/17work/Baymax 连接器 → 提示用户**直接粘贴文档内容**，照常生成用例，不中断
- 平台不能执行 Python → Markdown 产物保留，XMind 提示离线补跑
- 无业务知识库（`BUSINESS_KNOWLEDGE_ROOT`）→ 直接使用需求文档术语，不强行套业务词汇

## 与本 skill 的关系说明

`workflows/*.md` 是从本项目 `.claude/agents/`（Claude Code 项目级 subagent）提炼的**平台无关版本**。二者逻辑一致，表述不同：
- 项目内 `.claude/agents/` 是 Claude Code 专用调度层（含 `tools:`/`model:` frontmatter）
- `workflows/*.md` 是通用提示词，去掉了所有 Claude 专属语法，供其他平台直接使用

> 修改工作流逻辑时，若同时影响项目 agent，需两处同步（项目 agent + `workflows/*.md`）。
