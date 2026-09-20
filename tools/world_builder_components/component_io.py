"""Local immutable artifact writes and nonblocking job locks; no research dependency."""
from pathlib import Path
from contextlib import contextmanager
import tempfile

class ComponentIOError(ValueError):
    pass

def preserve_bytes(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() != payload:
            raise ComponentIOError("Refusing to overwrite a preserved source artifact")
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".partial", delete=False) as handle:
        temp = Path(handle.name)
        handle.write(payload)
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)

@contextmanager
def job_lock(job_dir: Path):
    handle = (job_dir / ".run.lock").open("a+b")
    handle.seek(0, 2)
    if not handle.tell():
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        if __import__("os").name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise ComponentIOError("This saved job is already running") from exc
    try:
        yield
    finally:
        handle.close()
