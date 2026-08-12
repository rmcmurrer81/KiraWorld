from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = "20260703_movement_frontdoor"
REPORT_DIR = ROOT / "Data" / "codex_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REPORT = REPORT_DIR / f"{STAMP}.md"


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def backup(path: Path) -> None:
    if path.exists():
        bak = path.with_suffix(path.suffix + f".bak_{STAMP}")
        if not bak.exists():
            shutil.copy2(path, bak)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup(path)
    path.write_text(text, encoding="utf-8")


def append_unique(path: Path, marker: str, block: str) -> bool:
    old = read_text(path) if path.exists() else ""
    if marker in old:
        return False
    write_text(path, old.rstrip() + "\n\n" + block.strip() + "\n")
    return True


def patch_main_js(report: list[str]) -> None:
    path = (
        ROOT
        / "Data"
        / "world_builds"
        / "notebook_worlds"
        / "home_world"
        / "builds"
        / "home_world_main_house_20260630_223000"
        / "preview"
        / "src"
        / "main.js"
    )
    if not path.exists():
        report.append(f"- main.js not found at `{path}`; front-door runtime cleanup was skipped.")
        return

    marker = "CODEX_PHASE_20260703_MOVEMENT_FRONT_DOOR_BEGIN"
    block = r"""
// CODEX_PHASE_20260703_MOVEMENT_FRONT_DOOR_BEGIN
// Runtime safety pass for the Home World shell. This is intentionally additive:
// it removes the small front-entry blocker if the current build names it, and
// exposes a movement-learning registry for the avatar builder.
(function () {
  const VERSION = "2026-07-03 movement-frontdoor-v1";

  function getWorldPosition(obj) {
    if (!obj) return { x: 0, y: 0, z: 0 };
    if (window.THREE && obj.getWorldPosition) {
      const v = new window.THREE.Vector3();
      obj.getWorldPosition(v);
      return v;
    }
    return obj.position || { x: 0, y: 0, z: 0 };
  }

  function objectName(obj) {
    return String((obj && (obj.name || obj.userData && obj.userData.name)) || "").toLowerCase();
  }

  function isNamedFrontDoorBlocker(obj) {
    const name = objectName(obj);
    return (
      /front.*(stub|blocker|collision|loose|post|pillar|wall)/.test(name) ||
      /entry.*(stub|blocker|collision|loose|post|pillar)/.test(name) ||
      /foyer.*(stub|blocker|collision|loose|post|pillar)/.test(name)
    );
  }

  function hideObject(obj, reason) {
    obj.visible = false;
    obj.userData = obj.userData || {};
    obj.userData.kiraRemovedBy = VERSION;
    obj.userData.kiraRemovedReason = reason;
    obj.raycast = function () {};
    if (obj.children) {
      obj.children.forEach(function (child) {
        child.visible = false;
        child.raycast = function () {};
      });
    }
  }

  function removeFrontDoorBlocker(scene) {
    if (!scene || !scene.traverse) return 0;
    let removed = 0;
    scene.traverse(function (obj) {
      if (!obj || obj.userData && obj.userData.kiraRemovedBy === VERSION) return;
      if (isNamedFrontDoorBlocker(obj)) {
        hideObject(obj, "named front-entry blocker");
        removed += 1;
      }
    });
    return removed;
  }

  function sceneCandidates() {
    return [
      window.scene,
      window.worldScene,
      window.kiraScene,
      window.kiraWorld && window.kiraWorld.scene,
      window.KiraWorld && window.KiraWorld.scene,
      window.homeWorld && window.homeWorld.scene,
      window.app && window.app.scene
    ].filter(Boolean);
  }

  window.kiraRemoveFrontDoorBlocker = function () {
    return sceneCandidates().reduce(function (total, scene) {
      return total + removeFrontDoorBlocker(scene);
    }, 0);
  };

  function makeDefaultMovementMemory() {
    return {
      version: 1,
      updatedAt: new Date().toISOString(),
      promotedClips: {},
      attempts: [],
      notes: [
        "Movement is goal-directed: navigation chooses a target, locomotion clips solve the body motion.",
        "New learned clips should be reviewed, then promoted into Avatar/movement_library for future avatars."
      ]
    };
  }

  function loadMovementMemory() {
    const key = "kira.avatar.movementLearning.v1";
    try {
      return JSON.parse(window.localStorage.getItem(key)) || makeDefaultMovementMemory();
    } catch (err) {
      return makeDefaultMovementMemory();
    }
  }

  function saveMovementMemory(memory) {
    const key = "kira.avatar.movementLearning.v1";
    memory.updatedAt = new Date().toISOString();
    try {
      window.localStorage.setItem(key, JSON.stringify(memory));
    } catch (err) {
      // Local storage may be unavailable in some embedded shells.
    }
  }

  window.kiraMovementLearning = window.kiraMovementLearning || {
    version: VERSION,
    memory: loadMovementMemory(),
    recordAttempt: function (attempt) {
      const item = Object.assign({ at: new Date().toISOString() }, attempt || {});
      this.memory.attempts.push(item);
      if (this.memory.attempts.length > 250) this.memory.attempts.shift();
      saveMovementMemory(this.memory);
      return item;
    },
    promoteClip: function (name, clip) {
      if (!name) return false;
      this.memory.promotedClips[name] = Object.assign({ promotedAt: new Date().toISOString() }, clip || {});
      saveMovementMemory(this.memory);
      return true;
    },
    exportForAvatarBuilder: function () {
      return JSON.parse(JSON.stringify(this.memory));
    }
  };

  window.kiraFoundationMotion = window.kiraFoundationMotion || {
    version: VERSION,
    walkGroundedV3: {
      cycleSeconds: 1.04,
      metersPerSecond: 0.82,
      strideMeters: 0.85,
      kneeLiftDegrees: 34,
      kneePlantDegrees: 10,
      ankleToeOffDegrees: 18,
      elbowSwingDegrees: 18,
      shoulderSwingDegrees: 14,
      hipCounterRotationDegrees: 5,
      footPlantRule: "support foot stays planted for 52% of the gait cycle; root motion must match strideMeters"
    },
    handContractV1: {
      digitsPerHand: 5,
      jointsPerFinger: 3,
      controls: ["curl", "spread", "thumbOppose", "pinch", "relax"]
    },
    stairsRuleV1: {
      mode: "step-by-step",
      maxVerticalStepMeters: 0.23,
      requireFootContactBeforePelvisLift: true
    }
  };

  let tries = 0;
  const timer = window.setInterval(function () {
    tries += 1;
    const count = window.kiraRemoveFrontDoorBlocker();
    if (count || tries > 40) window.clearInterval(timer);
  }, 250);
})();
// CODEX_PHASE_20260703_MOVEMENT_FRONT_DOOR_END
"""
    changed = append_unique(path, marker, block)
    report.append(
        "- Installed front-entry cleanup and movement-learning runtime hooks in `main.js`."
        if changed
        else "- `main.js` already had the 2026-07-03 movement/front-door runtime hooks."
    )


