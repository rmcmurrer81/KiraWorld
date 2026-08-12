"""Prepare a private, fact-gated Video Studio intake for Robert's movie review.

This creates a normal v2 project through ``StudioController``.  It deliberately
does not write a review, synthesize narration, acquire footage, render, publish,
or infer spoilers before Robert supplies his firsthand notes.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


STAGING = Path(r"C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1")
if str(STAGING) not in sys.path:
    sys.path.insert(0, str(STAGING))

from kira_video_studio.project_store import atomic_write_json, save_project  # noqa: E402
from kira_video_studio.settings import load_settings  # noqa: E402
from kira_video_studio.ui import StudioController  # noqa: E402


SUBJECT = "Spider-Man: Brand New Day — Robert's spoiler review"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def main() -> int:
    settings = load_settings(STAGING)
    controller = StudioController(staging_root=STAGING, settings=settings)
    project_dir = controller.create_project(
        "custom_video",
        SUBJECT,
        request_overrides={
            "research_mode": "automatic",
            "tone": "personal_documentary_review",
            "target_audience": "movie and MCU viewers who accept clearly warned spoilers",
            "desired_length": "medium_long",
            "approximate_chapter_count": 9,
            "fact_strictness": "strict",
            "source_recency": "current_when_relevant",
            "number_of_sources": 10,
            "robert_notes": (
                "AWAITING ROBERT'S FIRSTHAND MOVIE NOTES. Do not generate a review, "
                "script, narration, or edit until Robert supplies what he saw, his "
                "opinions, and the spoilers he wants discussed."
            ),
            "required_talking_points": [
                "spoiler warning before plot details",
                "Robert's overall reaction and rating",
                "story and major character arcs from Robert's notes",
                "performances and filmmaking",
                "MCU and Spider-Man continuity implications",
                "clearly separated verified facts, Robert observations, and theories",
            ],
            "subjects_or_rumors_to_include": [
                "Any role or future-X-Men theory Robert raises, but only as a labeled theory unless an official source confirms it"
            ],
            "subjects_to_avoid": [
                "invented plot details",
                "unverified actor-to-character claims presented as fact",
                "mismatched footage presented as the reviewed movie",
                "spoilers before the warning",
                "unlicensed or unattributed media",
            ],
            "automatic_visuals": True,
            "concept_visual_fallback_enabled": False,
            "animation_storyboard_enabled": True,
            "trailer_video_use": True,
            "voice_selection": "robert_approved_chatterbox",
            "captions": True,
            "private_review_watermark": False,
            "output_profiles": ["landscape_16_9"],
        },
        preset_options={
            "module_outline": [
                "spoiler_free_owner_verdict",
                "spoken_and_visible_spoiler_warning",
                "owner_observed_story_and_character_review",
                "craft_and_performance_review",
                "verified_continuity_context",
                "clearly_labeled_theories",
                "final_owner_verdict",
            ],
            "publication_guard_required": True,
            "release_status": "upcoming_owner_screening_intake",
            "owner_firsthand_review_required": True,
            "spoiler_warning_required": True,
            "actor_character_identity_check_required": True,
            "owner_screening_evidence_supported": True,
            "owner_evidence_provenance_is_private_metadata": True,
            "owner_confirmed_screening_facts_may_be_narrated_directly": True,
            "official_confirmation_language_requires_official_public_source": True,
        },
    )
    project = controller.project
    if project is None:
        raise RuntimeError("StudioController did not retain the created project")

    now = datetime.now(timezone.utc).isoformat()
    project["status"]["workflow_stage"] = "research"
    project["status"]["project_readiness"] = "AWAITING_ROBERT_OWNER_NOTES"
    project["status"]["blocked_reasons"] = [
        "Robert's firsthand movie notes and opinions have not been supplied.",
        "Spoiler claims cannot be independently inferred before owner intake.",
        "Actor-to-character claims require official verification; Sadie Sink's official cast listing does not by itself establish that she plays Jean Grey.",
        "No footage may be selected until exact scene/claim matching and rights review are recorded.",
    ]
    project["review"]["project_status"] = "AWAITING_ROBERT_OWNER_NOTES"
    project["review"]["owner_notes_received"] = False
    project["review"]["script_status"] = "blocked_owner_notes_required"
    project["review"]["source_status"] = "official_seed_sources_only"
    project["review"]["render_status"] = "not_started"
    project["publication_enabled"] = False

    project["owner_review_intake"] = {
        "status": "AWAITING_ROBERT_OWNER_NOTES",
        "firsthand_observation_channel": "Robert's own screening notes",
        "required_sections": [
            "spoiler-free quick reaction",
            "rating or overall verdict",
            "plot beats Robert wants discussed",
            "character and performance notes",
            "what worked",
            "what did not work",
            "specific scenes or dialogue Robert remembers",
            "continuity implications",
            "theories or casting interpretations",
            "ending and post-credit details",
        ],
        "classification_rule": {
            "PUBLIC_VERIFIED_SOURCE": "Information supported by an official source or reliable publication.",
            "OWNER_FIRSTHAND_SCREENING_NOTE": "What Robert personally reports seeing or hearing; valid private evidence that remains unconfirmed until Robert explicitly confirms the fact status.",
            "OWNER_CONFIRMED_SCREENING_FACT": "A firsthand fact Robert explicitly confirms was clearly shown, stated, named in dialogue, or identified in credits.",
            "OWNER_INTERPRETATION": "Robert's conclusion or theory when the movie implies something without explicitly establishing it.",
            "UNVERIFIED_PUBLIC_RUMOR": "An online claim that lacks sufficient confirmation and is not eligible as a factual script source.",
        },
        "spoken_script_rule": (
            "Provenance stays in private metadata. A confirmed screening fact may "
            "be stated directly without saying 'according to Robert'; interpretations "
            "must remain hedged. Do not claim official Marvel/Sony/etc. confirmation "
            "without a linked official public source."
        ),
        "spoiler_rule": "Open with a spoiler-free reaction, give a prominent spoken/on-screen warning, then begin the spoiler section.",
    }
    project["editorial_plan"] = {
        "video_style": "Robert-voiced movie review with matched moving footage first and strong stills when correct video is unavailable",
        "provisional_chapters": [
            "Opening title and spoiler-free verdict",
            "Spoiler warning",
            "Where Peter begins",
            "Story and major turns",
            "Characters and performances",
            "Villains, conflict, and action",
            "MCU continuity and earlier Spider-Man connections",
            "Theories and future implications — clearly labeled",
            "Final verdict",
        ],
        "visual_priority": [
            "official Brand New Day trailer/featurette footage matched to the exact claim",
            "official Brand New Day posters and promotional stills",
            "rights-reviewed stills or clips from earlier MCU Spider-Man films for explicitly labeled continuity context",
            "rights-reviewed prior Jean Grey animation only if Robert discusses Jean Grey as contextual comparison, never as proof of Sadie Sink's role",
            "clean labeled cards or diagrams when no accurate rights-cleared visual exists",
        ],
        "audio_policy": {
            "narration": "continuous Robert narration wherever planned",
            "source_audio": "deliberate excerpts only",
            "ducking": "source audio ducked beneath Robert narration",
            "silence": "no unintended silence",
        },
        "quality_gates": [
            "fact gate passes before voice generation",
            "every spoiler/plot claim maps to Robert's exact owner note",
            "actor/character identity gate passes",
            "every clip maps to exact source and in/out time",
            "visual remains on the correct movie/character as narration changes",
            "audio and video durations match",
            "full MP4 decodes to the end",
            "captions and chapters measured from encoded output",
        ],
    }
    official_sources = [
        {
            "source_id": "sony_official_movie_page",
            "url": "https://www.sonypictures.com/movies/spidermanbrandnewday",
            "publisher": "Sony Pictures Entertainment",
            "authority": "official",
            "purpose": "official synopsis, credits, cast, and theatrical date",
            "acquisition_status": "seed_only_not_downloaded",
            "retrieved_at_utc": now,
        },
        {
            "source_id": "marvel_official_movie_page",
            "url": "https://www.marvel.com/movies/spider-man-brand-new-day",
            "publisher": "Marvel",
            "authority": "official",
            "purpose": "official overview, release date, trailer and poster hub",
            "acquisition_status": "seed_only_not_downloaded",
            "retrieved_at_utc": now,
        },
        {
            "source_id": "sony_official_trailer_uk",
            "url": "https://www.youtube.com/watch?v=qwVAc2MmlwU",
            "publisher": "Sony Pictures Releasing UK",
            "authority": "official_verified_channel",
            "purpose": "candidate moving footage; download/use requires source and rights review",
            "acquisition_status": "seed_only_not_downloaded",
            "retrieved_at_utc": now,
        },
    ]
    project["sources"]["research_queries"] = [
        "official Spider-Man Brand New Day cast character roles Sony Marvel",
        "official Spider-Man Brand New Day trailers featurettes clips",
        "official Spider-Man Brand New Day production notes",
        "official post-release cast and filmmaker interviews",
        "Robert owner notes exact claims and spoiler timestamps",
    ]
    project["sources"]["records"] = official_sources
    project["sources"]["owner_evidence"] = []
    project["sources"]["owner_evidence_policy"] = {
        "schema_version": 1,
        "evidence_classes": [
            "PUBLIC_VERIFIED_SOURCE",
            "OWNER_FIRSTHAND_SCREENING_NOTE",
            "OWNER_CONFIRMED_SCREENING_FACT",
            "OWNER_INTERPRETATION",
            "UNVERIFIED_PUBLIC_RUMOR",
        ],
        "raw_firsthand_requires_owner_attestation": True,
        "confirmed_fact_requires_explicit_shown_stated_named_or_credited_confirmation": True,
        "internal_provenance_requires_spoken_attribution": False,
        "confirmed_screening_fact_direct_narration_allowed": True,
        "interpretation_requires_hedged_wording": True,
        "official_confirmation_language_requires_linked_official_source": True,
        "later_corroboration_preserves_original_note_hash_and_timestamp": True,
    }
    project["sources"]["fact_sheet"]["status"] = "blocked_owner_notes_required"
    project["sources"]["fact_sheet"]["uncertainties"] = [
        {
            "claim": "Sadie Sink plays Jean Grey",
            "status": "UNVERIFIED_CLAIM",
            "reason": "Official Sony materials currently list Sadie Sink in the cast but do not identify her role.",
            "script_policy": "omit as fact; include only as Robert's labeled theory unless an official role source confirms it",
        }
    ]

    intake_path = project_dir / "review" / "OWNER_SPOILER_REVIEW_INTAKE.md"
    write_text(
        intake_path,
        """# Spider-Man: Brand New Day — Robert owner-review intake

