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

**关键原则**：以上平台的页面用全局 CLI/skill 拉取（能直接输出结构化内容 JSON/Markdown），**不用 Playwright 抓取页面**。庄周设计稿 CLI 输出无结构化正文时，用 `scripts/extract_mockup_texts.py` 从 raw JSON 提取**全量文本清单**（逐字段枚举零丢失），并下载清单中 imagePath 指定的**设计稿原图做视觉读取**——部分标注全文（如字段删除/改名说明）只在图片里，文本清单 + 原图合看后才整理需求快照，无需开浏览器。

**raw HTML JS 注入检查（强制）**：17win/snack 类 HTML 需求稿中，最终版内容常由 `<script>` 的 `innerHTML`/`insertAdjacentHTML` 动态注入或改写（整节新增、章节重排、徽章标注、说明列替换、表格改写），静态文本提取会整节漏掉。拉取 raw HTML 后必须先扫描 `<script>` 段：grep `innerHTML`、`insertAdjacentHTML`、模板字符串里的章节标题与说明文字，把注入与改写内容合并进需求快照并标注「最终版改写，覆盖静态初稿」，**禁止只按静态正文出用例**。实例见 用例规则.md「教训实例」。

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

### Skill 打包同步（项目硬约束）

本项目可打包成跨平台 skill，产物在 `skills/testcase-workbench/`。skill 包是**通用提示词 + 脚本**形式，不含 Claude 专属的 `.claude/agents/`。**agent 工作流存在两份表述**，修改时必须两处同步：

- 源：`.claude/agents/`（Claude Code 项目级调度层，含 `tools:`/`model:` frontmatter）
- 通用版：`skills/testcase-workbench/workflows/`（去 Claude 专属语法，可供任意平台智能体直接粘贴）

**同步关系**：改项目 agent 的工作流逻辑时，把同样逻辑同步到 `workflows/*.md`（去 frontmatter、去 Claude 平台词汇、改通用表述）。项目 agent 保留不动，跨平台能力由 workflows 承载。

| 改了什么 | 必须同步到 |
|---|---|
| `.claude/agents/*.md`（工作流逻辑） | `skills/testcase-workbench/workflows/` |
| `scripts/` 下脚本 | `skills/testcase-workbench/scripts/` |
| CLAUDE.md 的 结构硬规则/优先级/格式规范/方法速查表+决策树 章节（核心规则，双份维护） | `skills/testcase-workbench/references/用例规则.md` |
| `用例参考.xmind` | `skills/testcase-workbench/templates/` |

> **细则无副本**：方法细则（各方法操作要点、错误推测常见方向、方法-优先级映射）与生成后检查清单的**唯一权威**是 `skills/testcase-workbench/references/用例规则.md`——CLAUDE.md 只留指针，改细则只动那一个文件，无需双向同步。

**同步命令**（改完跑一次）：
```bash
cd "d:/Trae CN/projects/testcase-workbench"
cp scripts/md2xmind.py scripts/xmind-edit.py scripts/search-related-docs.py scripts/extract_mockup_texts.py skills/testcase-workbench/scripts/
```
> `workflows/*.md` 是通用提示词，需手工从 `.claude/agents/*.md` 提炼改写（去 frontmatter / Claude 专属语法），不直接 cp。改 generator 同步 `workflows/generate.md`，改 supplementer 同步 `workflows/supplement.md`。

> **注意**：`scripts/parse_xmind.py` **不在**项目 `scripts/` 下（原项目无此文件），它只在 `~/.claude/skills/xmind/`（源）和 `skills/testcase-workbench/scripts/`（skill 副本）两处。改 parse_xmind 时同步这两处，项目 `scripts/` 不维护它。

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