def patch_builder(report: list[str]) -> None:
    path = ROOT / "tools" / "build_ladybug_foundation_skeleton_v1.py"
    if not path.exists():
        report.append(f"- Skeleton builder not found at `{path}`; builder tuning was skipped.")
        return

    text = read_text(path)
    original = text
    replacements = [
        (r"walk_speed\s*=\s*[0-9.]+", "walk_speed = 0.82"),
        (r"stride_length\s*=\s*[0-9.]+", "stride_length = 0.85"),
        (r"step_length\s*=\s*[0-9.]+", "step_length = 0.425"),
        (r"cycle_duration\s*=\s*[0-9.]+", "cycle_duration = 1.04"),
        (r"knee_bend(?:_degrees)?\s*=\s*[0-9.]+", "knee_bend_degrees = 34.0"),
        (r"elbow_bend(?:_degrees)?\s*=\s*[0-9.]+", "elbow_bend_degrees = 18.0"),
        (r"arm_swing(?:_degrees)?\s*=\s*[0-9.]+", "arm_swing_degrees = 14.0"),
        (r"foot_lift\s*=\s*[0-9.]+", "foot_lift = 0.105"),
        (r"pelvis_bob\s*=\s*[0-9.]+", "pelvis_bob = 0.035"),
    ]
    applied = 0
    for pattern, repl in replacements:
        text, count = re.subn(pattern, repl, text, count=1)
        applied += count

    marker = "CODEX_FOUNDATION_GAIT_V3"
    if marker not in text:
        text += r'''

# CODEX_FOUNDATION_GAIT_V3
# Shared movement contract used by Kira World and the avatar builder. The current
# simple body should keep this mechanical and readable; later visual bodies can
# bind richer meshes, cloth, hair, and facial rigs to the same controls.
FOUNDATION_GAIT_V3 = {
    "cycle_seconds": 1.04,
    "meters_per_second": 0.82,
    "stride_meters": 0.85,
    "support_phase": 0.52,
    "knee_lift_degrees": 34.0,
    "knee_plant_degrees": 10.0,
    "ankle_toeoff_degrees": 18.0,
    "elbow_swing_degrees": 18.0,
    "shoulder_swing_degrees": 14.0,
    "hip_counter_rotation_degrees": 5.0,
    "hand_contract": {
        "digits_per_hand": 5,
        "joints_per_finger": 3,
        "controls": ["curl", "spread", "thumbOppose", "pinch", "relax"],
    },
    "stairs": {
        "mode": "step-by-step",
        "max_vertical_step_meters": 0.23,
        "require_foot_contact_before_pelvis_lift": True,
    },
}
'''

    if text != original:
        write_text(path, text)
        report.append(f"- Tuned `build_ladybug_foundation_skeleton_v1.py` gait constants/contract ({applied} direct replacements).")
    else:
        report.append("- Skeleton builder already matched the current gait patch.")

    try:
        result = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(ROOT),
            timeout=90,
            capture_output=True,
            text=True,
        )
        report.append(f"- Rebuilt foundation skeleton with `{path.name}`; exit code `{result.returncode}`.")
        if result.stderr.strip():
            report.append("  - Builder stderr was captured in this report's sibling log.")
            (REPORT_DIR / f"{STAMP}_builder_stderr.txt").write_text(result.stderr, encoding="utf-8", errors="replace")
        if result.stdout.strip():
            (REPORT_DIR / f"{STAMP}_builder_stdout.txt").write_text(result.stdout, encoding="utf-8", errors="replace")
    except Exception as exc:
        report.append(f"- Tried to rebuild foundation skeleton, but builder execution failed: `{exc}`.")


