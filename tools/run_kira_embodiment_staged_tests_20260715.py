#!/usr/bin/env python3
"""Run a short, isolated, truth-gated Kira embodiment test.

This runner never replaces Kira's live GLB, never starts an unattended life
loop, and never uses debug position setters.  It loads the current approved
runtime body in a temporary browser profile, asks for a small set of actions,
and records whether the runtime can support them without teleporting or
inventing object/hand evidence.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.embodiment_evidence import CAPABILITIES, evaluate_capability, redact_private_snapshot


PREVIEW_ROOT = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "home_world"
    / "builds"
    / "home_world_main_house_20260630_223000"
    / "preview"
)
LIVE_MODEL = ROOT / "Avatar" / "models" / "temp_ai" / "kira" / "avatar.glb"
BODY_MANIFEST = ROOT / "Avatar" / "models" / "temp_ai" / "kira" / "base_body_manifest.json"
STAGED_BODY_ROOT = ROOT / "Avatar" / "avatar_builder" / "kira_adult_body_eye_passes"
REPORT_ROOT = ROOT / "Data" / "world_tests" / "kira_embodiment_staged_20260715"
HELPER_PATH = ROOT / "tools" / "observe_kira_life_loop_report.py"
ACTION_PROBE_SECONDS = 1.0


def evaluate_snapshot_for_report(
    capability: str,
    raw_snapshot: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Evaluate transient raw evidence, then return only privacy-safe evidence.

    Restroom evaluation needs an exact fixture distance and room label. Those
    values are used in memory and discarded before the report is serialized.
    """
    result = evaluate_capability(capability, raw_snapshot)
    saved_snapshot = (
        redact_private_snapshot(raw_snapshot)
        if capability == "restroom_private_use"
        else raw_snapshot
    )
    return result, saved_snapshot


