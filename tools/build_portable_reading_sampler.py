"""Build the project-original portable reading-room magazine.

The output contains only project-original text and vector decoration.  It
does not copy photographs, avatar references, or pages from the resident
private media library.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "Data"
    / "library"
    / "portable_selection"
    / "magazines"
    / "reading_room_issue_001.pdf"
)

PAGE_WIDTH, PAGE_HEIGHT = letter
INK = colors.HexColor("#14213D")
PAPER = colors.HexColor("#F6F1E7")
CORAL = colors.HexColor("#E76F51")
GOLD = colors.HexColor("#E9C46A")
TEAL = colors.HexColor("#2A9D8F")
MIST = colors.HexColor("#DDE9E7")
WHITE = colors.white


def _wrap(text: str, font: str, size: float, width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and stringWidth(candidate, font, size) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _paragraph(
    pdf: canvas.Canvas,
    text: str,
    *,
    x: float,
    y: float,
    width: float,
    font: str = "Helvetica",
    size: float = 10.5,
    leading: float = 15,
    color=INK,
) -> float:
    pdf.setFillColor(color)
    pdf.setFont(font, size)
    for line in _wrap(text, font, size, width):
        pdf.drawString(x, y, line)
        y -= leading
    return y


def _page_header(pdf: canvas.Canvas, section: str, page_number: int) -> None:
    pdf.setFillColor(PAPER)
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(42, PAGE_HEIGHT - 32, "READING ROOM / ISSUE 001")
    pdf.setFont("Helvetica", 8)
    pdf.drawRightString(PAGE_WIDTH - 42, PAGE_HEIGHT - 32, section.upper())
    pdf.setStrokeColor(GOLD)
    pdf.setLineWidth(1.5)
    pdf.line(42, PAGE_HEIGHT - 41, PAGE_WIDTH - 42, PAGE_HEIGHT - 41)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(PAGE_WIDTH / 2, 24, str(page_number))


def _title(pdf: canvas.Canvas, title: str, subtitle: str = "") -> float:
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 25)
    pdf.drawString(42, PAGE_HEIGHT - 84, title)
    y = PAGE_HEIGHT - 109
    if subtitle:
        y = _paragraph(
            pdf,
            subtitle,
            x=42,
            y=y,
            width=PAGE_WIDTH - 84,
            font="Helvetica",
            size=11,
            leading=16,
            color=colors.HexColor("#475569"),
        )
    return y - 10


def _card(
    pdf: canvas.Canvas,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    label: str,
    title: str,
    body: str,
    accent,
) -> None:
    pdf.setFillColor(WHITE)
    pdf.roundRect(x, y - height, width, height, 10, fill=1, stroke=0)
    pdf.setFillColor(accent)
    pdf.roundRect(x, y - height, 7, height, 3, fill=1, stroke=0)
    pdf.setFillColor(accent)
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawString(x + 18, y - 20, label.upper())
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x + 18, y - 40, title)
    _paragraph(
        pdf,
        body,
        x=x + 18,
        y=y - 58,
        width=width - 34,
        size=8.7,
        leading=12,
        color=colors.HexColor("#475569"),
    )


def _cover(pdf: canvas.Canvas) -> None:
    pdf.setFillColor(INK)
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    pdf.setFillColor(TEAL)
    pdf.circle(PAGE_WIDTH - 72, PAGE_HEIGHT - 90, 112, fill=1, stroke=0)
    pdf.setFillColor(GOLD)
    pdf.circle(PAGE_WIDTH - 34, PAGE_HEIGHT - 43, 48, fill=1, stroke=0)
    pdf.setFillColor(CORAL)
    pdf.roundRect(42, 104, 345, 18, 9, fill=1, stroke=0)
    pdf.setFillColor(WHITE)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(42, PAGE_HEIGHT - 68, "PORTABLE MEDIA SAMPLER")
    pdf.setFont("Helvetica-Bold", 44)
    pdf.drawString(42, PAGE_HEIGHT - 180, "READING")
    pdf.drawString(42, PAGE_HEIGHT - 230, "ROOM")
    pdf.setFont("Helvetica", 18)
    pdf.drawString(44, PAGE_HEIGHT - 270, "Issue 001 / Books, scenes, and quiet curiosity")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(55, 109, "PROJECT-ORIGINAL / NON-ADULT / NO REAL-PERSON PHOTOS")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(42, 55, "A small offline issue for slow reading and reviewable enjoyment.")


def _welcome(pdf: canvas.Canvas) -> None:
    _page_header(pdf, "Welcome", 2)
    y = _title(
        pdf,
        "A quiet shelf that travels",
        "This issue is a compact starting point for reading when a larger resident library is not available.",
    )
    y = _paragraph(
        pdf,
        "The portable collection keeps source material separate from lived memory. Reading a page can create a note, a question, a preference, or a future project idea. It does not mean anyone lived the events, finished the whole work, activated a new person, or gained a body or skill.",
        x=42,
        y=y,
        width=330,
        size=11,
        leading=17,
    )
    pdf.setFillColor(MIST)
    pdf.roundRect(398, PAGE_HEIGHT - 306, 152, 178, 14, fill=1, stroke=0)
    pdf.setFillColor(TEAL)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(416, PAGE_HEIGHT - 157, "USE IT SLOWLY")
    _paragraph(
        pdf,
        "Pick one item. Read a small unit. Pause. Save only a grounded reaction. Stop if interest fades.",
        x=416,
        y=PAGE_HEIGHT - 181,
        width=116,
        size=9.5,
        leading=14,
    )
    y -= 32
    pdf.setFillColor(CORAL)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(42, y, "Rights boundary")
    y -= 22
    _paragraph(
        pdf,
        "The magazine text and vector artwork are project-original. The selected shelf also contains older works already reviewed as U.S. public-domain or no-known-restrictions scans. Public-domain status may differ outside the United States. Private scripts and modern magazines are not part of this portable set.",
        x=42,
        y=y,
        width=508,
        size=10.3,
        leading=16,
    )


def _shelf(pdf: canvas.Canvas) -> None:
    _page_header(pdf, "Shelf picks", 3)
    _title(pdf, "Four starting points", "A deliberately small rotation: story, place, nature, and practical reflection.")
    _card(
        pdf,
        x=42,
        y=PAGE_HEIGHT - 145,
        width=244,
        height=178,
        label="Historical fiction",
        title="Samantha at Saratoga",
        body="A pre-1931 scan with travel, social observation, humor, and period fashion. Treat the narration as source text, not current social guidance.",
        accent=CORAL,
    )
    _card(
        pdf,
        x=306,
        y=PAGE_HEIGHT - 145,
        width=244,
        height=178,
        label="Chicago history",
        title="Chicago, 1917",
        body="A city-history source for slow contextual reading. Keep historical claims tied to the exact pages reviewed.",
        accent=TEAL,
    )
    _card(
        pdf,
        x=42,
        y=PAGE_HEIGHT - 349,
        width=244,
        height=178,
        label="Natural history",
        title="Forms of Animal Life",
        body="An older illustrated science volume useful for comparing historical description with modern knowledge. Flag dated terminology rather than repeating it as current fact.",
        accent=GOLD,
    )
    _card(
        pdf,
        x=306,
        y=PAGE_HEIGHT - 349,
        width=244,
        height=178,
        label="Life skills history",
        title="Life: How to Enjoy It",
        body="A historical self-improvement text. Read it as a record of its era, keeping personal advice optional and open to present-day review.",
        accent=INK,
    )


def _script_corner(pdf: canvas.Canvas) -> None:
    _page_header(pdf, "Script corner", 4)
    y = _title(pdf, "The Reading Room After Rain", "An original short scene included in full as a separate Markdown script.")
    pdf.setFillColor(WHITE)
    pdf.roundRect(42, 125, 508, y - 135, 12, fill=1, stroke=0)
    y -= 16
    for speaker, line in (
        ("READER ONE", "The rain stopped, but the windows are still telling the story."),
        ("READER TWO", "Then let the room stay quiet for one more page."),
        ("READER ONE", "Which shelf? History, nature, or the one marked 'surprise me'?"),
        ("READER TWO", "History first. Surprise needs a little trust."),
        ("READER ONE", "One chapter, then tea."),
        ("READER TWO", "One chapter, and permission to stop at half a chapter."),
    ):
        pdf.setFillColor(CORAL if speaker == "READER ONE" else TEAL)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(62, y, speaker)
        y -= 16
        y = _paragraph(pdf, line, x=62, y=y, width=462, size=10.5, leading=15)
        y -= 13
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(62, 145, "The lamp clicks on. Neither reader rushes the next choice.")


def _long_session(pdf: canvas.Canvas) -> None:
    _page_header(pdf, "Long-session route", 5)
    _title(pdf, "Enjoyment without instant ingestion", "A conservative route for a long supervised or user-away reading period.")
    steps = [
        ("01", "Choose", "Select one indexed item for a stated reason: comfort, curiosity, study, or shared discussion."),
        ("02", "Read", "Advance only a small page, scene, section, or chapter unit. Never claim the whole work was consumed instantly."),
        ("03", "Pause", "Leave time between units. A pause can include rest, a question, or switching to another ordinary activity."),
        ("04", "Reflect", "Save a bounded reaction separately from memory: what stood out, what was confusing, and whether interest continued."),
        ("05", "Stop honestly", "Completion is optional. Boredom, discomfort, resource pressure, or a new conversation are valid reasons to stop."),
    ]
    y = PAGE_HEIGHT - 154
    for number, label, body in steps:
        pdf.setFillColor(TEAL if int(number) % 2 else CORAL)
        pdf.circle(66, y - 5, 20, fill=1, stroke=0)
        pdf.setFillColor(WHITE)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawCentredString(66, y - 8, number)
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(101, y + 1, label)
        _paragraph(pdf, body, x=101, y=y - 18, width=440, size=9.6, leading=13)
        y -= 102


def _high_resource(pdf: canvas.Canvas) -> None:
    _page_header(pdf, "Experimental media lane", 6)
    y = _title(
        pdf,
        "For a stronger computer - later",
        "The optional launcher is disabled by default and has not been run on this machine because of local RAM and GPU restrictions.",
    )
    rows = [
        ("IMPLEMENTED", "Group text/voice routing, portable media search, PDF/image presentation, local speech-to-text sidecar, and an owner-requested single transient camera still."),
        ("HARDWARE-DEPENDENT", "The number of active sessions, local model responsiveness, voice synthesis, speech recognition, media decoding, and one-still vision depend on installed RAM, GPU/VRAM, drivers, and local models."),
        ("NOT CONNECTED", "Continuous semantic video understanding, identity recognition, automatic body capability, and simultaneous animated 3D group bodies are not enabled by this launcher."),
    ]
    colors_by_status = {"IMPLEMENTED": TEAL, "HARDWARE-DEPENDENT": GOLD, "NOT CONNECTED": CORAL}
    for status, body in rows:
        pdf.setFillColor(colors_by_status[status])
        pdf.roundRect(42, y - 10, 138, 24, 12, fill=1, stroke=0)
        pdf.setFillColor(INK if status == "HARDWARE-DEPENDENT" else WHITE)
        pdf.setFont("Helvetica-Bold", 7.5)
        pdf.drawCentredString(111, y - 2, status)
        y = _paragraph(pdf, body, x=198, y=y + 5, width=352, size=9.6, leading=14)
        y -= 34
    pdf.setFillColor(MIST)
    pdf.roundRect(42, 88, 508, 112, 12, fill=1, stroke=0)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(60, 174, "Hardware guidance is not proof")
    _paragraph(
        pdf,
        "The profile suggests 64 GB RAM for a cautious two-session experiment and 128 GB RAM for a requested four-session ceiling, with a discrete GPU and ample VRAM for richer local media work. The runtime still measures RAM and can reduce capacity. A successful launch does not prove that every optional capability works.",
        x=60,
        y=153,
        width=470,
        size=9.3,
        leading=14,
    )


def build(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(
        str(output),
        pagesize=letter,
        pageCompression=1,
        invariant=1,
    )
    pdf.setTitle("Reading Room - Issue 001")
    pdf.setAuthor("KiraWorld project")
    pdf.setSubject("Portable non-adult reading and media sampler")
    for page in (_cover, _welcome, _shelf, _script_corner, _long_session, _high_resource):
        page(pdf)
        pdf.showPage()
    pdf.save()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    build(output.resolve())
    print(output.resolve())


if __name__ == "__main__":
    main()