def write_movement_library(report: list[str]) -> None:
    movement_dir = ROOT / "Avatar" / "movement_library"
    movement_dir.mkdir(parents=True, exist_ok=True)
    registry = {
        "version": "2026-07-03.foundation-movement-v1",
        "purpose": "Shared movement knowledge for the simple foundation skeleton and future avatar-builder bodies.",
        "phase_breakdown": {
            "phase_1_now": [
                "Remove blocking front-entry geometry through runtime cleanup.",
                "Tune grounded walk so root travel, stride length, knee bend, and foot plant agree.",
                "Add movement learning registry so attempts and promoted clips are not lost.",
                "Keep the current body as a readable foundation skeleton before likeness work resumes.",
            ],
            "phase_2_next": [
                "Add IK-style foot planting and stair-step solver.",
                "Replace visible finger guides with true articulated hand controls.",
                "Add door-open, sit, reach, pick-up, and turn-in-place clips.",
            ],
            "phase_3_body": [
                "Bind a more realistic Marinette visual mesh to the foundation rig.",
                "Add facial blink and speech blendshapes.",
                "Add hair and clothing simulation proxies after the motion rig is stable.",
            ],
            "phase_4_learning": [
                "Let AIs review videos/media and create candidate motion clips.",
                "Store learned clips as untrusted drafts until reviewed.",
                "Promote approved clips into this movement library for future avatars.",
            ],
        },
        "rig_contract": {
            "root": ["root", "pelvis", "spine", "chest", "neck", "head"],
            "arms": ["clavicle", "upper_arm", "lower_arm", "wrist"],
            "hands": {
                "digits_per_hand": 5,
                "joints_per_digit": 3,
                "controls": ["curl", "spread", "thumbOppose", "pinch", "relax"],
                "current_status": "Foundation fingers are readable control guides; production grasping still needs per-finger colliders and IK."
            },
            "legs": ["hip", "thigh", "shin", "foot", "toe"],
            "hair": "Later visual pass should bind hair cards/strands to hair bones and wetness parameters.",
        },
        "clips": {
            "idle_balance_v1": {
                "loop": True,
                "seconds": 3.0,
                "notes": "Small breathing, weight shift, eye/head attention. No root translation."
            },
            "walk_grounded_v3": {
                "loop": True,
                "cycle_seconds": 1.04,
                "meters_per_second": 0.82,
                "stride_meters": 0.85,
                "support_phase": 0.52,
                "knee_lift_degrees": 34,
                "knee_plant_degrees": 10,
                "toe_off_degrees": 18,
                "shoulder_swing_degrees": 14,
                "elbow_swing_degrees": 18,
                "rule": "Do not advance root faster than the planted-foot stride supports."
            },
            "turn_in_place_v1": {
                "loop": False,
                "seconds": 0.8,
                "notes": "Use before walking to prevent sideways/backwards skating."
            },
            "stairs_step_v1": {
                "loop": False,
                "seconds": 0.72,
                "notes": "One stair at a time; foot contact must exist before pelvis rises."
            },
            "hand_open_close_v1": {
                "loop": False,
                "seconds": 0.5,
                "notes": "First hand test clip for future door handles, phones, purses, and books."
            },
            "door_approach_v1": {
                "loop": False,
                "seconds": 1.2,
                "notes": "Stop at handle range, rotate torso, reach, then request door open."
            },
        },
        "learning_policy": {
            "walk_to_walk": "Navigation goals choose destinations; walk clips should never move without a goal except in calibration/test mode.",
            "new_motion": "Jog/run/dance clips are stored as draft attempts first, then promoted after review.",
            "avatar_builder": "Promoted clips are reusable by new AIs if their rig satisfies rig_contract."
        },
    }
    path = movement_dir / "foundation_skeleton_movements_v1.json"
    write_text(path, json.dumps(registry, indent=2))
    report.append(f"- Wrote movement registry `{path}`.")

    readme = """# Avatar Movement Library

This folder is the shared movement memory for Kira World avatars.

The current Marinette body is intentionally a simple foundation skeleton. Its job is to prove that navigation, foot planting, knees, elbows, hands, doors, stairs, and learning work before a more realistic visual body is bound to the rig.

Approved learned motions should be added here so the avatar builder can give future AIs the same movement knowledge instead of making every body relearn from zero.
"""
    write_text(movement_dir / "README.md", readme)
    report.append("- Refreshed `Avatar/movement_library/README.md`.")


