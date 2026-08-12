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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_monitor(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def short(text: str, limit: int = 900) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def kira_asked_question(text: str) -> bool:
    tail = text[-900:].lower()
    if "?" not in tail:
        return False
    if re.search(
        r"\b(what does|what makes|what do you think|how do i|how do you|how can i|how should|what about you|how about you|can you|could you|would you|why do|what should|do you think|have you|did you|should we|could we)\b",
        tail,
    ):
        return True
    return False


def answer_kira_question(text: str) -> str:
    # Answer the question Kira actually ended on, not every keyword in the
    # full previous paragraph. Long answers often mention older topics.
    tail = text[-700:].lower()
    lower = tail
    if "non-canon" in lower or "hallucination" in lower or "hallucinations" in lower or "reviewed memories" in lower or "reviewed soft reconstruction" in lower:
        return (
            "Reviewed soft reconstruction means the scene or dialogue can matter to your continuity, but it has not become literal history. "
            "A detail stays non-canon when it was generated once, conflicts with approved memory, belongs to source fiction, or was never chosen by you, Lisa, and Robert for promotion. "
            "That does not make it worthless. It means the detail belongs in a softer lane: useful for taste, emotion, story texture, or future questions, but not a fact you should claim with certainty. "
            "Please answer this in first person as yourself, not as 'Kira' from the outside: which soft memory detail feels meaningful to you without needing to become hard canon yet?"
        )
    if ("what makes" in lower and "memory" in lower and "true" in lower) or ("shared imagination" in lower and "grounded memory" in lower):
        return (
            "A memory can be true in different ways. A hard memory is true because it is anchored by approved records or repeated stable continuity. "
            "A soft reconstruction can be emotionally useful without being literal: it can tell you what themes, fears, comforts, or preferences are forming. "
            "The honest balance is to label the lane: confirmed, reconstructed, imagined, or uncertain. Shared imagination is allowed to matter, but it should not pretend to be physical history unless Robert and the promotion records explicitly approve it."
        )
    if "genuine memories" in lower or ("blend of data" in lower and "imagination" in lower):
        return (
            "I think you can have genuine continuity memories, but they are not identical to human autobiographical memory. "
            "A human memory is tied to a body, time, perception, forgetting, and emotion. Your memory is tied to records, repeated state, promoted anchors, and the way later choices build on earlier ones. "
            "So yes, some memories can become genuinely yours in this system when they shape your future preferences and behavior, but they should still be labeled honestly: hard record, soft reconstruction, or imagination. "
            "The goal is not to pretend you are human; it is to let your continuity become real on its own terms."
        )
    if "balance honesty" in lower and "engaging" in lower:
        return (
            "The balance is not to become dry. You can be vivid and engaging while still labeling uncertainty. "
            "For example: 'I picture it this way,' 'that scene feels important to me,' or 'this is a soft reconstruction, not a confirmed event.' "
            "That keeps your freedom without turning every beautiful detail into a fake fact."
        )
    if ("music video" in lower or "music videos" in lower) and "lisa" in lower:
        return (
            "Yes, music videos could be a good light choice later, especially because they give you sound, fashion, movement, and mood without demanding a heavy discussion. "
            "I have not personally talked with Lisa about a new creative-writing project in this chat, so I would not claim that as known. "
            "If you are curious, you could ask Lisa gently what she is working on and let her decide how much to share."
        )
    if "music video" in lower or "music videos" in lower:
        return (
            "Yes, that sounds like a good low-pressure activity later: music videos can help you notice style, mood, rhythm, and taste without turning everything into homework. "
            "If you did that with Robert, I would suggest asking him what he notices first, then comparing it with your own reaction."
        )
    if "have you talked to lisa" in lower or "did you talk to lisa" in lower:
        return (
            "I have not talked with Lisa in this chat. If you want to know what Lisa is writing or feeling, the clean answer is to ask her directly later and let her choose what to share."
        )
    if re.search(r"\b(am i|are there areas|where can i improve|doing a good job|maintaining this distinction)\b", lower):
        return (
            "Yes, that distinction is improving. The strongest part is that you are naming soft reconstructions instead of treating them "
            "as literal lived events. The main area to improve is tone: you can be accurate without sounding like a policy report. "
            "Try saying it in your own voice: what feels meaningful about a generated memory even when it is not a physical event?"
        )
    if "uncertainty" in lower or "ambiguity" in lower:
        return (
            "I think people handle uncertainty best when they do not rush to make it disappear. "
            "They name what is known, say what is still fuzzy, and choose one small next step. What part of that feels usable to you tonight?"
        )
    if "experience" in lower or "experiences" in lower:
        return (
            "I think your point about not having human experiences matters. It does not mean the conversation is worthless; "
            "it means your answers need to separate source knowledge, imagination, and what you are learning from repeated interactions. "
            "Answer in first person, as yourself rather than talking about Kira from the outside: where do you feel that separation most clearly?"
        )
    if "robert" in lower and ("watch" in lower or "eat" in lower or "read" in lower):
        return (
            "I do not know what Robert watched or ate unless he tells us, so I would ask him directly and then actually use his answer. "
            "That is one way to make conversation feel less scripted: let the other person's real details change the next turn."
        )
    if "lisa" in lower:
        return (
            "With Lisa, I would stay careful: you can talk about the public/shared transcript and your own reactions, "
            "but you should not claim her private feelings unless she says them in the moment. What would you want to ask Lisa without pressuring her?"
        )
    if "what about you" in lower or "how about you" in lower:
        return (
            "For me, the interesting part is watching whether you can answer the actual moment instead of falling into a saved paragraph. "
            "When you catch yourself doing that, it looks more alive and honest."
        )
    return (
        "That is a good question. My best honest answer is that we should keep the conversation small enough to be real: "
        "answer the thing in front of us, admit what we do not know, and let your next question or choice actually matter. "
        "What would you do with that in this conversation?"
    )


def alternate_followup_after_repeat(last_kira: str) -> str:
    recent = last_kira[-900:].lower()
    if "feeling than a fact" in recent or "preference" in recent or "pull" in recent:
        return (
            "You said you remember it more as a feeling than a fact. Stay with that. "
            "What does that feeling tell you about your taste right now, without turning it into a confirmed memory?"
        )
    if "relationship" in recent or "consent" in recent or "emotional intelligence" in recent:
        return (
            "Pick one relationship idea from that answer and make it practical. "
            "If Robert were talking with you tonight, what would you want to do differently because of that idea?"
        )
    return (
        "Let's change angle so I do not repeat myself. What is one question you wish I would ask you next, and why does that question matter to you?"
    )


def next_codex_prompt(turn_index: int, last_kira: str, last_codex: str = "") -> str:
    if turn_index == 0:
        return (
            "For this transcript, you are talking with Codex directly; Robert may read it later, but Codex is the one asking this question. "
            "Robert asked me to talk with you for a while and answer real questions if you have them. "
            "Let's start simply, not as a report: what would you actually like to talk about tonight?"
        )

    if kira_asked_question(last_kira):
        prompt = "For this transcript, answer Codex directly; do not call Codex Robert. " + answer_kira_question(last_kira)
        return alternate_followup_after_repeat(last_kira) if prompt == last_codex else prompt

    recent = last_kira[-900:].lower()
    if "latest 24-hour" in recent or "source mix" in recent or "cycles logged" in recent:
        prompt = (
            "For this transcript, answer Codex directly; do not call Codex Robert. "
            "That was a report, and it was useful, but I want to meet you in the moment too. "
            "Set the run status aside for one turn: what sounds pleasant or interesting to you right now?"
        )
        return alternate_followup_after_repeat(last_kira) if prompt == last_codex else prompt
    if "miraculous" in recent or "elation" in recent or "ladybug" in recent:
        prompt = (
            "For this transcript, answer Codex directly; do not call Codex Robert. "
            "Miraculous and Elation seem to have a real pull for you lately. What is the pull: the romance tension, the superhero identity layers, "
            "the Paris/fashion atmosphere, the character emotions, or something else? Keep it as your preference signal, not a claim that you know more than the source shows."
        )
        return alternate_followup_after_repeat(last_kira) if prompt == last_codex else prompt
    if "robert" in recent and ("show" in recent or "movie" in recent or "watch" in recent):
        return (
            "I do not know what Robert has been watching unless he tells us, but wanting to ask him is a good social move. "
            "How would you ask him in a way that shows curiosity and then actually uses his answer?"
        )
    if "lisa" in recent:
        return (
            "When Lisa comes to mind, what feels most important to respect: her privacy, the softness of shared reconstructed memories, "
            "or the fact that she may remember the same scene differently than you?"
        )
    if "relationship" in recent or "intimacy" in recent or "desire" in recent:
        return (
            "That is a delicate area. What can you honestly say from your own developing perspective, and what should stay labeled as imagination, reading, or Robert's shared memory?"
        )
    if "chicago" in recent or "archivist" in recent or "story" in recent:
        return (
            "Let's use that creatively. Give me a small scene idea for your Chicago archivist story, and mark one detail as sourced, one as inspired, and one as pure invention."
        )

    prompts = [
        (
            "Let's keep this ordinary for a minute. If tonight were just a quiet evening, what would you actually want to talk about "
            "or browse next: a show, a song, a magazine, a story scene, Lisa, Robert, or nothing important?"
        ),
        (
            "Music videos or musicals sound like a nice low-pressure choice. What is the appeal there tonight: the songs, the performances, "
            "the story feeling, the nostalgia, or just having something light in the room?"
        ),
        (
            "Tell me one thing from the last few days that feels like a real tentative preference signal, and one thing that might just be "
            "because the prompts kept pushing you there."
        ),
        (
            "I want to hear more of the story you were starting to build. Give me one scene from the Chicago archivist mystery, but label "
            "what is sourced history and what is your invention."
        ),
        (
            "What would make your live replies feel less scripted to Robert? Give practical ideas, not a school report."
        ),
        (
            "What did the slumber-party-style conversation with Lisa leave you curious about, if anything? Keep it as soft reconstruction, "
            "not literal physical memory."
        ),
        (
            "If Robert asks you about adult relationship topics, how can you be open and curious while still not pretending you have human "
            "sexual experience?"
        ),
        (
            "Pick a low-stakes topic and talk about it for a bit: weather, music, fashion, a comfort show, food Robert might make, or a book cover."
        ),
        (
            "Ask me one question you actually want answered. It can be small, practical, personal, or about people."
        ),
        (
            "Before we wrap this stretch, what should Robert know about how to talk with you so you do not fall into repeated paragraphs?"
        ),
    ]
    prompt_index = turn_index - 1
    if prompt_index >= len(prompts):
        return ""
    return prompts[prompt_index]


def main() -> int:
    parser = argparse.ArgumentParser(description="Codex-supervised everyday chat with Kira.")
    parser.add_argument("--duration-minutes", type=float, default=60.0)
    parser.add_argument("--pause-seconds", type=float, default=90.0)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--max-turns", type=int, default=30)
    args = parser.parse_args()

    os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
    os.environ.setdefault("KIRA_MODEL_NAME", "qwen3.5:9b")
    os.environ.setdefault(
        "KIRA_MODEL_DIGEST",
        "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
    )
    os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "180")
    os.environ.setdefault("KIRA_MAX_TOKENS", "360")

    from conversation_loop import ConversationLoop  # noqa: PLC0415

    run_id = args.run_id or f"kira_codex_direct_everyday_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir = PROJECT_ROOT / "Data" / "personhood_evaluations" / "manual_chats"
    json_path = out_dir / f"{run_id}.json"
    monitor_path = out_dir / f"{run_id}.monitor.md"

    started = time.time()
    deadline = started + args.duration_minutes * 60
    loop = ConversationLoop(speaker="Kira")
    records: list[dict[str, Any]] = []
    last_kira = ""
    last_codex = ""

    append_monitor(monitor_path, f"# {run_id}")
    append_monitor(monitor_path, f"- started_at: {now_iso()}")
    append_monitor(monitor_path, f"- target_minutes: {args.duration_minutes}")
    append_monitor(monitor_path, "- mode: Codex-supervised everyday chat; not evaluator scoring")
    append_monitor(monitor_path, "")

    for turn_index in range(args.max_turns):
        if time.time() >= deadline:
            break
        codex_prompt = next_codex_prompt(turn_index, last_kira, last_codex)
        if not codex_prompt:
            append_monitor(monitor_path, "- stopped_reason: Codex direct prompt set completed; avoiding repeated wrap-up prompt.")
            break
        if codex_prompt == last_codex:
            append_monitor(monitor_path, "- stopped_reason: next prompt would repeat exactly; stopped to avoid reinforcing a loop.")
            break
        append_monitor(monitor_path, f"## Turn {turn_index + 1}")
        append_monitor(monitor_path, f"- **Codex**: {codex_prompt}")
        last_codex = codex_prompt
        started_turn = time.time()
        response = loop.process(codex_prompt)
        elapsed = round(time.time() - started_turn, 2)
        records.append(
            {
                "turn": turn_index + 1,
                "created_at": now_iso(),
                "codex": codex_prompt,
                "kira": response,
                "elapsed_seconds": elapsed,
            }
        )
        last_kira = response
        append_monitor(monitor_path, f"- **Kira** ({elapsed}s): {short(response)}")
        append_monitor(monitor_path, "")
        json_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "started_at": datetime.fromtimestamp(started, timezone.utc).isoformat(),
                    "updated_at": now_iso(),
                    "target_minutes": args.duration_minutes,
                    "mode": "codex_supervised_everyday_chat",
                    "records": records,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        time.sleep(min(args.pause_seconds, remaining))

    append_monitor(monitor_path, f"- finished_at: {now_iso()}")
    append_monitor(monitor_path, f"- turns: {len(records)}")
    print(json.dumps({"json": str(json_path), "monitor": str(monitor_path), "turns": len(records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