def _load_helper():
    spec = importlib.util.spec_from_file_location("observe_kira_life_loop_report", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load browser helper: {HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HELPER = _load_helper()
CdpWebSocket = HELPER.CdpWebSocket
find_target = HELPER.find_target
maybe_launch_edge = HELPER.maybe_launch_edge
runtime_eval = HELPER.runtime_eval


class CorsHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def log_message(self, fmt, *args):
        return


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_http(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status < 500:
                    return
        except Exception as exc:  # pragma: no cover - browser integration only
            error = exc
        time.sleep(0.2)
    raise RuntimeError(f"Timed out waiting for {url}: {error}")


def _wait_eval(cdp: CdpWebSocket, expression: str, timeout: float = 30.0):
    deadline = time.time() + timeout
    value = None
    while time.time() < deadline:
        value = runtime_eval(cdp, expression)
        if value:
            return value
        time.sleep(0.2)
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _failed_review_inventory() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not STAGED_BODY_ROOT.exists():
        return rows
    for path in sorted(STAGED_BODY_ROOT.rglob("*failed*.json")):
        payload = _read_json(path)
        rows.append({
            "path": path.relative_to(ROOT).as_posix(),
            "status": payload.get("status") or payload.get("review_status") or "failed_review_artifact",
            "runtime_activation_allowed": payload.get("runtime_activation_allowed") is True,
        })
    followup = STAGED_BODY_ROOT / "kira_robert_review_20260714_dinner_followup.json"
    if followup.is_file():
        payload = _read_json(followup)
        rows.append({
            "path": followup.relative_to(ROOT).as_posix(),
            "status": payload.get("status") or payload.get("review_status") or "review_followup",
            "runtime_activation_allowed": payload.get("runtime_activation_allowed") is True,
        })
    return rows


def _position(snapshot: dict[str, Any]) -> dict[str, float]:
    value = snapshot.get("activePosition")
    return value if isinstance(value, dict) else {}


def _distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    try:
        return ((float(a["x"]) - float(b["x"])) ** 2 + (float(a["z"]) - float(b["z"])) ** 2) ** 0.5
    except (KeyError, TypeError, ValueError):
        return 0.0


def _browser_probe() -> dict[str, Any]:
    if not LIVE_MODEL.is_file():
        raise FileNotFoundError(LIVE_MODEL)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    vite_port = _free_port()
    asset_port = _free_port()
    cdp_port = _free_port()
    world_url = f"http://127.0.0.1:{vite_port}/?area=home&embodimentStage=20260715"

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    vite = subprocess.Popen(
        ["npm.cmd" if os.name == "nt" else "npm", "run", "dev", "--", "--port", str(vite_port), "--strictPort"],
        cwd=str(PREVIEW_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    asset_server = ThreadingHTTPServer(("127.0.0.1", asset_port), CorsHandler)
    threading.Thread(target=asset_server.serve_forever, daemon=True).start()
    edge = None
    cdp = None
    try:
        _wait_http(world_url)
        edge = maybe_launch_edge(cdp_port, world_url, REPORT_ROOT / "edge_profile")
        if edge is None:
            raise RuntimeError("Could not launch isolated Edge test profile")
        time.sleep(2.0)
        target = find_target(f"http://127.0.0.1:{cdp_port}", "embodimentStage")
        cdp = CdpWebSocket(target["webSocketDebuggerUrl"])
        cdp.connect()
        if cdp.sock:
            cdp.sock.settimeout(60.0)
        _wait_eval(cdp, "Boolean(window.kiraHomeWorldDebug?.embodimentEvidenceSnapshot)")

        model_url = f"http://127.0.0.1:{asset_port}/Avatar/models/temp_ai/kira/avatar.glb?v={int(LIVE_MODEL.stat().st_mtime)}"
        shell_state = {
            "active_label": "Kira",
            "active_candidate": "kira",
            "active_action": "idle",
            "active_form": "civilian",
            "location": "home",
            "active_model_url": model_url,
        }
        runtime_eval(cdp, f"window.kiraHomeWorldDebug.injectShellState({json.dumps(shell_state)})")
        _wait_eval(cdp, "window.kiraHomeWorldDebug?.activeAvatarState?.().rootPresent", timeout=25.0)
        time.sleep(0.5)

        initial = runtime_eval(cdp, "window.kiraHomeWorldDebug.embodimentEvidenceSnapshot('initial_loaded_body')") or {}
        model_nodes = runtime_eval(cdp, "window.kiraHomeWorldDebug.activeAvatarModelNodeNames()") or []
        limb = runtime_eval(cdp, "window.kiraHomeWorldDebug.activeLimbDiagnostics()") or {}
        truth_inventory = runtime_eval(cdp, """
(() => {
  const allowed = new Set(['tablet','phone','book','notebook','food','fruit','milk','coffee_cup','cup','toilet','bath_shower']);
  return window.kiraHomeWorldDebug.truthProps().filter((item) => allowed.has(item.kind));
})()
""") or []
        scene_inventory = runtime_eval(cdp, """
(() => {
  const terms = ['one-bedroom', 'couch', 'sofa', 'bed', 'mattress', 'coffee table', 'tablet', 'toilet', 'sink', 'refrigerator', 'snack'];
  return window.kiraHomeWorldDebug.sceneObjectSummaries().filter((item) => terms.some((term) => item.name.toLowerCase().includes(term))).slice(0, 240);
})()
""") or []

        action_map = {
            "restroom_private_use": "use_bathroom",
            "eat_food": "eat_food",
            "drink": "drink",
            "sit_couch": "sit",
            "lie_bed": "lie_down",
            "tablet_pickup": "read_tablet",
            "tablet_putdown": "put_down_tablet",
            "tablet_read": "read_tablet",
            "tablet_online_lookup": "look_online",
            "tablet_note_writing": "take_notes",
        }
        snapshots: dict[str, Any] = {}
        capability_results: list[dict[str, Any]] = []
        action_probe_results: list[dict[str, Any]] = []
        previous = initial
        for capability in CAPABILITIES:
            next_state = dict(shell_state)
            next_state["active_action"] = action_map[capability]
            before = runtime_eval(cdp, "window.kiraHomeWorldDebug.embodimentEvidenceSnapshot('before_action_probe')") or {}
            runtime_eval(cdp, f"window.kiraHomeWorldDebug.injectShellState({json.dumps(next_state)})")
            time.sleep(ACTION_PROBE_SECONDS)
            after = runtime_eval(cdp, f"window.kiraHomeWorldDebug.embodimentEvidenceSnapshot({json.dumps(capability)})") or {}
            result, saved_snapshot = evaluate_snapshot_for_report(capability, after)
            capability_results.append(result)
            snapshots[capability] = saved_snapshot
            action_probe_results.append({
                "capability": capability,
                "requested_action": action_map[capability],
                "body_displacement_meters": round(_distance(_position(before), _position(after)), 4),
                "last_block": after.get("lastEmbodimentCapabilityBlock"),
                "held_prop": after.get("activeHeldProp"),
            })
            previous = after

        runtime_eval(cdp, f"window.kiraHomeWorldDebug.injectShellState({json.dumps(shell_state)})")
        return {
            "world_url": world_url,
            "model_url": model_url,
            "initial_snapshot": initial,
            "model_node_count_sampled": len(model_nodes),
            "model_node_names_sample": model_nodes,
            "limb_diagnostics": limb,
            "truth_prop_inventory": truth_inventory,
            "scene_inventory": scene_inventory,
            "action_probe_results": action_probe_results,
            "capability_results": capability_results,
            "capability_snapshots": snapshots,
            "max_action_probe_displacement_meters": max((row["body_displacement_meters"] for row in action_probe_results), default=0),
        }
    finally:
        if cdp is not None:
            cdp.close()
        if edge is not None:
            try:
                edge.terminate()
                edge.wait(timeout=5)
            except Exception:
                pass
        asset_server.shutdown()
        asset_server.server_close()
        if os.name == "nt":
            # npm launches Vite as a child process; stop the isolated tree so
            # the short test never leaves a background dev server behind.
            subprocess.run(
                ["taskkill", "/PID", str(vite.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                creationflags=creationflags,
            )
        else:
            vite.terminate()
        try:
            vite.wait(timeout=5)
        except subprocess.TimeoutExpired:
            vite.kill()


def _environment_summary(probe: dict[str, Any]) -> dict[str, Any]:
    truth = probe.get("truth_prop_inventory") if isinstance(probe.get("truth_prop_inventory"), list) else []
    scene = probe.get("scene_inventory") if isinstance(probe.get("scene_inventory"), list) else []
    kinds = {str(item.get("kind") or "") for item in truth if isinstance(item, dict)}
    names = " ".join(str(item.get("name") or "").lower() for item in scene if isinstance(item, dict))
    checks = {
        "runtime_body_loaded": bool((probe.get("initial_snapshot") or {}).get("activeModelLoaded")),
        "tablet_world_prop_present": "tablet" in kinds or "tablet" in names,
        "food_or_drink_world_prop_present": bool(kinds & {"food", "fruit", "milk", "coffee_cup", "cup"}),
        "restroom_fixture_present": "toilet" in kinds or "toilet" in names,
        "couch_or_sofa_present": "couch" in names or "sofa" in names,
        "bed_or_mattress_present": "bed" in names or "mattress" in names,
    }
    return {
        "status": "passed" if all(checks.values()) else "incomplete",
        "checks": checks,
        "note": "Environment presence is not proof that Kira performed an interaction.",
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    body = report["body_safety"]
    environment = report["environment_readiness"]
    capability_results = report["capability_results"]
    lines = [
        "# Kira staged embodiment evidence report",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "This was a short isolated browser test. It did not replace Kira's live model, run an unattended life loop, enter a private restroom camera view, or use debug teleport setters.",
        "",
        "## Body safety",
        "",
        f"- Current runtime GLB loaded: **{'yes' if body['live_model_loaded_in_browser'] else 'no'}**",
        f"- Current runtime SHA-256 remained `{body['live_model_sha256']}`.",
        f"- Rejected staged body activated: **{'yes' if body['rejected_staged_body_activated'] else 'no'}**",
        f"- Approved full adult anatomy/animation ready: **{'yes' if body['full_adult_anatomy_animation_approved'] else 'no'}**",
        "- Result: the clean adult base may remain the runtime body, but missing full anatomy/animation cannot be claimed as complete.",
        "",
        "## Environment readiness",
        "",
    ]
    for name, passed in environment["checks"].items():
        lines.append(f"- {'PASS' if passed else 'BLOCKED'}: {name.replace('_', ' ')}")
    lines.extend(["", "## Capability results", ""])
    for result in capability_results:
        reasons = "; ".join(result["reasons"][:4]) if result["reasons"] else "all required evidence present"
        lines.append(f"- **{result['status'].upper()} - {result['capability']}**: {reasons}")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The world contains the expected household props, but current action shortcuts do not yet prove a complete biological-style routine. Generated hand props are now labeled preview-only, and direct target placement is blocked by the strict evidence gate. Restroom use, consumption, couch/bed posture, and tablet work stay blocked until actual travel, support, pickup/put-down, hand contact, and content evidence are present.",
        "",
        "No multi-hour test was run.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    live_hash_before = _sha256(LIVE_MODEL)
    browser_probe = _browser_probe()
    live_hash_after = _sha256(LIVE_MODEL)
    reviews = _failed_review_inventory()
    capability_results = browser_probe.get("capability_results") or []
    if len(capability_results) != len(CAPABILITIES):
        raise RuntimeError("Browser probe did not return one evaluated result per capability.")
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "test_mode": "short_isolated_browser_staged_truth_gate",
        "privacy": {
            "restroom_snapshot_redacted": True,
            "restroom_screenshots_captured": False,
            "private_content_logged": False,
        },
        "body_safety": {
            "live_model": LIVE_MODEL.relative_to(ROOT).as_posix(),
            "live_model_sha256": live_hash_after,
            "live_model_unchanged_during_test": live_hash_before == live_hash_after,
            "live_model_loaded_in_browser": bool((browser_probe.get("initial_snapshot") or {}).get("activeModelLoaded")),
            "base_body_manifest": _read_json(BODY_MANIFEST),
            "rejected_review_artifacts": reviews,
            "rejected_staged_body_activated": False,
            "full_adult_anatomy_animation_approved": False,
            "full_adult_body_result": "blocked_until_exact_model_visual_review_and_anatomy_animation_evidence_pass",
        },
        "environment_readiness": _environment_summary(browser_probe),
        "capability_summary": {
            "passed": sum(1 for result in capability_results if result["passed"]),
            "blocked": sum(1 for result in capability_results if not result["passed"]),
            "overall": "passed" if all(result["passed"] for result in capability_results) else "blocked",
        },
        "capability_results": capability_results,
        "browser_probe": browser_probe,
        "constraints": {
            "teleport_allowed": False,
            "generated_prop_counts_as_pickup": False,
            "missing_hand_contact_counts_as_use": False,
            "unapproved_anatomy_claimed": False,
            "multi_hour_test_run": False,
        },
    }
    json_path = REPORT_ROOT / "report.json"
    markdown_path = REPORT_ROOT / "README.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_markdown(report, markdown_path)
    print(json.dumps({
        "report": str(json_path),
        "markdown": str(markdown_path),
        "body_loaded": report["body_safety"]["live_model_loaded_in_browser"],
        "model_unchanged": report["body_safety"]["live_model_unchanged_during_test"],
        "environment": report["environment_readiness"]["status"],
        "capability_summary": report["capability_summary"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
