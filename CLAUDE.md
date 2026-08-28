# CLAUDE.md — testcase-workbench

通用测试用例工作台，承担**两个工作流**：
1. **生成**：给定需求（庄周产品稿、禅道 story、Walle 接口、17work 资料包）→ 输出 Markdown 测试点 + Markdown 测试用例 + XMind 用例文件
2. **补充优化**：给定现有 XMind + 新设计文档 → 保留主框架，只追加缺失测试点

> **本项目不含业务知识库**。业务知识由独立的 `business-knowledge` 项目提供，通过环境变量 `BUSINESS_KNOWLEDGE_ROOT` 接入。
> 不设置该变量时本项目照常运行，只是没有业务术语辅助。

## 新成员 Setup

工作流依赖两个**项目级 agent**（`.claude/agents/`），随 repo 分发，clone 即用，无需安装。

首次使用只需登录内部 CLI（触发 OAuth）：

```bash
npx -y --registry=http://npm.dc.servyou-it.com @servyou-ai/17work-cli@latest login
```

启动 Claude Code，说"生成测试用例"或"补充 XMind"即可触发 agent。

## 业务知识库接入（**可选**）

如果团队有独立的知识库项目，设置环境变量：

```powershell
$env:BUSINESS_KNOWLEDGE_ROOT = "D:\Trae CN\projects\business-knowledge"
```

设置后 agent 会自动读取 `$BUSINESS_KNOWLEDGE_ROOT/knowledge/` 下的术语表和文档。

## Skill 路由表（看到对应 URL/关键词即调用全局 skill）

| 输入 | 全局 skill | 命令 |
|---|---|---|
| `chuangtzu.dc.servyou-it.com` 链接 | `chuangtzu-skill` | `npx -y --registry=http://npm.dc.servyou-it.com @servyou-ai/chuangtzu-cli@latest -u <url> -t md` |
| `zentao.dc.servyou-it.com` 链接 | `zentao-skill` | `node ~/.claude/skills/zentao-skill/scripts/cli.cjs zentao url <url>` |
| `walle.dc.servyou-it.com` 链接 | `walle-skill` | `node ~/.claude/skills/walle-skill/scripts/cli.cjs walle url <url>` |
| `baymax.dc.servyou-it.com` 链接 | `usecase-skill` | `node ~/.claude/skills/usecase-skill/scripts/cli.cjs usecase url <url>` |
| `17work.dc.servyou-it.com` Spec 链接 | `spec-skill` | `npx -y --registry=http://npm.dc.servyou-it.com @servyou-ai/17work-spec-cli@latest spec download --url <url>` |
| `17work.dc.servyou-it.com` 知识库链接（`/read/book/<X>/<id>`） | `forum-skill` | `npx -y --registry=http://npm.dc.servyou-it.com @servyou-ai/17work-cli@latest docs download <postsId> -o .` |
| 庄周 `17boot` 业务项目 | `17boot-skill` | 拉取远端激活说明 + 业务知识 |
| `用例参考.xmind` 格式模板（层级结构参考，含占位说明文字） | `xmind` skill | `python3 ~/.claude/skills/xmind/parse_xmind.py 用例参考.xmind` |
| `202607.xmind` 具体用例（参照格式模板编写的真实用例） | `xmind` skill | `python3 ~/.claude/skills/xmind/parse_xmind.py 202607.xmind` |
| "生成测试用例" / "出测试点" | `testcase-generator` agent（**项目级**） | `.claude/agents/testcase-generator.md` |
| 现有 XMind + 新设计文档，"补充"/"完善"/"优化这份 XMind" | `testcase-supplementer` agent（**项目级**） | `.claude/agents/testcase-supplementer.md` |

**关键原则**：不要用 Playwright 抓取以上平台的页面 — 它们的全局 CLI/skill 已能直接输出结构化内容（JSON/Markdown）。

## Agent 调用入口

按用户意图**派发给对应全局 subagent**（Claude Code 自动按 description 匹配）：

| 用户意图 | Agent | 流程封装 |
|---|---|---|
| 从零生成用例 | `testcase-generator` | 多源拉取 → 整合 → 生成测试点 → 生成测试用例 → `md2xmind.py` → XMind |
| 补充优化现有用例 | `testcase-supplementer` | 解析现有 XMind → 拉新文档 → 识别补充点 → 生成 plan → `xmind-edit.py apply` → 输出 `<原名>-new.xmind` |

- 两个 agent 都定义在 `.claude/agents/`（**项目级**，随 repo 分发，任意 clone 该项目即用）
- 触发关键词：见各 agent 的 `description` 字段