1. **材料涉及接口时，每个被测功能必须有 功能用例 + 接口用例 成对出现；材料不涉及接口时不写接口用例**——判断依据：需求材料含 Walle 接口文档、或需求正文明确给出接口 URL/字段 → 视为涉及接口，按成对规则出；否则只出功能用例，**不臆造接口用例、不在功能用例里臆测标注接口**（前置条件不写"调用的接口"、测试数据不臆测接口字段）。**接口用例归属**：接口用例不并入业务模块，统一放在名为「接口」的固定模块下——H3「接口」→ H4 接口中文名称（每个接口一个节点）→ H5 接口用例（带元数据块）；结构参考 `用例参考.xmind`（其 http/dubbo 协议分组层级比生成产物深，生成时不加协议层）
2. **前置条件按需添加，只写执行前需单独准备的业务前提**——数据/造数准备（数据存在性，如"往来对账列表存在多条不同账龄的往来单位"）、配置状态（授权/会员/白名单、角色配置、功能开关、已命中卡片）、业务逻辑依赖（如"客户已存在未读跟进记录"、"商机处于跟进中状态"、"票家家授权有效"）。**不写三类废话性前提**：① **通用背景类**——任何用例都适用的泛化操作或整份用例通用的开通/入口大前提（"已登录账号""进入首页""机构已开通某产品/端""账号可进入某页面"），它们是所有用例的默认背景，写出来只稀释有区分度的前提；② **动作状态类**——本用例步骤顺手就能产生的中间状态（"提示气泡处于展开状态""已在列表选择某排序""已切换到某页签"），这是步骤不是前置，并入条件 bullet（如"气泡展开状态下切换排序项"）；③ **具体值复述类**——具体输入值/参数/账号，归测试数据，前置条件只写数据形态。**判断口诀**：执行前需单独准备 → `前置条件:`；本用例步骤顺手可做 → 写进条件 bullet；任何用例都适用 → 不写。**与测试数据的分工**：前置条件描述数据形态/状态要求（"存在多条账龄区间不同的往来单位"），测试数据给具体值与造数指引（"3年以上/近2年/1年以内，造数见…"）——两者并存不算重复，是要求与实例的关系；业务前提信息必须在 前置条件/测试数据/用例正文 之一体现，**不能哪都没有**。元数据块 `前置条件:` 字段非必填，无前置条件时省略整个字段。知道所调用接口时用 `调用的接口:` 子项写明；**不知道接口时不捏造、不占位**接口前置条件（不写"调用的接口: 待补充"之类占位符），但可写其他业务前提：
   ```
   > 优先级: P1 | 关联需求: REQ_XXX | 前置条件: 调用的接口: /api/itcrmweb/follow/saveFollowRecord、/api/itcrmweb/contact/getNotRelationCallRecord | 测试数据: ...
   ```
   无前置条件时省略该字段：`> 优先级: P1 | 关联需求: REQ_XXX | 测试数据: ...`
3. **接口用例不区分新增/修改**——用例标题用接口中文名，不加前后缀，**不写**"本期新增/改造"等时间标记
4. **新增接口的 URL 本身是一条优先级 3 用例**——形式 `查询 {完整URL}`，仅用于反查接口所属模块归属，无实际业务含义
   - **这条用例必须带 4 字段元数据 + priority-3 marker**——是"补充场景不强制加元数据"风格的唯一例外
5. **有前置条件时，用例的前置条件子节点用 `flag-red`（红旗）标记**——而不是在 notes 里写"前置条件: xxx"文字。无前置条件则不加；功能用例和接口用例统一处理，不按标题猜测用例类型。
6. **用例标题必须是"动作 + 预期结果"的完整句**——只写动作（如"传参指定默认账号类型为机构账号"）或名词短语（如"XX映射判定表"）不是完整用例标题，看标题不知道要验证什么；正确示例："传参指定默认账号类型为机构账号时默认展示机构账号管理"。模块/子模块容器标题不受此约束。

**Markdown 标题层级**（XMind 兼容性硬性要求）：
```
H1 当前迭代（如"代账合规8月迭代"，日期并入迭代名，不单列层级）→ XMind 根节点
H2 需求名称（必填）→ 一级节点
H3 模块名 或 用例（需求简单、不拆模块时直接挂用例）
H4 子模块名 或 用例（拆了模块、不拆子模块时用例在这层）
H5 用例（拆了模块+子模块时用例在这层）
  - 条件/场景（bullet）
    - 预期结果（nested bullet，缩进 2 空格）
  - 前置条件描述（flag-red 子节点，按需添加；功能/接口用例统一）
```

**用例层级识别**：用例不一定固定在某一层——**判断依据是标题后紧跟 `> 优先级:` 元数据块**（不管 H3/H4/H5）。模块/子模块标题后无元数据块，是分组容器。

**模块按需拆分原则**（三档，避免滥用）：
| 复杂度 | 拆分方式 | 用例落地层 | 适用场景 |
|---|---|---|---|
| 简单 | 不拆模块 | H3（直接用例） | 单一功能、无多模块/多角色/多平台 |
| 中等 | 拆一层模块 | H4（模块下的用例） | 多模块但每模块内部结构简单 |
| 复杂 | 拆模块+子模块 | H5（子模块下的用例） | 多模块且模块内部还有子结构（如"列表页"下分"筛选/列表/批量操作"）/ 需求天然有 ≥2 个并列顶层分组（多页面、多角色、多子系统），分组作 H3 容器、组内再拆 H4 子模块、用例落 H5 |
- **反模式**：每个模块下仅 1-2 用例（拆太碎）/ 同一功能在多模块重复（应合并）/ 简单需求强行拆模块（直接 H3 用例即可）/ **用"功能用例"等用例类型标签作 H3 分组容器**（用例类型不承载业务语义，应按业务模块组织或简单需求直接 H3 挂用例；**接口用例例外**——涉及接口时统一放固定命名的「接口」模块下，结构见硬规则 1，不算类型标签滥用）/ **把并列顶层分组（页面/角色/子系统）压进模块名前缀**（如"应用-顶部导航栏"、"我的-全局信息"）——应把分组上升为 H3 容器，分组内再按需拆 H4 子模块、H5 用例
- **用例绝不超过 H5**：条件/结果/前置条件一律用 nested bullet 表示，不再下沉到 H6

