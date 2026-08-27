#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""XMind 增量编辑工具（统一脚本：增/删/改 节点）

子命令：
  remove      删除指定节点
  add         在指定父节点下添加子节点
  apply       按 JSON 计划批量应用增/删/改
  set-notes   更新节点 notes
  set-marker  更新节点 marker（如 priority-1/2/3、flag-red）

工作原理：
  1. 解析 content.xml（XMind 8 XML 格式，与 parse_xmind.py 一致）
  2. 在树中定位目标节点
  3. 修改树（增/删/改）
  4. 写回 zip（默认输出新文件，加 --in-place 才原地修改）

用法示例：
  # 删除节点
  python xmind-edit.py remove foo.xmind "待删除的节点" --parent "其父节点"

  # 添加子节点
  python xmind-edit.py add foo.xmind "父节点" "新子节点" --notes "备注" --marker priority-1

  # 批量应用补充计划
  python xmind-edit.py apply foo.xmind --plan plan.json

  # 更新 notes
  python xmind-edit.py set-notes foo.xmind "节点标题" "新的备注内容"

补充计划 JSON 格式（apply 子命令）：
  {
    "operations": [
      {"op": "add", "parent": "...", "child": "...", "level": 4, "notes": "...", "marker": "priority-1"},
      {"op": "add", "parent": "...", "child": "...", "level": 5},
      {"op": "remove", "title": "...", "parent": "..."},
      {"op": "set-notes", "title": "...", "notes": "新内容"},
      {"op": "set-marker", "title": "...", "marker": "priority-1"}
    ]
  }

约定：
  - level: 2/3/4/5/6（对应 H2-H6；不强制，仅用于语义提示）
  - marker 取值: priority-1 (高) / priority-2 (中) / priority-3 (低)
  - 同名子节点自动追加 " (2)" / " (3)" 后缀避免冲突
  - 找不到父节点时报错并列出可用的父节点
  - 默认输出 <原名>-new.xmind，加 --in-place 原地修改
