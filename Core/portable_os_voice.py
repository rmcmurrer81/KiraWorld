"""Portable, explicitly labeled operating-system voice fallback.

This module is intentionally separate from Kira's and Robert's approved voice
routes.  A caller must try a valid character-specific voice pack first.  When
none is usable, this module can discover an installed, offline operating-system
text-to-speech command and speak with a generic voice.  It never downloads a
model, clones a person, or represents the selected voice as authentic.

Discovery is fail-closed: a command merely being named in a profile is not
enough.  Windows must report an enabled System.Speech voice, macOS ``say`` must
list an installed voice, and Linux must expose either an installed eSpeak voice
or an installed Speech Dispatcher client.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any, Callable, Mapping, Sequence

from Core.synthetic_robert_voice_route import (
    is_synthetic_robert_persistent_identity,
)


_SPEECH_LOCK = threading.Lock()


@dataclass(frozen=True)
class OSVoiceRoute:
    """One verified local OS TTS route.

    ``voice_name`` is an installed OS voice or a documented generic voice
    selector.  It is never a character identity or a custom voice-pack claim.
    """

    available: bool
    platform: str
    backend: str = ""
    executable: str = ""
    voice_name: str = ""
    gender_preference: str = ""
    selection_basis: str = ""
    reason: str = ""
    installed_voice_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_gender(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"m", "man", "masculine", "male"}:
        return "male"
    if normalized in {"f", "woman", "feminine", "female"}:
        return "female"
    return ""


def candidate_os_voice_preferences(
    candidate: Mapping[str, Any] | None,
    voice_profile: Mapping[str, Any] | None = None,
) -> tuple[str, str]:
    """Return ``(gender, preferred_windows_voice)`` for a fallback route.

    The H. H. Holmes name mapping is deliberately explicit because the owner
    requested the generic male Windows voice previously used for that
    historical reconstruction.  A SAPI approximation may choose an installed
    Windows voice, but it remains an OS fallback rather than a custom pack.
    """

    candidate = candidate or {}
    profile = candidate.get("profile")
    if not isinstance(profile, Mapping):
        profile = candidate
    gender = normalize_gender(profile.get("gender_preference"))

    candidate_id = str(
        candidate.get("candidate_id") or profile.get("candidate_id") or ""
    ).strip().lower()
    if candidate_id == "h_h_holmes_h_h_holmes_20260605_221432":
        gender = "male"

    preferred_windows_voice = ""
    if isinstance(voice_profile, Mapping):
        approximation = voice_profile.get("sapi_approximation")
        if isinstance(approximation, Mapping):
            preferred_windows_voice = str(
                approximation.get("voice_name") or ""
            ).strip()
    if not preferred_windows_voice and gender == "male":
        preferred_windows_voice = "Microsoft David Desktop"
    elif not preferred_windows_voice and gender == "female":
        preferred_windows_voice = "Microsoft Zira Desktop"
    return gender, preferred_windows_voice


def is_synthetic_robert_persistent_runtime(candidate: Mapping[str, Any] | None) -> bool:
    """Keep Synthetic Robert out of TemporaryAI/generic voice routing."""

    return is_synthetic_robert_persistent_identity(candidate)


def _platform_family(platform_name: str | None) -> str:
    value = str(platform_name if platform_name is not None else sys.platform).lower()
    if value.startswith("win"):
        return "windows"
    if value == "darwin" or value.startswith("mac"):
        return "macos"
    if value.startswith("linux"):
        return "linux"
    return value or "unknown"


def _find_executable(
    candidates: Sequence[str],
    which: Callable[[str], str | None],
) -> str:
    for candidate in candidates:
        found = which(candidate)
        if found:
            return str(found)
    return ""


def _run_probe(
    run: Callable[..., Any],
    args: list[str],
    *,
    timeout: int = 8,
) -> tuple[Any | None, str]:
    try:
        completed = run(
            args,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"probe_error:{type(exc).__name__}:{exc}"
    if int(getattr(completed, "returncode", 1)) != 0:
        stderr = str(getattr(completed, "stderr", "") or "").strip()
        return completed, f"probe_failed:{stderr or 'nonzero_exit'}"
    return completed, ""


def _windows_voices(
    executable: str,
    run: Callable[..., Any],
) -> tuple[list[dict[str, str]], str, str]:
    script = (
        "$ErrorActionPreference='Stop';"
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$v=@($s.GetInstalledVoices()|Where-Object {$_.Enabled}|ForEach-Object {"
        "[pscustomobject]@{name=$_.VoiceInfo.Name;gender=[string]$_.VoiceInfo.Gender;"
        "culture=[string]$_.VoiceInfo.Culture}});"
        "$s.Dispose();$v|ConvertTo-Json -Compress"
    )
    completed, reason = _run_probe(
        run,
        [executable, "-NoProfile", "-NonInteractive", "-Command", script],
    )
    backend = "windows_system_speech"
    output = "" if reason else str(getattr(completed, "stdout", "") or "").strip()
    if reason or not output:
        # Some otherwise healthy Windows installations expose desktop voices
        # through legacy SAPI COM while System.Speech.GetInstalledVoices raises
        # a null-reference exception.  Probe that built-in API before declaring
        # voice unavailable; no speech is produced by either probe.
        com_script = (
            "$ErrorActionPreference='Stop';"
            "$s=New-Object -ComObject SAPI.SpVoice;"
            "$v=@($s.GetVoices()|ForEach-Object {"
            "[pscustomobject]@{name=$_.GetDescription();gender=$_.GetAttribute('Gender');"
            "culture=$_.GetAttribute('Language')}});"
            "$v|ConvertTo-Json -Compress"
        )
        com_completed, com_reason = _run_probe(
            run,
            [executable, "-NoProfile", "-NonInteractive", "-Command", com_script],
        )
        if com_reason:
            return [], "windows_sapi_com", f"system_speech:{reason or 'no_voices'};sapi_com:{com_reason}"
        output = str(getattr(com_completed, "stdout", "") or "").strip()
        backend = "windows_sapi_com"
        if not output:
            return [], backend, "windows_sapi_reported_no_installed_voices"
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        return [], backend, f"invalid_windows_voice_probe_json:{exc}"
    if isinstance(payload, Mapping):
        payload = [payload]
    if not isinstance(payload, list):
        return [], backend, "invalid_windows_voice_probe_shape"
    voices: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or item.get("Name") or "").strip()
        if name:
            voices.append(
                {
                    "name": name,
                    "gender": normalize_gender(item.get("gender") or item.get("Gender")),
                    "culture": str(item.get("culture") or item.get("Culture") or "").strip(),
                }
            )
    return voices, backend, "" if voices else "windows_sapi_reported_no_installed_voices"


def _select_voice(
    voices: Sequence[Mapping[str, str]],
    gender: str,
    preferred_name: str,
    preferred_names: Mapping[str, Sequence[str]],
) -> tuple[str, str]:
    by_name = {str(item.get("name") or "").casefold(): item for item in voices}
    if preferred_name and preferred_name.casefold() in by_name:
        return str(by_name[preferred_name.casefold()].get("name") or ""), "exact_preference"
    if preferred_name:
        preferred_folded = preferred_name.casefold()
        for item in voices:
            installed = str(item.get("name") or "")
            installed_folded = installed.casefold()
            if installed_folded.startswith(preferred_folded) or preferred_folded.startswith(installed_folded):
                return installed, "exact_preference"
    for name in preferred_names.get(gender, ()):
        if name.casefold() in by_name:
            return str(by_name[name.casefold()].get("name") or ""), "gender_preference"
        folded = name.casefold()
        for item in voices:
            installed = str(item.get("name") or "")
            if installed.casefold().startswith(folded):
                return installed, "gender_preference"
    if gender:
        for item in voices:
            if normalize_gender(item.get("gender")) == gender:
                return str(item.get("name") or ""), "installed_gender_match"
    if voices:
        return str(voices[0].get("name") or ""), "installed_default"
    return "", ""


def _macos_voices(executable: str, run: Callable[..., Any]) -> tuple[list[dict[str, str]], str]:
    completed, reason = _run_probe(run, [executable, "-v", "?"])
    if reason:
        return [], reason
    voices: list[dict[str, str]] = []
    for raw_line in str(getattr(completed, "stdout", "") or "").splitlines():
        line = raw_line.strip()
        match = re.match(r"^(.+?)\s+([a-z]{2}(?:[_-][A-Z]{2})?)\s+#", line)
        if not match:
            continue
        voices.append({"name": match.group(1).strip(), "gender": "", "culture": match.group(2)})
    return voices, "" if voices else "say_reported_no_installed_voices"


def _espeak_voices(executable: str, run: Callable[..., Any]) -> tuple[list[dict[str, str]], str]:
    completed, reason = _run_probe(run, [executable, "--voices=en"])
    if reason:
        return [], reason
    voices: list[dict[str, str]] = []
    for raw_line in str(getattr(completed, "stdout", "") or "").splitlines():
        fields = raw_line.split()
        if len(fields) < 4 or not fields[0].isdigit():
            continue
        gender_token = fields[2].upper()
        gender = "female" if "F" in gender_token else "male" if "M" in gender_token else ""
        voices.append(
            {
                "name": fields[3],
                "gender": gender,
                "culture": fields[1],
            }
        )
    return voices, "" if voices else "espeak_reported_no_english_voices"


def detect_os_voice_route(
    *,
    gender_preference: str = "",
    preferred_windows_voice: str = "",
    platform_name: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[..., Any] = subprocess.run,
) -> OSVoiceRoute:
    """Discover one installed offline OS voice without producing speech."""

    family = _platform_family(platform_name)
    gender = normalize_gender(gender_preference)
    if family == "windows":
        executable = _find_executable(
            ("powershell.exe", "powershell", "pwsh.exe", "pwsh"), which
        )
        if not executable:
            return OSVoiceRoute(False, family, reason="powershell_not_installed")
        voices, backend, reason = _windows_voices(executable, run)
        if reason:
            return OSVoiceRoute(
                False,
                family,
                backend=backend,
                executable=executable,
                gender_preference=gender,
                reason=reason,
            )
        selected, basis = _select_voice(
            voices,
            gender,
            preferred_windows_voice,
            {
                "male": ("Microsoft David Desktop", "Microsoft Mark Desktop"),
                "female": ("Microsoft Zira Desktop",),
            },
        )
        return OSVoiceRoute(
            bool(selected),
            family,
            backend=backend,
            executable=executable,
            voice_name=selected,
            gender_preference=gender,
            selection_basis=basis,
            reason="" if selected else "no_selectable_system_speech_voice",
            installed_voice_count=len(voices),
        )

    if family == "macos":
        executable = _find_executable(("say",), which)
        if not executable:
            return OSVoiceRoute(False, family, reason="macos_say_not_installed")
        voices, reason = _macos_voices(executable, run)
        if reason:
            return OSVoiceRoute(
                False,
                family,
                backend="macos_say",
                executable=executable,
                gender_preference=gender,
                reason=reason,
            )
        selected, basis = _select_voice(
            voices,
            gender,
            "",
            {
                "male": ("Alex", "Daniel", "Fred"),
                "female": ("Samantha", "Victoria", "Karen"),
            },
        )
        return OSVoiceRoute(
            bool(selected),
            family,
            backend="macos_say",
            executable=executable,
            voice_name=selected,
            gender_preference=gender,
            selection_basis=basis,
            reason="" if selected else "no_selectable_macos_voice",
            installed_voice_count=len(voices),
        )

    if family == "linux":
        espeak = _find_executable(("espeak-ng", "espeak"), which)
        if espeak:
            voices, reason = _espeak_voices(espeak, run)
            if not reason:
                selected, basis = _select_voice(voices, gender, "", {})
                return OSVoiceRoute(
                    bool(selected),
                    family,
                    backend="linux_espeak",
                    executable=espeak,
                    voice_name=selected,
                    gender_preference=gender,
                    selection_basis=basis,
                    reason="" if selected else "no_selectable_espeak_voice",
                    installed_voice_count=len(voices),
                )
        dispatcher = _find_executable(("spd-say",), which)
        if dispatcher:
            completed, dispatcher_reason = _run_probe(run, [dispatcher, "--version"])
            if not dispatcher_reason and completed is not None:
                selector = "male1" if gender == "male" else "female1" if gender == "female" else ""
                return OSVoiceRoute(
                    True,
                    family,
                    backend="linux_spd_say",
                    executable=dispatcher,
                    voice_name=selector,
                    gender_preference=gender,
                    selection_basis="speech_dispatcher_generic_type" if selector else "speech_dispatcher_default",
                    installed_voice_count=1,
                )
            return OSVoiceRoute(
                False,
                family,
                backend="linux_spd_say",
                executable=dispatcher,
                gender_preference=gender,
                reason=dispatcher_reason,
            )
        return OSVoiceRoute(
            False,
            family,
            gender_preference=gender,
            reason="no_supported_installed_linux_tts_command",
        )

    return OSVoiceRoute(
        False,
        family,
        gender_preference=gender,
        reason=f"unsupported_platform:{family}",
    )


def detect_candidate_os_voice_route(
    candidate: Mapping[str, Any] | None,
    voice_profile: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> OSVoiceRoute:
    if is_synthetic_robert_persistent_runtime(candidate):
        return OSVoiceRoute(
            False,
            _platform_family(kwargs.get("platform_name")),
            reason="synthetic_robert_persistent_runtime_voice_route_required",
        )
    gender, preferred_windows_voice = candidate_os_voice_preferences(
        candidate, voice_profile
    )
    return detect_os_voice_route(
        gender_preference=gender,
        preferred_windows_voice=preferred_windows_voice,
        **kwargs,
    )


@lru_cache(maxsize=16)
def _cached_os_voice_route(
    gender_preference: str,
    preferred_windows_voice: str,
) -> OSVoiceRoute:
    return detect_os_voice_route(
        gender_preference=gender_preference,
        preferred_windows_voice=preferred_windows_voice,
    )


def cached_candidate_os_voice_route(
    candidate_id: str,
    display_name: str,
    gender_preference: str,
    preferred_windows_voice: str = "",
) -> OSVoiceRoute:
    """Process-local cached discovery for responsive desktop controls.

    Installed OS voices normally change only between application launches.
    Keeping this cache in memory avoids starting a silent discovery process
    every time the GUI refreshes a candidate card.  Unit-testable discovery
    remains available through :func:`detect_candidate_os_voice_route`.
    """

    candidate = {
        "candidate_id": str(candidate_id),
        "profile": {
            "candidate_id": str(candidate_id),
            "display_name": str(display_name),
            "gender_preference": str(gender_preference),
        },
    }
    if is_synthetic_robert_persistent_runtime(candidate):
        return OSVoiceRoute(
            False,
            _platform_family(None),
            reason="synthetic_robert_persistent_runtime_voice_route_required",
        )
    voice_profile: dict[str, Any] = {}
    if preferred_windows_voice:
        voice_profile["sapi_approximation"] = {
            "voice_name": str(preferred_windows_voice)
        }
    gender, preferred = candidate_os_voice_preferences(candidate, voice_profile)
    # The installed route depends on the resolved preference, not the identity
    # string.  Characters that share a generic male/female/default route also
    # share one silent OS discovery probe.
    return _cached_os_voice_route(gender, preferred)


def _clean_speech_text(text: object, max_chars: int = 1600) -> str:
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"[*_#>~]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if max_chars > 0 and len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 1].rstrip() + "."
    return cleaned


def speak_with_os_voice(
    text: object,
    route: OSVoiceRoute,
    *,
    run: Callable[..., Any] = subprocess.run,
    max_chars: int = 1600,
    timeout: int = 180,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Speak via a verified route, serialized across all fallback speakers."""

    speech_text = _clean_speech_text(text, max_chars=max_chars)
    common = {
        "text": speech_text,
        "engine": route.backend,
        "voice_name": route.voice_name,
        "os_voice_fallback_used": False,
        "custom_voice_pack_used": False,
        "authentic_voice_claim": False,
    }
    if not speech_text:
        return {**common, "spoken": False, "reason": "empty_text"}
    if not route.available:
        return {
            **common,
            "spoken": False,
            "reason": route.reason or "os_voice_route_unavailable",
        }
    if dry_run:
        return {**common, "spoken": False, "reason": "dry_run"}

    kwargs: dict[str, Any] = {
        "text": True,
        "capture_output": True,
        "timeout": max(20, min(180, int(timeout))),
        "check": False,
    }
    if route.backend == "windows_system_speech":
        script = (
            "$ErrorActionPreference='Stop';"
            "$p=[Console]::In.ReadToEnd()|ConvertFrom-Json;"
            "Add-Type -AssemblyName System.Speech;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$s.SelectVoice([string]$p.voice_name);"
            "$s.Rate=[int]$p.rate;$s.Volume=[int]$p.volume;"
            "$s.Speak([string]$p.text);$s.Dispose()"
        )
        args = [
            route.executable,
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ]
        kwargs["input"] = json.dumps(
            {
                "text": speech_text,
                "voice_name": route.voice_name,
                "rate": -2 if route.gender_preference == "male" else -1,
                "volume": 90,
            },
            ensure_ascii=False,
        )
    elif route.backend == "windows_sapi_com":
        script = (
            "$ErrorActionPreference='Stop';"
            "$p=[Console]::In.ReadToEnd()|ConvertFrom-Json;"
            "$s=New-Object -ComObject SAPI.SpVoice;"
            "$match=@($s.GetVoices()|Where-Object {$_.GetDescription() -eq [string]$p.voice_name});"
            "if($match.Count -ne 1){throw 'Selected installed SAPI voice is unavailable'};"
            "$s.Voice=$match[0];$s.Rate=[int]$p.rate;$s.Volume=[int]$p.volume;"
            "[void]$s.Speak([string]$p.text)"
        )
        args = [
            route.executable,
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ]
        kwargs["input"] = json.dumps(
            {
                "text": speech_text,
                "voice_name": route.voice_name,
                "rate": -2 if route.gender_preference == "male" else -1,
                "volume": 90,
            },
            ensure_ascii=False,
        )
    elif route.backend == "macos_say":
        args = [route.executable, "-v", route.voice_name, speech_text]
    elif route.backend == "linux_espeak":
        args = [route.executable]
        if route.voice_name:
            args.extend(["-v", route.voice_name])
        args.extend(["-a", "90", speech_text])
    elif route.backend == "linux_spd_say":
        args = [route.executable, "--wait"]
        if route.voice_name:
            args.extend(["--voice-type", route.voice_name])
        args.append(speech_text)
    else:
        return {
            **common,
            "spoken": False,
            "reason": f"unsupported_os_voice_backend:{route.backend}",
        }

    try:
        with _SPEECH_LOCK:
            completed = run(args, **kwargs)
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            **common,
            "spoken": False,
            "reason": f"os_voice_execution_error:{type(exc).__name__}",
            "error": str(exc),
        }
    if int(getattr(completed, "returncode", 1)) != 0:
        return {
            **common,
            "spoken": False,
            "reason": "os_voice_command_failed",
            "stderr": str(getattr(completed, "stderr", "") or "").strip(),
        }
    return {
        **common,
        "spoken": True,
        "reason": "ok",
        "os_voice_fallback_used": True,
        "generic_voice_used": True,
    }


__all__ = [
    "OSVoiceRoute",
    "cached_candidate_os_voice_route",
    "candidate_os_voice_preferences",
    "detect_candidate_os_voice_route",
    "detect_os_voice_route",
    "is_synthetic_robert_persistent_runtime",
    "normalize_gender",
    "speak_with_os_voice",
]