**预期结果格式**：
- **使用 nested bullet**（`  - 预期结果`），**不使用标题**（条件/结果/前置条件一律用 bullet，避免用例层级超过 H5）
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

## 测试设计方法（8 种，**生成时选方法、补充时查遗漏**）

生成测试用例时**必须**为每个功能点/接口选择对应的黑盒设计方法，并在"预期结果"的设计中体现方法特征。补充优化时用方法清单对照原 XMind，判断是否遗漏某类场景。

### 方法速查表

| 方法 | 核心思想（一句话） | 适用场景 | 何时选用 |
|---|---|---|---|
| **等价类划分** | 把输入分成有效/无效等价类，每类取代表值 | 输入有取值范围/格式约束/枚举集合 | 有明确输入域时**必用**，是其他方法的基础 |
| **边界值分析** | 错误集中在边界，专测边界值 | 数值范围、字符串长度、数组大小、时间区间 | 与等价类**配合用**，覆盖上点/内点/离点 |
| **因果图法** | 分析输入条件（因）与输出（果）的逻辑关系 | 多条件组合影响输出 | 多条件组合场景，画图后转判定表 |
| **判定表法** | 条件组合 → 动作映射成表，每规则一条用例 | 业务规则复杂、条件组合多 | 由因果图转化，每条规则至少 1 条用例 |
| **场景法** | 模拟用户业务路径，基本流 + 备选流 | 多步骤业务流程、端到端 | 有完整业务流程时必用 |
| **状态迁移法** | 分析对象状态及转换规则 | 有生命周期的对象（订单/审批/账号） | 有状态流转时必用 |
| **正交实验法** | 用正交表科学筛选代表性组合 | 多因素多水平、全组合过大 | 全组合数过大时用，降低用例数 |
| **错误推测法** | 基于经验推测易错场景，兜底补充 | 作为其他方法的补充 | **每个功能点必补**，至少 2 条 |

### 方法选择决策树

按输入特征选方法，**自上而下匹配，命中即用**：

```
1. 输入有取值范围/格式约束？
   └─ 是 → 等价类划分（必用）+ 边界值分析（配合）
2. 多个输入条件组合影响输出？
   └─ 是 → 因果图法 → 转判定表法
3. 是多步骤业务流程（端到端）？
   └─ 是 → 场景法（基本流 + 备选流）
4. 对象有状态流转/生命周期？
   └─ 是 → 状态迁移法（合法转换 + 非法转换尝试）
5. 多因素多水平，全组合过大？
   └─ 是 → 正交实验法（选合适正交表）
6. 以上都用过后兜底补充
   └─ 错误推测法（每功能点至少 2 条）
```

> 一个功能点常**同时命中多种方法**（如"跟进记录列表"既有输入筛选→等价类+边界值，又有业务流程→场景法）。多种方法叠加覆盖，不互斥。

> **全面性第二层保障**：8 种方法都从需求材料推导，保证「需求内不漏」；需求外的系统性风险靠两层清单兜底（细则均在 `skills/testcase-workbench/references/用例规则.md`）：**「横切维度清单」**（多账号、多端、时序竞态、聚合来源、存量回归等系统级维度）+ **「功能类型常规测试思路」**（消息通知/列表/表单/导入导出/权限等按类型积累的常规检查项）——每个功能点对两层清单逐条三态判定（已覆盖/不适用/待确认），禁止静默跳过。**清单不可能穷举所有类型**：生成时对每个功能点必须自问"这个功能有没有常见测试点/测试经验"，即使清单未收录该类型，也必须自行拓展出常规测试用例，不能以"清单里没有"为由只测需求字面。

### 细则权威（本文件不留副本）

各方法操作要点与反模式（「先全组合后删除」「禁止对称反推」等）、错误推测常见方向、方法与优先级映射，统一维护在 `skills/testcase-workbench/references/用例规则.md`「测试设计方法」；生成后检查清单同在该文件。agent 阶段 0 加载该文件，新增方法细则也只写那边。

## 格式规范

**参考文件**（理念参考，非严格格式契约——两个文件是 XMind 原生手工维护，层级比 Markdown 生成产物深，展示"按需拆分"理念，不要求生成产物严格对齐其层级深度）：
- `用例参考.xmind` — 格式模板，含占位说明文字，展示需求→模块→子模块→用例按需拆分理念
- `202607.xmind` — 具体用例，参照格式模板编写的真实用例