"""

import sys
import os
import io
import json
import argparse
import zipfile
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# 强制 UTF-8 输出（Windows 默认 GBK 会乱码）
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

NS = {'xmap': 'urn:xmind:xmap:xmlns:content:2.0'}
ET.register_namespace('', NS['xmap'])


# ========== XMind XML 通用操作函数 ==========

def get_title(t):
    e = t.find('xmap:title', NS)
    return e.text if e is not None and e.text else ''


def get_children(t):
    e = t.find("xmap:children/xmap:topics[@type='attached']", NS)
    return e.findall('xmap:topic', NS) if e is not None else []


def get_children_container(t):
    """获取父节点的 children container（topics[@type='attached']）；不存在则创建。"""
    children = t.find('xmap:children', NS)
    if children is None:
        children = ET.SubElement(t, f'{{{NS["xmap"]}}}children')
    container = children.find("xmap:topics[@type='attached']", NS)
    if container is None:
        container = ET.SubElement(children, f'{{{NS["xmap"]}}}topics')
        container.set('type', 'attached')
    return container


def set_title(t, title):
    e = t.find('xmap:title', NS)
    if e is None:
        e = ET.SubElement(t, f'{{{NS["xmap"]}}}title')
        # 移到 children 之前（XMind 结构约定）
        t.remove(e)
        t.insert(0, e)
    e.text = title


def set_notes(t, notes_text):
    """设置节点 notes（plain 格式）。notes_text 为空字符串则删除 notes。"""
    notes_elem = t.find('xmap:notes', NS)
    if not notes_text:
        if notes_elem is not None:
            t.remove(notes_elem)
        return
    if notes_elem is None:
        notes_elem = ET.SubElement(t, f'{{{NS["xmap"]}}}notes')
    # 重建 plain 元素（避免重复）
    for child in list(notes_elem):
        notes_elem.remove(child)
    plain = ET.SubElement(notes_elem, f'{{{NS["xmap"]}}}plain')
    plain.text = notes_text


def set_marker(t, marker_id):
    """设置节点 marker。marker_id 为空字符串则删除 marker。"""
    # XMind marker 通常以 <marker-ref> 形式出现在 children 之前；为简化只处理最常见的 priority
    marker_refs = t.findall('xmap:marker-refs/xmap:marker-ref', NS)
    # 清除所有 priority 类的 marker
    for ref in list(marker_refs):
        mid = ref.get('marker-id', '')
        if mid.startswith('priority-'):
            ref.getparent() if hasattr(ref, 'getparent') else None
            refs_parent = ref.getparent() if hasattr(ref, 'getparent') else None
            if refs_parent is not None:
                refs_parent.remove(ref)
    if not marker_id:
        return
    # 添加新 marker
    refs_container = t.find('xmap:marker-refs', NS)
    if refs_container is None:
        refs_container = ET.SubElement(t, f'{{{NS["xmap"]}}}marker-refs')
        # 移到 notes 之后
    ref = ET.SubElement(refs_container, f'{{{NS["xmap"]}}}marker-ref')
    ref.set('marker-id', marker_id)


def find_node_by_title(root, title, parent_title=None):
    """找到指定标题的节点。可选 parent_title 限定父节点。返回 (node, parent_node)。"""
    def search(t, parent_t):
        if get_title(t) == title:
            if parent_title is None or (parent_t is not None and get_title(parent_t) == parent_title):
                return (t, parent_t)
        for c in get_children(t):
            r = search(c, t)
            if r is not None:
                return r
        return None
    return search(root, None)


def list_first_level_titles(root_topic, depth_limit=2):
    """列出 root 下前 N 层的节点标题，用于错误提示。"""
    titles = []

    def walk(t, depth):
        if depth > depth_limit:
            return
        titles.append(get_title(t))
        for c in get_children(t):
            walk(c, depth + 1)

    for c in get_children(root_topic):
        walk(c, 1)
    return titles


def unique_child_title(parent, desired_title):
    """若 desired_title 在 parent 的子节点中已存在，返回带 " (N)" 后缀的唯一标题。"""
    existing = {get_title(c) for c in get_children(parent)}
    if desired_title not in existing:
        return desired_title
    n = 2
    while f"{desired_title} ({n})" in existing:
        n += 1
    return f"{desired_title} ({n})"


def make_topic(title, notes=None, marker=None):
    """构造一个新 topic 元素。"""
    topic = ET.Element(f'{{{NS["xmap"]}}}topic')
    topic.set('id', f'new-{os.urandom(4).hex()}')
    # title 必须放在最前
    t = ET.SubElement(topic, f'{{{NS["xmap"]}}}title')
    t.text = title
    if notes:
        n = ET.SubElement(topic, f'{{{NS["xmap"]}}}notes')
        p = ET.SubElement(n, f'{{{NS["xmap"]}}}plain')
        p.text = notes
    if marker:
        refs = ET.SubElement(topic, f'{{{NS["xmap"]}}}marker-refs')
        ref = ET.SubElement(refs, f'{{{NS["xmap"]}}}marker-ref')
        ref.set('marker-id', marker)
    return topic


def load_xmind(xmind_path):
    """加载 XMind 文件，返回 (root_element, other_files_dict, file_path)。"""
    fp = Path(xmind_path)
    if not fp.exists():
        print(f'错误: 文件不存在: {fp}', file=sys.stderr)
        sys.exit(1)

    with zipfile.ZipFile(fp, 'r') as z:
        try:
            content_bytes = z.read('content.xml')
        except KeyError:
            print(f'错误: XMind 文件不含 content.xml，可能不是 XMind 8 格式', file=sys.stderr)
            print('       提示：本脚本仅支持 XMind 8 XML 格式；如需支持 JSON 格式请用其他工具', file=sys.stderr)
            sys.exit(1)
        other_files = {n: z.read(n) for n in z.namelist() if n != 'content.xml'}

    root = ET.fromstring(content_bytes)
    return root, other_files, fp


def save_xmind(root, other_files, fp, output_path=None, in_place=False):
    """保存 XMind 文件。默认输出 <原名>-new.xmind；in_place=True 原地覆盖。"""
    new_content = ET.tostring(root, encoding='utf-8', xml_declaration=True)

    if in_place:
        target = fp
    else:
        if output_path:
            target = Path(output_path)
        else:
            target = fp.with_name(f'{fp.stem}-new{fp.suffix}')

    tmp_path = target.with_suffix(target.suffix + '.tmp')
    with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        zout.writestr('content.xml', new_content)
        for name, data in other_files.items():
            zout.writestr(name, data)

    shutil.move(str(tmp_path), str(target))
    return target


def each_sheet_root(root):
    """遍历所有画布的 root topic。"""
    sheets = root.findall('xmap:sheet', NS)
    for sheet in sheets:
        rt = sheet.find('xmap:topic', NS)
        if rt is not None:
            yield rt


# ========== 子命令实现 ==========

def cmd_remove(args):
    root, other_files, fp = load_xmind(args.xmind)
    target = None
    parent = None
    sheet_root = None
    for sr in each_sheet_root(root):
        result = find_node_by_title(sr, args.title, args.parent)
        if result:
            target, parent = result
            sheet_root = sr
            break

    if target is None:
        print(f'错误: 未找到节点 "{args.title}"（parent={args.parent or "(any)"}）', file=sys.stderr)
        for sr in each_sheet_root(root):
            print('可用的一级节点:', file=sys.stderr)
            for c in get_children(sr):
                print(f'  - {get_title(c)}', file=sys.stderr)
        sys.exit(2)

    if args.dry_run:
        print(f'[dry-run] 将删除节点 "{get_title(target)}"（其子节点共 {len(get_children(target))} 个）')
        return

    # 删除
    if parent is None:
        # target 是一级节点，从 sheet root 移除
        container = get_children_container(sheet_root)
        for c in list(container.findall('xmap:topic', NS)):
            if c is target:
                container.remove(c)
                break
    else:
        container = get_children_container(parent)
        for c in list(container.findall('xmap:topic', NS)):
            if c is target:
                container.remove(c)
                break

    out = save_xmind(root, other_files, fp, args.output, args.in_place)
    print(f'✅ 已删除节点 "{get_title(target)}"')
    print(f'   输出: {out}')


def cmd_add(args):
    root, other_files, fp = load_xmind(args.xmind)
    parent = None
    for sr in each_sheet_root(root):
        for c in get_children(sr):
            if get_title(c) == args.parent:
                parent = c
                break
        if parent is not None:
            break
        # 也支持更深层（递归找）
        def deep_find(t):
            if get_title(t) == args.parent:
                return t
            for c in get_children(t):
                r = deep_find(c)
                if r is not None:
                    return r
            return None
        for sr in each_sheet_root(root):
            r = deep_find(sr)
            if r is not None:
                parent = r
                break
        if parent is not None:
            break

    if parent is None:
        print(f'错误: 未找到父节点 "{args.parent}"', file=sys.stderr)
        for sr in each_sheet_root(root):
            print('可用节点（前 2 层）:', file=sys.stderr)
            for t in list_first_level_titles(sr)[:50]:
                print(f'  - {t}', file=sys.stderr)
        sys.exit(2)

    # 处理同名冲突
    final_title = unique_child_title(parent, args.child)
    if final_title != args.child:
        print(f'⚠️  父节点下已存在同名子节点 "{args.child}"，自动改名为 "{final_title}"')

    new_topic = make_topic(final_title, args.notes, args.marker)
    container = get_children_container(parent)
    container.append(new_topic)

    out = save_xmind(root, other_files, fp, args.output, args.in_place)
    print(f'✅ 已在父节点 "{args.parent}" 下添加子节点 "{final_title}"')
    print(f'   输出: {out}')


def cmd_apply(args):
    """按 JSON 计划批量应用。"""
    with open(args.plan, 'r', encoding='utf-8') as f:
        plan = json.load(f)
    ops = plan.get('operations', [])
    if not ops:
        print('计划文件中无 operations', file=sys.stderr)
        sys.exit(1)

    root, other_files, fp = load_xmind(args.xmind)
    applied = []  # 记录每条 op 的执行结果
    errors = []

    for i, op in enumerate(ops, 1):
        try:
            optype = op.get('op')
            if optype == 'add':
                # 找父节点
                parent_title = op.get('parent', '')
                parent = None
                for sr in each_sheet_root(root):
                    def deep_find(t):
                        if get_title(t) == parent_title:
                            return t
                        for c in get_children(t):
                            r = deep_find(c)
                            if r is not None:
                                return r
                        return None
                    parent = deep_find(sr)
                    if parent is not None:
                        break
                if parent is None:
                    errors.append(f'#{i} add: 父节点 "{parent_title}" 不存在')
                    continue
                child_title = op.get('child', '')
                if not child_title:
                    errors.append(f'#{i} add: child 为空')
                    continue
                final = unique_child_title(parent, child_title)
                if final != child_title:
                    applied.append(f'add "{child_title}" → "{final}" (under "{parent_title}")')
                else:
                    applied.append(f'add "{child_title}" (under "{parent_title}")')
                new_topic = make_topic(final, op.get('notes'), op.get('marker'))
                get_children_container(parent).append(new_topic)
            elif optype == 'remove':
                target = None
                for sr in each_sheet_root(root):
                    result = find_node_by_title(sr, op.get('title', ''), op.get('parent'))
                    if result:
                        target, parent = result
                        break
                if target is None:
                    errors.append(f'#{i} remove: 节点 "{op.get("title")}" 不存在')
                    continue
                applied.append(f'remove "{get_title(target)}"')
                container = get_children_container(parent) if parent is not None else None
                if container is not None:
                    for c in list(container.findall('xmap:topic', NS)):
                        if c is target:
                            container.remove(c)
                            break
            elif optype == 'set-notes':
                target = None
                for sr in each_sheet_root(root):
                    result = find_node_by_title(sr, op.get('title', ''), op.get('parent'))
                    if result:
                        target, _ = result
                        break
                if target is None:
                    errors.append(f'#{i} set-notes: 节点 "{op.get("title")}" 不存在')
                    continue
                set_notes(target, op.get('notes', ''))
                applied.append(f'set-notes "{get_title(target)}"')
            elif optype == 'set-marker':
                target = None
                for sr in each_sheet_root(root):
                    result = find_node_by_title(sr, op.get('title', ''), op.get('parent'))
                    if result:
                        target, _ = result
                        break
                if target is None:
                    errors.append(f'#{i} set-marker: 节点 "{op.get("title")}" 不存在')
                    continue
                set_marker(target, op.get('marker', ''))
                applied.append(f'set-marker "{get_title(target)}" = {op.get("marker", "")}')
            else:
                errors.append(f'#{i} 未知 op 类型: {optype}')
        except Exception as e:
            errors.append(f'#{i} 异常: {e}')

    if errors:
        print('⚠️  以下操作失败:', file=sys.stderr)
        for e in errors:
            print(f'   {e}', file=sys.stderr)
        # 即使有错误也尝试保存成功的部分
        if not applied:
            sys.exit(3)

    out = save_xmind(root, other_files, fp, args.output, args.in_place)
    print(f'✅ 批量应用完成: {len(applied)} 成功, {len(errors)} 失败')
    print(f'   输出: {out}')
    if applied:
        print('   变更清单:')
        for a in applied:
            print(f'     - {a}')
    if errors:
        print('   失败项:', file=sys.stderr)
        for e in errors:
            print(f'     - {e}', file=sys.stderr)


def cmd_set_notes(args):
    root, other_files, fp = load_xmind(args.xmind)
    target = None
    for sr in each_sheet_root(root):
        result = find_node_by_title(sr, args.title, args.parent)
        if result:
            target, _ = result
            break
    if target is None:
        print(f'错误: 未找到节点 "{args.title}"', file=sys.stderr)
        sys.exit(2)
    set_notes(target, args.notes)
    out = save_xmind(root, other_files, fp, args.output, args.in_place)
    print(f'✅ 已更新节点 "{args.title}" 的 notes')
    print(f'   输出: {out}')


def cmd_set_marker(args):
    root, other_files, fp = load_xmind(args.xmind)
    target = None
    for sr in each_sheet_root(root):
        result = find_node_by_title(sr, args.title, args.parent)
        if result:
            target, _ = result
            break
    if target is None:
        print(f'错误: 未找到节点 "{args.title}"', file=sys.stderr)
        sys.exit(2)
    set_marker(target, args.marker)
    out = save_xmind(root, other_files, fp, args.output, args.in_place)
    print(f'✅ 已更新节点 "{args.title}" 的 marker = {args.marker}')
    print(f'   输出: {out}')


# ========== 主入口 ==========

def main():
    parser = argparse.ArgumentParser(
        description='XMind 增量编辑工具（增/删/改 节点）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest='cmd', required=True, metavar='<subcommand>')

    # 通用参数
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('xmind', help='XMind 文件路径')
    common.add_argument('--in-place', action='store_true', help='原地修改（默认输出 <原名>-new.xmind）')
    common.add_argument('--output', help='输出文件路径（与 --in-place 互斥）')

    # remove
    p = sub.add_parser('remove', parents=[common], help='删除指定节点',
                      description='删除指定标题的节点。可用 --parent 限定父节点以防误删同名节点。')
    p.add_argument('title', help='要删除的节点标题')
    p.add_argument('--parent', help='限定父节点标题（可选）')
    p.add_argument('--dry-run', action='store_true', help='只分析不修改')
    p.set_defaults(func=cmd_remove)

    # add
    p = sub.add_parser('add', parents=[common], help='在指定父节点下添加子节点',
                      description='在父节点下添加子节点。父节点通过标题定位（递归搜索全树）。')
    p.add_argument('parent', help='父节点标题（递归搜索全树定位）')
    p.add_argument('child', help='子节点标题')
    p.add_argument('--notes', help='子节点 notes（备注）')
    p.add_argument('--marker', choices=['priority-1', 'priority-2', 'priority-3', 'flag-red'],
                   help='优先级 marker（priority-1=高/2=中/3=低）')
    p.set_defaults(func=cmd_add)

    # apply
    p = sub.add_parser('apply', parents=[common[:-0] if False else common], help='从 JSON 计划批量应用增/删/改',
                      description='按 JSON 计划批量执行多个操作。计划文件见模块顶部 docstring。')
    # 重新声明 apply 不需要 parents（避免 xmind 在 --in-place 之前被吞掉）
    # 实际上保留 parents[common] 是对的
    p.add_argument('--plan', required=True, help='补充计划 JSON 文件路径')
    p.set_defaults(func=cmd_apply)

    # set-notes
    p = sub.add_parser('set-notes', parents=[common], help='更新节点 notes',
                      description='替换指定节点的 notes 内容。空字符串则删除 notes。')
    p.add_argument('title', help='目标节点标题')
    p.add_argument('notes', help='新 notes 内容（空字符串则删除）')
    p.add_argument('--parent', help='限定父节点标题（可选）')
    p.set_defaults(func=cmd_set_notes)

    # set-marker
    p = sub.add_parser('set-marker', parents=[common], help='更新节点 marker',
                      description='替换指定节点的 marker。空字符串则删除 marker。')
    p.add_argument('title', help='目标节点标题')
    p.add_argument('marker', help='新 marker-id（如 priority-1，空字符串则删除）')
    p.add_argument('--parent', help='限定父节点标题（可选）')
    p.set_defaults(func=cmd_set_marker)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
