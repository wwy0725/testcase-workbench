---
name: testcase-workbench
description: |
  生成/补充优化测试用例工作台（平台无关）。当用户说以下任意一种时使用：
  - "生成测试用例" / "出测试点" / "帮我做测试用例" / "分析这个需求"
  - 提供庄周/禅道/Walle/17work/Baymax 需求 URL 让出用例
  - "补充测试用例" / "补漏" / "完善/优化这份 XMind" / "补全这份用例"
  - "根据这几份文档补这份 XMind"
  产出：Markdown 测试点 + Markdown 测试用例 + XMind 用例文件。
  工作流以平台无关的通用提示词提供（workflows/），脚本纯 Python stdlib（零第三方依赖），可跨平台。

  不要用于：纯查看需求/接口（用 walle/zentao 各自 skill）、UI 自动化测试、代码 review。
---

# Testcase Workbench Skill

通用测试用例生成/补充优化工作台。承担**两个工作流**：

1. **生成**：给定需求（庄周产品稿、禅道 story、Walle 接口、17work 资料包）→ 输出 Markdown 测试点 + Markdown 测试用例 + XMind 用例文件
2. **补充优化**：给定现有 XMind + 新设计文档 → 保留主框架，只追加缺失测试点

> **本项目不含业务知识库**。业务知识由独立的 `business-knowledge` 项目通过环境变量 `BUSINESS_KNOWLEDGE_ROOT` 接入。不设置时照常运行，只是没有业务术语辅助。

## 适用场景

- 从零生成测试用例（多源需求 → 测试点 → 测试用例 → XMind）
- 对现有 XMind 增量补充（保留主框架，只补缺失测试点）

## 使用方法

**本 skill 已平台无关化**：能力以两套形式提供——

1. **工作流提示词**（`workflows/`）：可直接粘贴到任意平台智能体的系统提示词/人设框，推荐跨平台使用
2. **工具脚本**（`scripts/`）：纯 Python stdlib，供工作流调用产出 XMind

触发关键词（各平台按自身机制匹配 `description` 字段）：

```
生成测试用例 / 出测试点 / 补充这份 XMind / 优化这份 XMind
```

非 skill 式平台（手动配置智能体、粘贴提示词）：见 [workflows/PLATFORMS.md](workflows/PLATFORMS.md)。

## 目录结构

```
testcase-workbench/
├── SKILL.md                       ← 本文件（入口）
├── workflows/                     ← 平台无关的工作流（通用智能体提示词）
│   ├── generate.md                ← 生成测试用例（可直接粘贴为智能体提示词）
│   ├── supplement.md              ← 补充优化现有 XMind（可直接粘贴为智能体提示词）
│   └── PLATFORMS.md               ← 跨平台接入说明
├── scripts/                       ← 工具脚本（纯 Python stdlib，零第三方依赖）
│   ├── parse_xmind.py             ← 读 XMind → Markdown 树
│   ├── md2xmind.py                ← Markdown → XMind 全量转换
│   ├── xmind-edit.py              ← XMind 增量编辑（增/删/改）
│   └── search-related-docs.py     ← 全文检索知识库 + Baymax 索引（需知识库时）
├── references/
│   └── 用例规则.md                ← 用例结构硬规则 + 优先级规则 + 格式规范
└── templates/
    └── 用例参考.xmind             ← 格式模板（层级结构参考）
```

## 前置依赖清单（跨平台安装必读）

本 skill 自带能力（脚本/工作流/规则）**零依赖**。但访问公司平台需外部 skill/CLI，它们是**独立安装的前置条件**，不随本 skill 打包：

