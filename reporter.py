"""
reporter.py — Export comparison results to a clean plain-text report or PDF.
"""

from datetime import datetime
from typing import Optional
from comparator import ComparisonResult, Change


# ─── Shared Formatting Helpers ────────────────────────────────────────────────

CHANGE_ICONS = {
    "added":    "✚  ADDED",
    "removed":  "✖  REMOVED",
    "modified": "✎  MODIFIED",
    "moved":    "↕  MOVED",
}


def _header(title: str, width: int = 72) -> str:
    line = "═" * width
    return f"\n{line}\n  {title}\n{line}"


def _section(label: str, width: int = 72) -> str:
    return f"\n{'─' * width}\n  {label}\n{'─' * width}"


def _format_change_text(change: Change) -> str:
    lines = []
    icon = CHANGE_ICONS.get(change.change_type, "?")

    # Position info
    pos_parts = []
    if change.old_line_num:
        pos_parts.append(f"Line {change.old_line_num}")
    if change.new_line_num and change.new_line_num != change.old_line_num:
        pos_parts.append(f"→ Line {change.new_line_num}")
    if change.old_para_num:
        pos_parts.append(f"(¶{change.old_para_num})")
    pos_str = "  " + "  ".join(pos_parts) if pos_parts else ""

    lines.append(f"  {icon}{pos_str}")

    if change.material_tags:
        lines.append(f"  ⚡ Material: {', '.join(change.material_tags)}")

    if change.change_type == "added":
        lines.append(f'  ▶  "{change.new_text}"')

    elif change.change_type == "removed":
        lines.append(f'  ◀  "{change.old_text}"')

    elif change.change_type == "modified":
        lines.append(f'  OLD: "{change.old_text}"')
        lines.append(f'  NEW: "{change.new_text}"')
        sim_pct = int(change.similarity * 100)
        lines.append(f"  ≈  {sim_pct}% similar")

    elif change.change_type == "moved":
        lines.append(f'  CONTENT: "{change.old_text or change.new_text}"')
        lines.append(f"  FROM ¶{change.old_para_num}  →  TO ¶{change.new_para_num}")

    return "\n".join(lines)


# ─── Plain-Text Report ────────────────────────────────────────────────────────

def build_text_report(
    result: ComparisonResult,
    old_filename: str,
    new_filename: str,
) -> str:
    s = result.stats
    lines = []

    # ── Header ──
    lines.append(_header("📄  DOCUMENT COMPARISON REPORT"))
    lines.append(f"\n  Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Old File  : {old_filename}")
    lines.append(f"  New File  : {new_filename}")

    # ── Executive Summary ──
    lines.append(_section("📊  EXECUTIVE SUMMARY"))
    lines.append(f"""
  Total Changes    : {s['total_changes']}
    ✚  Added       : {s['added']}
    ✖  Removed     : {s['removed']}
    ✎  Modified    : {s['modified']}
    ↕  Moved       : {s['moved']}

  ⚡ Material Changes : {s['material_changes']}   ← numbers, dates, legal terms

  Document Size
    Old: {s['old_lines']} lines / {s['old_paragraphs']} paragraphs
    New: {s['new_lines']} lines / {s['new_paragraphs']} paragraphs
    """)

    if s["total_changes"] == 0:
        lines.append("  ✅  No differences found. Documents are identical.")
        return "\n".join(lines)

    # ── Material Changes First ──
    material = [c for c in result.changes if c.is_material]
    if material:
        lines.append(_section(f"⚡  MATERIAL CHANGES  ({len(material)} flagged)"))
        for c in material:
            lines.append(_format_change_text(c))
            lines.append("")

    # ── All Changes by Group ──
    lines.append(_section("🔍  ALL CHANGES  (grouped by proximity)"))

    # Group changes
    groups: dict = {}
    for c in result.changes:
        gid = c.group_id or 0
        groups.setdefault(gid, []).append(c)

    for gid, group_changes in sorted(groups.items()):
        if len(group_changes) > 1:
            lines.append(f"\n  ┌─ Change Group #{gid + 1} ({len(group_changes)} related changes) ─")
        for c in group_changes:
            lines.append(_format_change_text(c))
            lines.append("")
        if len(group_changes) > 1:
            lines.append("  └─────────────────────────────────")

    lines.append(_header("END OF REPORT"))
    return "\n".join(lines)


# ─── PDF Report ───────────────────────────────────────────────────────────────

