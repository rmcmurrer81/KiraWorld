from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIFE_DIR = PROJECT_ROOT / "Data" / "life_sessions"
OUT_DIR = PROJECT_ROOT / "Data" / "hardware" / "gpu_bridge_status"


def run(command: list[str], timeout: int = 10) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": (result.stdout or "").strip(),
            "stderr": (result.stderr or "").strip(),
        }
    except Exception as exc:  # noqa: BLE001 - status tool should report instead of crashing
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}


def latest_life_json() -> Path | None:
    candidates = sorted(LIFE_DIR.glob("kira_life_day*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def load_latest_life() -> dict[str, Any]:
    path = latest_life_json()
    if not path:
        return {"found": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"found": True, "path": str(path.relative_to(PROJECT_ROOT)), "error": str(exc)}
    return {
        "found": True,
        "path": str(path.relative_to(PROJECT_ROOT)),
        "run_id": data.get("run_id") or path.stem,
        "status": data.get("status"),
        "cycles": len(data.get("cycles", [])) if isinstance(data.get("cycles"), list) else data.get("cycles") or len(data.get("cycles_log", [])),
        "errors": data.get("errors") or data.get("issue_counts", {}).get("errors", 0),
        "source_errors": data.get("source_errors") or data.get("issue_counts", {}).get("source_errors", 0),
        "last_activity": data.get("last_activity") or data.get("current_activity"),
        "current_source": data.get("current_source") or data.get("last_source"),
        "updated_at": data.get("updated_at"),
    }


def parse_nvidia() -> dict[str, Any]:
    result = run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.used,temperature.gpu,utilization.gpu,power.draw",
            "--format=csv,noheader,nounits",
        ]
    )
    if not result["ok"] or not result["stdout"]:
        return {"ok": False, "detail": result["stderr"] or "nvidia-smi returned no output"}
    parts = [part.strip() for part in result["stdout"].splitlines()[0].split(",")]
    if len(parts) < 6:
        return {"ok": False, "detail": result["stdout"]}
    return {
        "ok": True,
        "name": parts[0],
        "memory_total_mb": int(float(parts[1])),
        "memory_used_mb": int(float(parts[2])),
        "temperature_c": int(float(parts[3])),
        "utilization_percent": int(float(parts[4])),
        "power_draw_w": float(parts[5]),
    }


def parse_ollama_ps() -> dict[str, Any]:
    result = run(["ollama", "ps"])
    processor = ""
    model = ""
    lines = result.get("stdout", "").splitlines()
    if len(lines) >= 2:
        row = lines[1]
        model = row.split()[0] if row.split() else ""
        if "100% GPU" in row:
            processor = "100% GPU"
        elif "CPU" in row:
            processor = "CPU"
        else:
            processor = row
    return {
        "ok": result["ok"],
        "model": model,
        "processor": processor,
        "raw": result.get("stdout", ""),
    }


def parse_ram() -> dict[str, Any]:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_OperatingSystem | ConvertTo-Json -Compress",
    ]
    result = run(command)
    if not result["ok"]:
        return {"ok": False, "detail": result["stderr"]}
    data = json.loads(result["stdout"])
    free_gb = round(int(data["FreePhysicalMemory"]) / 1024 / 1024, 2)
    total_gb = round(int(data["TotalVisibleMemorySize"]) / 1024 / 1024, 2)
    return {"ok": True, "free_gb": free_gb, "total_gb": total_gb, "used_percent": round((1 - free_gb / total_gb) * 100, 1)}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report_id = datetime.now().strftime("gpu_bridge_status_%Y%m%d_%H%M%S")
    report = {
        "report_id": report_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "life": load_latest_life(),
        "ollama": parse_ollama_ps(),
        "gpu": parse_nvidia(),
        "ram": parse_ram(),
    }
    path = OUT_DIR / f"{report_id}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Kira GPU bridge status")
    print("======================")
    life = report["life"]
    print(f"Life run: {life.get('run_id', 'none')} status={life.get('status', 'unknown')} cycles={life.get('cycles', 'unknown')} errors={life.get('errors', 'unknown')}")
    print(f"Ollama: model={report['ollama'].get('model') or 'none'} processor={report['ollama'].get('processor') or 'none'}")
    gpu = report["gpu"]
    if gpu.get("ok"):
        used = round(gpu["memory_used_mb"] / 1024, 2)
        total = round(gpu["memory_total_mb"] / 1024, 2)
        print(f"GPU: {gpu['name']} {used}/{total}GB {gpu['temperature_c']}C util={gpu['utilization_percent']}% power={gpu['power_draw_w']}W")
    else:
        print(f"GPU: {gpu.get('detail', 'unknown')}")
    ram = report["ram"]
    if ram.get("ok"):
        print(f"RAM: {ram['free_gb']}/{ram['total_gb']}GB free, used={ram['used_percent']}%")
    print(f"Saved: {path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
