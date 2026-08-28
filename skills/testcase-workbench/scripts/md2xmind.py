#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Markdown 测试用例 → XMind 转换器

用法：
  python md2xmind.py <input.md> <output.xmind>

输入：testcases/{name}-测试用例-{n}.md（遵循 .trae/templates/testcase-spec.md 6 级标题规范）
输出：xmind/{name}-测试用例-{n}.xmind（可在 XMind 中"导入画布"或直接打开）

节点映射：
  H1 (#)        → Sheet 标题（XMind 画布名）
  H2 (##)       → 一级节点（功能模块）
  H3 (###)      → 二级节点（功能测试点）
  H4 (####)     → 三级节点（验证点）
  H5 (#####)    → 用例场景节点（含元数据 notes + 优先级 marker）
  H6 (######)   → 预期结果子节点（列表项转为子节点）

元数据解析（H5 后的 `> 优先级: 高 | 关联需求: REQ_X | ...` 块）：
  优先级：高/中/低 → XMind marker 标识符（priority-1/2/3）
  关联需求/前置条件/测试数据 → 节点 notes（plain 文本）
"""

import sys
import os
import io
import re
import json
import zipfile
import uuid
from pathlib import Path

# 强制 UTF-8 输出（Windows 默认 GBK 会乱码）
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

# 优先级 → XMind marker-id 映射
PRIORITY_MARKERS = {
    'P1': 'priority-1',
    'P2': 'priority-2',
    'P3': 'priority-3',
    'P4': 'priority-4',
    '高': 'priority-1',
    '中': 'priority-2',
    '低': 'priority-3',
}

# 匹配 H5 后紧跟的元数据引用块：
#   > 优先级: 高 | 关联需求: REQ_X | 前置条件: ... | 测试数据: ...
META_PATTERN = re.compile(r'^>\s*(.+)$')


def parse_markdown(md_path):
    """解析测试用例 Markdown，返回结构化树。

    层级结构：
      H5 用例标题
        ├── 1. 步骤描述          ← 编号列表项 = 步骤节点
        │     └── - 预期：xxx    ← 步骤下缩进的列表项 = 结果节点
        └── - 前置条件：xxx      ← flag-red 节点

    Returns:
        dict: {
            'sheet_title': str,
            'root_topics': [  # 一级节点（H2）
                {
                    'title': str,
                    'level': 2,
                    'children': [...],
                    'notes': str,
                }
            ]
        }
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    sheet_title = ''
    root_topics = []
    stack = []
    h6_mode = None
    _precondition_lines = []

    def attach(node):
        if not stack:
            root_topics.append(node)
        else:
            stack[-1]['children'].append(node)

    def flush_precondition():
        nonlocal _precondition_lines
        if not _precondition_lines:
            return
        parent = stack[-1] if stack else None
        if parent:
            merged_text = '\n'.join(_precondition_lines)
            parent['children'].append({
                'title': merged_text,
                'level': 6,
                'children': [],
                'notes': '',
                'markers': [{'markerId': 'flag-red'}],
            })
        _precondition_lines = []

    import re as re_mod
    step_pattern = re_mod.compile(r'^(\d+)\.\s+(.+)')
    bullet_pattern = re_mod.compile(r'^(\s*)-\s+(.+)')

    root_title = ''  # H1 → 根节点（代账合规）

    for raw_line in lines:
        line = raw_line.rstrip('\n')

        if not line.strip():
            continue

        m = re.match(r'^(#{1,6})\s+(.+?)(?:\s+#+\s*)?$', line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()

            flush_precondition()
            h6_mode = None

            if level == 1:
                # H1 → 根节点标题（团队名，如"代账合规"）
                root_title = title
                continue

            if level == 6 and title.strip() == '预期结果':
                h6_mode = 'expected'
                continue

            if level == 6 and title.strip() == '前置条件':
                h6_mode = 'precondition'
                _precondition_lines = []
                continue

            node = {
                'title': title,
                'level': level,
                'children': [],
                'notes': '',
            }

            while stack and stack[-1]['level'] >= level:
                stack.pop()
            attach(node)
            stack.append(node)

            if level in (5, 6):
                h6_mode = 'generic'
            continue

        # 元数据行
        m_meta = META_PATTERN.match(line.strip())
        if m_meta and stack and stack[-1]['level'] in (5, 6):
            stack[-1]['notes'] = m_meta.group(1).strip()
            continue

        # 编号列表项（步骤）: "1. xxx"
        m_step = step_pattern.match(line.strip())
        if h6_mode in ('expected', 'generic') and m_step:
            step_node = {
                'title': m_step.group(2).strip(),
                'level': 7,
                'children': [],
                'notes': '',
            }
            parent = stack[-1] if stack else None
            if parent:
                parent['children'].append(step_node)
            continue

        # 缩进列表项: "   - 预期：xxx" 或 "   - xxx"
        m_bullet = bullet_pattern.match(line)
        if m_bullet:
            indent = len(m_bullet.group(1))
            content = m_bullet.group(2).strip()

            # 前置条件
            if content.startswith('前置条件：') or content.startswith('前置条件:'):
                _precondition_lines.append(content.split('：', 1)[-1].split(':', 1)[-1].strip())
                continue

            # 预期/普通内容
            if h6_mode == 'precondition':
                _precondition_lines.append(content)
            elif h6_mode in ('expected', 'generic'):
                parent = stack[-1] if stack else None
                if not parent:
                    continue
                if indent == 0:
                    # 顶级 bullet (- )：挂到当前父节点（H5）
                    parent['children'].append({
                        'title': content,
                        'level': 7,
                        'children': [],
                        'notes': '',
                    })
                else:
                    # 嵌套 bullet (  - )：挂到最后一个子节点下
                    if parent['children']:
                        last_step = parent['children'][-1]
                        last_step['children'].append({
                            'title': content.replace('预期：', '').replace('预期:', '').strip(),
                            'level': 8,
                            'children': [],
                            'notes': '',
                        })
                    else:
                        # 没有顶级步骤时，直接挂到父节点
                        parent['children'].append({
                            'title': content,
                            'level': 7,
                            'children': [],
                            'notes': '',
                        })
            continue

    flush_precondition()

    return {
        'root_title': root_title,
        'sheet_title': sheet_title or Path(md_path).stem,
        'root_topics': root_topics,
    }


def make_id():
    return str(uuid.uuid4())


def build_xmind_topic(node):
    """把内部节点结构转成 XMind JSON 格式。"""
    topic = {
        'id': make_id(),
        'class': 'topic',
        'title': node['title'],
    }

    # 元数据 → markers + notes
    notes_text = node.get('notes', '')

    # 节点自身携带的 markers（如 flag-red）
    node_markers = node.get('markers', [])

    if notes_text or node_markers:
        markers = list(node_markers)
        # 解析优先级
        for k, v in PRIORITY_MARKERS.items():
            if f'优先级: {k}' in notes_text or f'优先级:{k}' in notes_text:
                markers.append({'markerId': v})
                break
        if markers:
            topic['markers'] = markers

        # 整段元数据写入 notes
        # XMind 8 期望格式：{"plain": {"content": "..."}}，多余字段可能不识别
        topic['notes'] = {
            'plain': {
                'content': notes_text,
            }
        }

    # 递归子节点
    if node['children']:
        topic['children'] = {
            'attached': [build_xmind_topic(child) for child in node['children']]
        }

    return topic


def build_content_json(parsed):
    """构造 XMind content.json。

    XMind 8+ (Zen 格式) 顶层是 sheet 数组，不是包装对象：
        [
          {
            "id": "<sheet-id>",
            "class": "sheet",
            "title": "<sheet-title>",
            "rootTopic": {...}
          }
        ]
    """
    sheet_id = make_id()
    root_id = make_id()

    root_topic = {
        'id': root_id,
        'class': 'topic',
        'title': parsed.get('root_title') or parsed['sheet_title'],
        'structureClass': 'org.xmind.ui.logic.right',
    }

    if parsed['root_topics']:
        root_topic['children'] = {
            'attached': [build_xmind_topic(t) for t in parsed['root_topics']]
        }

    # 顶层直接返回数组（关键修复：之前错误地包了一层对象）
    return [{
        'id': sheet_id,
        'class': 'sheet',
        'title': parsed['sheet_title'],
        'rootTopic': root_topic,
    }]


def build_metadata_json():
    """构造 XMind metadata.json（基础元信息）。"""
    return {
        'creator': {
            'name': 'md2xmind.py',
            'version': '1.0.0'
        },
        'annotations': {},
    }


def write_xmind(content_json, metadata_json, output_path):
    """把 JSON 写入 XMind zip 包。

    XMind 8+ 实际只需要两个文件：
      - content.json （顶层是 sheet 数组）
      - metadata.json
    不需要 manifest.json（我之前加的是多余的）。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('content.json', json.dumps(content_json, ensure_ascii=False, indent=2))
        zf.writestr('metadata.json', json.dumps(metadata_json, ensure_ascii=False, indent=2))


def main():
    if len(sys.argv) != 3:
        print('用法: python md2xmind.py <input.md> <output.xmind>', file=sys.stderr)
        sys.exit(1)

    input_md = Path(sys.argv[1])
    output_xmind = Path(sys.argv[2])

    if not input_md.exists():
        print(f'错误: 输入文件不存在: {input_md}', file=sys.stderr)
        sys.exit(1)

    parsed = parse_markdown(input_md)
    content_json = build_content_json(parsed)
    metadata_json = build_metadata_json()
    write_xmind(content_json, metadata_json, output_xmind)

    # 统计输出
    def count_topics(topics):
        n = 0
        for t in topics:
            n += 1 + count_topics(t['children'])
        return n

    total = count_topics(parsed['root_topics'])
    print(f'✅ 已生成: {output_xmind}')
    print(f'   画布标题: {parsed["sheet_title"]}')
    print(f'   节点总数: {total}')


if __name__ == '__main__':
    main()
