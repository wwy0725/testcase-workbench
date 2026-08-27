#!/usr/bin/env bash
# scripts/install.sh
# testcase 项目：安装全局 agent 到 ~/.claude/agents/
# 用途：让新成员 clone repo 后，第一次跑这个脚本就能用上"生成测试用例"/"补充 XMind"等功能
# 幂等：可重复运行，源文件覆盖目标文件

set -e

# 解析 repo 根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
AGENTS_SOURCE="$REPO_ROOT/agents"
AGENTS_TARGET="$HOME/.claude/agents"

echo -e "\033[36m=== testcase 项目：安装全局 agent ===\033[0m"
echo "源目录: $AGENTS_SOURCE"
echo "目标目录: $AGENTS_TARGET"
echo ""

# 1. 校验源目录
if [ ! -d "$AGENTS_SOURCE" ]; then
    echo -e "\033[31m错误: 源目录不存在: $AGENTS_SOURCE\033[0m" >&2
    exit 1
fi

# 2. 创建目标目录
if [ ! -d "$AGENTS_TARGET" ]; then
    mkdir -p "$AGENTS_TARGET"
    echo "[创建] 目标目录 $AGENTS_TARGET"
else
    echo "[存在] 目标目录 $AGENTS_TARGET"
fi

# 3. 复制所有 .md agent 文件
copied=0
for f in "$AGENTS_SOURCE"/*.md; do
    [ -f "$f" ] || continue
    cp "$f" "$AGENTS_TARGET/"
    echo -e "  \033[32m[复制] $(basename "$f")\033[0m"
    copied=$((copied + 1))
done

echo ""
echo -e "\033[36m完成！共复制 $copied 个 agent 到 $AGENTS_TARGET\033[0m"
echo ""
echo -e "\033[33m后续步骤（仅第一次需要）：\033[0m"
echo "  1. 打开任意内部 CLI 触发 OAuth 登录（任选一个即可）："
echo "     npx -y --registry=http://npm.dc.servyou-it.com @servyou-ai/17work-cli@latest login"
echo "  2. 启动 Claude Code，说\"生成测试用例\"或\"补充 XMind\"即可触发 agent"
