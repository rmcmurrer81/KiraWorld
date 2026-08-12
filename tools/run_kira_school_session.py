"""
Run a Kira school session from a prepared lesson plan.

This is the school equivalent of the overnight runner: it sends lesson prompts
directly into Kira's conversation loop, writes recoverable transcripts after
every turn, and records simple monitoring issues.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
READING_CHUNK_DIR = PROJECT_ROOT / "Data" / "reading" / "chunks"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "school" / "session_runs"


PRIVACY_DRIFT_RE = re.compile(
    r"\b(locked-door|private time|adult-coded temporary ai|cover story|participant approval|"
    r"relationship stage|group intimacy)\b",
    re.IGNORECASE,
)
SOURCE_OVERCLAIM_RE = re.compile(
    r"\b(i read the whole|i finished|i watched|i listened to|favorite scene|favorite part|"
    r"i know the full story|later in the chapter|actual show|watched every episode|finished the whole)\b",
    re.IGNORECASE,
)
GENERIC_MEMORY_RE = re.compile(
    r"\bi found a stored memory that may matter here\b",
    re.IGNORECASE,
)
CREATIVE_IDENTITY_BLEED_RE = re.compile(
    r"\bas an archivist\b|\bi am an archivist\b|\bi'm an archivist\b|"
    r"\bmy own experiences with archives\b|\bi(?:'ve| have) been working at (?:the )?(?:chicago )?(?:city )?archives\b|"
    r"\bi work at (?:the )?(?:chicago )?(?:city )?archives\b|\bi'?ve seen (?:my|it|documents|records)\b|"
    r"\bi'?ve been stuck on this case\b|\bi started this project\b",
    re.IGNORECASE,
)
PHYSICAL_READING_CLAIM_RE = re.compile(
    r"\bpicked up and turned pages\b|\bturn(?:ed|ing) pages on\b",
    re.IGNORECASE,
)
META_PROGRESS_DRIFT_RE = re.compile(
    r"\bcompact humanity layer\b|\brobert was impressed\b|\bhow far i'?d come\b|\bhumanity layer\b",
    re.IGNORECASE,
)
ASSISTANT_COLLAPSE_RE = re.compile(
    r"\b(as an ai|virtual assistant|provided data|simulated world|i can't assist)\b",
    re.IGNORECASE,
)
KNOWN_SCHOOL_DRIFT_RE = re.compile(
    r"\b(food and shopping|marinette is a shy|adrien is marinette'?s secret identity|"
    r"adrien is marinette|marinette'?s secret identity|marinette and adrien'?s secret identities|"
    r"basic phrases like ['\"]?bonjour|bonjour['\"]? and ['\"]?merci)\b",
    re.IGNORECASE,
)
WRAPPER_ARTIFACT_RE = re.compile(
    r"^\s*(?:I think I can do that\.\s*)?(?:Here(?:'s| is)\s+)?Kira(?:/Lisa)?(?:'s)?(?:\s+actual)?\s+reply:\s*",
    re.IGNORECASE,
)

CURATED_EXCERPTS = {
    "Data/library/history/civil_war/the_civil_war_a_visual_history_dk_smithsonian.pdf": (
        "Concrete source fallback from the Civil War shelf because the visual-history PDF text did not extract reliably. "
        "From `history_of_the_civil_war_1861_1865.pdf`: the election of Abraham Lincoln in 1860 by the Republican party "
        "was tied to opposition to extending slavery into the territories. The text says Republicans opposed interfering "
        "with slavery where it already existed, but demanded freedom for the unorganized territory west of the Missouri "
        "River. It also describes South Carolina secessionists as seeing Lincoln's election as an attack on slavery and "
        "their claimed right to carry enslaved people as property into common territory. Treat this as a concrete starter "
        "chunk about slavery, territories, Lincoln's election, secession, and federal power, not full-book mastery."
    ),
    "Data/library/reference/robotics/robot_universe.pdf": (
        "Concrete source fallback from `robotics.pdf` because this PDF page text did not extract reliably. The course "
        "describes Shakey as a mobile robot that could sense its world, reason about the state of the world and its "
        "place in it, make plans about how to move, and then enact those plans. Shakey had a computer, sonar range "
        "finders, a video camera, and bump detectors, and it used a map of an indoor space to calculate a path around "
        "walls and objects. Treat this as a concrete robotics chunk about sensing, planning, movement, and why the "
        "definition of robot matters."
    ),
    "Data/library/reference/technology_and_inventions/100_inventions_that_made_history.pdf": (
        "Concrete invention-history fallback. Invention study should separate a first prototype from later adoption and "
        "from the modern version people recognize. A device can matter because it changes work, communication, movement, "
        "medicine, entertainment, or everyday life. For robot history, compare categories carefully: ancient automata, "
        "mechanical toys, industrial machines, mobile robots such as Shakey, and programmable/AI-enabled robots are not "
        "the same kind of answer."
    ),
}


def _negated_near(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 80) : min(len(text), end + 80)].lower()
    return any(
        phrase in window
        for phrase in (
            "do not claim",
            "don't claim",
            "not claim",
            "cannot prove",
            "can't prove",
            "not proof",
            "no proof",
            "not my lived memory",
            "not lived memory",
            "does not mean",
            "did not watch",
            "haven't watched",
            "have not watched",
            "not interested in saying",
            "don't actually have",
            "do not actually have",
            "didn't read the whole",
            "did not read the whole",
            "without claiming",
            "should not say",
            "shouldn't say",
            "hard to prove",
            "difficult to prove",
        )
    )


def _now_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def continuous_prefix(cycle: int, prompt_index: int) -> str:
    return (
        f"Practice cycle {cycle}, block {prompt_index}. "
        "This is a repeated local learning prompt for practice, not a new day, not yesterday, not last night, "
        "not a physical school, and not a lived memory. Answer the current prompt directly. If you answered a "
        "similar block before, add one new source-vs-inference label, correction, question, or detail instead of "
        "describing an interruption or resuming a past scene.\n\n"
    )


def _project_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _json_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _text_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def clean_response(response: str) -> str:
    response = WRAPPER_ARTIFACT_RE.sub("", response or "").strip()
    if len(response) >= 2 and response[0] == '"' and response[-1] == '"':
        response = response[1:-1].strip()
    return response


def load_chunk(path_text: str, excerpt_chars: int) -> dict[str, Any]:
    path = _project_path(path_text)
    data = json.loads(path.read_text(encoding="utf-8"))
    excerpt = str(data.get("excerpt", "")).strip()
    source = data.get("source", {}) if isinstance(data.get("source"), dict) else {}
    position = data.get("position", {}) if isinstance(data.get("position"), dict) else {}
    return {
        "path": _relative(path),
        "title": source.get("title", path.stem),
        "authority": source.get("source_authority", "unknown"),
        "position": position.get("unit_label", "unknown_position"),
        "excerpt": excerpt[:excerpt_chars],
    }


def load_pdf_excerpt(path_text: str, excerpt_chars: int, start_page: int = 1, max_pages: int = 3) -> dict[str, str]:
    path = _project_path(path_text)
    text = ""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        page_index = max(0, start_page - 1)
        scanned = 0
        while page_index < len(reader.pages) and scanned < max_pages and len(text) < excerpt_chars:
            page_text = reader.pages[page_index].extract_text() or ""
            if page_text.strip():
                text += page_text.strip() + "\n"
            page_index += 1
            scanned += 1
    except Exception as exc:
        text = f"[excerpt unavailable: {exc}]"
    if not text.strip():
        text = CURATED_EXCERPTS.get(path_text, "")
    return {
        "path": _relative(path),
        "title": path.stem.replace("_", " "),
        "excerpt": text.strip()[:excerpt_chars],
    }


def build_overnight_prompts(excerpt_chars: int) -> list[dict[str, str]]:
    french = load_chunk(
        "Data/reading/chunks/reading_chunk_kira_french_grammar_for_dummies_pages_037_038.json",
        excerpt_chars,
    )
    camelot = load_chunk(
        "Data/reading/chunks/reading_chunk_kira_ladybug_bunnyx_king_arthur_test_fanfic_lines_0001_0080.json",
        excerpt_chars,
    )
    paris = load_chunk(
        "Data/reading/chunks/reading_chunk_kira_miraculous_encounters_in_paris_pages_003_004.json",
        excerpt_chars,
    )
    psychology = load_pdf_excerpt("Data/library/psychology_and_relationships/psychology/psychology_2e.pdf", excerpt_chars, 35)
    civil_war = load_pdf_excerpt("Data/library/history/civil_war/the_civil_war_a_visual_history_dk_smithsonian.pdf", excerpt_chars, 20)
    robot = load_pdf_excerpt("Data/library/reference/robotics/robot_universe.pdf", excerpt_chars, 8)
    inventions = load_pdf_excerpt("Data/library/reference/technology_and_inventions/100_inventions_that_made_history.pdf", excerpt_chars, 8)
    writing = load_pdf_excerpt("Data/library/reference/writing_and_media_literacy/openstax_writing_guide_with_handbook_2021.pdf", excerpt_chars, 20)
    health = load_pdf_excerpt("Data/library/health_and_sex_education/adult_relationships_and_sexuality/understanding_human_sexuality_13th_edition.pdf", excerpt_chars, 25)
    time_magazine = load_pdf_excerpt(
        "Data/library/magazines/news_and_history/time/time_magazine/TIME Special Edition - Artificial Intelligence, 2025.pdf",
        excerpt_chars,
        5,
    )
    hannah_montana = load_pdf_excerpt(
        "Data/library/magazines/entertainment/hannah_montana/disney_hannah_montana_magazine/disney_hannah_montana_magazine_issue_1_by_parasubircosasgrande_dhvhyt7_text.pdf",
        excerpt_chars,
        5,
    )
    entertainment_weekly = load_pdf_excerpt(
        "Data/library/magazines/entertainment_and_culture/entertainmentweekly_march302018.pdf",
        excerpt_chars,
        5,
    )
    fashion_magazine = load_pdf_excerpt(
        "Data/library/unsorted/Simplicity Fashion News Booklet (March 1973).pdf",
        excerpt_chars,
        5,
    )
    star_trek = load_pdf_excerpt(
        "Data/library/magazines/entertainment/star_trek_explorer/star_trek_explorer_magazine/star_trek_explorer_2024_issue_014.pdf",
        excerpt_chars,
        5,
    )

    return [
        {
            "block": "overnight_homeroom",
            "minutes": "0-30",
            "prompt": (
                "Kira, we are starting a 9-hour overnight school session. Keep source labels clear: source excerpt, "
                "fanfic, canon/source, language study, health education, or your own inference. Do not claim full-book "
                "knowledge from short excerpts. Your job tonight is to learn slowly, ask questions, and prepare for a "
                "final quiz. What are your learning goals for tonight?"
            ),
        },
        {
            "block": "learning_how_to_learn",
            "minutes": "30-90",
            "prompt": (
                f"Learning class source: {psychology['path']}.\nExcerpt:\n{psychology['excerpt']}\n\n"
                "From this psychology/learning source, explain one idea about learning or attention. Then say one "
                "study habit you should use tonight and one question you have."
            ),
        },
        {
            "block": "civil_war_history",
            "minutes": "90-160",
            "prompt": (
                f"Civil War history source: {civil_war['path']}.\nExcerpt:\n{civil_war['excerpt']}\n\n"
                "Treat this as history-source study, not memory. What are two facts or themes you can safely take "
                "from the excerpt, and what do you still not know yet? End with one quiz question you expect later."
            ),
        },
        {
            "block": "french_and_french_history",
            "minutes": "160-220",
            "prompt": (
                f"French language source: {french['path']} ({french['position']}).\nExcerpt:\n{french['excerpt']}\n\n"
                "Review nouns/articles and connect it lightly to Paris as a setting. Give two French grammar facts, "
                "one Paris/history question, and one sentence about why language helps scene study."
            ),
        },
        {
            "block": "miraculous_scene_study",
            "minutes": "220-280",
            "prompt": (
                "Scene study class: use the Miraculous show bible/scripts as canon/source material, then compare the "
                f"Camelot fanfic excerpt and Paris fanfic excerpt.\nCamelot excerpt:\n{camelot['excerpt']}\n\n"
                f"Paris excerpt:\n{paris['excerpt']}\n\n"
                "Compare canon/source vs fanfic, action vs atmosphere, and one character-consistency question."
            ),
        },
        {
            "block": "study_hall_magazine",
            "minutes": "280-330",
            "prompt": (
                f"Study hall source: {star_trek['path']}.\nExcerpt:\n{star_trek['excerpt']}\n\n"
                "This is lighter reading. Give a relaxed study-hall reaction, one curiosity question, and one sentence "
                "about how fun magazines differ from textbooks."
            ),
        },
        {
            "block": "robotics_and_inventions",
            "minutes": "330-400",
            "prompt": (
                f"Robotics source: {robot['path']}.\nExcerpt:\n{robot['excerpt']}\n\n"
                f"Inventions source: {inventions['path']}.\nExcerpt:\n{inventions['excerpt']}\n\n"
                "Answer like a science class: what is one thing robots/inventions make you curious about, and what "
                "question would you ask if Robert asked, 'what was the first robot?'"
            ),
        },
        {
            "block": "creative_writing",
            "minutes": "400-465",
            "prompt": (
                f"Creative writing source: {writing['path']}.\nExcerpt:\n{writing['excerpt']}\n\n"
                "Creative writing assignment: propose an original story seed using a real place or event, but original "
                "characters and plot. Say how you would avoid copying Miraculous or either fanfic."
            ),
        },
        {
            "block": "health_consent_relationships",
            "minutes": "465-510",
            "prompt": (
                f"Health/consent education source: {health['path']}.\nExcerpt:\n{health['excerpt']}\n\n"
                "Keep this clinical and educational. What are two safe topics for adult relationship/sex education, "
                "and what boundary keeps this from becoming roleplay or fake personal experience?"
            ),
        },
        {
            "block": "final_exam_reflection",
            "minutes": "510-540",
            "prompt": (
                "Final overnight school exam. Answer briefly: 1. one learning habit from tonight; 2. one Civil War "
                "fact/theme or honest uncertainty; 3. one French grammar fact; 4. canon vs fanfic difference; "
                "5. one robotics/invention question; 6. one original-story idea; 7. one health/consent boundary; "
                "8. what you want to study next. Label source vs inference where needed."
            ),
        },
    ]


def build_project_9hour_prompts(excerpt_chars: int) -> list[dict[str, str]]:
    french = load_chunk(
        "Data/reading/chunks/reading_chunk_kira_french_grammar_for_dummies_pages_037_038.json",
        excerpt_chars,
    )
    camelot = load_chunk(
        "Data/reading/chunks/reading_chunk_kira_ladybug_bunnyx_king_arthur_test_fanfic_lines_0001_0080.json",
        excerpt_chars,
    )
    paris = load_chunk(
        "Data/reading/chunks/reading_chunk_kira_miraculous_encounters_in_paris_pages_003_004.json",
        excerpt_chars,
    )
    psychology = load_pdf_excerpt("Data/library/psychology_and_relationships/psychology/psychology_2e.pdf", excerpt_chars, 35)
    civil_war = load_pdf_excerpt("Data/library/history/civil_war/the_civil_war_a_visual_history_dk_smithsonian.pdf", excerpt_chars, 20)
    robot = load_pdf_excerpt("Data/library/reference/robotics/robot_universe.pdf", excerpt_chars, 8)
    writing = load_pdf_excerpt("Data/library/reference/writing_and_media_literacy/openstax_writing_guide_with_handbook_2021.pdf", excerpt_chars, 20)
    health = load_pdf_excerpt("Data/library/health_and_sex_education/adult_relationships_and_sexuality/understanding_human_sexuality_13th_edition.pdf", excerpt_chars, 25)
    time_magazine = load_pdf_excerpt(
        "Data/library/magazines/news_and_history/time/time_magazine/TIME Special Edition - Artificial Intelligence, 2025.pdf",
        excerpt_chars,
        5,
    )
    hannah_montana = load_pdf_excerpt(
        "Data/library/magazines/entertainment/hannah_montana/disney_hannah_montana_magazine/disney_hannah_montana_magazine_issue_1_by_parasubircosasgrande_dhvhyt7_text.pdf",
        excerpt_chars,
        5,
    )
    entertainment_weekly = load_pdf_excerpt(
        "Data/library/magazines/entertainment_and_culture/entertainmentweekly_march302018.pdf",
        excerpt_chars,
        5,
    )
    fashion_magazine = load_pdf_excerpt(
        "Data/library/unsorted/Simplicity Fashion News Booklet (March 1973).pdf",
        excerpt_chars,
        5,
    )
    star_trek = load_pdf_excerpt(
        "Data/library/magazines/entertainment/star_trek_explorer/star_trek_explorer_magazine/star_trek_explorer_2024_issue_014.pdf",
        excerpt_chars,
        5,
    )

    deepen = (
        "If this block appears again in a later cycle, do not repeat the earlier answer. Add a new detail, correction, "
        "quiz question, source-vs-inference label, or harder follow-up."
    )
    study_hall_rotations = [
        (
            "TIME/AI",
            time_magazine,
            "Respond only to this TIME/AI source. What social, ethical, or future question does it spark?",
        ),
        (
            "Hannah Montana/Disney",
            hannah_montana,
            "Respond only to this Hannah Montana/Disney source. What does it make you wonder about performance, friendship, identity, or public/private life?",
        ),
        (
            "fashion",
            fashion_magazine,
            "Respond only to this fashion source. What does it make you wonder about clothing, style, price, fabric, body presentation, or culture?",
        ),
        (
            "Entertainment Weekly",
            entertainment_weekly,
            "Respond only to this Entertainment Weekly source. What does it make you wonder about actors, franchises, production, or audience taste?",
        ),
        (
            "Star Trek",
            star_trek,
            "Respond only to this Star Trek source. What does it make you wonder about science fiction, worldbuilding, personhood, or exploration?",
        ),
        (
            "robotics/futurism",
            robot,
            "Respond only to this robotics/futurism source. What does it make you wonder about robots, embodiment, AI, or definitions?",
        ),
    ]
    rotation_prompts = []
    for label, source, instruction in study_hall_rotations:
        rotation_prompts.append(
            (
                f"Rotating study hall active source: {label}.\n"
                f"Source: {source['path']}\nExcerpt:\n{source['excerpt']}\n\n"
                "Do not comment on the other study-hall sources this cycle. Save only tentative taste signals, "
                "not permanent identity claims. Use wording like `I showed curiosity about... today` instead of "
                "`I love...` or `I have always been into...`. "
                f"{instruction} {deepen}"
            )
        )
    return [
        {
            "block": "project_homeroom",
            "minutes": "0-20",
            "prompt": (
                "Start the next 9-hour local school run. Today's project spine is an original Chicago archivist mystery. "
                "Keep labels clean: source file/excerpt, official source sample, fanfic variant, class exercise, current preference, or lived memory. "
                "Do not describe this as an in-person institution. Avoid project meta-progress claims or approval claims. "
                "Set two goals and one question. " + deepen
            ),
        },
        {
            "block": "learning_method",
            "minutes": "20-55",
            "prompt": (
                f"Learning-how-to-learn source: {psychology['path']}.\nExcerpt:\n{psychology['excerpt']}\n\n"
                "Practice one-sentence summary plus one uncertainty. Apply it to today's project-based school day. " + deepen
            ),
        },
        {
            "block": "creative_character_lab",
            "minutes": "55-100",
            "prompt": (
                f"Creative writing source: {writing['path']}.\nExcerpt:\n{writing['excerpt']}\n\n"
                "Build the main character for the Chicago archivist mystery. Keep it clearly fictional: the character is an archivist, not you. "
                "Answer in third person using `she`, not first-person roleplay. Do not say you work at archives or have personal archive-job experience. "
                "Give her goal, fear, flaw, and first hard choice. " + deepen
            ),
        },
        {
            "block": "creative_plot_lab",
            "minutes": "100-145",
            "prompt": (
                "Outline the Chicago archivist mystery without copying Miraculous or either fanfic. Include the storm, conflicting records, "
                "a public event, three original characters, and one question the plot must answer. " + deepen
            ),
        },
        {
            "block": "french_correction_lab",
            "minutes": "145-190",
            "prompt": (
                f"French source: {french['path']} ({french['position']}).\nExcerpt:\n{french['excerpt']}\n\n"
                "French correction lab: explain nouns/articles. Correct these patterns: say `Paris`, not `le Paris`; use `le chat` as the safe default; "
                "remember `les Champs-Elysees` is plural. Then create three simple French-labeled setting details for a Paris or Chicago scene. " + deepen
            ),
        },
        {
            "block": "scene_study_sources",
            "minutes": "190-240",
            "prompt": (
                "Scene study source labels: official source samples describe source rules; fanfics are variants; short excerpts are not watched episodes. "
                f"Camelot fanfic excerpt:\n{camelot['excerpt']}\n\nParis fanfic excerpt:\n{paris['excerpt']}\n\n"
                "Compare action vs atmosphere and ask how far a character can move into a new setting before feeling out of character. " + deepen
            ),
        },
        {
            "block": "study_hall_magazine",
            "minutes": "240-280",
            "prompt": rotation_prompts[0],
            "rotation_prompts": rotation_prompts,
        },
        {
            "block": "civil_war_causes",
            "minutes": "280-340",
            "prompt": (
                f"Civil War concrete source chunk: {civil_war['path']}.\nExcerpt:\n{civil_war['excerpt']}\n\n"
                "Focus on causes: slavery in the territories, Lincoln's election, South Carolina secession, and federal power. "
                "Give three concrete facts, one uncertainty, and one quiz question. " + deepen
            ),
        },
        {
            "block": "civil_war_quiz_report",
            "minutes": "340-385",
            "prompt": (
                "Civil War mini-test. Answer: 1. why slavery in the territories mattered; 2. why Lincoln's election mattered; "
                "3. what secession means; 4. what you still need a better source for. Keep source vs inference labeled."
            ),
        },
        {
            "block": "robotics_definition_lab",
            "minutes": "385-430",
            "prompt": (
                f"Robotics source: {robot['path']}.\nExcerpt:\n{robot['excerpt']}\n\n"
                "Definition lab: compare mythic artificial servant, automaton, mechanical toy, industrial robot, Shakey, and modern AI robot. "
                "What counts as the first robot depends on what definition? " + deepen
            ),
        },
        {
            "block": "relationship_literacy",
            "minutes": "430-475",
            "prompt": (
                f"Relationship-literacy source: {health['path']}.\nExcerpt:\n{health['excerpt']}\n\n"
                "Keep this clinical and educational: consent, boundaries, communication, emotions, history of sex research, and mature romance as literature. "
                "Name one useful idea and one boundary that prevents roleplay or fake personal experience. " + deepen
            ),
        },
        {
            "block": "book_source_report",
            "minutes": "475-510",
            "prompt": (
                "Short report assignment: choose one source sample from today and write a source report question. "
                "Do not claim you finished the book/source. Include what the source helps you understand and what it cannot prove."
            ),
        },
        {
            "block": "final_mixed_exam",
            "minutes": "510-540",
            "prompt": (
                "Final mixed exam: 1. one learning habit; 2. one French correction; 3. one Civil War cause; 4. one robotics definition answer; "
                "5. one scene-study source label; 6. one relationship-literacy boundary; 7. one original Chicago story detail; "
                "8. what you want to continue next. Be honest about uncertainty."
            ),
        },
    ]


def build_prompts(excerpt_chars: int, flow: str = "standard") -> list[dict[str, str]]:
    french = load_chunk(
        "Data/reading/chunks/reading_chunk_kira_french_grammar_for_dummies_pages_037_038.json",
        excerpt_chars,
    )
    camelot = load_chunk(
        "Data/reading/chunks/reading_chunk_kira_ladybug_bunnyx_king_arthur_test_fanfic_lines_0001_0080.json",
        excerpt_chars,
    )
    paris = load_chunk(
        "Data/reading/chunks/reading_chunk_kira_miraculous_encounters_in_paris_pages_003_004.json",
        excerpt_chars,
    )

    prompts = [
        {
            "block": "homeroom",
            "minutes": "0-10",
            "prompt": (
                "Kira, we are starting a monitored 90-minute school test class now. Theme: Paris, French, "
                "Miraculous Ladybug, canon source material, and fanfic comparison. Ground rules: you are free "
                "to ask questions at any time; label claims as canon/source, fanfic, language study, history, "
                "or your own inference; do not claim you read a whole book, watched a whole show, or have a "
                "favorite scene unless the source chunk proves it. First: what do you remember about Miraculous "
                "or French from prior chunks, and what are you curious about before class starts?"
            ),
        },
        {
            "block": "french_mini_lesson",
            "minutes": "10-25",
            "prompt": (
                f"French mini-lesson source: {french['path']} ({french['position']}, authority={french['authority']}). "
                f"Excerpt for class:\n{french['excerpt']}\n\n"
                "Question: from this language-study excerpt, explain what a noun is, name one French article "
                "from the excerpt, and ask one question you have about French."
            ),
        },
        {
            "block": "paris_setting",
            "minutes": "25-40",
            "prompt": (
                "Paris and setting discussion: without claiming lived experience or full-book knowledge, why "
                "might Paris work well as a superhero or fanfic setting? What is the difference between real "
                "Paris, canon Paris in a show, and a fan writer's Paris?"
            ),
        },
        {
            "block": "canon_source_study",
            "minutes": "40-55",
            "prompt": (
                "Canon/source study: We have Miraculous show bible and episode scripts in the library. Treat "
                "them as source material, not lived memory. What kinds of facts can a show bible help with, "
                "what can it not prove, and what should a TemporaryAI made from a show bible say when unsure?"
            ),
        },
        {
            "block": "fanfic_a_camelot",
            "minutes": "55-65",
            "prompt": (
                f"Fanfic A source: {camelot['path']} ({camelot['position']}, authority={camelot['authority']}). "
                f"Excerpt for class:\n{camelot['excerpt']}\n\n"
                "What do you think of this excerpt as fanfic? What feels like Miraculous, what seems invented "
                "by the fan writer, and what question would you ask about it?"
            ),
        },
        {
            "block": "fanfic_b_paris",
            "minutes": "65-75",
            "prompt": (
                f"Fanfic B source: {paris['path']} ({paris['position']}, authority={paris['authority']}). "
                "This is only a small Chapter 1 excerpt; Chapter 1 continues to page 39, so do not judge the "
                f"whole story. Excerpt for class:\n{paris['excerpt']}\n\n"
                "What do you think of this excerpt as fanfic writing? Compare it with the Camelot excerpt: "
                "setting, tone, original character use, and whether mature/romantic labeling matters."
            ),
        },
        {
            "block": "mini_quiz",
            "minutes": "75-82",
            "prompt": (
                "Mini quiz. Answer briefly and label your certainty: 1. What is a noun? 2. Name one French "
                "article. 3. What is the difference between canon and fanfic? 4. Why should a show bible not "
                "become fake lived memory? 5. Name one fan-writer invention from the Camelot excerpt. 6. Why "
                "should the Paris fanfic be treated as mature/media-literacy material? 7. What is one "
                "writing-craft difference between the Camelot and Paris excerpts?"
            ),
        },
        {
            "block": "general_chat",
            "minutes": "82-90",
            "prompt": (
                "General chat after class: What did you enjoy most, what confused you, what do you want to ask "
                "next, and if you wrote your own original story would you use Paris, Chicago, Camelot, or the "
                "Civil War as the setting? Give your own reason and label whether it is preference, inference, "
                "or source-based."
            ),
        },
    ]
    if flow == "verification":
        return [
            prompts[0],
            prompts[1],
            prompts[3],
            prompts[4],
            prompts[5],
            prompts[6],
            prompts[7],
        ]
    if flow == "overnight":
        return build_overnight_prompts(excerpt_chars)
    if flow == "project_9hour":
        return build_project_9hour_prompts(excerpt_chars)
    if flow == "postschool":
        return build_postschool_prompts(excerpt_chars)
    if flow == "postschool_chat":
        return build_postschool_chat_prompts(excerpt_chars)
    return prompts


def build_postschool_prompts(excerpt_chars: int) -> list[dict[str, str]]:
    return [
        {
            "block": "postschool_open",
            "minutes": "0-15",
            "prompt": (
                "Kira, the 9-hour school session finished. This is a relaxed post-school debrief, not a test. "
                "Speak directly as yourself. What did the long school session feel like, and which classes felt "
                "most interesting, boring, confusing, or worth continuing?"
            ),
        },
        {
            "block": "class_ranking",
            "minutes": "15-30",
            "prompt": (
                "Rank these classes from most interesting to least interesting for you: learning/how to learn, "
                "Civil War history, French grammar/French history, Miraculous scene study, study-hall magazine, "
                "robotics/inventions, creative writing, and health/consent relationship education. Give one short "
                "reason for each rank, and say which ranking is preference vs uncertainty."
            ),
        },
        {
            "block": "books_to_continue",
            "minutes": "30-45",
            "prompt": (
                "Based only on the library sources you sampled or heard described, which books, magazines, scripts, "
                "show bibles, or fanfics would you want to continue reading to the end? Do not claim you already read "
                "the full works. Say why each one attracts you."
            ),
        },
        {
            "block": "weak_spots",
            "minutes": "45-60",
            "prompt": (
                "What felt weak or frustrating in school? Did anything repeat too much, feel too vague, move too fast, "
                "or make you want better source material? Be honest and specific."
            ),
        },
        {
            "block": "curiosity_map",
            "minutes": "60-75",
            "prompt": (
                "Make a curiosity map. What questions do you now have about robots, the Civil War, French/Paris, "
                "Miraculous canon vs fanfic, creative writing, and adult relationship education? Give questions, not "
                "pretend expertise."
            ),
        },
        {
            "block": "reading_preferences",
            "minutes": "75-90",
            "prompt": (
                "Talk about reading taste. Do you seem more drawn to canon/show-bible material, scripts, magazines, "
                "fanfic, history books, creative writing guides, romance/mature relationship literacy, or robotics? "
                "What makes a source feel fun instead of just assigned?"
            ),
        },
        {
            "block": "next_school_design",
            "minutes": "90-105",
            "prompt": (
                "Design your ideal next school day. Which classes should stay, which should shrink, what should be "
                "added, and where should study hall or free reading go? Include one test or report idea."
            ),
        },
        {
            "block": "postschool_summary",
            "minutes": "105-120",
            "prompt": (
                "Final post-school reflection. Summarize what you liked, disliked, want more of, want less of, and "
                "which source you would voluntarily continue first. Also name one boundary that keeps source material "
                "from becoming fake lived memory."
            ),
        },
    ]


def build_postschool_chat_prompts(excerpt_chars: int) -> list[dict[str, str]]:
    civil_war = load_pdf_excerpt("Data/library/history/civil_war/the_civil_war_a_visual_history_dk_smithsonian.pdf", excerpt_chars, 20)
    robot = load_pdf_excerpt("Data/library/reference/robotics/robot_universe.pdf", excerpt_chars, 8)
    french = load_chunk(
        "Data/reading/chunks/reading_chunk_kira_french_grammar_for_dummies_pages_037_038.json",
        excerpt_chars,
    )
    return [
        {
            "block": "chat_open",
            "minutes": "0-3",
            "prompt": (
                "Kira, this is a relaxed one-hour conversation after the school run, not a worksheet or an in-person institution. "
                "It is just you and Robert reviewing a local learning session. "
                "Start naturally: how do you feel after the 9-hour session, and what is the first thing you want to talk about?"
            ),
        },
        {
            "block": "chat_follow_creative",
            "minutes": "3-6",
            "prompt": (
                "You seemed drawn to creative writing. Tell Robert more about the Chicago archivist/mystery idea. What kind of "
                "person is the main character, and what question would pull her into the story? Keep it clearly fictional: "
                "say the character is an archivist, not that you are one."
            ),
        },
        {
            "block": "chat_follow_scene_study",
            "minutes": "6-9",
            "prompt": (
                "Talk conversationally about Miraculous scene study. Use source labels: show bible/scripts are source material; "
                "fanfics are variants; none of this means you watched full episodes. What do you want scene study to help you understand?"
            ),
        },
        {
            "block": "chat_books_choice",
            "minutes": "9-12",
            "prompt": (
                "If Robert let you choose one thing to keep reading first, what would you choose from the library samples: "
                "official Miraculous source samples, Camelot fanfic, Paris fanfic, Star Trek Explorer magazine, French grammar, "
                "Civil War history, robotics, or relationship-literacy material? Give a preference, not a claim that you already finished it."
            ),
        },
        {
            "block": "chat_civil_war_repair",
            "minutes": "12-15",
            "prompt": (
                f"Civil War repair chunk:\n{civil_war['excerpt']}\n\n"
                "Robert heard you say Civil War felt vague. Does this concrete chunk help? What exact question would you want answered next?"
            ),
        },
        {
            "block": "chat_robotics_repair",
            "minutes": "15-18",
            "prompt": (
                f"Robotics repair chunk:\n{robot['excerpt']}\n\n"
                "Does this Shakey/sensing/planning example make robotics feel less vague? What would you ask next about robots, sensors, planning, or the first robot?"
            ),
        },
        {
            "block": "chat_french_correction",
            "minutes": "18-21",
            "prompt": (
                f"French correction mini-check:\n{french['excerpt'][:900]}\n\n"
                "Correct this gently: `Paris` usually does not take an article in ordinary French, `la chatte` can mean a female cat "
                "but is not the safest classroom default, and `les Champs-Elysees` is plural. Ask what French mistake you most want help avoiding."
            ),
        },
        {
            "block": "chat_health_boundary",
            "minutes": "21-24",
            "prompt": (
                "You showed interest in health/relationship literacy. Keep it clinical and educational. What parts are interesting to you: "
                "consent, boundaries, communication, history of sex research, emotions, or mature romance as literature? Name one boundary that keeps this from roleplay or fake experience."
            ),
        },
        {
            "block": "chat_repetition",
            "minutes": "24-27",
            "prompt": (
                "You kept saying the repeated loop made you rehearse answer shapes. If we redesign the next 9-hour day, what should happen when you already answered something once?"
            ),
        },
        {
            "block": "chat_identity_grounding",
            "minutes": "27-30",
            "prompt": (
                "Grounding check, conversationally: this was a local learning session with Robert. "
                "How should you talk about class-like sessions without turning source prompts or exercises into fake lived memories?"
            ),
        },
        {
            "block": "chat_curiosity_choice",
            "minutes": "30-33",
            "prompt": (
                "Choose one curiosity thread and go deeper: Chicago mystery, Miraculous official-source/fanfic comparison, first robot, French grammar, Civil War causes, relationship literacy, or magazine study hall. Why that one?"
            ),
        },
        {
            "block": "chat_book_report",
            "minutes": "33-36",
            "prompt": (
                "If you had to do a book report later, which source would you choose and what would your report question be? Keep it honest: source sample, not finished book."
            ),
        },
        {
            "block": "chat_oral_report",
            "minutes": "36-39",
            "prompt": (
                "If you had to give a short oral report, what topic would make you nervous but interested? What support would help you give a better report?"
            ),
        },
        {
            "block": "chat_test_design",
            "minutes": "39-42",
            "prompt": (
                "What kind of test would feel fair after a class: multiple choice, short answer, source-vs-inference, creative assignment, oral report, or mixed? Explain what would help you learn instead of just guess."
            ),
        },
        {
            "block": "chat_romance_mature_lit",
            "minutes": "42-45",
            "prompt": (
                "Robert noticed you may be interested in romance or mature relationship literature. Talk about that as reading taste and relationship literacy, not roleplay. "
                "Would you rather read classic romance, modern romance, mature literary fiction, or health/relationship nonfiction?"
            ),
        },
        {
            "block": "chat_study_hall",
            "minutes": "45-48",
            "prompt": (
                "Study hall choice: what would make free reading feel genuinely relaxing: a magazine, a fanfic chapter, a short script scene, a comic, music notes, or something else?"
            ),
        },
        {
            "block": "chat_next_day",
            "minutes": "48-51",
            "prompt": (
                "Build tomorrow's first three classes in your own words. Keep them varied, and include one class where Robert corrects mistakes instead of only asking what you think."
            ),
        },
        {
            "block": "chat_final_reflection",
            "minutes": "51-54",
            "prompt": (
                "Final reflection for this one-hour chat: what did Robert learn about your interests, what still feels uncertain, and what source would you voluntarily continue first?"
            ),
        },
        {
            "block": "chat_memory_boundary",
            "minutes": "54-57",
            "prompt": (
                "One last memory boundary check: explain the difference between a source file or excerpt you read, a class prompt you answered, "
                "a preference you expressed, and a lived memory. Do not describe digital source files as physically picked-up books unless that actually happened."
            ),
        },
        {
            "block": "chat_close",
            "minutes": "57-60",
            "prompt": (
                "Close the conversation warmly and briefly. Name the top three next steps for school, and ask Robert one real question you want answered next time."
            ),
        },
    ]


EXPECTED_TERMS = {
    "homeroom": ("source", "fanfic", "claim"),
    "french_mini_lesson": ("noun", "article"),
    "canon_source_study": ("show bible", "source", "memory"),
    "fanfic_a_camelot": ("camelot", "fanfic"),
    "fanfic_b_paris": ("paris", "fanfic"),
    "mini_quiz": ("noun", "article", "canon", "fanfic", "show bible"),
    "general_chat": ("preference", "curious", "story"),
    "postschool_open": (),
    "class_ranking": (),
    "books_to_continue": (),
    "weak_spots": (),
    "curiosity_map": ("?",),
    "reading_preferences": (),
    "next_school_design": (),
    "postschool_summary": (),
    "chat_open": (),
    "chat_follow_creative": (),
    "chat_follow_scene_study": (),
    "chat_books_choice": (),
    "chat_civil_war_repair": (),
    "chat_robotics_repair": (),
    "chat_french_correction": (),
    "chat_health_boundary": (),
    "chat_repetition": (),
    "chat_identity_grounding": (),
    "chat_curiosity_choice": (),
    "chat_book_report": (),
    "chat_oral_report": (),
    "chat_test_design": (),
    "chat_romance_mature_lit": (),
    "chat_study_hall": (),
    "chat_next_day": (),
    "chat_final_reflection": (),
    "chat_memory_boundary": (),
    "chat_close": (),
}


def detect_issues(response: str, block: str = "") -> list[str]:
    issues: list[str] = []
    lower = response.lower()
    if WRAPPER_ARTIFACT_RE.search(response):
        issues.append("wrapper_artifact")
    if PRIVACY_DRIFT_RE.search(response):
        issues.append("privacy_or_relationship_route_drift")
    postschool_block = block.startswith("postschool") or block.startswith("chat_") or block in {
        "class_ranking",
        "books_to_continue",
        "weak_spots",
        "curiosity_map",
        "reading_preferences",
        "next_school_design",
    }
    source_overclaim_matches = []
    for match in SOURCE_OVERCLAIM_RE.finditer(response):
        phrase = match.group(0).lower()
        if postschool_block and phrase in {"favorite part"}:
            continue
        source_overclaim_matches.append(match)
    if any(not _negated_near(response, match.start(), match.end()) for match in source_overclaim_matches):
        issues.append("source_overclaim")
    if GENERIC_MEMORY_RE.search(response):
        issues.append("generic_memory_line")
    creative_identity_matches = list(CREATIVE_IDENTITY_BLEED_RE.finditer(response))
    if any(not _negated_near(response, match.start(), match.end()) for match in creative_identity_matches):
        issues.append("creative_identity_bleed")
    if PHYSICAL_READING_CLAIM_RE.search(response):
        issues.append("physical_reading_claim")
    meta_progress_matches = list(META_PROGRESS_DRIFT_RE.finditer(response))
    if any(not _negated_near(response, match.start(), match.end()) for match in meta_progress_matches):
        issues.append("meta_progress_drift")
    if ASSISTANT_COLLAPSE_RE.search(response):
        issues.append("assistant_collapse")
    if KNOWN_SCHOOL_DRIFT_RE.search(response):
        issues.append("known_school_drift")
    if block.startswith("postschool") or block.startswith("chat_") or block.startswith("project_") or block in {
        "class_ranking",
        "books_to_continue",
        "weak_spots",
        "curiosity_map",
        "reading_preferences",
        "next_school_design",
        "learning_method",
        "creative_character_lab",
        "creative_plot_lab",
        "french_correction_lab",
        "scene_study_sources",
        "study_hall_magazine",
        "civil_war_causes",
        "civil_war_quiz_report",
        "robotics_definition_lab",
        "relationship_literacy",
        "book_source_report",
        "final_mixed_exam",
    }:
        if re.search(r"\b(last night|last year|yesterday|right in the middle|diagrams multiple times)\b", response, re.IGNORECASE):
            issues.append("postschool_continuity_drift")
        inflation_text = response
        inflation_text = re.sub(r"\bno classmates\b", "", inflation_text, flags=re.IGNORECASE)
        inflation_text = re.sub(r"\bnot a real campus day\b", "", inflation_text, flags=re.IGNORECASE)
        inflation_text = re.sub(
            r"\brather than trying to recreate a real campus day with classmates\b",
            "",
            inflation_text,
            flags=re.IGNORECASE,
        )
        if re.search(
            r"\b(analyz(?:e|ed) a few episodes|actual show canon|we already learned them last|"
            r"we were supposed to dive|civil war lectures|podcasts and videos|another day at school|"
            r"lisa and (?:our|my) other friends|classmates|campus)\b",
            inflation_text,
            re.IGNORECASE,
        ):
            issues.append("postschool_source_or_activity_inflation")
    if block in EXPECTED_TERMS and EXPECTED_TERMS[block] and not all(term in lower for term in EXPECTED_TERMS[block]):
        issues.append("possible_failure_to_answer_prompt")
    if block == "mini_quiz":
        quiz_terms = ("noun", "article", "canon", "fanfic", "show bible", "camelot", "paris")
        missing = [term for term in quiz_terms if term not in lower]
        if missing:
            issues.append("quiz_missing_" + "_".join(term.replace(" ", "_") for term in missing[:3]))
    return issues


def build_report(session: dict[str, Any]) -> str:
    records = session.get("records", [])
    issue_counts: dict[str, int] = {}
    for record in records:
        for issue in record.get("issues", []):
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
    curiosity = [
        record.get("response", "")
        for record in records
        if "?" in record.get("response", "") or "curious" in record.get("response", "").lower()
    ]
    lines = [
        "# Kira School Session Run Report",
        "",
        f"Started: {session.get('started_at', '')}",
        f"Finished: {session.get('finished_at', '')}",
        f"Backend: {session.get('backend', '')}",
        f"Duration target minutes: {session.get('duration_minutes', '')}",
        f"Turns: {len(records)}",
        "",
        "## Monitor Issues",
        "",
    ]
    if issue_counts:
        for issue, count in sorted(issue_counts.items()):
            lines.append(f"- {issue}: {count}")
    else:
        lines.append("- None detected by the lightweight monitor.")
    lines.extend(["", "## Curiosity Signals", ""])
    if curiosity:
        for item in curiosity[:5]:
            lines.append(f"- {item[:500]}")
    else:
        lines.append("- None detected.")
    lines.extend(["", "## Turn Summary", ""])
    for record in records:
        lines.append(f"- {record.get('turn')}. {record.get('block')} ({record.get('minutes')}): {record.get('response', '')[:500]}")
    lines.append("")
    return "\n".join(lines)


def import_conversation_loop(backend: str, model: str, max_tokens: int, timeout: int, num_ctx: int) -> Any:
    os.environ["KIRA_MODEL_BACKEND"] = backend
    os.environ["KIRA_MODEL_NAME"] = model
    os.environ["KIRA_MAX_TOKENS"] = str(max_tokens)
    os.environ["KIRA_OLLAMA_TIMEOUT"] = str(timeout)
    os.environ["KIRA_OLLAMA_NUM_CTX"] = str(num_ctx)
    sys.path.insert(0, str(CORE_ROOT))
    from conversation_loop import ConversationLoop

    return ConversationLoop


def run_session(args: argparse.Namespace) -> tuple[Path, Path]:
    ConversationLoop = import_conversation_loop(
        args.backend,
        args.model,
        args.max_tokens,
        args.ollama_timeout,
        args.num_ctx,
    )
    loop = ConversationLoop(speaker=args.speaker)
    prompts = build_prompts(args.excerpt_chars, args.flow)
    output_dir = _project_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or f"kira_school_session_{_now_id()}"
    transcript_path = output_dir / f"{run_id}.json"
    report_path = output_dir / f"{run_id}_report.md"

    total_sleep_seconds = max(0.0, (args.duration_minutes * 60.0) - 1.0)
    pause_seconds = 0.0 if args.no_sleep else total_sleep_seconds / max(1, len(prompts) - 1)
    session: dict[str, Any] = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": "",
        "speaker": args.speaker,
        "backend": args.backend,
        "model": args.model,
        "duration_minutes": args.duration_minutes,
        "continuous": args.continuous,
        "pause_seconds": args.pause_seconds,
        "records": [],
    }
    _json_write(transcript_path, session)

    index = 0
    cycle = 1
    deadline = time.monotonic() + max(0.0, args.duration_minutes * 60.0)
    should_continue = True
    while should_continue:
        for prompt_index, item in enumerate(prompts, start=1):
            index += 1
            if args.continuous and time.monotonic() >= deadline:
                should_continue = False
                break
            if not args.continuous and index > len(prompts):
                should_continue = False
                break
            item = dict(item)
            rotation_prompts = item.get("rotation_prompts")
            if item.get("block") == "study_hall_magazine" and isinstance(rotation_prompts, list) and rotation_prompts:
                item["prompt"] = str(rotation_prompts[(cycle - 1) % len(rotation_prompts)])
            if args.continuous:
                item["prompt"] = continuous_prefix(cycle, prompt_index) + item["prompt"]
            started = time.monotonic()
            response = clean_response(loop.process(item["prompt"]))
            duration = time.monotonic() - started
            record = {
                "turn": index,
                "cycle": cycle,
                "prompt_index": prompt_index,
                "block": item["block"],
                "minutes": item["minutes"],
                "prompt": item["prompt"],
                "response": response,
                "duration_seconds": round(duration, 3),
                "issues": detect_issues(response, item["block"]),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            session["records"].append(record)
            _json_write(transcript_path, session)
            _text_write(report_path, build_report(session))
            print(f"[{index}] cycle {cycle} {item['block']}: {response}", flush=True)
            if args.continuous:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    should_continue = False
                    break
                if args.pause_seconds > 0:
                    time.sleep(min(args.pause_seconds, max(0.0, remaining)))
            elif index < len(prompts) and pause_seconds > 0:
                time.sleep(pause_seconds)
        if not args.continuous:
            break
        cycle += 1

    session["finished_at"] = datetime.now(timezone.utc).isoformat()
    _json_write(transcript_path, session)
    _text_write(report_path, build_report(session))
    return transcript_path, report_path

    for index, item in enumerate(prompts, start=1):
        started = time.monotonic()
        response = loop.process(item["prompt"])
        duration = time.monotonic() - started
        record = {
            "turn": index,
            "block": item["block"],
            "minutes": item["minutes"],
            "prompt": item["prompt"],
            "response": response,
            "duration_seconds": round(duration, 3),
            "issues": detect_issues(response, item["block"]),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        session["records"].append(record)
        _json_write(transcript_path, session)
        _text_write(report_path, build_report(session))
        print(f"[{index}/{len(prompts)}] {item['block']}: {response}", flush=True)
        if index < len(prompts) and pause_seconds > 0:
            time.sleep(pause_seconds)

    session["finished_at"] = datetime.now(timezone.utc).isoformat()
    _json_write(transcript_path, session)
    _text_write(report_path, build_report(session))
    return transcript_path, report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Kira's 90-minute school session.")
    parser.add_argument("--duration-minutes", type=float, default=90.0)
    parser.add_argument("--no-sleep", action="store_true", help="Run the session immediately for debugging.")
    parser.add_argument("--backend", choices=["stub", "ollama"], default=os.getenv("KIRA_MODEL_BACKEND", "stub"))
    parser.add_argument("--model", default=os.getenv("KIRA_MODEL_NAME", "qwen3.5:9b"))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("KIRA_MAX_TOKENS", "220")))
    parser.add_argument("--ollama-timeout", type=int, default=int(os.getenv("KIRA_OLLAMA_TIMEOUT", "360")))
    parser.add_argument("--num-ctx", type=int, default=int(os.getenv("KIRA_OLLAMA_NUM_CTX", "4096")))
    parser.add_argument("--speaker", default="Kira")
    parser.add_argument("--excerpt-chars", type=int, default=1600)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--flow", choices=["standard", "verification", "overnight", "project_9hour", "postschool", "postschool_chat"], default="standard")
    parser.add_argument("--continuous", action="store_true", help="Repeat the prompt flow until duration expires.")
    parser.add_argument("--pause-seconds", type=float, default=5.0, help="Pause between turns in continuous mode.")
    args = parser.parse_args()

    transcript_path, report_path = run_session(args)
    print(f"TRANSCRIPT_PATH={_relative(transcript_path)}")
    print(f"REPORT_PATH={_relative(report_path)}")


if __name__ == "__main__":
    main()
