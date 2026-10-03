#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线自检：校验纯函数与 CLI 帮助面，不发起网络请求。"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import ximalaya_album_downloader as xl  # noqa: E402


def check_pure_functions() -> None:
    assert xl.get_album_id("https://www.ximalaya.com/album/72503439") == "72503439"
    try:
        xl.get_album_id("https://example.com/nope")
        raise AssertionError("expected ValueError for invalid album URL")
    except ValueError:
        pass
    assert ":" not in xl.sanitize_filename('a:b/c*?"')
    assert xl.sanitize_filename("   ") == "untitled"
    assert xl.fmt_duration(65) == "1:05"
    assert xl.fmt_size(2048).endswith("KB")


def check_skip_existing_alt_name() -> None:
    """兼容非补零文件名时应识别为已存在并跳过。"""
    with tempfile.TemporaryDirectory() as tmp:
        title = "样例标题"
        alt = os.path.join(tmp, f"3_{title}.m4a")
        with open(alt, "wb") as f:
            f.write(b"x")
        track = {"index": 3, "trackId": 1, "title": title, "status": None}
        idx, st, fname, err = xl.download_one(track, tmp, width=3, headers={})
        assert idx == 3 and st == "skip" and err is None
        assert fname in (f"003_{title}.m4a", f"3_{title}.m4a")


def check_cli_help() -> None:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "ximalaya_album_downloader.py"), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or "help exited non-zero"
    help_text = proc.stdout or ""
    for flag in ("--start", "--end", "--dry-run", "--to-mp3", "--no-manifest", "--workers", "--only-list"):
        assert flag in help_text, f"missing flag in --help: {flag}"


def main() -> int:
    ap = argparse.ArgumentParser(description="ximalaya-downloader 离线自检")
    ap.parse_args()
    check_pure_functions()
    check_skip_existing_alt_name()
    check_cli_help()
    print("self_check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
