import os

import pytest

from diagram2graph.storage import private_cache, prune_cache


def test_restart_cleanup_discovers_old_cache_without_process_registry(tmp_path):
    root = private_cache(tmp_path / "cache")
    old = root / "old-session" / "upload.png"
    old.parent.mkdir()
    old.write_bytes(b"old screenshot")
    now = old.stat().st_ctime + 4000
    fresh = root / "fresh-session" / "upload.png"
    fresh.parent.mkdir()
    fresh.write_bytes(b"new screenshot")
    os.utime(fresh, (now, now))
    sample = tmp_path / "public-example.png"
    sample.write_bytes(b"public example")
    # Reopen the directory as a new process would: no in-memory cache registry.
    reopened = private_cache(tmp_path / "cache")
    prune_cache(reopened, now=now)
    assert not old.exists()
    assert fresh.exists() and sample.exists()
    assert root.stat().st_mode & 0o777 == 0o700


def test_private_cache_refuses_symlink_and_never_follows_nested_links(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "keep.txt"
    secret.write_text("untouched")
    link = tmp_path / "linked-root"
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        private_cache(link)
    root = private_cache(tmp_path / "cache")
    (root / "external").symlink_to(outside, target_is_directory=True)
    prune_cache(root, now=secret.stat().st_ctime + 4000)
    assert secret.read_text() == "untouched"
