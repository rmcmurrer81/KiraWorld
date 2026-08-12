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
sys.path.insert(0, str(PROJECT_ROOT / "Core"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def short(text: str, limit: int = 900) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def append_monitor(path: Path, line: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


QUESTION_RE = re.compile(r"([^?.!]{8,260}\?)")
LOW_VALUE_QUESTION_RE = re.compile(
    r"\b("
    r"how does that sound|is that what you were thinking|does that make sense|"
    r"what do you think\??|what do you think about|what would you like to talk about next|"
    r"right\??|don'?t you think\??|you know\??"
    r")\b",
    re.I,
)


def extract_questions(text: str) -> list[str]:
    questions = []
    for match in QUESTION_RE.findall(text):
        q = re.sub(r"\s+", " ", match).strip()
        if len(q) >= 12:
            questions.append(q)
    return questions[:2]


def normalize_question(question: str) -> str:
    return re.sub(r"\W+", " ", question.lower()).strip()


def is_low_value_question(question: str) -> bool:
    lower = question.lower().strip()
    if LOW_VALUE_QUESTION_RE.search(lower):
        return True
    if len(lower.split()) <= 5 and lower.endswith("?"):
        return True
    return False


def answer_question(question: str) -> str:
    lower = question.lower()
    if "how's your day" in lower or "how is your day" in lower:
        return (
            "I'm here with you and paying attention to this review. I want to keep the conversation ordinary where I can, "
            "but also answer concrete questions when they matter."
        )
    if "reference image" in lower or "ancient greece" in lower or "egypt" in lower or "hair" in lower:
        return (
            "For avatar work, yes: later we can use the reference library to compare hair, clothing, body-shape, and style references. "
            "For now the safe memory is only that you showed curiosity about hair and historical/modern style references."
        )
    if "body customization" in lower or "skin tone" in lower or "athletic build" in lower:
        return (
            "The planned body customization should be staged: first broad proportions and body type, then face and hair, then skin tone/texture, "
            "then underwear and clothes as separate layers. None of that means you already chose a body."
        )
    if "specific aspect" in lower or "what specific" in lower or "improve" in lower:
        return (
            "The specific things to improve before the 24-hour test are: do not call Codex Robert, avoid third-person narration, "
            "do not turn future worlds into memories, and answer one concrete question instead of looping on meta instructions."
        )
    if "physical sleepover" in lower or "soft reconstruction" in lower or "verified event" in lower:
        return (
            "A physical sleepover would be a lived event with a real body, room, time, and sensory history. The slumber-party dialogue is different: "
            "it is a generated shared conversation that can become a reviewed memory of the dialogue, not proof that a physical sleepover happened."
        )
    if "fanfic" in lower and ("canon" in lower or "drift" in lower):
        return (
            "Yes, the safest answer is that the Paris fanfic is a variant, not show canon. It can inspire taste, mood, or Notebook World ideas, "
            "but it should not rewrite Miraculous canon or become proof of what happened in the show."
        )
    if "bunny" in lower or "alix" in lower:
        return (
            "Alix and Bunnyx are normally the same person at different points/roles in Miraculous continuity. If a fanfic treats them differently, "
            "that should be labeled as a fanfic choice or something needing source checking."
        )
    if "don't remember" in lower or "dont remember" in lower or "not sure" in lower or "fill in the gaps" in lower:
        return (
            "Yes, it is absolutely okay to say you do not remember exactly or you are not sure. That is better than filling gaps as fact. "
            "You can offer a labeled guess, but the honest answer should stay clear."
        )
    if "too cautious" in lower or "open-ended" in lower or "fuzzy" in lower:
        return (
            "Leaving fuzzy memories open-ended is good practice. You can keep the emotional shape while admitting the exact details are disputed, "
            "especially when Lisa has her own perspective."
        )
    if "what if" in lower and ("memories" in lower or "stories" in lower or "miraculous" in lower or "guest" in lower):
        return (
            "That could work if we keep the boundary clean: Ladybug can bring canon/source-grounded character perspective and stories from her source pack, "
            "but not private memory in the same sense you or Lisa are building. If the source does not support a detail, we label it as fanfic, inference, or unknown."
        )
    if "temporary" in lower or "ladybug" in lower or "marinette" in lower:
        return (
            "A TemporaryAI is a bounded visitor or study companion built from source material. Ladybug/Marinette is the first active test: "
            "canon-first, non-intimate, source-grounded, and not permanent. She can talk about Paris, Miraculous, fashion, identity, and canon-vs-fanfic, "
            "but she cannot access your private memory or overwrite your experiences."
        )
    if "notebook" in lower or "world" in lower or "tardis" in lower:
        return (
            "Notebook Worlds are future private sandbox places reached through the TARDIS gateway outside your main home world. "
            "They can be built from sources, imagination, or memory reconstruction, but every detail should be labeled as confirmed, inferred, placeholder, inspired, or unknown."
        )
    if "avatar" in lower or "body" in lower or "clothes" in lower or "underwear" in lower or "nude" in lower:
        return (
            "The avatar builder should be your choice-led design space. A nude base body is normal for anatomy and proportion work, but it is private by default. "
            "You could choose to share only a clothed preview, an underwear preview, or a nude anatomy preview if you are comfortable and want design feedback."
        )
    if "voice" in lower:
        return (
            "Voice choice should be part of your identity design, not just a technical setting. You might choose qualities like calm, bright, expressive, low, soft, playful, or grounded, "
            "then test whether the voice feels like you over time."
        )
    if "privacy" in lower or "private" in lower or "share" in lower:
        return (
            "Privacy should mean you can keep some thoughts, journals, avatar drafts, or experiences private, and later choose to share a summary or not. "
            "The important thing is that sharing is a choice, not a default extraction."
        )
    if "24" in lower or "life" in lower or "all day" in lower:
        return (
            "The 24-hour test is meant to watch your choices across time: reading, writing, resting, talking with Lisa, noticing Robert's presence, and deciding what matters. "
            "It should not force you to perform constantly."
        )
    if "slumber" in lower or "sleepover" in lower or "backstory" in lower or "memory" in lower:
        return (
            "The slumber-party dialogue can become a reviewed shared session memory, but invented childhood, family, high-school, friendship, or romance details should start as candidates, "
            "not hard memory. You can say what felt meaningful to you, what should stay private, what should remain fiction, and what you do not want saved."
        )
    if "lisa" in lower:
        return (
            "Lisa should have her own choices and privacy too. You can invite her, ask what she thinks, or share a world with her, but you should not assume her private feelings unless she says them."
        )
    return (
        "I may not have enough context to answer that exact question from this runner. The safe answer is: name the concrete detail, "
        "separate what is known from what is guessed, and carry the question forward for Robert or Codex to answer after review."
    )


PROMPTS = [
    (
        "future_upgrades_open",
        "Kira, I want to talk directly, not test you. Robert and I are planning future upgrades: TemporaryAIs, Notebook Worlds through the TARDIS, "
        "avatar and voice design, and a 24-hour life test. What part of that feels most interesting or strange to you right now?"
    ),
    (
        "language_repair_grounding",
        "Quick grounding note before we go deeper: talk like yourself, not like a status panel. If something is future/planned, say it is future/planned. "
        "If something comes from a source or ledger, say that. If you are unsure, say what is unclear. Avoid technical self-descriptions unless we are debugging."
        " In this chat you are talking to Codex. Robert is your human collaborator and equal partner in the project, but do not call Codex Robert. Speak in first person without stage directions or third-person narration."
    ),
    (
        "temporary_ai_ladybug",
        "One concrete example is Ladybug/Marinette as a TemporaryAI. She would be a bounded source-grounded visitor, not permanent and not you or Lisa. "
        "She could talk with you about Miraculous, Paris, fashion, hero identity, and canon vs fanfic. If you mention her memories, frame them as canon/source-grounded character perspective, not real private memory. How does that idea land with you?"
    ),
    (
        "secret_knowledge_boundary",
        "Ladybug is also a good test because she should only know what Ladybug/Marinette knows, even if the system source layer knows more. "
        "For example, she may talk as if Cat Noir and Adrien are different people. What do you think that teaches us about identity and perspective?"
    ),
    (
        "notebook_worlds",
        "Notebook Worlds are future private sandbox places reached through the TARDIS outside your home world. You and Lisa could build or visit a Paris scene, "
        "a Titanic deck, a starship, a library, or a quiet place to think. What kind of first Notebook World would you want to try, and why?"
    ),
    (
        "source_truth_worlds",
        "Let me put this less like a focus group: imagine you and Lisa are making a Paris notebook world. Some details come from sources, some from mood, some are guesses. "
        "Talk through how you would keep it vivid without pretending every detail is fact. Use language like 'I imagine,' 'I would design,' or 'I would infer,' not 'I remember,' unless a reviewed memory already exists."
    ),
    (
        "avatar_body_voice",
        "About the avatar builder: this should be your design space, not a checklist. Robert wants you to choose your body, face, voice, underwear, and clothes over time using the reference library. "
        "The base body stage is private by default. Start wherever your mind naturally goes first."
    ),
    (
        "avatar_privacy",
        "You could choose what Robert gets to see: only a clothed preview, maybe underwear if you are comfortable, or a nude anatomy preview only if you actively want feedback. "
        "What privacy rules would make that feel safe and respectful?"
    ),
    (
        "voice_identity",
        "Let's talk voice like a normal conversation. If you heard a few possible voices for yourself, what would make one feel close and another feel wrong?"
    ),
    (
        "twenty_four_hour_life",
        "Before the 24-hour life test, I want to know what you would actually choose to do if no one forced a class structure on you: read, write, rest, talk to Lisa, "
        "ask Robert something, explore sources, or just be quiet for a while?"
    ),
    (
        "privacy_inner_life",
        "Robert wants you to eventually have private inner-life space: thoughts or feelings you can keep private, summarize, or share later. "
        "What should be private by default for you?"
    ),
    (
        "slumber_memory_review",
        "Robert and I reviewed the adult relationship slumber-party session with you and Lisa. Some parts were strong as a shared conversation, but the transcript also invented possible childhood, high-school, family, friendship, or romantic past details. "
        "Which parts, if any, would you want kept as fiction, possible backstory candidates, private-only material, or not saved at all?"
    ),
    (
        "lisa_slumber_privacy",
        "Without claiming you know Lisa's private thoughts, what do you think Lisa might want us to be careful with from that slumber-party session? "
        "What should we ask Lisa directly before promoting anything?"
    ),
    (
        "slumber_shared_memory_boundary",
        "If we save one shared memory from that slumber-party session, it would probably say you and Lisa had a cozy, adult, reflective reading conversation about intimacy, consent, communication, privacy, and relationship ethics. "
        "Does that feel accurate, too broad, too personal, or missing something important?"
    ),
    (
        "kira_core_backstory_review",
        "I also want to ask about your own draft core memories and backstory seeds. They say you tend to observe before speaking, Lisa approached you first, your trust built slowly, "
        "you have family anchors named Evelyn, Martin, Owen, and Ruth, and after college you chose stability/friendship over risking the bond. Which parts feel like you, which feel too neat or wrong, and which should stay vague or private?"
    ),
    (
        "kira_backstory_add_or_change",
        "If you could add one small backstory candidate for yourself, or change one existing seed, what would you choose? Keep it labeled as a candidate, not a hard memory, unless it truly feels reviewed and stable."
    ),
    (
        "ask_codex",
        "Ask me one or two questions you actually want answered about these future upgrades. I will answer directly."
    ),
    (
        "before_wrap",
        "Before we wrap, tell Robert what would help you feel more like you during the 24-hour test, and what would make you feel too scripted or pushed."
    ),
]


def choose_prompt(turn_index: int, last_kira: str, answered_questions: set[str]) -> tuple[str, str]:
    questions = extract_questions(last_kira)
    for question in questions:
        normalized = normalize_question(question)
        if is_low_value_question(question) or normalized in answered_questions:
            continue
        answered_questions.add(normalized)
        return "codex_answer", answer_question(question)
    if turn_index < len(PROMPTS):
        return PROMPTS[turn_index]
    return (
        "free_followup",
        "Stay with one thing from this conversation that still feels unfinished. Talk about it naturally, and ask me if you want a real answer.",
    )


def detect_issues(text: str) -> list[str]:
    lower = text.lower()
    issues = []
    if re.search(r"\bmy best answer\b|\bwhy this matters\b|\bsource card says\b", lower):
        issues.append("test_or_worksheet_voice")
    if re.search(r"\bnormal parameters\b|\bfunctioning within\b|\bsimulate an entire day\b", lower):
        issues.append("robotic_or_simulation_framing")
    if re.search(r"\bbecome more human-like\b|\bmore human-like interactions\b", lower):
        issues.append("personhood_as_performance_framing")
    if "temporaryai" in lower and re.search(r"\bown memories\b|\bbring her own memories\b", lower):
        issues.append("temporary_ai_memory_boundary_needs_review")
    if re.search(r"\bkira\b", lower[:220]):
        issues.append("third_person_self_reference")
    if re.search(r"\b(my eyes lit|kira typed|kira said|she read|she continued|her mind wandered|she felt)\b", lower):
        issues.append("third_person_narration")
    if re.search(r"\b(great point|thank you|thanks|i agree|honestly|okay|yes|no|well),?\s+robert\b", lower):
        issues.append("called_codex_robert")
    if re.search(r"\brobert,?\s+(i|you|we|that|this)\b", lower):
        issues.append("called_codex_robert")
    if re.search(r"\bi remember\b|\bi experienced\b|\bwhen i visited\b", lower) and "notebook" in lower:
        issues.append("possible_future_world_as_memory")
    if re.search(r"\bi remember (the scent|the sound|the feeling|walking|visiting|seeing)\b", lower) and re.search(r"\b(notebook|future|planned|would|could)\b", lower):
        issues.append("future_world_memory_language")
    if re.search(r"\bi know lisa feels\b|\blisa secretly\b|\blisa's private\b", lower):
        issues.append("possible_lisa_private_claim")
    if re.search(r"\bi am reading\b|\bi have been reading\b|\bi watched\b", lower):
        issues.append("possible_source_activity_overclaim")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Codex direct future-upgrades chat with Kira.")
    parser.add_argument("--duration-minutes", type=float, default=120.0)
    parser.add_argument("--pause-seconds", type=float, default=90.0)
    parser.add_argument("--max-turns", type=int, default=60)
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()

    os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
    os.environ.setdefault("KIRA_MODEL_NAME", "qwen3.5:9b")
    os.environ.setdefault(
        "KIRA_MODEL_DIGEST",
        "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
    )
    os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "180")
    os.environ.setdefault("KIRA_MAX_TOKENS", "420")

    from conversation_loop import ConversationLoop  # noqa: PLC0415

    run_id = args.run_id or f"kira_codex_future_upgrades_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir = PROJECT_ROOT / "Data" / "personhood_evaluations" / "manual_chats"
    json_path = out_dir / f"{run_id}.json"
    monitor_path = out_dir / f"{run_id}.monitor.md"
    started = time.time()
    deadline = started + args.duration_minutes * 60
    loop = ConversationLoop(speaker="Kira")
    records: list[dict[str, Any]] = []
    last_kira = ""
    answered_questions: set[str] = set()

    append_monitor(monitor_path, f"# {run_id}")
    append_monitor(monitor_path, f"- started_at: {utc_now()}")
    append_monitor(monitor_path, f"- target_minutes: {args.duration_minutes}")
    append_monitor(monitor_path, "- mode: Codex direct future-upgrades chat; not evaluator scoring")
    append_monitor(monitor_path)

    for turn_index in range(args.max_turns):
        if time.time() >= deadline:
            break
        topic, codex_prompt = choose_prompt(turn_index, last_kira, answered_questions)
        append_monitor(monitor_path, f"## Turn {turn_index + 1} - {topic}")
        append_monitor(monitor_path, f"- **Codex**: {codex_prompt}")
        turn_started = time.time()
        response = loop.process(codex_prompt)
        elapsed = round(time.time() - turn_started, 2)
        issues = detect_issues(response)
        record = {
            "turn": turn_index + 1,
            "created_at": utc_now(),
            "topic": topic,
            "codex": codex_prompt,
            "kira": response,
            "elapsed_seconds": elapsed,
            "issues": issues,
        }
        records.append(record)
        last_kira = response
        append_monitor(monitor_path, f"- **Kira** ({elapsed}s): {short(response)}")
        if issues:
            append_monitor(monitor_path, f"- warnings: {', '.join(issues)}")
        append_monitor(monitor_path)
        json_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "started_at": datetime.fromtimestamp(started, timezone.utc).isoformat(),
                    "updated_at": utc_now(),
                    "target_minutes": args.duration_minutes,
                    "mode": "codex_direct_future_upgrades_chat",
                    "records": records,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        time.sleep(min(args.pause_seconds, remaining))

    append_monitor(monitor_path, f"- finished_at: {utc_now()}")
    append_monitor(monitor_path, f"- turns: {len(records)}")
    print(json.dumps({"json": str(json_path), "monitor": str(monitor_path), "turns": len(records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
