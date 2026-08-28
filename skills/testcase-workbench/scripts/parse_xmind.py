#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""XMind 解析脚本：从 .xmind 文件提取指定节点的 Markdown 树形结构。

用法：
  python parse_xmind.py <xmind_path> [target_topic_title] [output_dir] [--sheet N]

参数：
  xmind_path          XMind 文件路径（必填）
  target_topic_title  要提取的节点名（可选，递归搜索）
  output_dir          Markdown 输出目录（可选）
  --sheet N           指定画布索引，1-based，默认 1（XMind 多画布时使用）

输出：
  - 不带 target_topic_title：列出指定画布的所有一级节点到 stdout（含二级子节点预览）
  - 带 target_topic_title：递归搜索该名称，生成 Markdown 树到 output_dir

注意：XMind 文件常含多个画布（如 "画布 1"/"导入"），需用 --sheet 指定。
      不确定时建议先用 --list-sheets 查看所有画布。
"""

import sys
import os
import zipfile
import io
import xml.etree.ElementTree as ET
from pathlib import Path

# 强制 stdout/stderr 使用 UTF-8（Windows 默认 GBK 会导致部分字符无法显示）
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

NS = {'xmap': 'urn:xmind:xmap:xmlns:content:2.0'}


def get_title(topic):
    title_elem = topic.find('xmap:title', NS)
    if title_elem is not None and title_elem.text:
        return title_elem.text
    return ''


def get_notes(topic):
    notes_elem = topic.find('xmap:notes/xmap:plain', NS)
    if notes_elem is not None and notes_elem.text:
        return notes_elem.text
    return ''


def get_children_topics(topic):
    children_elem = topic.find('xmap:children/xmap:topics[@type="attached"]', NS)
    if children_elem is None:
        return []
    return children_elem.findall('xmap:topic', NS)


def count_all_children(topic):
    """递归统计所有后代节点数。"""
    count = 0
    for child in get_children_topics(topic):
        count += 1 + count_all_children(child)
    return count


def get_parent_path(target, root_topic):
    """获取 target 到 root 的完整父级路径（不含 target 自身）。"""
    def walk(node, current_path):
        current_path.append(get_title(node))
        if node is target:
            return list(current_path)
        for child in get_children_topics(node):
            r = walk(child, current_path)
            if r:
                return r
        current_path.pop()
        return None

    return walk(root_topic, [])


def find_all_topics(root_topic):
    """递归收集所有 topic 节点。"""
    result = [root_topic]
    for child in get_children_topics(root_topic):
        result.extend(find_all_topics(child))
    return result


def find_topic_recursive(root_topic, target_title):
    """递归查找所有 title 等于 target_title 的节点。"""
    return [t for t in find_all_topics(root_topic) if get_title(t) == target_title]


def list_first_level(root_topic):
    """列出所有一级节点（含二级子节点预览）。"""
    children = get_children_topics(root_topic)
    result = []
    for i, child in enumerate(children, 1):
        title = get_title(child)
        count = count_all_children(child)
        result.append({
            'index': i,
            'title': title,
            'child_count': count,
            'topic': child
        })
    return result


def topic_to_markdown(topic, depth=0, max_depth=30):
    """将 topic 转为 Markdown 树。"""
    if depth > max_depth:
        return ''
    title = get_title(topic)
    notes = get_notes(topic)
    children = get_children_topics(topic)

    indent = '  ' * depth
    if depth == 0:
        line = f'{indent}- {title} ({len(children)})'
    else:
        line = f'{indent}- {title}'

    lines = [line]

    if notes:
        lines.append(f'{indent}  > {notes}')

    for child in children:
        child_md = topic_to_markdown(child, depth + 1, max_depth)
        if child_md:
            lines.append(child_md)

    return '\n'.join(lines)


def list_sheets(root):
    """列出所有画布（sheet），返回 [(index_1based, sheet_title, root_topic_title), ...]"""
    sheets = root.findall('xmap:sheet', NS)
    result = []
    for i, sheet in enumerate(sheets, 1):
        st = sheet.find('xmap:title', NS)
        sheet_title = st.text if st is not None and st.text else f'sheet{i}'
        rt = sheet.find('xmap:topic', NS)
        rt_name = get_title(rt) if rt is not None else ''
        result.append((i, sheet_title, rt_name))
    return result


def main():
    # 解析 --sheet 和 --list-sheets 参数（从尾部向前扫描以兼容位置参数）
    args = list(sys.argv[1:])
    sheet_index = 1
    list_sheets_only = False

    # 提取 --sheet N
    if '--sheet' in args:
        idx = args.index('--sheet')
        if idx + 1 >= len(args):
            print('错误: --sheet 需要参数', file=sys.stderr)
            sys.exit(1)
        try:
            sheet_index = int(args[idx + 1])
        except ValueError:
            print(f'错误: --sheet 参数必须是整数，得到 "{args[idx + 1]}"', file=sys.stderr)
            sys.exit(1)
        args = args[:idx] + args[idx + 2:]

    # 提取 --list-sheets
    if '--list-sheets' in args:
        list_sheets_only = True
        args.remove('--list-sheets')

    if len(args) < 1:
        print('用法: python parse_xmind.py <xmind_path> [target_title] [output_dir] [--sheet N] [--list-sheets]', file=sys.stderr)
        sys.exit(1)

    xmind_path = args[0]
    target_title = args[1] if len(args) > 1 else None
    output_dir = args[2] if len(args) > 2 else None

    if not os.path.exists(xmind_path):
        print(f'错误: 文件不存在: {xmind_path}', file=sys.stderr)
        sys.exit(1)

    # 解压并解析
    try:
        with zipfile.ZipFile(xmind_path, 'r') as z:
            with z.open('content.xml') as f:
                root = ET.fromstring(f.read())
    except Exception as e:
        print(f'错误: 解析 XMind 失败: {e}', file=sys.stderr)
        sys.exit(1)

    sheets = root.findall('xmap:sheet', NS)
    if not sheets:
        print('错误: 未找到 sheet 节点', file=sys.stderr)
        sys.exit(1)

    # --list-sheets 模式：列出所有画布后退出
    if list_sheets_only:
        print(f'XMind 文件: {xmind_path}')
        print(f'共 {len(sheets)} 个画布（sheet）\n')
        for idx, st, rt in list_sheets(root):
            print(f'  [{idx}] sheet 标题: {st} | root topic: {rt}')
        return

    # 校验 sheet_index
    if sheet_index < 1 or sheet_index > len(sheets):
        print(f'错误: --sheet {sheet_index} 越界（文件共 {len(sheets)} 个 sheet）', file=sys.stderr)
        print('\n可用的 sheet:', file=sys.stderr)
        for idx, st, rt in list_sheets(root):
            print(f'  [{idx}] {st} (root: {rt})', file=sys.stderr)
        sys.exit(1)

    sheet = sheets[sheet_index - 1]
    sheet_title_elem = sheet.find('xmap:title', NS)
    sheet_title = sheet_title_elem.text if sheet_title_elem is not None and sheet_title_elem.text else f'sheet{sheet_index}'

    root_topic = sheet.find('xmap:topic', NS)
    if root_topic is None:
        print(f'错误: sheet {sheet_index} 内无 root topic', file=sys.stderr)
        sys.exit(1)

    first_level = list_first_level(root_topic)

    # 模式 1: 列出所有一级节点（含二级子节点预览）
    if target_title is None:
        print(f'XMind 文件: {xmind_path}')
        print(f'画布: [{sheet_index}/{len(sheets)}] {sheet_title} (root: {get_title(root_topic)})')
        print(f'共 {len(first_level)} 个一级节点\n')
        for item in first_level:
            print(f'[{item["index"]}] {item["title"]} ({item["child_count"]} 个子节点)')
            # 列出二级子节点
            for child in get_children_topics(item['topic']):
                print(f'    - {get_title(child)}')
        if len(sheets) > 1:
            print(f'\n提示: 该文件共 {len(sheets)} 个画布，可用 --sheet N 查看其他画布', file=sys.stderr)
        return

    # 模式 2: 递归搜索目标节点
    matches = find_topic_recursive(root_topic, target_title)
    if not matches:
        print(f'错误: 画布 [{sheet_index}] {sheet_title} 中未找到节点 "{target_title}"', file=sys.stderr)
        print('\n可用的节点:', file=sys.stderr)
        for item in first_level:
            print(f'  - {item["title"]}', file=sys.stderr)
            for child in get_children_topics(item['topic']):
                print(f'      - {get_title(child)}', file=sys.stderr)
        sys.exit(1)

    if len(matches) > 1:
        print(f'提示: 找到 {len(matches)} 个同名节点 "{target_title}"，将提取第一个', file=sys.stderr)
        for i, m in enumerate(matches, 1):
            path = get_parent_path(m, root_topic)
            print(f'  [{i}] 路径: {" > ".join(path)}', file=sys.stderr)

    target = matches[0]
    parent_path = get_parent_path(target, root_topic)
    path_header = ' > '.join(parent_path)

    # 生成 Markdown
    md_lines = [f'# {path_header}', '']
    md_lines.append(topic_to_markdown(target, depth=0))
    md_content = '\n'.join(md_lines)

    # 输出
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        xmind_basename = Path(xmind_path).stem
        safe_title = target_title.replace('/', '_').replace('\\', '_')
        output_path = os.path.join(output_dir, f'{xmind_basename}_s{sheet_index}_{safe_title}.md')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f'已保存到: {output_path}\n')
    else:
        print()

    print(md_content)


if __name__ == '__main__':
    main()