def build_pdf_report(
    result: ComparisonResult,
    old_filename: str,
    new_filename: str,
    output_path: str,
) -> str:
    """
    Generate a styled PDF report using reportlab.
    Falls back to saving a .txt file if reportlab is unavailable.
    """
    text_report = build_text_report(result, old_filename, new_filename)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer,
            HRFlowable, Table, TableStyle,
        )
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        story = []

        # Custom styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Title"],
            fontSize=18,
            textColor=colors.HexColor("#1a1a2e"),
            spaceAfter=6,
        )
        heading_style = ParagraphStyle(
            "SectionHead",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=colors.HexColor("#16213e"),
            spaceBefore=14,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=9,
            leading=14,
            spaceAfter=4,
        )
        code_old = ParagraphStyle(
            "CodeOld",
            parent=styles["Normal"],
            fontSize=9,
            backColor=colors.HexColor("#fdecea"),
            textColor=colors.HexColor("#7f0000"),
            fontName="Courier",
            leading=13,
            leftIndent=10,
            spaceAfter=2,
        )
        code_new = ParagraphStyle(
            "CodeNew",
            parent=styles["Normal"],
            fontSize=9,
            backColor=colors.HexColor("#e8f5e9"),
            textColor=colors.HexColor("#1b5e20"),
            fontName="Courier",
            leading=13,
            leftIndent=10,
            spaceAfter=2,
        )
        code_mod = ParagraphStyle(
            "CodeMod",
            parent=styles["Normal"],
            fontSize=9,
            backColor=colors.HexColor("#fff8e1"),
            textColor=colors.HexColor("#4e342e"),
            fontName="Courier",
            leading=13,
            leftIndent=10,
            spaceAfter=2,
        )

        def hr():
            return HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dddddd"))

        # Title
        story.append(Paragraph("📄 Document Comparison Report", title_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style))
        story.append(Paragraph(f"<b>Old:</b> {old_filename}  →  <b>New:</b> {new_filename}", body_style))
        story.append(Spacer(1, 0.3 * cm))
        story.append(hr())

        # Summary table
        s = result.stats
        story.append(Paragraph("Executive Summary", heading_style))
        summary_data = [
            ["Metric", "Count"],
            ["Total Changes", str(s["total_changes"])],
            ["✚ Added", str(s["added"])],
            ["✖ Removed", str(s["removed"])],
            ["✎ Modified", str(s["modified"])],
            ["↕ Moved", str(s["moved"])],
            ["⚡ Material Changes", str(s["material_changes"])],
        ]
        t = Table(summary_data, colWidths=[9 * cm, 4 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f9f9f9"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4 * cm))

        def _safe(text):
            """Escape special XML chars for reportlab."""
            return (text or "").\
                replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Material changes
        material = [c for c in result.changes if c.is_material]
        if material:
            story.append(hr())
            story.append(Paragraph(f"⚡ Material Changes ({len(material)})", heading_style))
            for c in material:
                _add_change_to_pdf(story, c, body_style, code_old, code_new, code_mod, _safe)
            story.append(Spacer(1, 0.3 * cm))

        # All changes
        story.append(hr())
        story.append(Paragraph("🔍 All Changes", heading_style))
        groups: dict = {}
        for c in result.changes:
            groups.setdefault(c.group_id or 0, []).append(c)

        for gid, group_changes in sorted(groups.items()):
            for c in group_changes:
                _add_change_to_pdf(story, c, body_style, code_old, code_new, code_mod, _safe)

        doc.build(story)
        return output_path

    except ImportError:
        # Fallback: write text report
        txt_path = output_path.replace(".pdf", ".txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text_report)
        return txt_path


def _add_change_to_pdf(story, change: Change, body_style, code_old, code_new, code_mod, _safe):
    from reportlab.platypus import Paragraph, Spacer
    from reportlab.lib.units import cm

    icon = CHANGE_ICONS.get(change.change_type, "?")
    pos_parts = []
    if change.old_line_num:
        pos_parts.append(f"Line {change.old_line_num}")
    if change.old_para_num:
        pos_parts.append(f"¶{change.old_para_num}")
    pos_str = "  " + " / ".join(pos_parts) if pos_parts else ""

    mat_str = f"  ⚡ {', '.join(change.material_tags)}" if change.material_tags else ""
    story.append(Paragraph(f"<b>{icon}</b>{pos_str}{mat_str}", body_style))

    if change.change_type == "added":
        story.append(Paragraph(_safe(change.new_text or ""), code_new))
    elif change.change_type == "removed":
        story.append(Paragraph(_safe(change.old_text or ""), code_old))
    elif change.change_type == "modified":
        story.append(Paragraph(f"OLD: {_safe(change.old_text or '')}", code_old))
        story.append(Paragraph(f"NEW: {_safe(change.new_text or '')}", code_new))
    elif change.change_type == "moved":
        story.append(Paragraph(
            f"Moved ¶{change.old_para_num} → ¶{change.new_para_num}: {_safe(change.old_text or '')}",
            code_mod,
        ))

    story.append(Spacer(1, 0.15 * cm))
