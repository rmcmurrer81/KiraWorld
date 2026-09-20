"""Save bounded WebM bytes only in this preview's dedicated local output directory."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid

MAX_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_SECONDS = 30
ALLOWED_MIME = {'video/webm', 'video/webm;codecs=vp8', 'video/webm;codecs=vp9'}


class RecordingError(ValueError):
    pass


def plain_directory(path):
    for part in (path, *path.parents):
        if part.exists():
            stat = part.lstat()
            if part.is_symlink() or getattr(stat,'st_file_attributes',0) & 0x400:
                raise RecordingError('Recording directory cannot follow a link or junction')
    if not path.is_dir():
        raise RecordingError('Recording directory is unavailable')


def save_webm(candidate_root, stream, length, mime, set_timeout=lambda _:None, clock=time.monotonic):
    """Caller serializes saves. No caller-supplied filename or destination is accepted."""
    if type(length) is not int or not 0 < length <= MAX_BYTES:
        raise RecordingError('Recording must be between 1 byte and 64 MiB')
    if mime.lower().replace(' ','') not in ALLOWED_MIME:
        raise RecordingError('Only WebM video is accepted')
    root = Path(candidate_root).absolute()
    plain_directory(root)
    folder = root/'recording-output'
    folder.mkdir(exist_ok=True)
    plain_directory(folder)
    total = 0
    for path in folder.iterdir():
        if path.is_symlink() or getattr(path.lstat(),'st_file_attributes',0) & 0x400 or not path.is_file():
            raise RecordingError('Unexpected recording output entry')
        total += path.stat().st_size
    if total + length + 4096 > MAX_TOTAL_BYTES:
        raise RecordingError('Local recording directory reached its 256 MiB limit')
    identifier = uuid.uuid4().hex
    filename = 'Kira-Mattress-Physics-Engineering-' + identifier + '.webm'
    final = folder/filename
    temporary = folder/('.recording-' + identifier + '.partial')
    receipt_temporary = folder/('.receipt-' + identifier + '.partial')
    digest = hashlib.sha256();remaining = length;prefix = b'';deadline = clock()+MAX_SECONDS
    temporary_owned = False;receipt_temporary_owned = False
    try:
        with temporary.open('xb') as handle:
            temporary_owned = True
            while remaining:
                left = deadline-clock()
                if left <= 0: raise RecordingError('Recording save timed out')
                set_timeout(min(5,left))
                chunk = stream.read1(min(1024*1024,remaining)) if hasattr(stream,'read1') else stream.read(min(1024*1024,remaining))
                if not chunk: raise RecordingError('Recording ended before all declared bytes arrived')
                remaining -= len(chunk);handle.write(chunk);digest.update(chunk)
                if len(prefix)<4096:prefix += chunk[:4096-len(prefix)]
            if not prefix.startswith(b'\x1a\x45\xdf\xa3') or b'webm' not in prefix:
                raise RecordingError('Recording is not a WebM container')
            handle.flush();os.fsync(handle.fileno())
        plain_directory(folder)
        # A hard-link publication refuses an existing destination atomically.
        os.link(temporary,final)
        actual = hashlib.sha256()
        with final.open('rb') as handle:
            for chunk in iter(lambda:handle.read(1024*1024),b''):actual.update(chunk)
        if final.stat().st_size != length or actual.hexdigest() != digest.hexdigest():
            raise RecordingError('Saved recording verification failed')
        result = {'status':'saved_verified','filename':filename,'relative_path':'recording-output/'+filename,
                  'receipt_filename':filename+'.json','bytes':length,'sha256':actual.hexdigest(),
                  'container':'webm','media_decode_verified':False}
        receipt = json.dumps(result,sort_keys=True,indent=2).encode('utf-8')
        with receipt_temporary.open('xb') as handle:
            receipt_temporary_owned = True
            handle.write(receipt);handle.flush();os.fsync(handle.fileno())
        os.link(receipt_temporary,folder/result['receipt_filename'])
        if (folder/result['receipt_filename']).read_bytes()!=receipt:
            raise RecordingError('Saved recording receipt verification failed')
        return result
    finally:
        if temporary_owned and temporary.exists():temporary.unlink()
        if receipt_temporary_owned and receipt_temporary.exists():receipt_temporary.unlink()


def parse_upload_headers(headers):
    if headers.get_all('Transfer-Encoding'):
        raise RecordingError('Chunked recording requests are not accepted')
    lengths = headers.get_all('Content-Length',[])
    mimes = headers.get_all('Content-Type',[])
    if len(lengths)!=1 or not re.fullmatch('[0-9]{1,9}',lengths[0]) or len(mimes)!=1:
        raise RecordingError('One recording length and MIME type are required')
    length = int(lengths[0]);mime = mimes[0]
    if not 0 < length <= MAX_BYTES:raise RecordingError('Recording exceeds the 64 MiB limit')
    if mime.lower().replace(' ','') not in ALLOWED_MIME:raise RecordingError('Only WebM video is accepted')
    return length,mime
