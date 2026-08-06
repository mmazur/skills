#!/usr/bin/env python3
"""Convert Google Docs API JSON (documents.get) to per-tab Markdown files.

Usage:
    python3 gdoc2md.py INPUT.json [--outdir DIR]

Reads the JSON file, writes one .md file per tab into outdir,
and prints a JSON summary to stdout listing tabs with their file paths.
"""

import json
import sys
import os
import re
import argparse

HEADING_MAP = {
    "HEADING_1": "# ",
    "HEADING_2": "## ",
    "HEADING_3": "### ",
    "HEADING_4": "#### ",
    "HEADING_5": "##### ",
    "HEADING_6": "###### ",
}

MONO_FONTS = frozenset({
    "Courier New", "Consolas", "Roboto Mono", "Source Code Pro",
    "Fira Code", "Inconsolata", "JetBrains Mono", "Ubuntu Mono",
    "Noto Sans Mono", "Droid Sans Mono", "PT Mono",
})


def _is_mono(style: dict) -> bool:
    family = style.get("weightedFontFamily", {}).get("fontFamily", "")
    return family in MONO_FONTS


def _paragraph_is_code(paragraph: dict) -> bool:
    elements = paragraph.get("elements", [])
    has_non_empty = False
    for el in elements:
        tr = el.get("textRun")
        if not tr:
            continue
        content = tr.get("content", "")
        if content.strip() == "":
            continue
        has_non_empty = True
        if not _is_mono(tr.get("textStyle", {})):
            return False
    return has_non_empty


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def _build_heading_map(body: dict) -> dict[str, str]:
    """Map Google Docs heading IDs (h.xxx) to markdown anchor slugs."""
    hmap = {}
    for element in body.get("content", []):
        para = element.get("paragraph")
        if not para:
            continue
        style = para.get("paragraphStyle", {})
        heading_id = style.get("headingId")
        named_style = style.get("namedStyleType", "")
        if heading_id and named_style in HEADING_MAP:
            text_parts = []
            for el in para.get("elements", []):
                tr = el.get("textRun")
                if tr:
                    text_parts.append(tr.get("content", "").strip())
            heading_text = " ".join(text_parts).strip()
            if heading_text:
                hmap[heading_id] = _slugify(heading_text)
    return hmap


def extract_text_run(element: dict, *, code_block: bool = False,
                     heading_anchors: dict | None = None,
                     inline_objects: dict | None = None) -> str:
    if "inlineObjectElement" in element:
        obj_id = element["inlineObjectElement"].get("inlineObjectId", "")
        if inline_objects and obj_id in inline_objects:
            obj = inline_objects[obj_id]
            props = obj.get("inlineObjectProperties", {}).get("embeddedObject", {})
            img_props = props.get("imageProperties", {})
            uri = img_props.get("contentUri", "")
            title = props.get("title", "")
            desc = props.get("description", title or "image")
            if uri:
                return f"![{desc}]({uri})"
        return ""

    tr = element.get("textRun")
    if not tr:
        return ""
    content = tr.get("content", "")
    style = tr.get("textStyle", {})

    if not content or content == "\n":
        return content

    text = content
    trailing_newline = text.endswith("\n")
    if trailing_newline:
        text = text[:-1]

    if not text:
        return "\n" if trailing_newline else ""

    if code_block:
        if trailing_newline:
            text += "\n"
        return text

    link_info = style.get("link", {})
    link_url = link_info.get("url")
    heading_id = link_info.get("headingId")
    bookmark_id = link_info.get("bookmarkId")

    bold = style.get("bold", False)
    italic = style.get("italic", False)
    strikethrough = style.get("strikethrough", False)
    is_mono = _is_mono(style)

    if is_mono:
        text = f"`{text}`"
    else:
        if bold and italic:
            text = f"***{text}***"
        elif bold:
            text = f"**{text}**"
        elif italic:
            text = f"*{text}*"
        if strikethrough:
            text = f"~~{text}~~"

    if link_url:
        text = f"[{text}]({link_url})"
    elif heading_id and heading_anchors and heading_id in heading_anchors:
        slug = heading_anchors[heading_id]
        text = f"[{text}](#{slug})"
    elif bookmark_id:
        text = f"[{text}](#bookmark-{bookmark_id})"

    if trailing_newline:
        text += "\n"
    return text


def convert_paragraph(paragraph: dict, lists: dict, *,
                      code_block: bool = False,
                      heading_anchors: dict | None = None,
                      inline_objects: dict | None = None) -> str:
    style = paragraph.get("paragraphStyle", {})
    named_style = style.get("namedStyleType", "NORMAL_TEXT")
    heading_prefix = HEADING_MAP.get(named_style, "")

    bullet = paragraph.get("bullet")
    bullet_prefix = ""
    if bullet and not code_block:
        list_id = bullet.get("listId", "")
        nesting = bullet.get("nestingLevel", 0)
        indent = "  " * nesting
        list_props = lists.get(list_id, {})
        nesting_levels = list_props.get("listProperties", {}).get("nestingLevels", [])
        glyph = None
        if nesting < len(nesting_levels):
            glyph = nesting_levels[nesting].get("glyphType")
        if glyph and glyph in ("DECIMAL", "ALPHA", "UPPER_ALPHA", "ROMAN", "UPPER_ROMAN"):
            bullet_prefix = f"{indent}1. "
        else:
            bullet_prefix = f"{indent}- "

    elements = paragraph.get("elements", [])
    text_parts = []
    for el in elements:
        text_parts.append(extract_text_run(
            el, code_block=code_block,
            heading_anchors=heading_anchors,
            inline_objects=inline_objects,
        ))

    line = "".join(text_parts)

    if line.strip() == "":
        return "\n"

    trailing = line.endswith("\n")
    if trailing:
        line = line[:-1]

    if not code_block:
        if heading_prefix:
            line = heading_prefix + line
        elif bullet_prefix:
            line = bullet_prefix + line

    if trailing:
        line += "\n"
    return line