**默认风格：画布 2（按业务需求/迭代组织）**
- H2 需求标题以 `【模块名】` 开头
- 用户明确说"按功能模块全量沉淀"时才用画布 1 风格
- 元数据块**强制**：`> 优先级: P1/P2/P3/P4 | 关联需求: ... | 测试数据: ...`（优先级/关联需求/测试数据必填，`前置条件` 按需，知道接口时用 `调用的接口:` 写明）

**模块拆分原则**：见上方「Markdown 标题层级」章节的「模块按需拆分原则」三档表（简单不拆 / 中等拆模块 / 复杂拆模块+子模块），避免滥用。

## 工具脚本

| 脚本 | 用途 | 依赖 |
|---|---|---|
| `scripts/md2xmind.py` | Markdown → XMind 全量转换（生成场景） | Python 3.8+（无第三方依赖） |
| `scripts/xmind-edit.py` | XMind 增量编辑（增/删/改 节点，**统一脚本**） | Python 3.8+（无第三方依赖） |
| `scripts/search-related-docs.py` | 全文检索相关文档（grep 知识库 + 查 Baymax 索引） | Python 3.8+ |
| `scripts/extract_mockup_texts.py` | 庄周 mockup raw JSON → 全量文本清单 + 设计稿图片 URL | Python 3.8+（无第三方依赖） |

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

每次生成或更新用例后（`testcase-generator` / `testcase-supplementer` 输出成品前），**必须**按 `skills/testcase-workbench/references/用例规则.md`「用例生成后检查」清单逐项自检：

1. **内容正确性**（对照需求快照，禁止臆测）
2. **格式规范**（标题层级 / 元数据块 / 完整句标题）
3. **优先级合理性**（禁止全量 P1，必须分层）
4. **测试点完整性**（逐条比对需求 + 理解需求真实意图与作用范围全集）
5. **横切维度 + 功能类型全面性**（按 用例规则.md「横切维度清单」逐维度三态判定 + 按功能点命中的「功能类型常规测试思路」逐条三态判定：已覆盖/不适用/待确认，禁止静默跳过——8 种方法保证需求内不漏，这两层保证需求外不漏）

- 自检通过 → 输出成品（Markdown + XMind）
- 自检发现问题 → 先修复、复检通过后再输出，**并在最终回复里简短报告修了什么**（无需逐条列出全部检查项）

> 此规则对 `testcase-generator` 和 `testcase-supplementer` 均强制生效，是交付前的最后一道关卡。

## 规则文件维护原则

本项目规则分散在四个位置，**调整用例规则时请按此分工定位，不要错放**：

| 文件 | 负责 | 不负责 |
|---|---|---|
| **`CLAUDE.md`**（本文件） | 每条用例都用的**核心规则**：结构硬规则、优先级规则、方法速查表+决策树、格式规范；细则只留指针 | 方法细则/检查清单正文（在 用例规则.md）、agent 工作流 |
| **`skills/testcase-workbench/references/用例规则.md`** | **细则唯一权威**：各方法操作要点与反模式、错误推测常见方向、方法与优先级映射、生成后检查清单、教训实例（错题本）；同时作为 skill 跨平台副本携带核心规则章节 | agent 工作流 |
| **`.claude/agents/testcase-generator.md`** | 生成用例的**工作流**（阶段 0-8） | 不重复规则，阶段 0 读 CLAUDE.md + 用例规则.md |
| **`.claude/agents/testcase-supplementer.md`** | 补充优化的**工作流** + 补充特有规则 | 不重复规则，阶段 0 读 CLAUDE.md + 用例规则.md |

**维护原则**：
1. **新增规则先判断归属**：每条用例都用的核心 → CLAUDE.md（改后同步 用例规则.md 对应副本章节）；用到才查的细则/新反模式/检查项 → **只写 用例规则.md**；工作流 → agent 文件
2. **Agent 阶段 0 必读两份**：`CLAUDE.md` + `skills/testcase-workbench/references/用例规则.md`，细则不依赖上下文记忆
3. **agent 定义在 `.claude/agents/`** — 本项目 agent 是**项目级**（随 repo 分发），与 CLAUDE.md 同级维护

## 归档说明

⚠️ **`.trae/rules/` 下的 4 份旧规则文件已废弃**，仅作历史归档保留。**请勿使用**，全部内容已被以下文件取代：

| 旧文件 | 替代为 |
|---|---|
| `.trae/rules/测试用例生成整体流程规则.md` | `.claude/agents/testcase-generator.md`（项目级 subagent） |
| `.trae/rules/生成测试点规则.md` | `.claude/agents/testcase-generator.md` |
| `.trae/rules/基于测试点生成测试用例规则.md` | `.claude/agents/testcase-generator.md` |
| `.trae/rules/测试用例设计.md` | `.claude/agents/testcase-generator.md` |