def update_handoffs(report: list[str]) -> None:
    block = f"""
## Codex Update - {now()} - Movement/Foundation Skeleton Phase

- Broke the current avatar work into phases:
  - Phase 1 now: front-entry blocker cleanup, grounded walk tuning, movement-learning registry, and foundation skeleton contract.
  - Phase 2 next: IK-style foot planting, stair stepping, usable articulated hands, door/sit/reach/pick-up clips.
  - Phase 3 body: bind a more realistic Marinette mesh, facial blendshapes, blink/lipsync, hair and clothing simulation proxies.
  - Phase 4 learning: reviewed video/media motions become draft clips, then promoted into the avatar builder for future AIs.
- Added runtime hooks in the Home World shell for `window.kiraMovementLearning`, `window.kiraFoundationMotion`, and `window.kiraRemoveFrontDoorBlocker`.
- Added `Avatar/movement_library/foundation_skeleton_movements_v1.json` as the shared movement contract for Kira World and the avatar builder.
- Tuned/rebuilt the current foundation skeleton builder when available. Current hand/finger geometry remains a control-readable prototype, not the final production hand.
- Important remaining work: connect the runtime locomotion controller to promoted clips, add foot IK/contact checks, and make stair movement step-by-step instead of shortcutting through floors.
"""
    targets = [
        ROOT / "HANDOFF_FOR_NEXT_CODEX_SESSION.md",
        ROOT / "System" / "Docs" / "AVATAR_FUNCTIONAL_V2_HANDOFF_20260630.md",
        ROOT / "System" / "Docs" / "HOME_WORLD_MAIN_HOUSE_HANDOFF_20260701.md",
    ]
    for target in targets:
        append_unique(target, "Movement/Foundation Skeleton Phase", block)
        report.append(f"- Updated handoff doc `{target}`.")


def main() -> int:
    report: list[str] = [f"# Movement / Front Door Phase Report", "", f"Generated: {now()}", ""]
    patch_main_js(report)
    patch_builder(report)
    write_movement_library(report)
    update_handoffs(report)
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    (REPORT_DIR / f"{STAMP}.done").write_text(now() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
