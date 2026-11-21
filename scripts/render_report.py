"""Render an issue index, journal distribution, and citation audit cards in one PDF."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepInFrame, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


HEADING = "#171717"
INK = "#161616"
MUTED = "#363636"
RULE = "#A0A0A0"
WHITE = "#FFFFFF"
WINDOWS_FONTS = Path("C:/Windows/Fonts")
SONG_FONT = WINDOWS_FONTS / "simsun.ttc"
LATIN_TEXT = re.compile(r"[\u0000-\u024F\u1E00-\u1EFF\u2000-\u206F]+")
ISSUE_INDEX_DESTINATION = "audit-issue-index"
SOURCE_TYPES = {"journal", "non_journal", "unverified", "orphan"}
SECTION_TITLES = {
    "location": "1  文末条目编号及位置",
    "authenticity": "2  真实性及其链接",
    "support": "3  原文支持判定",
    "format": "4  标准引用格式",
}


def register_fonts(regular, bold):
    pdfmetrics.registerFont(TTFont("AuditText", str(regular)))
    pdfmetrics.registerFont(TTFont("AuditStrong", str(bold)))
    latin = WINDOWS_FONTS / "times.ttf"
    latin_bold = WINDOWS_FONTS / "timesbd.ttf"
    pdfmetrics.registerFont(TTFont("AuditLatin", str(latin if latin.is_file() else regular)))
    pdfmetrics.registerFont(TTFont("AuditLatinStrong", str(latin_bold if latin_bold.is_file() else bold)))


def text_block(text, *, bold=False, size=9.8, leading=14, color=INK, markup=False):
    style = ParagraphStyle("audit", fontName="AuditStrong" if bold else "AuditText",
                           fontSize=size, leading=leading, textColor=HexColor(color), wordWrap="CJK")
    latin_font = "AuditLatinStrong" if bold else "AuditLatin"
    content = text if markup else escape(text).replace("\n", "<br/>")
    segments = re.split(r"(<[^>]+>)", content)
    for index in range(0, len(segments), 2):
        segments[index] = LATIN_TEXT.sub(
            lambda match: f'<font name="{latin_font}">{match.group()}</font>', segments[index]
        )
    return Paragraph("".join(segments), style)


def link_blocks(links):
    result = []
    for link in links:
        url = urlsplit(link["url"])
        if url.scheme not in {"https", "http"} or not url.hostname or url.username is not None:
            raise ValueError("Source links must be public HTTP(S) URLs without user information.")
        result.append(f"<link href={quoteattr(link['url'])}><u>{escape(link['label'])}</u></link>")
    return "   ·   ".join(result)


def internal_link(label, destination):
    return f'<link href={quoteattr("#" + destination)}><u>{escape(label)}</u></link>'


def index_findings(card, models):
    def checked_issues(value):
        if not isinstance(value, list) or any(
            not isinstance(issue, str) or not issue.strip() for issue in value
        ):
            raise ValueError(f"{card['id']} issues must be a list of nonempty strings.")
        return [issue.strip() for issue in value]

    if "model_issues" not in card:
        return checked_issues(card.get("issues", [])), "issues" not in card

    model_issues = card["model_issues"]
    if not isinstance(model_issues, list) or len(model_issues) != len(models):
        raise ValueError(f"{card['id']} model_issues must have one entry for each model.")
    sources_by_issue = {}
    for model, issues in zip(models, model_issues):
        if issues is None:
            continue
        for issue in dict.fromkeys(checked_issues(issues)):
            sources_by_issue.setdefault(issue, []).append(model["status"])
    lines = [f"{'、'.join(sources)}：{issue}" for issue, sources in sources_by_issue.items()]
    return lines, None in model_issues


def issue_index(entries, models, width):
    rows = [[text_block(label, bold=True, color=INK) for label in ("编号", "文献题名", "问题摘要")]]
    unmarked = 0
    for card, destination in entries:
        issues, incomplete = index_findings(card, models)
        unmarked += int(incomplete)
        if issues:
            rows.append([
                text_block(internal_link(card["id"], destination), bold=True, color=INK, markup=True),
                text_block(internal_link(card["title"], destination), color=INK, markup=True),
                text_block("\n".join(issues)),
            ])

    count = len(rows) - 1
    totals = f"审查对象 {len(entries)} 条   ·   有问题 {count} 条"
    if unmarked:
        totals += f"   ·   未标注问题状态 {unmarked} 条"
    heading = f'<a name="{ISSUE_INDEX_DESTINATION}"/>问题索引'
    content = [
        text_block(heading, bold=True, size=25, leading=32, color=HEADING, markup=True),
        Spacer(1, 8),
        text_block(totals, bold=True, color=INK),
        text_block("点击编号或题名跳转到逐条报告。点击详情页顶部题名返回首页。", color=MUTED),
        Spacer(1, 10),
    ]
    if not count:
        message = "当前报告未列出问题条目。" if unmarked else "本次审查未发现问题条目。"
        return [*content, text_block(message)]

    id_width = 54
    title_width = (width - id_width) * 0.52
    table = Table(rows, colWidths=[id_width, title_width, width - id_width - title_width],
                  repeatRows=1, splitInRow=1)
    table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), .85, HexColor(HEADING)),
        ("LINEBELOW", (0, 0), (-1, 0), .55, HexColor(RULE)),
        ("LINEBELOW", (0, -1), (-1, -1), .8, HexColor(HEADING)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return [*content, table]


def tally_reference_sources(references):
    buckets, journal_counts = Counter(), Counter()
    journal_names = {}
    seen = set()
    for reference in references:
        identifier = reference["id"]
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen:
            raise ValueError("Each reference needs a distinct original identifier.")
        seen.add(identifier)
        kind = reference.get("source_type", "unverified")
        if kind not in SOURCE_TYPES:
            raise ValueError(f"{identifier} has an unsupported source type.")
        if kind == "journal":
            name = " ".join((reference.get("journal") or "").split())
            if not name:
                raise ValueError(f"{identifier} has no verified journal name.")
            key = name.casefold()
            journal_names.setdefault(key, name)
            journal_counts[key] += 1
        buckets[kind] += 1
    journals = sorted(((journal_names[key], amount) for key, amount in journal_counts.items()),
                      key=lambda pair: (-pair[1], pair[0].casefold()))
    return buckets, journals


def overview_table(buckets, journals, width):
    total = buckets["journal"] + buckets["non_journal"] + buckets["unverified"]
    labels = [
        ("文末参考文献", total),
        ("期刊文献", buckets["journal"]),
        ("涉及期刊", len(journals)),
    ]
    row = [[text_block(str(value), bold=True, size=22, leading=27, color=INK),
            text_block(label, size=9.4, color=MUTED)] for label, value in labels]
    table = Table([row], colWidths=[width / len(labels)] * len(labels))
    table.setStyle(TableStyle([
        ("LINEBEFORE", (1, 0), (1, 0), .5, HexColor(RULE)),
        ("LINEBEFORE", (2, 0), (2, 0), .5, HexColor(RULE)),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return table


def journal_table(journals, total, width):
    headings = [text_block(label, bold=True, color=INK) for label in ("期刊名称", "条目数", "占期刊文献")]
    rows = [headings]
    for name, amount in journals:
        rows.append([text_block(name), text_block(str(amount), bold=True, color=INK),
                     text_block(f"{amount / total:.1%}")])
    rows.append([text_block("合计", bold=True), text_block(str(total), bold=True),
                 text_block("100%", bold=True)])
    table = Table(rows, colWidths=[width - 152, 60, 92], repeatRows=1)
    table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), .85, HexColor(HEADING)),
        ("LINEBELOW", (0, 0), (-1, 0), .55, HexColor(RULE)),
        ("LINEBELOW", (0, -1), (-1, -1), .8, HexColor(HEADING)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def distribution_section(references, width):
    counts, journals = tally_reference_sources(references)
    details = f"非期刊文献 {counts['non_journal']} 条   ·   来源待核 {counts['unverified']} 条"
    content = [
        KeepTogether([
            Spacer(1, 18),
            text_block("参考文献分布", bold=True, size=20, leading=26, color=HEADING),
            Spacer(1, 8),
            overview_table(counts, journals, width),
            Spacer(1, 8),
            text_block(details, size=9.3, color=MUTED),
        ]),
        Spacer(1, 9),
    ]
    if journals:
        content.append(journal_table(journals, counts["journal"], width))
    else:
        content.append(text_block("审查范围内的文末条目暂无已核实的期刊来源。"))
    content.extend([
        Spacer(1, 9),
        text_block("按审查范围内的文末条目计数。各刊占比以已核实的期刊条目总数为分母。",
                   size=8.8, color=MUTED),
    ])
    return content


def title_block(card, width, destination):
    title = f'<a name="{destination}"/>{internal_link(card["title"], ISSUE_INDEX_DESTINATION)}'
    banner = Table([[
        text_block(card["id"], bold=True, size=20, leading=24, color=HEADING),
        [
            text_block(title, bold=True, size=16, leading=21, color=INK, markup=True),
            Spacer(1, 4),
            text_block(card.get("authors", ""), size=9.4, color=MUTED),
        ],
    ]], colWidths=[66, width - 66])
    banner.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), .8, HexColor(HEADING)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return banner


def model_cell(cell):
    blocks = []
    if cell.get("status"):
        status = cell["status"]
        blocks.append(text_block(status, bold=True, size=9.2,
                                 color=MUTED if status in {"未运行", "未返回"} else INK))
    if cell.get("detail"):
        blocks.append(text_block(cell["detail"], size=9.1, leading=13))
    return blocks or [text_block("未返回", size=9.1, color=MUTED)]


def section_box(heading, width, *, shared=None, model_blocks=None, evidence=None):
    title = text_block(heading, bold=True, size=11.0, color=HEADING)
    count = len(model_blocks) if model_blocks else 1
    rows = [[title] + [""] * (count - 1)]
    styles = [
        ("BOX", (0, 0), (-1, -1), .65, HexColor(RULE)),
        ("LINEBELOW", (0, 0), (-1, 0), .45, HexColor(RULE)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if count > 1:
        styles.append(("SPAN", (0, 0), (-1, 0)))
    if model_blocks:
        rows.append(model_blocks)
        for column in range(1, count):
            styles.append(("LINEBEFORE", (column, 1), (column, 1), .45, HexColor(RULE)))
    if shared or evidence:
        rows.append([[block for block in (shared, evidence) if block is not None]] + [""] * (count - 1))
        if count > 1:
            styles.append(("SPAN", (0, len(rows) - 1), (-1, len(rows) - 1)))
    return Table(rows, colWidths=[width / count] * count, style=TableStyle(styles),
                 repeatRows=1, splitInRow=1)


def reference_sections(card, models, width):
    count = len(models)
    lead = {**models[0], "status": f"{models[0]['status']}  ·  {card['id']}"}
    model_header = Table([[model_cell(model) for model in [lead, *models[1:]]]],
                         colWidths=[width / count] * count,
                         style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    content = [model_header]
    sections = card["sections"]
    missing_sections = {"location", "authenticity", "format"} - sections.keys()
    if missing_sections:
        raise ValueError(f"{card['id']} is missing sections: {', '.join(sorted(missing_sections))}.")
    for key, heading in SECTION_TITLES.items():
        section = sections.get(key)
        if section is None:
            box = section_box(heading, width, shared=text_block("未提供原文支持判定。", color=MUTED))
        elif key == "format":
            citation = section.get("shared")
            if not isinstance(citation, str) or not citation.strip():
                raise ValueError(f"{card['id']} requires a standard reference or a pending-status message.")
            box = section_box(heading, width, shared=text_block(citation))
        else:
            cells = section["cells"]
            if len(cells) != count:
                raise ValueError(f"{card['id']} {key} must have one cell for every displayed model.")
            shared = text_block(section["shared"], size=9, leading=13, color=MUTED) if section.get("shared") else None
            evidence = (text_block(link_blocks(section["links"]), size=8.8, leading=13, markup=True)
                        if section.get("links") else None)
            box = section_box(heading, width, shared=shared,
                              model_blocks=[model_cell(cell) for cell in cells], evidence=evidence)
        content.extend([Spacer(1, 7), box])
    if count > 1 and not card.get("summary"):
        raise ValueError(f"{card['id']} needs a multi-model summary.")
    if card.get("summary"):
        label = "5  交叉检验总结" if count > 1 else "本条总评"
        content.extend([Spacer(1, 7), section_box(label, width, shared=text_block(card["summary"]))])
    return content


def draw_report_page(canvas, layout, data):
    canvas.setFillColor(HexColor(WHITE))
    canvas.rect(0, 0, *A4, fill=1, stroke=0)
    left = layout.leftMargin + 6
    footer = text_block(f"{data['manuscript']}   ·   {data['date']}", size=8, leading=10, color=MUTED)
    footer.wrap(layout.width - 12, 15)
    footer.drawOn(canvas, left, 22)
    canvas.setFont("AuditLatin", 8)
    canvas.setFillColor(HexColor(MUTED))
    canvas.drawRightString(A4[0] - layout.rightMargin - 6, 25, f"{layout.page}")

def build_pdf(document, content, data):
    def draw_page(canvas, layout):
        draw_report_page(canvas, layout, data)

    document.build(content, onFirstPage=draw_page, onLaterPages=draw_page)


def render(data, output):
    models, cards = data["models"], data["references"]
    if not 1 <= len(models) <= 3 or not cards:
        raise ValueError("A report needs one to three model columns and at least one reference.")
    if any(card.get("source_type") == "orphan" for card in cards):
        raise ValueError("Bibliography reports require entries from the reference list.")
    document = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=43, rightMargin=43,
                                 topMargin=41, bottomMargin=40, title="稿件引文审查报告")
    width = document.width - 12
    height = document.height - 12
    entries = [(card, f"audit-reference-{index}") for index, card in enumerate(cards, 1)]
    content = issue_index(entries, models, width)
    content.append(PageBreak())
    content.extend(distribution_section(cards, width))
    for card, destination in entries:
        detail = [
            title_block(card, width, destination), Spacer(1, 8),
            *reference_sections(card, models, width),
        ]
        content.extend([PageBreak(), KeepInFrame(width, height, detail, mode="shrink")])

    build_pdf(document, content, data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--regular-font", type=Path, default=SONG_FONT)
    parser.add_argument("--bold-font", type=Path, default=SONG_FONT)
    args = parser.parse_args()
    register_fonts(args.regular_font, args.bold_font)
    render(json.loads(args.input.read_text(encoding="utf-8-sig")), args.output)


if __name__ == "__main__":
    main()