> **关于 subagent 项目级**：`.claude/agents/` 下的 agent 仅限当前项目使用，但随 repo 分发，clone 即可用；`~/.claude/agents/` 下的才全局可用。

### 复用原则（项目硬约束）
- **能复用就复用，能扩展就扩展，减少不必要的新增**：
  - 读 XMind → `scripts/parse_xmind.py`（**不写新读 XMind 的代码**）
  - 拉文档 → 庄周/禅道/Walle/17work/Baymax 全局 skill（**不自己写 HTTP 抓取**）
  - 写/改 XMind → `scripts/xmind-edit.py`（**不自己写 XML**）
  - 全量生成 XMind → `scripts/md2xmind.py`（**不重写转换器**）
- agent 本身**只是"调度 + 推理"层**，不引入新脚本/工具

## 输出文件位置

| 类型 | 路径 | 命名 |
|---|---|---|
| 需求快照（中间产物） | `requests/{需求名称}-{时间戳}/` | 含 `requirement.md`、`chuangtzu/`、`walle/`、`_sources.md` |
| 补充计划 JSON（仅 supplement 场景） | `requests/{需求名称}-{时间戳}/supplement-plan.json` | 由 `testcase-supplementer` 生成 |
| 补充变更报告（仅 supplement 场景） | `requests/{需求名称}-{时间戳}/supplement-changelog.md` | 由 `testcase-supplementer` 生成 |
| 历史测试沉淀（中间产物） | `_history/{关键词}-{日期}.md` | 用户提供 Baymax URL 时生成 |
| 测试点 | `testpoints/{需求名称}-测试点-{序号}.md` | 序号从 1 开始 |
| 测试用例（Markdown） | `testcases/{需求名称}-测试用例-{序号}.md` | 序号与测试点一致 |
| 测试用例（XMind，生成场景） | `xmind/{需求名称}-测试用例-{序号}.xmind` | 由 `scripts/md2xmind.py` 从 Markdown 生成 |
| 测试用例（XMind，补充场景） | `xmind/{原名}-补充-{YYYYMMDD}.xmind` 或 `<原路径>-new.xmind` | 由 `scripts/xmind-edit.py apply` 应用 supplement-plan.json 生成 |

## 测试用例结构硬规则（**生成 + 补充优化都遵循**）

1. **每个被测功能必须有 功能用例 + 接口用例 成对出现**
2. **功能用例的前置条件必须列出接口**——元数据块 `前置条件:` 字段用 `调用的接口:` 子项写明：
   ```
   > 优先级: P1 | 关联需求: REQ_XXX | 前置条件: 调用的接口: /api/itcrmweb/follow/saveFollowRecord、/api/itcrmweb/contact/getNotRelationCallRecord | 测试数据: ...
   ```
3. **接口用例不区分新增/修改**——H5 标题用接口中文名，不加前后缀，**不写**"本期新增/改造"等时间标记
4. **新增接口的 URL 本身是一条优先级 3 用例**——形式 `查询 {完整URL}`，仅用于反查接口所属模块归属，无实际业务含义
   - **这条用例必须带 4 字段元数据 + priority-3 marker**——是"补充场景不强制加元数据"风格的唯一例外
5. **功能用例的前置条件子节点用 `flag-red`（红旗）标记**——而不是在 notes 里写"前置条件: xxx"文字。接口用例不需要 flag-red。

**Markdown 标题层级**（XMind 兼容性硬性要求）：
```
H1 团队名（如"代账合规"）→ XMind 根节点
H2 迭代名（如"代账合规8月迭代"）→ XMind 画布标题
H3 日期（如 20260827）→ 一级节点
H4 【模块名】需求名称（**必填**，不可省略）
H5 功能点（必带元数据块）
  - 条件/场景（bullet）
    - 预期结果（nested bullet，缩进 2 空格）← 这是"H6"，用 nested bullet 表示
```

**预期结果格式**：
- **使用 nested bullet**（`  - 预期结果`），**不使用 H6 标题**
- 条件/场景作为一级 bullet（`- `），预期结果作为其嵌套子项
- 原因：md2xmind.py 将 nested bullet 转为 XMind 子节点，视觉上条件与结果成组

**条件 vs 结果的判断**（易错点）：
- **条件 = 测试人员执行的操作或设置的场景**（如"点击按钮"、"查看卡片"、"接口返回空"）
- **结果 = 操作后可验证的现象**（如"页面跳转"、"文案展示"、"弹窗打开"）
- **同一操作下的多个观察维度合并为一个条件**，多个预期结果作为其子项：
  ```
  - 查看兜底卡片           ← 条件（一个操作）
    - 卡片名称显示"X"      ← 结果1（观察维度A）
    - 文案展示"Y"          ← 结果2（观察维度B）
    - 样式为 [icon] [按钮] ← 结果3（观察维度C）
  ```
