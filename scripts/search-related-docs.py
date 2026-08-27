#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全文检索相关文档。

本质：每次全量 grep 知识库的 _raw/ 目录（< 1 秒），不是索引。
Baymax 部分查预建索引（baymax-功能映射.json）。

业务术语和同义词从知识库项目的 glossary.md 加载，硬编码的同义词组已移除。

用法：
  python search-related-docs.py --need "做XX功能测试" --raw-dir ../testcase-knowledge/knowledge/_raw
  python search-related-docs.py --keywords "关键词1,关键词2" --raw-dir ../testcase-knowledge/knowledge/_raw
  python search-related-docs.py --keywords "关键词" --raw-dir ../testcase-knowledge/knowledge/_raw --output debug.md
"""

import sys
import os
import io
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 强制 UTF-8 输出
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

def load_synonyms_from_glossary(glossary_path: Path) -> dict:
    """从 glossary.md 加载同义词组。

    期望格式（markdown 表格）：
    | 术语 | 同义词 | 定义 | 来源 |
    | 跟进记录 | 跟进,写跟进,新增跟进 | ... | ... |

    如果没有同义词列或解析失败，返回空 dict。
    """
    if not glossary_path.exists():
        return {}

    content = glossary_path.read_text(encoding='utf-8')
    synonyms = {}

    for line in content.split('\n'):
        m = re.match(r'\|\s*\*?\*?([^*|]+?)\*?\*?\s*\|\s*\*?\*?([^*|]+?)\*?\*?\s*\|', line)
        if m:
            term = m.group(1).strip().replace('**', '').strip()
            syns = m.group(2).strip().replace('**', '').strip()
            if term and syns and term not in ('术语', '同义词', '---'):
                synonyms[term] = [s.strip() for s in syns.split(',') if s.strip()]

    return synonyms


def load_business_terms(glossary_path: Path = None) -> list:
    """从 glossary.md 加载业务术语列表（用于 fuzzy 匹配用户输入）。"""
    if glossary_path is None:
        # 默认尝试从环境变量推导知识库路径
        knowledge_root = os.environ.get('BUSINESS_KNOWLEDGE_ROOT')
        if knowledge_root:
            glossary_path = Path(knowledge_root) / 'knowledge' / 'glossary.md'
        else:
            return []

    if not glossary_path.exists():
        return []

    content = glossary_path.read_text(encoding='utf-8')
    terms = set()

    # 提取 markdown 表格中的"术语"列
    for line in content.split('\n'):
        m = re.match(r'\|\s*\*?\*?([^*|]+?)\*?\*?\s*\|', line)
        if m:
            term = m.group(1).strip()
            if term and not term.startswith('---') and len(term) < 30:
                term = term.replace('**', '').strip()
                if term and not term.startswith('|') and term not in ('术语', '定义', '来源', '业务线归属', '同义词'):
                    terms.add(term)

    return list(terms)


def extract_keywords_from_need(need_text: str, business_terms: list = None) -> list:
    """从用户需求描述中智能提取关键词。

    策略：用 glossary.md 的业务术语做 fuzzy 匹配，匹配上的算关键词。
    避免分词切碎（如"做跟进记录功能测试" → "做跟进记录功"+"能测试"）。
    """
    if not need_text:
        return []

    if business_terms is None:
        business_terms = load_business_terms()

    # 按术语长度从长到短排序，优先匹配长词（避免"跟进记录"被"跟进"先匹配走）
    sorted_terms = sorted(business_terms, key=len, reverse=True)

    matched = []
    used_positions = set()  # 已匹配的位置，避免重复

    for term in sorted_terms:
        # 在 need_text 中找所有出现位置
        for m in re.finditer(re.escape(term), need_text):
            pos_range = range(m.start(), m.end())
            # 如果该位置已被更长词占用，跳过
            if any(p in used_positions for p in pos_range):
                continue
            used_positions.update(pos_range)
            if term not in matched:
                matched.append(term)
            break  # 一个术语匹配一次即可

    return matched[:10]


def expand_keywords(keywords: list, synonym_groups: dict = None) -> list:
    """基于同义词组扩展关键词。synonym_groups 从 glossary.md 动态加载。"""
    expanded = set(keywords)
    if not synonym_groups:
        return list(expanded)
    for kw in keywords:
        for group_key, group_words in synonym_groups.items():
            if kw in group_words or kw == group_key:
                expanded.update(group_words)
    return list(expanded)


def search_in_raw(raw_dir: Path, keywords: list) -> dict:
    """在 _raw/ 中搜索关键词，返回 {文件路径: {命中行, 命中数, 标题命中, 上下文}}。"""
    results = {}

    for md_file in raw_dir.rglob('*.md'):
        try:
            content = md_file.read_text(encoding='utf-8')
        except Exception:
            continue

        file_result = {
            'path': str(md_file.relative_to(raw_dir.parent.parent)),
            'hits': [],  # [(行号, 上下文行)]
            'count': 0,
            'title_hit': False,
            'size_kb': len(content) / 1024,
        }

        for line_no, line in enumerate(content.split('\n'), 1):
            line_lower = line.lower()
            for kw in keywords:
                if kw.lower() in line_lower:
                    file_result['count'] += 1
                    if line_no <= 5:  # 标题区域
                        file_result['title_hit'] = True
                    # 收集上下文（前后各 1 行）
                    file_result['hits'].append((line_no, line.strip()[:150]))

        if file_result['count'] > 0:
            # 限制每个文件最多 10 个命中行（避免索引文件过大）
            file_result['hits'] = file_result['hits'][:10]
            results[md_file] = file_result

    return results


def categorize_results(results: dict) -> dict:
    """按相关度分级：必读 / 相关 / 可能相关。"""
    must_read = []
    relevant = []
    possible = []

    for file_path, info in results.items():
        entry = (file_path, info)
        if info['title_hit'] or info['count'] >= 5:
            must_read.append(entry)
        elif info['count'] >= 2:
            relevant.append(entry)
        else:
            possible.append(entry)

    # 内部排序：按命中数倒序
    must_read.sort(key=lambda x: -x[1]['count'])
    relevant.sort(key=lambda x: -x[1]['count'])
    possible.sort(key=lambda x: -x[1]['count'])

    return {
        'must_read': must_read,
        'relevant': relevant,
        'possible': possible,
    }


def find_data_creation_docs(raw_dir: Path) -> list:
    """找出所有"造数"相关的文档。

    注意：造数文档是**测试执行阶段**的参考（怎么准备测试数据），
    不是**生成用例阶段**的输入。subagent 默认不读造数。
    """
    data_docs = []
    for md_file in raw_dir.rglob('*.md'):
        try:
            content = md_file.read_text(encoding='utf-8')
        except Exception:
            continue

        # 文件名含"造数"或内容高频含"造数"
        if '造数' in md_file.name:
            data_docs.append((md_file, {'reason': '文件名含"造数"', 'size_kb': len(content) / 1024}))
        elif content.count('造数') >= 3:
            data_docs.append((md_file, {'reason': f'内容含"造数" {content.count("造数")} 次', 'size_kb': len(content) / 1024}))

    return data_docs


def find_cross_module_links(raw_dir: Path, keywords: list) -> list:
    """找出与关键词相关的跨模块引用（如"跟进记录"引用了商机/签到等）。"""
    cross_links = []

    for md_file in raw_dir.rglob('*.md'):
        try:
            content = md_file.read_text(encoding='utf-8')
        except Exception:
            continue

        # 提取其他业务模块名（在文档中作为章节引用）
        module_keywords = ['商机', '签到', '签退', '一人式', '机构一户式', '企业一户式',
                           '客户管理', '责任户', '公共池', '续费', '联合经营', '转介绍',
                           '评论', '外呼', '附件']

        for mk in module_keywords:
            if mk in keywords:  # 跳过关键词自身
                continue
            if mk in content and any(kw in content for kw in keywords):
                # 这个文档既包含关键词又包含 mk → 跨模块关联
                cross_links.append((md_file.name, mk))
                break

    # 去重
    seen = set()
    unique = []
    for name, mk in cross_links:
        key = (name, mk)
        if key not in seen:
            seen.add(key)
            unique.append((name, mk))

    return unique


def find_baymax_cases(keywords: list, expanded: list, baymax_idx_path: Path = None) -> list:
    """从 Baymax 索引中找相关历史用例。返回 [(uid, score, title, source), ...] 按分数降序。

    仅做关键词匹配（by_tag + by_path），不做路径层级兜底。
    baymax_idx_path 从知识库项目读取。"""
    if baymax_idx_path is None or not baymax_idx_path.exists():
        return []

    try:
        with open(baymax_idx_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f'⚠️ Baymax 索引读取失败: {e}', file=sys.stderr)
        return []

    case_scores = defaultdict(int)
    for kw in expanded:
        if kw in data['by_tag']:
            for uid in data['by_tag'][kw]:
                case_scores[uid] += 2
        for path_node, uids in data['by_path'].items():
            if kw in path_node:
                for uid in uids:
                    case_scores[uid] += 1

    sorted_cases = sorted(case_scores.items(), key=lambda x: -x[1])[:50]
    cases_index = data.get('cases', {})

    results = []
    for uid, score in sorted_cases:
        if uid in cases_index:
            info = cases_index[uid]
            results.append((uid, score, info.get('t', ''), info.get('s', '')))
    return results


def format_index_markdown(need_text: str, keywords: list, expanded: list,
                          categorized: dict, data_docs: list,
                          cross_links: list, baymax_cases: list = None,
                          include_data_creation: bool = False) -> str:
    """格式化输出 Markdown 索引。"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = []

    lines.append(f"# 按需索引：{need_text or '+'.join(keywords[:3])}")
    lines.append('')
    lines.append(f'- **生成时间**: {now}')
    lines.append(f'- **原始需求**: {need_text or "(未提供)"}')
    lines.append(f'- **关键词集**: {", ".join(keywords)}')
    lines.append(f'- **扩展词**: {", ".join([k for k in expanded if k not in keywords])}')
    lines.append(f'- **命中文件总数**: {len(categorized["must_read"]) + len(categorized["relevant"]) + len(categorized["possible"])}')
    lines.append('')
    lines.append('---')
    lines.append('')

    # 🔥 必读
    if categorized['must_read']:
        lines.append(f'## 🔥 必读（{len(categorized["must_read"])} 个）')
        lines.append('')
        for i, (file_path, info) in enumerate(categorized['must_read'], 1):
            rel_path = file_path.relative_to(file_path.parents[3]) if len(file_path.parts) > 3 else file_path.name
            lines.append(f'### {i}. `{rel_path}`')
            lines.append(f'- **大小**: {info["size_kb"]:.1f} KB')
            lines.append(f'- **命中次数**: {info["count"]}')
            if info['title_hit']:
                lines.append(f'- **标题命中**: ✓（在文档前 5 行）')
            lines.append(f'- **关键段落**（最多 10 行）:')
            for line_no, snippet in info['hits'][:8]:
                lines.append(f'  - L{line_no}: {snippet}')
            lines.append('')

    # 📌 相关
    if categorized['relevant']:
        lines.append(f'## 📌 相关（{len(categorized["relevant"])} 个）')
        lines.append('')
        for file_path, info in categorized['relevant']:
            rel_path = file_path.relative_to(file_path.parents[3]) if len(file_path.parts) > 3 else file_path.name
            lines.append(f'- **`{rel_path}`**（命中 {info["count"]} 次，{info["size_kb"]:.1f} KB）')
        lines.append('')

    # 💡 可能相关
    if categorized['possible']:
        lines.append(f'## 💡 可能相关（{len(categorized["possible"])} 个）')
        lines.append('')
        for file_path, info in categorized['possible']:
            rel_path = file_path.relative_to(file_path.parents[3]) if len(file_path.parts) > 3 else file_path.name
            lines.append(f'- `{rel_path}`（命中 1 次）')
        lines.append('')

    # 🧪 涉及的造数方式（仅当显式启用时显示）
    if data_docs and include_data_creation:
        lines.append(f'## 🧪 涉及的造数方式（{len(data_docs)} 个）')
        lines.append('')
        lines.append('> ⚠️ **造数是测试执行阶段参考，不是生成用例的输入**。')
        lines.append('> 这些文档讲解"如何造测试数据"，测试人员拿到用例后准备数据时参考。')
        lines.append('> subagent 生成用例时**不需要**读这些。')
        lines.append('')
        for file_path, info in data_docs:
            rel_path = file_path.relative_to(file_path.parents[3]) if len(file_path.parts) > 3 else file_path.name
            lines.append(f'- **`{rel_path}`**（{info["reason"]}，{info["size_kb"]:.1f} KB）')
        lines.append('')

    # 🔗 跨模块影响
    if cross_links:
        lines.append(f'## 🔗 跨模块影响（{len(cross_links)} 个关联）')
        lines.append('')
        lines.append('> 这些模块与当前需求存在数据/流程耦合，**用例必须覆盖跨模块交互**。')
        lines.append('')
        for file_name, mk in cross_links:
            lines.append(f'- `{file_name}` ↔ **{mk}**')
        lines.append('')

    # 📜 Baymax 历史用例（作为回归参考）
    if baymax_cases:
        lines.append(f'## 📜 Baymax 历史用例参考（{len(baymax_cases)} 个最相关）')
        lines.append('')
        lines.append('> 来自 Baymax 团队级用例库（12,696 个历史用例）。仅列标题作为风格/覆盖/回归参考，**不要读全文**。')
        lines.append('')
        for uid, score, title, source in baymax_cases:
            score_str = '★' * min(score, 5) if score > 0 else '·'
            lines.append(f'- {score_str} **{title}**')
            lines.append(f'  - 来源: `{source}` (uid: `{uid}`, 相关度: {score})')
        lines.append('')

    lines.append('---')
    lines.append('')
    lines.append('## 📋 使用建议')
    lines.append('')
    lines.append('1. **subagent 必读顺序**：🔥 必读 → 🔗 跨模块 → 📜 Baymax → 📌 相关 → 💡 可能')
    lines.append('2. 命中"标题"或"5+ 次"的文档是核心，**不能跳过**')
    lines.append('3. 跨模块影响必须写集成测试用例，不能只测单模块')
    lines.append('4. **Baymax 历史用例作为风格/覆盖/回归参考**——列出的标题可参考写法和场景，但不要复述步骤')
    lines.append('5. **造数不在本索引范围内**——造数是测试执行阶段参考，不参与用例生成')
    lines.append('6. 用例中的 `测试数据` 字段写引用即可（例："造数见 _raw/.../xxx.md"），不展开造数细节')
    lines.append('')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='按需建立知识库反向索引')
    parser.add_argument('--need', '-n', help='需求描述（用于智能提取关键词）')
    parser.add_argument('--keywords', '-k', help='显式关键词列表（逗号分隔）')
    parser.add_argument('--raw-dir', required=True, help='原始知识库目录（必填，如 ../testcase-knowledge/knowledge/_raw）')
    parser.add_argument('--output', '-o', help='输出到文件（不指定则输出到 stdout）')
    parser.add_argument('--quiet', action='store_true', help='静默模式（仅摘要，不输出索引内容）')
    parser.add_argument('--with-data-creation', action='store_true',
                        help='包含造数文档（默认不包含——造数是执行阶段参考，与生成用例无关）')
    parser.add_argument('--knowledge-root', default=os.environ.get('BUSINESS_KNOWLEDGE_ROOT'),
                        help='知识库项目根目录（默认从 BUSINESS_KNOWLEDGE_ROOT 环境变量读取）')

    args = parser.parse_args()

    # 确定知识库 glossary 路径
    glossary_path = None
    if args.knowledge_root:
        glossary_path = Path(args.knowledge_root) / 'knowledge' / 'glossary.md'

    # 加载同义词组和术语
    synonym_groups = load_synonyms_from_glossary(glossary_path) if glossary_path and glossary_path.exists() else {}
    business_terms = load_business_terms(glossary_path) if glossary_path and glossary_path.exists() else []

    # 解析关键词
    keywords = []
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(',') if k.strip()]
    if args.need and business_terms:
        # 用 glossary.md 的业务术语做 fuzzy 匹配
        auto_kws = extract_keywords_from_need(args.need, business_terms)
        keywords.extend(auto_kws)

    if not keywords:
        print('错误：必须提供 --keywords 或 --need 至少一个', file=sys.stderr)
        sys.exit(1)

    # 去重
    keywords = list(dict.fromkeys(keywords))

    # 扩展同义词（从 glossary.md 动态加载）
    expanded = expand_keywords(keywords, synonym_groups)

    # 确定 raw 目录
    raw_dir = Path(args.raw_dir)
    if not raw_dir.exists():
        print(f'错误：原始知识库目录不存在: {raw_dir}', file=sys.stderr)
        sys.exit(1)

    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_path = None  # 输出到 stdout

    # 确定 Baymax 索引路径（从知识库项目读取）
    baymax_idx_path = None
    if args.knowledge_root:
        baymax_idx_path = Path(args.knowledge_root) / 'knowledge' / '_index' / 'baymax-功能映射.json'

    # 搜索
    total_found = 0
    if not args.quiet:
        print(f'🔍 搜索 {len(expanded)} 个关键词（原始 {len(keywords)} + 扩展 {len(expanded) - len(keywords)}）...', file=sys.stderr)

    results = search_in_raw(raw_dir, expanded)
    categorized = categorize_results(results)
    data_docs = find_data_creation_docs(raw_dir) if args.with_data_creation else []
    cross_links = find_cross_module_links(raw_dir, expanded)
    baymax_cases = find_baymax_cases(keywords, expanded, baymax_idx_path)

    # 格式化输出
    content = format_index_markdown(
        args.need or '',
        keywords,
        expanded,
        categorized,
        data_docs,
        cross_links,
        baymax_cases=baymax_cases,
        include_data_creation=args.with_data_creation,
    )

    # 输出：有 --output 则写文件，否则 stdout（subagent 直接读）
    if args.output:
        output_path.write_text(content, encoding='utf-8')
    else:
        sys.stdout.write(content)

    if not args.quiet:
        total = len(categorized['must_read']) + len(categorized['relevant']) + len(categorized['possible'])
        summary = (
            f'\n📊 必读:{len(categorized["must_read"])}  相关:{len(categorized["relevant"])}  '
            f'可能:{len(categorized["possible"])}  跨模块:{len(cross_links)}  '
            f'Baymax:{len(baymax_cases)}  合计:{total}'
        )
        if args.output:
            print(f'✅ 索引已生成: {output_path}', file=sys.stderr)
        print(summary, file=sys.stderr)


if __name__ == '__main__':
    main()
