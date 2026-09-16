#!/usr/bin/env python3
"""Build the EarthArXiv-ready CH-008 manuscript PDF from Markdown."""

from __future__ import annotations

import html
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
FIGURES = PAPER / "figures"
OUTPUT = ROOT / "output" / "pdf"
MANUSCRIPT = PAPER / "manuscript.md"
PDF = OUTPUT / "ch008-preprospective-manuscript-v0.1.pdf"

INK = "#15212b"
MUTED = "#586975"
TEAL = "#087f8c"
GREEN = "#2f855a"
GOLD = "#b7791f"
RED = "#b44545"
PALE = "#eef4f5"


def make_method_figure(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.8, 4.5))
    ax.set_xlim(0, 10.8)
    ax.set_ylim(0, 4.5)
    ax.axis("off")

    boxes = [
        (0.2, 2.55, 2.3, 1.2, "Frozen ETAS", "background + triggered", TEAL),
        (3.0, 3.0, 2.3, 0.95, "Renewal state", "magnitude-marked age", GOLD),
        (3.0, 1.55, 2.3, 0.95, "Frailty state", "observed / expected bg", GREEN),
        (5.85, 2.25, 2.15, 1.25, "Bounded tilt", "27.6% mixture cap", "#526d82"),
        (8.55, 2.25, 2.0, 1.25, "CH-008", "same total rate", RED),
    ]
    for x, y, w, h, title, subtitle, color in boxes:
        patch = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.025,rounding_size=0.07",
            linewidth=1.5, edgecolor=color, facecolor="white"
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
                fontsize=12, color=INK, weight="bold")
        ax.text(x + w / 2, y + h * 0.30, subtitle, ha="center", va="center",
                fontsize=9.5, color=MUTED)

    arrows = [
        ((2.5, 3.15), (3.0, 3.45)),
        ((2.5, 2.85), (3.0, 2.05)),
        ((5.3, 3.45), (5.85, 3.05)),
        ((5.3, 2.05), (5.85, 2.65)),
        ((8.0, 2.88), (8.55, 2.88)),
    ]
    for start, end in arrows:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=14,
                                     linewidth=1.3, color="#83939d"))
    ax.text(1.35, 1.45, "Triggered component passes through unchanged",
            ha="center", va="center", fontsize=9.5, color=MUTED)
    ax.add_patch(FancyArrowPatch((2.45, 1.45), (9.25, 2.22), connectionstyle="arc3,rad=-0.14",
                                 arrowstyle="-|>", mutation_scale=14, linewidth=1.3,
                                 color="#83939d"))
    ax.text(5.4, 0.48, "Causal daily update: only events before issue time enter state",
            ha="center", va="center", fontsize=10, color=INK, weight="bold")
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_evidence_figure(path: Path) -> None:
    labels = ["California\nvalidation", "California\nlater period", "New Zealand\nexploratory", "Chile\nexploratory"]
    means = [0.0052134832, 0.0078646125, 0.0185613228, 0.0097184294]
    lo30 = [0.0019816550, 0.0050927317, 0.0120060366, 0.0068622690]
    hi30 = [0.0088799911, 0.0106231594, 0.0296706779, 0.0132194540]
    lo90 = [0.0018444070, 0.0053693552, 0.0118173829, 0.0063210820]
    hi90 = [0.0092161379, 0.0109144248, 0.0313572766, 0.0143484400]
    n = [5204, 3995, 2270, 1909]
    x = range(len(labels))

    fig, ax = plt.subplots(figsize=(10.8, 5.0))
    ax.axhline(0, color="#6f7d85", linewidth=1)
    for i in x:
        ax.vlines(i, lo90[i], hi90[i], color="#9fb0ba", linewidth=2.5, zorder=1)
        ax.vlines(i, lo30[i], hi30[i], color=TEAL, linewidth=7, alpha=0.68, zorder=2)
        ax.scatter(i, means[i], s=70, color=INK, edgecolor="white", linewidth=1.2, zorder=3)
        ax.text(i, hi90[i] + 0.0015, f"N={n[i]:,}", ha="center", va="bottom", fontsize=9, color=MUTED)
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("Information gain per earthquake (nats)")
    ax.set_ylim(-0.0015, 0.0355)
    ax.grid(axis="y", color="#dbe3e7", linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title("Qualified pre-prospective evidence against frozen ETAS", loc="left",
                 fontsize=13, weight="bold", color=INK, pad=14)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_timeline_figure(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.8, 3.2))
    ax.set_xlim(0, 10.8)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    stages = [
        (0.15, 1.60, "Warm-up", "2007--2013\nunscored", "#9aaab3"),
        (1.95, 1.60, "Fit / selection", "2014--2018\nCalifornia", GOLD),
        (3.75, 1.60, "Validation", "2019--2022\nqualified", TEAL),
        (5.55, 1.60, "Later period", "2023--Aug 2026\nsupportive", GREEN),
        (7.35, 1.60, "Dry run", "1--14 Sep 2026\nnot claim", RED),
        (9.15, 1.60, "Prospective", "24 Sep 2026\n365 days", INK),
    ]
    for i, (x, width, label, sub, color) in enumerate(stages):
        ax.add_patch(FancyBboxPatch((x, 1.36), width, 0.62,
                                    boxstyle="round,pad=0.02,rounding_size=0.06",
                                    facecolor=color, edgecolor="none", alpha=0.92))
        ax.text(x + width / 2, 1.67, label, ha="center", va="center",
                fontsize=9.2, color="white", weight="bold")
        ax.text(x + width / 2, 1.12, sub, ha="center", va="top",
                fontsize=8.1, color=MUTED, linespacing=1.35)
        if i < len(stages) - 1:
            ax.add_patch(FancyArrowPatch((x + width + 0.04, 1.67),
                                         (stages[i + 1][0] - 0.04, 1.67),
                                         arrowstyle="-|>", mutation_scale=11,
                                         linewidth=1.0, color="#8797a0"))
    ax.text(0.15, 2.70, "Evidence chronology", fontsize=13, weight="bold", color=INK)
    ax.text(0.15, 2.35, "Only the final stage is eligible for the formal prospective claim.",
            fontsize=9.3, color=MUTED)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def inline_markup(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", escaped)
    escaped = re.sub(r"(https?://[^\s<]+)", r'<a href="\1" color="#087f8c">\1</a>', escaped)
    return escaped


def parse_markdown(text: str, styles: dict[str, ParagraphStyle]) -> list:
    lines = text.splitlines()
    story: list = []
    paragraph: list[str] = []
    bullets: list[str] = []
    numbered: list[str] = []
    seen_title = False
    front_matter = True

    def flush_paragraph() -> None:
        if paragraph:
            story.append(Paragraph(inline_markup(" ".join(x.strip() for x in paragraph)), styles["Body"]))
            story.append(Spacer(1, 2.5 * mm))
            paragraph.clear()

    def flush_lists() -> None:
        nonlocal bullets, numbered
        if bullets:
            items = [ListItem(Paragraph(inline_markup(x), styles["List"]), leftIndent=4 * mm) for x in bullets]
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=5 * mm, bulletFontSize=7))
            story.append(Spacer(1, 2 * mm))
            bullets = []
        if numbered:
            items = [ListItem(Paragraph(inline_markup(x), styles["List"]), leftIndent=4 * mm) for x in numbered]
            story.append(ListFlowable(items, bulletType="1", start="1", leftIndent=6 * mm))
            story.append(Spacer(1, 2 * mm))
            numbered = []

    for line in lines:
        stripped = line.strip()
        image_match = re.match(r"!\[(.+)]\((.+)\)", stripped)
        if not stripped:
            flush_paragraph()
            flush_lists()
            continue
        if image_match:
            flush_paragraph(); flush_lists()
            caption, rel = image_match.groups()
            img_path = PAPER / rel
            image = Image(str(img_path), width=166 * mm, height=70 * mm, kind="proportional")
            cap = Paragraph(inline_markup(caption), styles["Caption"])
            story.extend([Spacer(1, 2 * mm), KeepTogether([image, Spacer(1, 1.5 * mm), cap]), Spacer(1, 3 * mm)])
            continue
        if stripped.startswith("# "):
            flush_paragraph(); flush_lists()
            if not seen_title:
                story.append(Spacer(1, 11 * mm))
                story.append(Paragraph(inline_markup(stripped[2:]), styles["Title"]))
                story.append(Spacer(1, 7 * mm))
                seen_title = True
            continue
        if stripped.startswith("## "):
            flush_paragraph(); flush_lists()
            front_matter = False
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph(inline_markup(stripped[3:]), styles["H1"]))
            story.append(Spacer(1, 1.5 * mm))
            continue
        if stripped.startswith("### "):
            flush_paragraph(); flush_lists()
            story.append(Paragraph(inline_markup(stripped[4:]), styles["H2"]))
            continue
        if stripped.startswith("- "):
            flush_paragraph(); flush_lists() if numbered else None
            bullets.append(stripped[2:])
            continue
        match_num = re.match(r"\d+\.\s+(.+)", stripped)
        if match_num:
            flush_paragraph(); flush_lists() if bullets else None
            numbered.append(match_num.group(1))
            continue
        if stripped.startswith("**") and stripped.endswith("**") and len(stripped) < 100:
            flush_paragraph(); flush_lists()
            story.append(Paragraph(inline_markup(stripped), styles["Meta"]))
            continue
        if front_matter and seen_title:
            flush_paragraph(); flush_lists()
            story.append(Paragraph(inline_markup(stripped.rstrip("  ")), styles["Meta"]))
            continue
        paragraph.append(stripped)
    flush_paragraph(); flush_lists()
    return story


class ManuscriptDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=22 * mm,
            rightMargin=22 * mm,
            topMargin=19 * mm,
            bottomMargin=19 * mm,
            title="CH-008: Causal Renewal-Frailty Reallocation of ETAS Background Seismicity",
            author="Saban Baris Boga",
            subject="Earthquake forecasting methods and pre-prospective evidence",
        )
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        self.addPageTemplates(PageTemplate(id="main", frames=[frame], onPage=self._decorate))

    @staticmethod
    def _decorate(canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d5dfe3"))
        canvas.setLineWidth(0.5)
        canvas.line(22 * mm, 14 * mm, 188 * mm, 14 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(22 * mm, 9 * mm, "CH-008 pre-prospective manuscript v0.1")
        canvas.drawRightString(188 * mm, 9 * mm, f"{doc.page}")
        canvas.restoreState()


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle("Title", parent=base["Title"], fontName="Helvetica-Bold",
                                fontSize=22, leading=26, textColor=colors.HexColor(INK),
                                alignment=TA_LEFT, spaceAfter=4 * mm),
        "CoverTitle": ParagraphStyle("CoverTitle", parent=base["Title"], fontName="Helvetica-Bold",
                                     fontSize=24, leading=29, textColor=colors.HexColor(INK),
                                     alignment=TA_LEFT, spaceAfter=8 * mm),
        "CoverKicker": ParagraphStyle("CoverKicker", parent=base["BodyText"], fontName="Helvetica-Bold",
                                      fontSize=10, leading=13, textColor=colors.HexColor(TEAL),
                                      alignment=TA_LEFT, spaceAfter=3 * mm),
        "CoverStatement": ParagraphStyle("CoverStatement", parent=base["BodyText"], fontName="Helvetica",
                                         fontSize=11, leading=15, textColor=colors.HexColor(INK),
                                         backColor=colors.HexColor(PALE), borderColor=colors.HexColor("#cbd9de"),
                                         borderWidth=0.7, borderPadding=10, spaceBefore=5 * mm,
                                         spaceAfter=7 * mm),
        "Meta": ParagraphStyle("Meta", parent=base["BodyText"], fontName="Helvetica",
                               fontSize=9.3, leading=12.5, textColor=colors.HexColor(MUTED),
                               alignment=TA_LEFT, spaceAfter=1.2 * mm),
        "H1": ParagraphStyle("H1", parent=base["Heading1"], fontName="Helvetica-Bold",
                             fontSize=14.2, leading=17, textColor=colors.HexColor(INK),
                             spaceBefore=5 * mm, spaceAfter=2 * mm, keepWithNext=True),
        "H2": ParagraphStyle("H2", parent=base["Heading2"], fontName="Helvetica-Bold",
                             fontSize=11.2, leading=14, textColor=colors.HexColor(TEAL),
                             spaceBefore=3.5 * mm, spaceAfter=1.2 * mm, keepWithNext=True),
        "Body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica",
                               fontSize=9.35, leading=13.1, textColor=colors.HexColor(INK),
                               alignment=TA_JUSTIFY, allowWidows=0, allowOrphans=0),
        "List": ParagraphStyle("List", parent=base["BodyText"], fontName="Helvetica",
                               fontSize=9.2, leading=12.6, textColor=colors.HexColor(INK),
                               alignment=TA_LEFT),
        "Caption": ParagraphStyle("Caption", parent=base["BodyText"], fontName="Helvetica-Oblique",
                                  fontSize=8.2, leading=10.5, textColor=colors.HexColor(MUTED),
                                  alignment=TA_LEFT, keepWithNext=False),
    }


