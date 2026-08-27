# testcase-workbench

通用测试用例生成/更新工作台。**不含业务知识**，业务知识由独立的 `testcase-knowledge` 项目通过环境变量接入。

## 项目结构

```
testcase-workbench/
├── agents/                        ← 全局 subagent 定义
│   ├── testcase-generator.md      ← 从零生成用例
│   └── testcase-supplementer.md   ← 补充优化现有 XMind
├── scripts/
│   ├── md2xmind.py                ← Markdown → XMind 全量转换
│   ├── xmind-edit.py              ← XMind 增量编辑（增/删/改）
│   ├── search-related-docs.py     ← 全文检索知识库 + Baymax 索引
│   ├── install.ps1                ← 安装全局 agent（Windows）
│   └── install.sh                 ← 安装全局 agent（macOS/Linux）
├── requests/                      ← 需求快照（中间产物，gitignore）
├── testpoints/                    ← 测试点 Markdown
├── testcases/                     ← 测试用例 Markdown
├── xmind/                         ← 测试用例 XMind
└── CLAUDE.md                      ← 项目规则
```

## 快速开始

```bash
# 1. 安装全局 agent
powershell -ExecutionPolicy Bypass -File scripts/install.ps1

# 2. 登录内部 CLI
npx -y --registry=http://npm.dc.servyou-it.com @servyou-ai/17work-cli@latest login

# 3. 启动 Claude Code，说"生成测试用例"即可
```

## 接入业务知识库（可选）

```powershell
$env:BUSINESS_KNOWLEDGE_ROOT = "D:\Trae CN\projects\business-knowledge"
```

设置后 agent 会自动读取知识库项目的术语表和文档。

## 与知识库项目的关系

| 项目 | 职责 | 内容 |
|---|---|---|
| `testcase-workbench` | 用例生成/更新能力 | 脚本、agent、格式规则（**团队无关**） |
| `business-knowledge` | 业务知识存储 | 术语表、功能文档、历史用例索引（**团队相关**） |

两个项目独立 git 仓库，独立维护。