Status: AWAITING ROBERT OWNER NOTES

Paste or dictate your notes in Video Studio's **Robert notes** field, or fill
this file and reopen the project. The Studio must preserve your exact meaning
and classify each item as a firsthand note, an explicitly confirmed screening
fact, or an interpretation. Public background claims still require public
sources. Internal provenance does not have to be repeated in the narration.

## Spoiler-free reaction

- Overall reaction:
- Rating, if you want one:
- Best spoiler-free reason to watch or skip:

## Spoiler section

- Plot beats you want covered:
- Ending:
- Post-credit scene(s):

## Characters and performances

- Peter / Spider-Man:
- Returning characters:
- New characters:
- Best performance:
- Weakest or least convincing part:

## What worked

-

## What did not work

-

## Continuity and future theories

- MCU connections:
- Earlier Spider-Man connections:
- X-Men/Jean Grey or other casting interpretation:
- What is observation, what is opinion, and what is only a theory:

## Exact visual moments worth finding

- Scene or trailer moment:
- Character on screen:
- What narration it should support:
- Keep or mute source audio:

## Anything the Studio must avoid

-
""",
    )
    readiness_path = project_dir / "review" / "PROJECT_READINESS.json"
    atomic_write_json(
        readiness_path,
        {
            "schema_version": 1,
            "project_status": "AWAITING_ROBERT_OWNER_NOTES",
            "safe_to_research_official_sources": True,
            "safe_to_generate_script": False,
            "safe_to_generate_voice": False,
            "safe_to_acquire_or_select_media": False,
            "safe_to_render": False,
            "safe_to_publish": False,
            "next_owner_action": "Open this v2 project and supply firsthand review/spoiler notes.",
            "required_after_notes": [
                "extract and classify owner claims",
                "run official-source research",
                "verify actor/character identities",
                "build claim ledger and final fact audit",
                "present script and visual choices for review",
                "render only after the normal gates pass",
            ],
        },
    )
    source_seed_path = project_dir / "research" / "OFFICIAL_SOURCE_SEED.json"
    atomic_write_json(
        source_seed_path,
        {
            "schema_version": 1,
            "created_at_utc": now,
            "sources": official_sources,
            "role_guard": {
                "claim": "Sadie Sink plays Jean Grey",
                "decision": "UNVERIFIED_CLAIM",
                "rule": "A cast listing is not a character-role confirmation.",
            },
        },
    )
    project["artifacts"]["owner_spoiler_review_intake"] = str(
        intake_path.relative_to(project_dir)
    ).replace("\\", "/")
    project["artifacts"]["project_readiness"] = str(
        readiness_path.relative_to(project_dir)
    ).replace("\\", "/")
    project["artifacts"]["official_source_seed"] = str(
        source_seed_path.relative_to(project_dir)
    ).replace("\\", "/")
    save_project(project_dir, project)

    manifest_rows = []
    for path in (project_dir / "project.v2.json", intake_path, readiness_path, source_seed_path):
        manifest_rows.append(
            {
                "path": str(path.relative_to(project_dir)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    manifest_path = project_dir / "manifests" / "INTAKE_PACKAGE_MANIFEST.json"
    atomic_write_json(
        manifest_path,
        {
            "schema_version": 1,
            "status": "AWAITING_ROBERT_OWNER_NOTES",
            "publication_performed": False,
            "files": manifest_rows,
        },
    )
    print(
        json.dumps(
            {
                "status": "PASSED",
                "project_dir": str(project_dir),
                "project_status": "AWAITING_ROBERT_OWNER_NOTES",
                "publication_performed": False,
                "script_created": False,
                "media_acquired": False,
                "render_created": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