def convert_table(table: dict, lists: dict, *,
                  heading_anchors: dict | None = None,
                  inline_objects: dict | None = None) -> str:
    rows = table.get("tableRows", [])
    if not rows:
        return ""

    md_rows: list[list[str]] = []
    for row in rows:
        cells = row.get("tableCells", [])
        md_cells = []
        for cell in cells:
            cell_text_parts = []
            for content_el in cell.get("content", []):
                para = content_el.get("paragraph")
                if para:
                    t = convert_paragraph(
                        para, lists,
                        heading_anchors=heading_anchors,
                        inline_objects=inline_objects,
                    ).strip()
                    cell_text_parts.append(t)
            md_cells.append(" ".join(cell_text_parts).replace("|", "\\|"))
        md_rows.append(md_cells)

    if not md_rows:
        return ""

    col_count = max(len(r) for r in md_rows)
    for r in md_rows:
        while len(r) < col_count:
            r.append("")

    lines = []
    header = md_rows[0]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in md_rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return "\n".join(lines)


def convert_body(body: dict, lists: dict, *,
                 inline_objects: dict | None = None) -> str:
    heading_anchors = _build_heading_map(body)
    content = body.get("content", [])

    elements_classified: list[tuple[str, dict]] = []
    for element in content:
        if "paragraph" in element:
            para = element["paragraph"]
            if _paragraph_is_code(para):
                elements_classified.append(("code", element))
            else:
                elements_classified.append(("para", element))
        elif "table" in element:
            elements_classified.append(("table", element))
        elif "sectionBreak" in element:
            elements_classified.append(("break", element))

    parts: list[str] = []
    prev_was_bullet = False
    in_code_block = False

    for kind, element in elements_classified:
        if kind == "code":
            if not in_code_block:
                if prev_was_bullet:
                    parts.append("\n")
                    prev_was_bullet = False
                parts.append("```\n")
                in_code_block = True
            para = element["paragraph"]
            line = convert_paragraph(para, lists, code_block=True)
            parts.append(line)
        else:
            if in_code_block:
                parts.append("```\n\n")
                in_code_block = False

            if kind == "para":
                para = element["paragraph"]
                is_bullet = "bullet" in para
                if prev_was_bullet and not is_bullet:
                    parts.append("\n")
                line = convert_paragraph(
                    para, lists,
                    heading_anchors=heading_anchors,
                    inline_objects=inline_objects,
                )
                parts.append(line)
                prev_was_bullet = is_bullet
            elif kind == "table":
                if prev_was_bullet:
                    parts.append("\n")
                    prev_was_bullet = False
                parts.append(convert_table(
                    element["table"], lists,
                    heading_anchors=heading_anchors,
                    inline_objects=inline_objects,
                ))
            elif kind == "break":
                pass

    if in_code_block:
        parts.append("```\n")

    return "".join(parts)


def convert_tab(tab: dict) -> tuple[str, str, str]:
    props = tab.get("tabProperties", {})
    tab_id = props.get("tabId", "")
    title = props.get("title", "")
    doc_tab = tab.get("documentTab", {})
    body = doc_tab.get("body", {})
    lists = doc_tab.get("lists", {})
    inline_objects = doc_tab.get("inlineObjects", {})
    md = convert_body(body, lists, inline_objects=inline_objects)
    return tab_id, title, md


def find_tabs_recursive(tabs: list[dict]) -> list[dict]:
    result = []
    for tab in tabs:
        result.append(tab)
        for child in tab.get("childTabs", []):
            result.append(child)
            result.extend(find_tabs_recursive(child.get("childTabs", [])))
    return result


def main():
    parser = argparse.ArgumentParser(description="Convert Google Docs API JSON to per-tab Markdown files")
    parser.add_argument("input", help="Path to the Google Docs API JSON file")
    parser.add_argument("--outdir", default="/tmp/gdoc-read", help="Output directory for .md files (default: /tmp/gdoc-read)")
    args = parser.parse_args()

    with open(args.input) as f:
        doc = json.load(f)

    title = doc.get("title", "Untitled")
    doc_id = doc.get("documentId", "unknown")
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)

    tabs = doc.get("tabs")
    tab_results = []

    if tabs:
        all_tabs = find_tabs_recursive(tabs)
        for tab in all_tabs:
            tab_id, tab_title, md = convert_tab(tab)
            slug = _slugify(tab_title) or tab_id
            filename = f"{slug}.md"
            filepath = os.path.join(outdir, filename)
            with open(filepath, "w") as f:
                f.write(f"# {title} — {tab_title}\n\n")
                f.write(md)
            tab_results.append({
                "tab_id": tab_id,
                "title": tab_title,
                "file": filepath,
            })
    else:
        body = doc.get("body", {})
        lists = doc.get("lists", {})
        inline_objects = doc.get("inlineObjects", {})
        md = convert_body(body, lists, inline_objects=inline_objects)
        filename = f"{_slugify(title) or doc_id}.md"
        filepath = os.path.join(outdir, filename)
        with open(filepath, "w") as f:
            f.write(f"# {title}\n\n")
            f.write(md)
        tab_results.append({
            "tab_id": None,
            "title": title,
            "file": filepath,
        })

    summary = {
        "document_id": doc_id,
        "title": title,
        "tabs": tab_results,
    }
    json.dump(summary, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
