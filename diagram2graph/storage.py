import os
import tempfile
import time
from pathlib import Path

MARKER = ".diagram2graph-owner"
MAGIC = f"diagram2graph-cache-v1:{os.getuid()}\n"


def _verify(root):
    root = Path(root)
    marker = root / MARKER
    if root.is_symlink() or not root.is_dir() or root.stat().st_uid != os.getuid():
        raise ValueError("Cache must be an application-owned directory.")
    if (
        marker.is_symlink()
        or not marker.is_file()
        or marker.stat().st_size > 256
        or marker.read_text() != MAGIC
    ):
        raise ValueError("Refusing to clean an unmarked directory.")


def private_cache(path=None):
    # The configured path is a parent, never a disposable directory itself.
    parent = (
        Path(path) if path else Path(tempfile.gettempdir()) / f"diagram2graph-cache-{os.getuid()}"
    )
    if parent.is_symlink():
        raise ValueError("Cache parent must not be a symlink.")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    root = parent / ".diagram2graph-owned"
    if root.is_symlink():
        raise ValueError("Cache directory must not be a symlink.")
    root.mkdir(exist_ok=True, mode=0o700)
    if root.stat().st_uid != os.getuid():
        raise ValueError("Cache directory must belong to the current user.")
    marker = root / MARKER
    if not any(root.iterdir()):
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write(MAGIC)
    _verify(root)
    root.chmod(0o700)
    return root


def prune_cache(root, *, now=None):
    root = Path(root)
    _verify(root)
    now = time.time() if now is None else now
    for directory, subdirs, files in os.walk(root, followlinks=False):
        subdirs[:] = [name for name in subdirs if not (Path(directory) / name).is_symlink()]
        for name in files:
            path = Path(directory) / name
            if path == root / MARKER or path.is_symlink():
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
