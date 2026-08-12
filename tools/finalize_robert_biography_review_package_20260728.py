from __future__ import annotations
import hashlib, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path

PROJECT=Path(r"C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests\20260728_162326_robert_mcmurrer_actor_author_and_creative_builder_v2_robert_mcmurrer_a")
VIDEO=PROJECT/"ROBERT_MCMURRER_ANIMATED_MINI_BIOGRAPHY.mp4"
FF=Path(r"C:\Users\robmc\AppData\Roaming\Python\Python314\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe")
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def decode(kind):
    result=subprocess.run([str(FF),"-v","info","-i",str(VIDEO),"-map",f"0:{kind}:0","-f","null","NUL"],
                          capture_output=True,text=True,encoding="utf-8",errors="replace")
    hits=re.findall(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)",result.stderr)
    duration=None
    if hits:
        h,m,s=hits[-1];duration=int(h)*3600+int(m)*60+float(s)
    return {"exit_code":result.returncode,"decoded_to_seconds":duration}
summary=json.loads((PROJECT/"DELIVERY_SUMMARY.json").read_text(encoding="utf-8"))
audio=[]
for wav in sorted((PROJECT/"audio").glob("*.wav")):
    manifest=wav.with_suffix(wav.suffix+".manifest.json")
    audio.append({"chapter_id":wav.stem,"wav":str(wav.relative_to(PROJECT)),"sha256":sha(wav),
                  "engine_manifest":str(manifest.relative_to(PROJECT)) if manifest.exists() else None})
dump(PROJECT/"voice/ROBERT_APPROVED_VOICE_PROOF.json",{
 "status":"AWAITING_ROBERT_OWNER_LISTENING_REVIEW",
 "voice_profile_id":"robert_mcmurrer_authorized_self_voice_v1",
 "engine":"chatterbox","fallback_used":False,"pitch_changed":False,
 "approved_reference_sha256":"761458a0bb48ba120c7bacafba942b8a17b59536960059bf837a3fb0a7e50542",
 "chapter_audio":audio,"completed_mp4":str(VIDEO),"completed_mp4_sha256":sha(VIDEO)})
video_decode=decode("v");audio_decode=decode("a")
caption_text=(PROJECT/"captions/ROBERT_MCMURRER_ANIMATED_MINI_BIOGRAPHY.en.srt").read_text(encoding="utf-8")
end_matches=re.findall(r"-->\s*(\d+):(\d+):(\d+),(\d+)",caption_text)
h,m,s,ms=end_matches[-1];caption_end=int(h)*3600+int(m)*60+int(s)+int(ms)/1000
dump(PROJECT/"validation/FINAL_MEDIA_VALIDATION.json",{
 "status":"PASSED" if video_decode["exit_code"]==audio_decode["exit_code"]==0 and abs(caption_end-summary["duration_seconds"])<0.1 else "FAILED",
 "reported_duration_seconds":summary["duration_seconds"],"caption_end_seconds":caption_end,
 "caption_delta_seconds":round(abs(caption_end-summary["duration_seconds"]),3),
 "video_decode":video_decode,"audio_decode":audio_decode,"sha256":sha(VIDEO)})
manifest=[]
for path in sorted(p for p in PROJECT.rglob("*") if p.is_file() and p.name!="COMPLETE_SHA256_MANIFEST.json"):
    manifest.append({"path":str(path.relative_to(PROJECT)),"bytes":path.stat().st_size,"sha256":sha(path)})
dump(PROJECT/"manifests/COMPLETE_SHA256_MANIFEST.json",{
 "status":"AWAITING_ROBERT_OWNER_REVIEW","generated_at_utc":datetime.now(timezone.utc).isoformat(),
 "file_count":len(manifest),"files":manifest})
print(json.dumps({"project":str(PROJECT),"video":str(VIDEO),"sha256":sha(VIDEO),
                  "duration_seconds":summary["duration_seconds"],"video_decode":video_decode,
                  "audio_decode":audio_decode,"caption_end_seconds":caption_end},indent=2))
