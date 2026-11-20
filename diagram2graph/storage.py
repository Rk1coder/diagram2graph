import os
import tempfile
import time
from pathlib import Path


def private_cache(path=None):
    root = (
        Path(path) if path else Path(tempfile.gettempdir()) / f"diagram2graph-cache-{os.getuid()}"
    )
    if root.is_symlink():
        raise ValueError("Cache directory must not be a symlink.")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.stat().st_uid != os.getuid():
        raise ValueError("Cache directory must belong to the current user.")
    root.chmod(0o700)
    return root


def prune_cache(root, *, now=None):
    root = Path(root)
    now = time.time() if now is None else now
    for directory, subdirs, files in os.walk(root, followlinks=False):
        subdirs[:] = [name for name in subdirs if not (Path(directory) / name).is_symlink()]
        for name in files:
            path = Path(directory) / name
            if path.is_symlink():
                continue
            try:
                stat = path.stat()
                if now - max(stat.st_mtime, stat.st_ctime) > 3600:
                    path.unlink()
            except FileNotFoundError:
                pass
    for directory, _, _ in os.walk(root, topdown=False, followlinks=False):
        path = Path(directory)
        if path == root or path.is_symlink():
            continue
        try:
            path.rmdir()
        except OSError:
            pass
