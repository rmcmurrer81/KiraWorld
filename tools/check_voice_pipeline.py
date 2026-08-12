"""Report voice-reference and model pipeline readiness."""
from __future__ import annotations
import importlib.util, json, shutil, subprocess, sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from Core.voice_reference_pipeline import ffmpeg_readiness

def main() -> None:
    gpu = {"available": False, "name": "", "vram_mib": ""}
    if exe := shutil.which("nvidia-smi"):
        run = subprocess.run([exe, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=20, check=False)
        if run.returncode == 0 and run.stdout.strip():
            name, _, memory = run.stdout.strip().partition(","); gpu = {"available": True, "name": name.strip(), "vram_mib": memory.strip()}
    torch_runtime = {"imported": False, "version": "", "cuda_runtime": "", "cuda_available": False, "cuda_kernel_ok": False, "cuda_error": ""}
    try:
        import torch

        torch_runtime["imported"] = True
        torch_runtime["version"] = str(torch.__version__)
        torch_runtime["cuda_runtime"] = str(torch.version.cuda or "")
        torch_runtime["cuda_available"] = bool(torch.cuda.is_available())
        if torch_runtime["cuda_available"]:
            try:
                value = torch.ones(1, device="cuda") + torch.ones(1, device="cuda")
                torch.cuda.synchronize()
                torch_runtime["cuda_kernel_ok"] = bool(float(value.cpu()[0]) == 2.0)
            except Exception as exc:
                torch_runtime["cuda_error"] = str(exc)
    except Exception as exc:
        torch_runtime["cuda_error"] = str(exc)
    packages = {
        name: bool(importlib.util.find_spec(module))
        for name, module in {
            "yt-dlp": "yt_dlp",
            "pypdf": "pypdf",
            "imageio-ffmpeg": "imageio_ffmpeg",
            "torch": "torch",
            "torchaudio": "torchaudio",
            "chatterbox-tts": "chatterbox",
            "soundfile": "soundfile",
        }.items()
    }
    ffmpeg = ffmpeg_readiness()
    print(
        json.dumps(
            {
                "python": sys.version,
                "gpu": gpu,
                "torch_runtime": torch_runtime,
                "ffmpeg": ffmpeg,
                "packages": packages,
                "stages": {
                    "url_metadata_and_captions": packages["yt-dlp"],
                    "local_audio_extraction": ffmpeg["ready"],
                    "script_inventory": packages["pypdf"],
                    "voice_model_backend": packages["torch"] and packages["torchaudio"],
                    "local_chatterbox_tts": packages["chatterbox-tts"] and packages["soundfile"],
                },
                "note": "The model backend remains separate from source collection and speaker review.",
            },
            indent=2,
        )
    )
if __name__ == "__main__": main()
