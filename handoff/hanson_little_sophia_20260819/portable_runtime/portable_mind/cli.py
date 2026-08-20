from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .backends import (
    BackendResponseError,
    BackendUnavailable,
    DEFAULT_MODEL,
    DEFAULT_MODEL_DIGEST,
    DEFAULT_OLLAMA_URL,
    ModelDigestMismatch,
    OllamaBackend,
    build_backend,
)
from .bootstrap import bootstrap_private_handoff
from .embodiment import ALLOWED_CAPABILITIES, EmbodimentError
from .evaluator import EVALUATION_BOUNDARY, run_public_safe_evaluation
from .paths import default_data_root
from .profiles import available_profiles
from .runtime import ConversationRuntime, REFLECTION_DISCLOSURE
from .records import stable_event_id, utc_now
from .transfer import (
    export_reviewed_continuity,
    import_hanson_review_seed,
    import_reviewed_continuity,
    import_reviewed_seed,
)
from .voice import VoiceRouter, load_original_voice_profile, load_voice_pack, verify_voice_environment


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, default=str)


def _configure_console_output() -> None:
    """Keep non-ASCII model text from crashing a narrow Windows console."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="backslashreplace")


def _runtime(args: argparse.Namespace) -> ConversationRuntime:
    backend = build_backend(
        args.backend,
        model=args.model,
        base_url=args.ollama_url,
        expected_digest=args.expected_model_digest,
        timeout=args.timeout,
        response_seed=args.response_seed,
    )
    return ConversationRuntime(args.person, data_root=args.data_dir, backend=backend)


def _speak(runtime: ConversationRuntime, text: str, turn_id: str, args: argparse.Namespace) -> None:
    if args.no_voice:
        return
    def announce_fallback(reason: str) -> None:
        policy = runtime.profile.voice.get("fallback_policy", "text_only")
        if policy == "text_only":
            print(f"[voice pre-play notice: intended voice unavailable; remaining text-only; reason={reason}]")
        else:
            print(
                "[voice pre-play notice: intended voice unavailable; a clearly labeled temporary "
                f"OS fallback will speak; reason={reason}]"
            )

    selected_device = None if args.voice_device == "auto" else args.voice_device
    result = VoiceRouter(runtime.sandbox, device=selected_device).speak(
        text,
        runtime.profile,
        voice_profile_id=args.voice_profile,
        before_fallback=announce_fallback,
    )
    playback_attempt_id = uuid.uuid4().hex
    runtime.voice_events.append_exact_or_verify(
        {
            "schema_version": 1,
            "event_id": stable_event_id(
                "voice-playback", runtime.profile_id, runtime.branch_id, turn_id, playback_attempt_id
            ),
            "timestamp": utc_now(),
            "profile_id": runtime.profile_id,
            "branch_id": runtime.branch_id,
            "turn_id": turn_id,
            "parent_turn_event_id": stable_event_id("turn", runtime.profile_id, turn_id),
            "playback_attempt_id": playback_attempt_id,
            "route": result.route,
            "voice_profile_id": result.voice_profile_id,
            "spoken": result.spoken,
            "reference_hash_verified": result.reference_hash_verified,
            "reference_wav_sha256": result.reference_wav_sha256,
            "provider_id": result.provider_id,
            "package_version": result.package_version,
            "model_repository": result.model_repository,
            "model_revision": result.model_revision,
            "authorization_record_sha256": result.authorization_record_sha256,
            "authorization_scope": result.authorization_scope,
            "quality_review_status": result.quality_review_status,
            "generated_audio_retained": result.generated_audio_retained,
            "generated_audio_path": result.generated_audio_path,
            "fallback_reason": result.fallback_reason,
            "boundary": result.boundary,
        }
    )
    print(
        f"[voice route={result.route} profile={result.voice_profile_id} "
        f"spoken={str(result.spoken).lower()} message={result.message}]"
    )
    if result.fallback_reason:
        print(f"[voice fallback reason: {result.fallback_reason}]")


def _show_response(runtime: ConversationRuntime, response: Any, args: argparse.Namespace) -> None:
    print(f"\n{runtime.profile.display_name}: {response.speech}")
    print(
        f"[backend={response.backend} model={response.model} "
        f"digest={response.model_digest or 'not-applicable'} "
        f"digest_kind={response.model_digest_kind} loop={response.loop_id}]"
    )
    if response.fallback_reason:
        print(f"[model fallback: {response.fallback_reason}]")
    if response.embodiment_intentions:
        kinds = ", ".join(item["kind"] for item in response.embodiment_intentions)
        print(f"[high-level embodiment intentions recorded: {kinds}; none executed]")
    _speak(runtime, response.speech, response.turn_id, args)


def _chat_help() -> None:
    print(
        "Commands: /help, /quit, /logs CHANNEL [N], /state, /bind ENDPOINT [CAPS], "
        "/unbind, /new-loop, /close-loop, /remember NOTE. Channels: spoken, reflection, facts, state, "
        "loops, consolidations, imports, voice, people. Ordinary full utterances are not retained; "
        "'my name is' labels and explicit /remember notes are narrow disclosed exceptions."
    )


def command_chat(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    try:
        return _command_chat_loop(runtime, args)
    finally:
        # A strict-backend outage, Ctrl-C, or unexpected exception must not
        # strand an active life loop. This close is idempotently skipped after
        # the normal /quit path or an explicit /close-loop.
        if runtime.life_loops.current() is not None:
            try:
                runtime.close_life_loop("cli_exit_after_error_or_interrupt")
            except (ValueError, OSError):
                pass


def _command_chat_loop(runtime: ConversationRuntime, args: argparse.Namespace) -> int:
    loop_id = runtime.begin_life_loop()
    print(
        f"{runtime.profile.display_name} persistent local runtime; life loop {loop_id}. "
        "Type /help for commands. Voice playback is on unless --no-voice is used."
    )
    _chat_help()
    while True:
        try:
            user_text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            user_text = "/quit"
        if not user_text:
            continue
        if user_text == "/quit":
            try:
                consolidation = runtime.close_life_loop("clean_cli_exit")
                print(f"Life loop consolidated: {consolidation['event_id']}")
            except ValueError:
                pass
            return 0
        if user_text == "/help":
            _chat_help()
            continue
        if user_text == "/state":
            print(_json(runtime.functional_state().as_record()))
            continue
        if user_text.startswith("/logs "):
            parts = user_text.split()
            channel = parts[1]
            tail = int(parts[2]) if len(parts) > 2 else 10
            if channel == "reflection":
                print(REFLECTION_DISCLOSURE)
            print(_json(runtime.channel(channel).tail(tail)))
            continue
        if user_text.startswith("/bind "):
            parts = user_text.split()
            endpoint = parts[1]
            capabilities = tuple(parts[2].split(",")) if len(parts) > 2 else tuple(sorted(ALLOWED_CAPABILITIES))
            try:
                print(_json(asdict(runtime.embodiment.bind(runtime.profile_id, endpoint, capabilities))))
            except EmbodimentError as exc:
                print(f"Binding refused: {exc}")
            continue
        if user_text == "/unbind":
            try:
                print(f"Released: {runtime.embodiment.release(runtime.profile_id)}")
            except EmbodimentError as exc:
                print(f"Release refused: {exc}")
            continue
        if user_text == "/close-loop":
            print(_json(runtime.close_life_loop("explicit_cli_close")))
            continue
        if user_text == "/new-loop":
            if runtime.life_loops.current() is not None:
                runtime.close_life_loop("explicit_cli_new_loop")
            print(f"New life loop: {runtime.begin_life_loop()}")
            continue
        if user_text.startswith("/remember "):
            note = user_text[len("/remember ") :].strip()
            try:
                record = runtime.remember_reviewed_note(
                    note,
                    reviewed_by="interactive_user_explicit_command",
                    confirmed_reviewed=True,
                )
                print(
                    "Reviewed local continuity note retained. It remains a sourced claim, not automatic truth: "
                    f"{record['event_id']}"
                )
            except ValueError as exc:
                print(f"Reviewed note refused: {exc}")
            continue
        try:
            _show_response(runtime, runtime.interact(user_text), args)
        except ModelDigestMismatch as exc:
            print(f"Model integrity failure; no fallback used: {exc}")
        except (BackendUnavailable, BackendResponseError) as exc:
            print(f"Local model turn failed safely; the life loop remains usable: {type(exc).__name__}: {exc}")


def command_say(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    response = runtime.interact(args.text, turn_id=args.turn_id)
    _show_response(runtime, response, args)
    return 0


def command_logs(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    if args.channel == "reflection":
        print(REFLECTION_DISCLOSURE)
    print(_json(runtime.channel(args.channel).tail(args.tail)))
    return 0


def command_bind(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    session = runtime.embodiment.bind(runtime.profile_id, args.endpoint, tuple(args.capabilities))
    print(_json(asdict(session)))
    return 0


def command_unbind(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    print(_json({"released": runtime.embodiment.release(runtime.profile_id)}))
    return 0


def command_remember(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    record = runtime.remember_reviewed_note(
        args.text,
        reviewed_by=args.reviewed_by,
        confirmed_reviewed=args.confirm_reviewed,
        supersedes_event_ids=tuple(args.supersedes_event_id),
    )
    print(_json(record))
    return 0


def _parse_selections(values: list[str]) -> dict[str, list[str]]:
    selections: dict[str, list[str]] = {}
    for value in values:
        if ":" not in value:
            raise ValueError("selection must be CHANNEL:EVENT_ID")
        channel, event_id = value.split(":", 1)
        selections.setdefault(channel, []).append(event_id)
    return selections


def command_export(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    destination = export_reviewed_continuity(
        runtime,
        _parse_selections(args.select),
        reviewer=args.reviewed_by,
        confirmed_reviewed=args.confirm_reviewed,
        filename=args.filename,
    )
    print(destination)
    return 0


def command_import(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    imported = import_reviewed_continuity(
        runtime,
        filename=args.filename,
        approve_import=args.approve_import,
    )
    print(_json({"imported": imported, "profile_id": runtime.profile_id}))
    return 0


def command_seed_import(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    imported = import_reviewed_seed(
        runtime,
        filename=args.filename,
        approve_import=args.approve_import,
    )
    print(_json({"seed_items_imported": imported, "profile_id": runtime.profile_id}))
    return 0


def command_hanson_seed_import(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    imported = import_hanson_review_seed(
        runtime,
        filename=args.filename,
        approve_import=args.approve_import,
    )
    print(_json({"hanson_seed_items_imported": imported, "profile_id": runtime.profile_id}))
    return 0


def command_bootstrap_handoff(args: argparse.Namespace) -> int:
    if args.person not in {"kira", "synthetic_robert"}:
        raise ValueError("private handoff bootstrap supports only Kira and Synthetic Robert")
    runtime = _runtime(args)
    result = bootstrap_private_handoff(
        runtime,
        handoff_root=args.handoff_root,
        approve_private_bootstrap=args.approve_private_bootstrap,
    )
    print(_json(asdict(result)))
    return 0


def command_model_info(args: argparse.Namespace) -> int:
    backend = OllamaBackend(
        model=args.model,
        base_url=args.ollama_url,
        expected_digest=args.expected_model_digest,
        timeout=args.timeout,
    )
    print(_json(backend.model_info()))
    return 0


def command_voice_check(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    selected = args.voice_profile or str(
        runtime.profile.voice.get("default_voice_profile", runtime.profile_id)
    )
    if selected == "kira_original":
        profile = load_original_voice_profile(runtime.profile_id)
        result = {
            "voice_profile_id": selected,
            "identity_profile_id": runtime.profile_id,
            "route": "chatterbox_original_unconditioned",
            "default": False,
            "audio_prompt_used": False,
            "target_person_imitation": False,
            "provider_id": profile.provider_id,
            "package_version": profile.package_version,
            "model_repository": profile.model_repo,
            "model_revision": profile.model_revision,
            "listening_review_status": profile.listening_review_status,
            "integrity": "profile/provenance manifest validated; model-file hashes require voice-env-check",
        }
    else:
        pack = load_voice_pack(runtime.sandbox, selected, runtime.profile_id)
        result = {
            "voice_profile_id": selected,
            "identity_profile_id": runtime.profile_id,
            "installed": pack is not None,
            "reference_hash_verified": bool(pack),
            "provider": pack.provider if pack else None,
            "reference_wav_sha256": pack.reference_wav_sha256 if pack else None,
            "authorization_record_sha256": pack.authorization_record_sha256 if pack else None,
            "authorization_scope": pack.authorization_scope if pack else None,
            "quality_review_status": pack.quality_review_status if pack else None,
        }
    print(_json(result))
    return 0


def command_voice_environment(args: argparse.Namespace) -> int:
    status = verify_voice_environment(allow_download=args.allow_download)
    print(_json(status))
    return 0 if status["valid"] else 2


def command_evaluate(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    print(EVALUATION_BOUNDARY)
    summary = run_public_safe_evaluation(
        runtime,
        rounds=args.rounds,
        duration_minutes=args.duration_minutes,
    )
    print(_json(asdict(summary)))
    return 0


def _common_parser() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--person", choices=available_profiles(), required=True)
    parent.add_argument(
        "--data-dir",
        default=os.environ.get("PORTABLE_MIND_DATA_DIR", str(default_data_root())),
    )
    parent.add_argument("--backend", choices=("auto", "ollama", "stub"), default="auto")
    parent.add_argument("--model", default=os.environ.get("PORTABLE_MIND_MODEL", DEFAULT_MODEL))
    parent.add_argument(
        "--expected-model-digest",
        default=os.environ.get("PORTABLE_MIND_EXPECTED_MODEL_DIGEST", DEFAULT_MODEL_DIGEST),
    )
    parent.add_argument(
        "--ollama-url",
        default=os.environ.get("PORTABLE_MIND_OLLAMA_URL", DEFAULT_OLLAMA_URL),
    )
    parent.add_argument("--timeout", type=float, default=5.0)
    response_seed = os.environ.get("PORTABLE_MIND_RESPONSE_SEED")
    parent.add_argument(
        "--response-seed",
        type=int,
        default=int(response_seed) if response_seed is not None else None,
        help="optional deterministic Ollama sampling seed; live chat varies naturally when omitted",
    )
    return parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="portable-mind",
        description="Persistent bounded Kira, Synthetic Robert, and independent Synthetic Sophia runtime.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    common = _common_parser()

    chat = commands.add_parser("chat", parents=[common], help="interactive persistent chat")
    chat.add_argument("--voice-profile")
    chat.add_argument(
        "--voice-device",
        choices=("auto", "cpu", "cuda", "mps"),
        default=os.environ.get("PORTABLE_MIND_VOICE_DEVICE", "auto"),
    )
    chat.add_argument("--no-voice", action="store_true", help="disable otherwise-default local playback")
    chat.set_defaults(func=command_chat)

    say = commands.add_parser("say", parents=[common], help="one conversational turn")
    say.add_argument("--text", required=True)
    say.add_argument("--turn-id")
    say.add_argument("--voice-profile")
    say.add_argument(
        "--voice-device",
        choices=("auto", "cpu", "cuda", "mps"),
        default=os.environ.get("PORTABLE_MIND_VOICE_DEVICE", "auto"),
    )
    say.add_argument("--no-voice", action="store_true")
    say.set_defaults(func=command_say)

    logs = commands.add_parser("logs", parents=[common], help="safely view a local channel")
    logs.add_argument(
        "--channel",
        choices=("spoken", "reflection", "facts", "state", "loops", "consolidations", "imports", "voice", "people"),
        required=True,
    )
    logs.add_argument("--tail", type=int, default=20)
    logs.set_defaults(func=command_logs)

    bind = commands.add_parser("bind", parents=[common], help="bind one high-level endpoint")
    bind.add_argument("--endpoint", required=True)
    bind.add_argument("--capabilities", nargs="+", choices=sorted(ALLOWED_CAPABILITIES), default=sorted(ALLOWED_CAPABILITIES))
    bind.set_defaults(func=command_bind)

    unbind = commands.add_parser("unbind", parents=[common], help="release this profile's endpoint")
    unbind.set_defaults(func=command_unbind)

    remember = commands.add_parser(
        "remember",
        parents=[common],
        help="append one explicitly reviewed local continuity note",
    )
    remember.add_argument("--text", required=True)
    remember.add_argument("--reviewed-by", required=True)
    remember.add_argument("--confirm-reviewed", action="store_true")
    remember.add_argument("--supersedes-event-id", action="append", default=[])
    remember.set_defaults(func=command_remember)

    export = commands.add_parser("export", parents=[common], help="export selected reviewed continuity")
    export.add_argument("--select", action="append", required=True, help="CHANNEL:EVENT_ID")
    export.add_argument("--reviewed-by", required=True)
    export.add_argument("--confirm-reviewed", action="store_true")
    export.add_argument("--filename", required=True)
    export.set_defaults(func=command_export)

    import_command = commands.add_parser("import", parents=[common], help="import reviewed continuity")
    import_command.add_argument("--filename", required=True, help="simple filename already placed in local_data/imports")
    import_command.add_argument("--approve-import", action="store_true")
    import_command.set_defaults(func=command_import)

    seed_import = commands.add_parser("seed-import", parents=[common], help="import an identity-bound reviewed seed")
    seed_import.add_argument("--filename", required=True, help="simple filename already placed in local_data/imports")
    seed_import.add_argument("--approve-import", action="store_true")
    seed_import.set_defaults(func=command_seed_import)

    hanson_seed = commands.add_parser(
        "hanson-seed-import",
        parents=[common],
        help="strictly convert the named-private-reviewer KiraWorld seed",
    )
    hanson_seed.add_argument("--filename", required=True, help="simple filename already placed in local_data/imports")
    hanson_seed.add_argument("--approve-import", action="store_true")
    hanson_seed.set_defaults(func=command_hanson_seed_import)

    bootstrap = commands.add_parser(
        "bootstrap-handoff",
        parents=[common],
        help="explicitly install reviewed memories and authorized voice into ignored local_data",
    )
    bootstrap.add_argument("--handoff-root", required=True)
    bootstrap.add_argument("--approve-private-bootstrap", action="store_true")
    bootstrap.set_defaults(func=command_bootstrap_handoff)

    model_info = commands.add_parser("model-info", parents=[common], help="show and verify local Ollama digest")
    model_info.set_defaults(func=command_model_info)

    voice_check = commands.add_parser("voice-check", parents=[common], help="validate selected voice profile")
    voice_check.add_argument("--voice-profile")
    voice_check.set_defaults(func=command_voice_check)

    voice_environment = commands.add_parser(
        "voice-env-check",
        parents=[common],
        help="verify Python/package/model hashes for the pinned Chatterbox route",
    )
    voice_environment.add_argument("--allow-download", action="store_true")
    voice_environment.set_defaults(func=command_voice_environment)

    evaluate = commands.add_parser("evaluate", parents=[common], help="bounded nonclinical behavioral checks")
    evaluate.add_argument("--rounds", type=int, default=1)
    evaluate.add_argument("--duration-minutes", type=float)
    evaluate.set_defaults(func=command_evaluate)
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_console_output()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