def cover_sheet(s: dict[str, ParagraphStyle]) -> list:
    return [
        Spacer(1, 18 * mm),
        Paragraph("EARTHARXIV SUBMISSION COVERSHEET", s["CoverKicker"]),
        Paragraph(
            "CH-008: Causal Renewal-Frailty Reallocation of ETAS Background Seismicity "
            "Across California, New Zealand, and Chile",
            s["CoverTitle"],
        ),
        Paragraph(
            "This manuscript is a <b>non-peer-reviewed preprint submitted to EarthArXiv</b>. "
            "It may be revised. It has not been submitted to a peer-reviewed journal as of "
            "16 September 2026.",
            s["CoverStatement"],
        ),
        Paragraph("<b>Author</b>: Saban Baris Boga (sole author)", s["Meta"]),
        Paragraph("<b>Affiliation</b>: Independent Researcher, Adana, Turkiye", s["Meta"]),
        Paragraph(
            '<b>ORCID</b>: <a href="https://orcid.org/0009-0000-9076-946X" '
            'color="#087f8c">https://orcid.org/0009-0000-9076-946X</a>',
            s["Meta"],
        ),
        Paragraph("<b>Correspondence</b>: hello@bboga.com", s["Meta"]),
        Spacer(1, 6 * mm),
        Paragraph("<b>Version</b>: 0.1, 16 September 2026", s["Meta"]),
        Paragraph("<b>Submission type</b>: Research article / methods and pre-prospective evidence", s["Meta"]),
        Paragraph("<b>License</b>: Creative Commons Attribution 4.0 International (CC BY 4.0)", s["Meta"]),
        Paragraph(
            "<b>Keywords</b>: earthquake forecasting; ETAS; renewal process; frailty; "
            "information gain; prospective evaluation; CSEP",
            s["Meta"],
        ),
        Spacer(1, 8 * mm),
        Paragraph(
            "The formal 365-day prospective evaluation described in this manuscript is scheduled "
            "to begin with the target day of 24 September 2026. Pre-activation evidence is labeled "
            "according to its actual retrospective or operational status.",
            s["Body"],
        ),
        PageBreak(),
    ]


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    make_method_figure(FIGURES / "ch008-method.png")
    make_evidence_figure(FIGURES / "preprospective-evidence.png")
    make_timeline_figure(FIGURES / "evidence-timeline.png")
    style_map = styles()
    story = cover_sheet(style_map) + parse_markdown(MANUSCRIPT.read_text(encoding="utf-8"), style_map)
    ManuscriptDocTemplate(str(PDF)).build(story)
    print(PDF)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
