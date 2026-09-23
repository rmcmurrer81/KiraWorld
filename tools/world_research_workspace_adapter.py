"""Thin saved-job adapter for the isolated native World Builder workspace."""
from pathlib import Path
from world_research import DEFAULT_JOB_ROOT, ResearchError, brief_from_prompt, create_job, read_json


def submit_research_prompt(prompt: str, *, job_root: Path = DEFAULT_JOB_ROOT, latest_job: Path | None = None,
                           source_urls: list[str] | None = None, max_queries: int = 4, max_pages: int = 4) -> dict:
    if prompt.strip().lower() in {"resume", "resume research", "continue research", "retry research"}:
        if latest_job is None:
            candidates = list(job_root.glob("world_research_*/job.json")) if job_root.exists() else []
            latest_job = max(candidates, key=lambda path: path.stat().st_mtime).parent if candidates else None
        if latest_job is None:
            raise ResearchError("No saved research job to resume")
        path = latest_job
    else:
        brief = brief_from_prompt(prompt, source_urls=source_urls, max_queries=max_queries, max_pages=max_pages)
        path = create_job(brief, job_root=job_root)
    job = read_json(path / "job.json")
    return {"job_dir": path, "job_id": job["job_id"], "stage": job["stage"], "subject": job["brief"]["subject"],
            "research_mode": job["brief"]["research_mode"], "visual_style": job["brief"]["visual_style"]}
