"""Single-open, root-confined WAV inspection; never copies or enrolls audio."""
from __future__ import annotations
import hashlib, hmac, os, stat, wave
from pathlib import Path
from .errors import ValidationError
from .models import ReferenceDescriptor

MAX_REFERENCE_BYTES=64*1024*1024; MIN_REFERENCE_SECONDS=.5; MAX_REFERENCE_SECONDS=180.0
ALLOWED_SAMPLE_RATES=frozenset({16_000,22_050,24_000,32_000,44_100,48_000})


def _open_reference_read_only(path: Path) -> int:
    """Open one non-inheritable read handle that excludes concurrent writers.

    ``os.open`` on Windows normally permits another process to open the same
    file for writing.  NTFS timestamp propagation is not a sufficient mutation
    signal, so use ``CreateFileW`` with read sharing only.  Existing writers
    make this open fail, and writers/delete-replacers cannot open until the
    returned descriptor is closed.
    """

    if os.name != "nt":
        return os.open(
            path,
            os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )

    import ctypes
    import msvcrt
    from ctypes import wintypes

    create_file = ctypes.WinDLL("kernel32", use_last_error=True).CreateFileW
    create_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create_file.restype = wintypes.HANDLE
    close_handle = ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL

    generic_read = 0x80000000
    file_share_read = 0x00000001
    open_existing = 3
    file_attribute_normal = 0x00000080
    file_flag_sequential_scan = 0x08000000
    handle = create_file(
        str(path),
        generic_read,
        file_share_read,
        None,
        open_existing,
        file_attribute_normal | file_flag_sequential_scan,
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if handle is None or handle == invalid_handle:
        error = ctypes.get_last_error()
        raise OSError(error, "reference could not be opened without write sharing", str(path))
    try:
        return msvcrt.open_osfhandle(
            int(handle),
            os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0),
        )
    except Exception:
        close_handle(handle)
        raise

def inspect_wav(path: Path, *, allowed_root: Path | None = None) -> ReferenceDescriptor:
    raw_path = str(path)
    if raw_path.startswith("\\\\") or raw_path.startswith("//"):
        raise ValidationError("UNC reference paths are not accepted")
    root = allowed_root.resolve(strict=True) if allowed_root else path.parent.resolve(strict=True)
    requested = path.absolute()
    if requested.suffix.lower() != ".wav": raise ValidationError("reference must be an existing .wav file")
    if path.is_symlink() or (hasattr(os.path,"isjunction") and os.path.isjunction(path)):
        raise ValidationError("reference cannot be a link or junction")
    try: resolved = path.resolve(strict=True); resolved.relative_to(root)
    except (OSError, ValueError) as exc: raise ValidationError("reference is outside the configured intake root") from exc
    try: fd=_open_reference_read_only(resolved)
    except OSError as exc: raise ValidationError("reference is not readable") from exc
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not 44 < info.st_size <= MAX_REFERENCE_BYTES:
            raise ValidationError("reference WAV size or type is invalid")
        with os.fdopen(fd,"rb",closefd=False) as handle:
            digest=hashlib.sha256()
            for block in iter(lambda:handle.read(1024*1024),b""): digest.update(block)
            handle.seek(0)
            try:
                audio=wave.open(handle,"rb"); channels=audio.getnchannels(); width=audio.getsampwidth()
                rate=audio.getframerate(); frames=audio.getnframes(); compression=audio.getcomptype()
                data=audio.readframes(frames); audio.close()
            except (wave.Error,EOFError) as exc: raise ValidationError("reference is not a readable PCM WAV") from exc
            handle.seek(0)
            verification_digest=hashlib.sha256()
            for block in iter(lambda:handle.read(1024*1024),b""): verification_digest.update(block)
            if not hmac.compare_digest(digest.digest(),verification_digest.digest()):
                raise ValidationError("reference changed during inspection")
        if compression!="NONE" or channels not in {1,2} or width not in {2,3,4}:
            raise ValidationError("reference WAV format is unsupported")
        if rate not in ALLOWED_SAMPLE_RATES: raise ValidationError("reference WAV sample rate is unsupported")
        if len(data)!=frames*channels*width: raise ValidationError("reference WAV sample data is truncated")
        duration=frames/rate if rate else 0
        if not MIN_REFERENCE_SECONDS<=duration<=MAX_REFERENCE_SECONDS:
            raise ValidationError("reference WAV duration is outside the allowed range")
        after=os.fstat(fd)
        try: named=resolved.stat(follow_symlinks=False)
        except OSError as exc: raise ValidationError("reference changed during inspection") from exc
        # On Windows, CPython can report slightly different ``st_ctime_ns``
        # values for ``fstat(handle)`` and ``stat(path)`` on the same unchanged
        # NTFS file.  File identity, size, and modification time are stable
        # across both APIs; creation/change time is therefore not a reliable
        # cross-API mutation signal here.  The open-handle digest above still
        # binds the descriptor to the exact bytes that were inspected.
        before_identity=(info.st_dev,info.st_ino,info.st_size,getattr(info,"st_mtime_ns",None))
        after_identity=(after.st_dev,after.st_ino,after.st_size,getattr(after,"st_mtime_ns",None))
        named_identity=(named.st_dev,named.st_ino,named.st_size,getattr(named,"st_mtime_ns",None))
        if before_identity!=after_identity or after_identity!=named_identity:
            raise ValidationError("reference changed during inspection")
        return ReferenceDescriptor(digest.hexdigest(),info.st_size,round(duration,6),channels,width,rate,frames)
    finally: os.close(fd)