| 能力 | 依赖来源 | 接入方式 | 是否必装 |
|---|---|---|---|
| 生成/补充核心逻辑 | 本 skill（`scripts/` + `workflows/`） | 随 skill 自带 | ✅ 必装 |
| 庄周（产品稿） | `@servyou-ai/chuangtzu-cli`（npm） | `npx -y --registry=http://npm.dc.servyou-it.com @servyou-ai/chuangtzu-cli@latest`（平台无关，直接跑） | 按需 |
| 禅道（需求） | `zentao-skill` | 平台连接器机制安装；命令行调用见 `workflows/generate.md`（`<skill_dir>` 占位） | 按需 |
| Walle（接口） | `walle-skill` | 同上 | 按需 |
| Baymax（历史用例） | `usecase-skill` | 同上 | 按需 |
| 17work（Spec/知识库） | `@servyou-ai/17work-cli`、`@servyou-ai/17work-spec-cli`（npm） | `npx -y --registry=... @servyou-ai/17work-cli@latest login`（平台无关） | 按需 |
| 业务知识库 | `$BUSINESS_KNOWLEDGE_ROOT`（独立项目） | 设置环境变量指向知识库项目 | 可选 |

**安装后首次使用**：需登录内部 CLI（触发 OAuth）：
```bash
npx -y --registry=http://npm.dc.servyou-it.com @servyou-ai/17work-cli@latest login
```

**依赖降级**：外部 skill 未安装时，工作流会自动探测并降级——请用户直接粘贴文档内容，照常生成用例，不中断。核心脚本 `parse_xmind.py` / `md2xmind.py` / `xmind-edit.py` **不依赖任何外部 skill**，离线可用。

## 工作流

完整工作流见 `workflows/` 目录（平台无关提示词）：

### 工作流 1：生成测试用例 → [workflows/generate.md](workflows/generate.md)

```
多源拉取（庄周/禅道/Walle/17work/Baymax）→ 整合 → 生成测试点 → 生成测试用例 → md2xmind.py → XMind
```

产物固定三个：
- `testpoints/{需求名称}-测试点-{序号}.md`
- `testcases/{需求名称}-测试用例-{序号}.md`
- `xmind/{需求名称}-测试用例-{序号}.xmind`

### 工作流 2：补充优化现有 XMind → [workflows/supplement.md](workflows/supplement.md)

```
解析现有 XMind → 拉新文档 → 识别补充点 → 生成 plan → xmind-edit.py apply → 输出 <原名>-new.xmind
```

产物固定两个：
- `xmind/{原名}-补充-{YYYYMMDD}.xmind`（默认输出，由 `xmind-edit.py apply` 生成）
- 变更报告（stdout + `requests/{name}-{YYYYMMDD}/supplement-changelog.md`）

## 工具脚本

| 脚本 | 用途 | 依赖 |
|---|---|---|
| `scripts/parse_xmind.py` | 读 XMind → Markdown 树（含多画布支持） | Python 3.8+（无第三方依赖） |
| `scripts/md2xmind.py` | Markdown → XMind 全量转换（生成场景） | Python 3.8+（无第三方依赖） |
| `scripts/xmind-edit.py` | XMind 增量编辑（增/删/改，统一脚本） | Python 3.8+（无第三方依赖） |
| `scripts/search-related-docs.py` | 全文检索知识库 + Baymax 索引 | Python 3.8+（无第三方依赖） |

### 跨平台注意

- 所有脚本**纯 Python stdlib**，`python3`（或 `python`）可直接运行，无需安装任何包
- Windows 下用 `python`，macOS/Linux 下用 `python3`；脚本内部已强制 UTF-8 输出，规避 GBK 编码问题
- 脚本路径用 `<skill_dir>/scripts/xxx.py` 相对定位，不写死绝对路径

## 详细规则

用例结构硬规则、优先级规则（P1-P4）、格式规范、生成后检查项 → 见 [references/用例规则.md](references/用例规则.md)（工作流启动时加载）。

## 跨平台说明

- 本 skill 已去掉 Claude 专属的 `.claude/agents/` subagent，能力降级为**通用提示词（workflows/）+ 平台无关脚本**
- 数据连接器（庄周/禅道/Walle/17work/Baymax）外部化为前置依赖，可降级为用户粘贴内容
- 平台能执行 Python → 三样产物全部可落地；不能 → 只出 Markdown，XMind离线补跑
- 详细接入见 [workflows/PLATFORMS.md](workflows/PLATFORMS.md)
