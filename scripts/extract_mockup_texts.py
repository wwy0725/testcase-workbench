#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""庄周 mockup 原始 JSON → 全量文本清单 + 设计稿图片 URL

用法：
  python extract_mockup_texts.py <mockup-raw 输出文件> [输出文件]

输入是 chuangtzu CLI 拉回的原始响应（含进度行 + JSON，图层 JSON 双重转义）。
逐字段枚举全部 content 文本节点（去重保序），并列出图片 URL。
文本清单零丢失，供 agent 通读；图片下载后视觉读取——部分标注全文
（如字段删除/改名说明）只存在于设计稿图片中，只读文本会漏。

输出：默认写 <输入名>-texts.txt（与输入同目录）并打印到 stdout。
"""

import sys
import io
import re
import json
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

Q = '"'
BS = chr(92)  # 反斜杠（避免源码转义歧义）


def _decode(s):
    """还原 content 值中的 \\uXXXX 等转义；失败则原样返回。"""
    try:
        return json.loads(Q + s + Q)
    except Exception:
        return s


def extract_texts(t):
    """提取全部 content 文本节点，去重保序。兼容转义与未转义两种形态。"""
    texts = []
    seen = set()

    def push(v):
        v = v.strip()
        if v and v not in seen:
            seen.add(v)
            texts.append(v)

    # 转义形态：\"content\":\"...\"
    esc = re.escape(BS + Q + "content" + BS + Q + ":" + BS + Q)
    for v in re.findall(esc + "([^" + re.escape(BS) + Q + r"]+)" + re.escape(BS + Q), t):
        push(_decode(v))
    # 普通形态："content":"..."
    plain = re.escape(Q + "content" + Q + ":" + Q)
    for v in re.findall(plain + "([^" + Q + r"]*)\"", t):
        push(_decode(v))
    return texts


def extract_image_urls(t):
    """提取图片 URL（http(s):// 或协议相对 // 开头，以图片扩展名结尾）。"""
    pat = "(?:https?:)?//[^\\s" + re.escape(BS) + Q + "'<>]+"
    urls = []
    for u in re.findall(pat, t):
        if re.search(r"\.(png|jpe?g|webp|gif|bmp)$", u, re.I) and u not in urls:
            urls.append(u)
    return urls


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src = Path(sys.argv[1])
    t = src.read_text(encoding="utf-8", errors="replace")
    texts = extract_texts(t)
    urls = extract_image_urls(t)

    # imagePath 字段指定的图是 mockup 原图，排最前
    primary = None
    i = t.find("imagePath")
    if i >= 0:
        m = re.search("(?:https?:)?//[^\\s" + re.escape(BS) + Q + "'<>]+", t[i:i + 500])
        if m:
            primary = m.group(0)
    ordered = ([primary] if primary else []) + [u for u in urls if u != primary]

    lines = ["## 文本节点（共 %d 条，去重保序）" % len(texts)]
    for idx, v in enumerate(texts, 1):
        lines.append("%d. %s" % (idx, v))
    lines.append("")
    lines.append("## 图片 URL（第 1 个为 imagePath 指定的设计稿原图，下载后视觉读取）")
    for u in ordered:
        lines.append("- " + u)
    out = "\n".join(lines)

    dest = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name(src.stem + "-texts.txt")
    dest.write_text(out + "\n", encoding="utf-8")
    print(out)
    print()
    print("已写入:", dest)


if __name__ == "__main__":
    main()