- **反模式**：把"卡片名称"、"卡片文案"、"卡片样式"拆成三个独立的条件→结果对（错误）
- **判断方法**：问自己"这是测试人员要做的操作吗？" → 是=条件，是观察到的现象=结果

**命名**：测试点与测试用例的 `{需求名称}-{序号}` 必须一一对应。

## 优先级规则（P1-P4，按**执行要求**区分）

| 优先级 | 含义 | 适用场景 | 执行要求 |
|---|---|---|---|
| **P1** | 阻塞性场景 | 核心主流程必经节点 / 关键数据正确性 / 一旦错就影响全局 | 冒烟必含、回归必跑 |
| **P2** | 重要功能 | 正常业务场景 / 主要功能路径 / 业务规则正例 | 正常回归必跑 |
| **P3** | 辅助功能 | 排序 / 搜索 / 标签 / 导出 / 头部信息 / 提示文案 / Excel 格式 / 新接口 URL 反查 | 按需测试 |
| **P4** | 极端场景 | 空列表 / null 值 / 极端输入 / 极少触发场景 | 有时间再测 |

**四步判断流程**：
1. 是否阻塞性 / 核心流程必经？→ **P1**
2. 是否重要功能 / 正常业务场景？→ **P2**
3. 是否辅助功能 / 边界场景？→ **P3**
4. 是否极端场景 / 极少触发？→ **P4**

**反模式**：
- ❌ 全部用例标 P1 → 没有分层，回归跑不动
- ❌ 头部信息 / 提示文案标 P1 → 归 P3
- ❌ 导出 / 排序标 P1/P2 → 归 P3
- ❌ P4 写成正常功能 → P4 只写极端场景（空列表/null/极端输入）
- ❌ 用"用户重要程度"判断 → 应该用"执行要求"判断

## 格式规范

**参考文件**（两者结合学习）：
- `用例参考.xmind` — 格式模板，含占位说明文字，展示层级结构规范
- `202607.xmind` — 具体用例，参照格式模板编写的真实用例

**默认风格：画布 2（按业务需求/迭代组织）**
- H3 业务需求标题以 `【模块名】` 开头
- 用户明确说"按功能模块全量沉淀"时才用画布 1 风格
- 元数据块**强制**：`> 优先级: P1/P2/P3/P4 | 关联需求: ... | 前置条件: ... | 测试数据: ...`（4 字段全填）

**模块拆分原则**：
- 简单需求：少拆（深度 4-5 层）
- 复杂需求：按需拆（满足任一：多模块/多角色/多平台/多 API → 拆出独立模块）
- 反模式：每个 H4 下仅 1-2 用例（拆太碎）/ 同一功能在多 H4 重复（应合并）

## 工具脚本

| 脚本 | 用途 | 依赖 |
|---|---|---|
| `scripts/md2xmind.py` | Markdown → XMind 全量转换（生成场景） | Python 3.8+（无第三方依赖） |
| `scripts/xmind-edit.py` | XMind 增量编辑（增/删/改 节点，**统一脚本**） | Python 3.8+（无第三方依赖） |
| `scripts/search-related-docs.py` | 全文检索相关文档（grep 知识库 + 查 Baymax 索引） | Python 3.8+ |

> 知识库同步脚本（`sync-knowledge.ps1`、`sync-baymax.ps1`、`build-baymax-index.py`）已移至独立的 `testcase-knowledge` 项目。

### `scripts/xmind-edit.py` 子命令

| 子命令 | 用途 | 典型场景 |
|---|---|---|
| `add` | 在父节点下添加子节点 | 补充单个遗漏测试点 |
| `remove` | 删除指定节点 | 删除已废弃/重复节点 |
| `apply` | 按 JSON 计划批量应用增/删/改 | **核心**：配合 `testcase-supplementer` agent 输出补充计划 |
| `set-notes` | 更新节点 notes（4 字段元数据） | 补全/修正元数据 |
| `set-marker` | 更新节点优先级 marker | 调整优先级 |

**默认行为**：输出 `<原名>-new.xmind`，不覆盖原文件；加 `--in-place` 原地修改。

**JSON 计划格式**（`apply` 用）：
```json
{
  "operations": [
    {"op": "add", "parent": "...", "child": "...", "level": 5, "notes": "...", "marker": "priority-1"},
    {"op": "remove", "title": "...", "parent": "..."},
    {"op": "set-notes", "title": "...", "notes": "..."},
    {"op": "set-marker", "title": "...", "marker": "priority-2"}
  ]
}
```

