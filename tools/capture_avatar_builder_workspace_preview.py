"""Capture Avatar Builder Workspace previews through Edge DevTools."""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.parse
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from observe_kira_life_loop_report import (  # noqa: E402
    CdpWebSocket,
    capture_screenshot,
    maybe_launch_edge,
    read_json,
)


def wait_for_devtools(cdp_base: str, seconds: float = 8.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            read_json(cdp_base.rstrip("/") + "/json/version", timeout=1.0)
            return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError(f"DevTools did not become ready at {cdp_base}")


def wait_for_target(cdp_base: str, fragment: str, seconds: float = 12.0) -> dict:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            targets = read_json(cdp_base.rstrip("/") + "/json/list")
            pages = [target for target in targets if target.get("type") == "page" and target.get("webSocketDebuggerUrl")]
            for target in pages:
                haystack = f"{target.get('title','')} {target.get('url','')}".lower()
                if fragment.lower() in haystack:
                    return target
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError(f"No DevTools target found for {fragment}")


def select_candidate_expression(candidate_id: str, frame_mode: str) -> str:
    return f"""
(async () => {{
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  for (let i = 0; i < 80; i++) {{
    if (document.querySelector("#candidate") && document.querySelector("#preview")) break;
    await sleep(100);
  }}
  const id = {json.dumps(candidate_id)};
  const item = [...document.querySelectorAll(".item")].find(node => node.dataset.id === id);
  if (item) {{
    item.click();
  }} else {{
    const select = document.querySelector("#candidate");
    if (!select) return {{ ok: false, error: "candidate select missing" }};
    select.value = id;
    select.dispatchEvent(new Event("change", {{ bubbles: true }}));
  }}
  await sleep(2400);
  const frameButton = document.querySelector({json.dumps("#frameHead" if frame_mode == "head" else "#frameBody")});
  if (frameButton) frameButton.click();
  await sleep(1200);
  const canvas = document.querySelector("#previewCanvas") || document.querySelector("canvas");
  const status = document.querySelector("#previewStatus")?.textContent || "";
  const meta = document.querySelector("#previewMeta")?.textContent || "";
  const title = document.querySelector("#previewTitle")?.textContent || "";
  let nonBlank = false;
  let sample = null;
  if (canvas) {{
    const ctx = canvas.getContext("webgl2") || canvas.getContext("webgl");
    if (ctx) {{
      const w = canvas.width, h = canvas.height;
      const pixels = new Uint8Array(4 * 16 * 16);
      ctx.readPixels(Math.max(0, Math.floor(w / 2) - 8), Math.max(0, Math.floor(h / 2) - 8), 16, 16, ctx.RGBA, ctx.UNSIGNED_BYTE, pixels);
      let total = 0;
      for (let i = 0; i < pixels.length; i += 4) total += pixels[i] + pixels[i + 1] + pixels[i + 2];
      nonBlank = total > 2000;
      sample = total;
    }}
  }}
  return {{
    ok: Boolean(canvas),
    candidate: id,
    title,
    status,
    meta,
    canvas: canvas ? {{ width: canvas.width, height: canvas.height }} : null,
    canvas_rect: canvas ? (() => {{
      const rect = canvas.getBoundingClientRect();
      return {{ left: rect.left, top: rect.top, width: rect.width, height: rect.height }};
    }})() : null,
    center_pixel_sum: sample,
    center_nonblank: nonBlank,
  }};
}})()
"""


def screenshot_canvas_sample(path: Path, rect: dict | None) -> dict:
    if not rect or not path.exists():
        return {"ok": False, "reason": "missing screenshot or canvas rectangle"}
    image = Image.open(path).convert("RGB")
    left = max(0, int(rect.get("left", 0)))
    top = max(0, int(rect.get("top", 0)))
    right = min(image.width, left + max(1, int(rect.get("width", 0))))
    bottom = min(image.height, top + max(1, int(rect.get("height", 0))))
    crop = image.crop((left, top, right, bottom))
    step_x = max(1, crop.width // 120)
    step_y = max(1, crop.height // 80)
    total = 0
    bright = 0
    colors: set[tuple[int, int, int]] = set()
    for y in range(0, crop.height, step_y):
        for x in range(0, crop.width, step_x):
            r, g, b = crop.getpixel((x, y))
            total += 1
            if r + g + b > 90:
                bright += 1
            colors.add((r // 12, g // 12, b // 12))
    return {
        "ok": bright > 150 and len(colors) > 20,
        "sampled_pixels": total,
        "bright_pixels": bright,
        "distinct_color_buckets": len(colors),
        "crop": {"left": left, "top": top, "width": crop.width, "height": crop.height},
    }


def runtime_eval_long(cdp: CdpWebSocket, expression: str):
    deadline = time.time() + 30.0
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            result = cdp.call(
                "Runtime.evaluate",
                {
                    "expression": expression,
                    "returnByValue": True,
                    "awaitPromise": True,
                    "timeout": 20000,
                },
            )
            remote = result.get("result", {})
            return remote.get("value")
        except RuntimeError as exc:
            message = str(exc)
            if "Cannot find default execution context" not in message and "Execution context was destroyed" not in message:
                raise
            last_error = exc
            time.sleep(0.5)
    if last_error:
        raise last_error
    raise RuntimeError("Runtime.evaluate did not return before timeout")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8770/")
    parser.add_argument("--cdp-port", type=int, default=9336)
    parser.add_argument("--profile-dir", default="_tmp_edge_cdp_avatar_builder_reference_pass")
    parser.add_argument("--out-dir", default="Data/avatar_builder_workspace_tests")
    parser.add_argument("--candidate", action="append", required=True)
    parser.add_argument("--frame", choices=["body", "head"], default="body")
    args = parser.parse_args()

    out_dir = PROJECT_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    cdp_base = f"http://127.0.0.1:{args.cdp_port}"
    process = maybe_launch_edge(args.cdp_port, args.url, PROJECT_ROOT / args.profile_dir)
    try:
        wait_for_devtools(cdp_base)
        time.sleep(1.5)
        target_fragment = urllib.parse.urlparse(args.url).netloc or args.url
        target = wait_for_target(cdp_base, target_fragment)
        cdp = CdpWebSocket(target["webSocketDebuggerUrl"], timeout=45.0)
        cdp.connect()
        try:
            cdp.call("Page.enable")
            cdp.call("Runtime.enable")
            cdp.call(
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": 1600,
                    "height": 1000,
                    "deviceScaleFactor": 1,
                    "mobile": False,
                },
            )
            cdp.call("Page.bringToFront")
            time.sleep(2.0)
            results = []
            for candidate in args.candidate:
                candidate_url = args.url.rstrip("/") + "/"
                cdp.call("Page.navigate", {"url": candidate_url})
                time.sleep(2.0)
                inspected = runtime_eval_long(
                    cdp,
                    select_candidate_expression(candidate, args.frame),
                )
                shot_path = out_dir / f"{candidate}_workspace_reference_pass_{args.frame}.png"
                ok = capture_screenshot(cdp, shot_path)
                result = {
                    "ok": ok,
                    "candidate": candidate,
                    "url": candidate_url,
                    "frame": args.frame,
                    "inspection": inspected,
                    "canvas_rect": (inspected or {}).get("canvas_rect"),
                }
                result["screenshot"] = str(shot_path.relative_to(PROJECT_ROOT))
                result["screenshot_ok"] = ok
                result["screenshot_canvas_sample"] = screenshot_canvas_sample(shot_path, result.get("canvas_rect"))
                results.append(result)
            print(json.dumps({"ok": True, "results": results}, indent=2))
        finally:
            cdp.close()
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=3)
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