详细见 `python scripts/xmind-edit.py <subcommand> --help`。

## 用例生成后检查（**生成 + 补充优化都必须执行**）

每次生成或更新用例后（`testcase-generator` / `testcase-supplementer` 输出成品前），**必须**对最终 Markdown + XMind 执行一轮自检，逐项确认：

### 检查项

1. **内容正确性**
   - 接口 URL、字段名、枚举值是否与需求快照（`requests/.../requirement.md`、`walle/`、`chuangtzu/`）一致，**禁止臆测**
   - 功能逻辑是否覆盖需求文档中声明的所有分支（正向/逆向/边界/异常）
   - 每条预期结果是"预期"而非操作步骤（步骤应可执行，结果应可验证）

2. **格式规范**
   - 标题层级完整（H1→H2→H3→H4→H5），H4 必填
   - 每个 H5 必须带 4 字段元数据块（`优先级 | 关联需求 | 前置条件 | 测试数据`），**缺一不可**
   - 功能用例的 `前置条件:` 里必须含 `调用的接口:` 子项
   - 接口 H5 用中文名，不加"新增/改造/本期"等时间标记
   - 补充场景下，新增接口 URL 那条**例外**必须带元数据 + priority-3 marker

3. **优先级合理性**
   - 按本文「优先级规则」四步判断流程逐条验证
   - 禁止全量都是 P1 或都是 P3，必须分层

4. **测试点完整性（对照需求与设计）**
   - 逐条比对需求文档 / 设计稿：每个功能点、每个接口、每条业务规则是否都有对应 H5 覆盖
   - **功能用例 + 接口用例必须成对出现**（被测功能既有 UI 层用例也有接口层用例）
   - 补充场景：对比原 XMind + 新设计文档，确认新设计引入的功能点/接口/规则**全部**有新增节点落地，无遗漏
   - 发现缺失 → 回修后再输出，**禁止带着遗漏交付**

### 输出要求

- 自检通过 → 输出成品（Markdown + XMind）
- 自检发现问题 → 先修复、复检通过后再输出，**并在最终回复里简短报告修了什么**（无需逐条列出全部检查项）

> 此规则对 `testcase-generator` 和 `testcase-supplementer` 均强制生效，是交付前的最后一道关卡。

## 规则文件维护原则

本项目规则分散在三个文件，**调整用例规则时请按此分工定位，不要错放**：

| 文件 | 负责 | 不负责 | 示例 |
|---|---|---|---|
| **`CLAUDE.md`**（本文件） | 项目级权威规则源：结构硬规则、优先级规则(P1-P4)、格式规范、生成后检查项 | 不写 agent 工作流细节 | "H4 必填"、"P1=阻塞性"、"nested bullet" |
| **`.claude/agents/testcase-generator.md`** | 生成用例的**工作流**（阶段 0-8） | 不重复 CLAUDE.md 已有规则，引用即可 | "先读庄周→再读 Baymax→生成测试点→导出 XMind" |
| **`.claude/agents/testcase-supplementer.md`** | 补充优化的**工作流** + 补充特有规则 + 风格约束 | 不重复 CLAUDE.md 已有规则，引用即可 | "不强制加元数据"、"优先改写 H5"、"散文+缩进" |

**维护原则**：
1. **CLAUDE.md 是唯一规则权威** — 结构/格式/优先级规则只在这里写一份
2. **Agent 文件不重复规则** — 阶段 0 读 CLAUDE.md 获取共享规则，自身只描述工作流
3. **新增规则先判断归属**：
   - 影响两个 agent 的 → 写 CLAUDE.md
   - 只影响生成流程的 → 写 generator
   - 只影响补充流程的 → 写 supplementer
4. **agent 定义在 `.claude/agents/`** — 本项目 agent 是**项目级**（随 repo 分发），与 CLAUDE.md 同级维护

## 归档说明

⚠️ **`.trae/rules/` 下的 4 份旧规则文件已废弃**，仅作历史归档保留。**请勿使用**，全部内容已被以下文件取代：

| 旧文件 | 替代为 |
|---|---|
| `.trae/rules/测试用例生成整体流程规则.md` | `.claude/agents/testcase-generator.md`（项目级 subagent） |
| `.trae/rules/生成测试点规则.md` | `.claude/agents/testcase-generator.md` |
| `.trae/rules/基于测试点生成测试用例规则.md` | `.claude/agents/testcase-generator.md` |
| `.trae/rules/测试用例设计.md` | `.claude/agents/testcase-generator.md` |
