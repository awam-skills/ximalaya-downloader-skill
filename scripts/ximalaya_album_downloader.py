#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
喜马拉雅专辑下载脚本 (Ximalaya Album Downloader)

原理（均为喜马拉雅公开接口，无需登录、无 webtk 依赖）：
  1. 专辑列表:  GET https://www.ximalaya.com/revision/play/v1/show?id=<albumId>&num=<page>&size=<pageSize>&ptype=0
                -> data.tracksAudioPlay[]  (每集 trackId / trackName / trackUrl / duration)
  2. 单集直链:  GET https://m.ximalaya.com/tracks/<trackId>.json
                -> play_path_64 / play_path_32  (m4a 直链), is_paid=False 表示免费可下
  说明: 本脚本仅下载免费/可合法获取的音频。

功能：
  - 下载专辑全部/区间音频为 m4a，按"集号_标题"命名并自动建专辑目录
  - 默认生成 Markdown 格式专辑目录清单（专辑名_清单.md）
  - 可选 --to-mp3：用 ffmpeg 把 m4a 批量转成 mp3（默认不转）

用法:
  python ximalaya_album_downloader.py <album_url> [-o <output_dir>]
      [--start N] [--end N] [--only-list] [--to-mp3] [--no-manifest] [--page-size N]

示例:
  python ximalaya_album_downloader.py "https://www.ximalaya.com/album/72503439"
  python ximalaya_album_downloader.py "https://www.ximalaya.com/album/72503439" -o "D:\Downloads" --to-mp3
  python ximalaya_album_downloader.py "https://www.ximalaya.com/album/72503439" --start 10 --end 20
  python ximalaya_album_downloader.py "https://www.ximalaya.com/album/72503439" --only-list
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

UA_PC = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
UA_MOBILE = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"

PAGE_SIZE = 30
TIMEOUT = 30
RETRY = 3


class HTTP:
    @staticmethod
    def get_json(url, headers, retry=RETRY):
        for i in range(retry):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    raw = resp.read()
                    return json.loads(raw.decode("utf-8"))
            except Exception as e:
                if i == retry - 1:
                    raise
                time.sleep(2 * (i + 1))

    @staticmethod
    def download(url, path, headers, retry=RETRY):
        for i in range(retry):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp, open(path, "wb") as f:
                    while True:
                        chunk = resp.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                return True
            except Exception as e:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                if i == retry - 1:
                    raise
                time.sleep(2 * (i + 1))


def sanitize_filename(name):
    """去除 Windows 文件系统非法字符并清理空白。"""
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name or "untitled"


def get_album_id(url):
    m = re.search(r"/album/(\d+)", url)
    if not m:
        raise ValueError(f"无法从 URL 解析专辑 ID: {url}")
    return m.group(1)


def fetch_all_tracks(album_id, headers, start=None, end=None):
    """分页拉取专辑全部曲目（含 trackId / title / trackUrl / duration）。"""
    tracks = []
    page = 1
    while True:
        url = ("https://www.ximalaya.com/revision/play/v1/show"
               f"?id={album_id}&num={page}&size={PAGE_SIZE}&ptype=0")
        data = HTTP.get_json(url, headers)
        if data.get("ret") != 200:
            raise RuntimeError(f"专辑列表接口异常 ret={data.get('ret')} msg={data.get('msg')}")
        batch = (data.get("data") or {}).get("tracksAudioPlay") or []
        for t in batch:
            tracks.append({
                "index": t.get("index"),
                "trackId": t.get("trackId"),
                "trackUrl": t.get("trackUrl"),
                "title": t.get("trackName"),
                "duration": t.get("duration"),
            })
        if len(batch) < PAGE_SIZE:
            break
        page += 1
        time.sleep(0.3)

    total = len(tracks)
    # 支持区间下载（1-based）
    if start is not None or end is not None:
        lo = start if start is not None else 1
        hi = end if end is not None else total
        tracks = [t for t in tracks if lo <= t["index"] <= hi]
    return tracks


def fetch_audio_url(track_id, headers):
    """取单集 m4a 直链（优先 play_path_64，其次 play_path_32）。"""
    url = f"https://m.ximalaya.com/tracks/{track_id}.json"
    info = HTTP.get_json(url, headers)
    link = info.get("play_path_64") or info.get("play_path_32") or info.get("play_path")
    if not link:
        raise RuntimeError(f"track {track_id} 无可用播放直链 is_paid={info.get('is_paid')}")
    if info.get("is_paid"):
        raise RuntimeError(f"track {track_id} 为付费/VIP 内容，无法免费下载")
    return link, info


def find_ffmpeg():
    """定位 ffmpeg 可执行文件。"""
    for cand in ("ffmpeg", "ffmpeg.exe"):
        p = shutil.which(cand)
        if p:
            return p
    # 常见兜底路径
    for base in (os.environ.get("LOCALAPPDATA", ""), "C:\\ffmpeg\\bin", "C:\\Program Files\\ffmpeg\\bin"):
        cand = os.path.join(base, "bin", "ffmpeg.exe") if base else ""
        cand2 = os.path.join(base, "ffmpeg.exe") if base else ""
        for c in (cand, cand2):
            if c and os.path.exists(c):
                return c
    return None


def convert_m4a_to_mp3(out_dir, width):
    """把目录内 m4a 批量转成 mp3（保留原文件，新增同名 mp3）。返回 (成功数, 失败数)。"""
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("[to-mp3] 未找到 ffmpeg，跳过转换（可安装后重跑 --to-mp3）", file=sys.stderr)
        return 0, 0
    m4a_files = sorted(
        f for f in os.listdir(out_dir)
        if f.lower().endswith(".m4a") and not f.startswith(".")
    )
    ok = fail = 0
    print(f"[to-mp3] 找到 {len(m4a_files)} 个 m4a，开始转换为 mp3 ...")
    for f in m4a_files:
        src = os.path.join(out_dir, f)
        mp3 = os.path.join(out_dir, os.path.splitext(f)[0] + ".mp3")
        if os.path.exists(mp3) and os.path.getsize(mp3) > 0:
            print(f"[to-mp3] 跳过已存在 {os.path.basename(mp3)}")
            ok += 1
            continue
        try:
            subprocess.run(
                [ffmpeg, "-y", "-i", src, "-codec:a", "libmp3lame", "-q:a", "2", mp3],
                check=True, capture_output=True, timeout=600)
            ok += 1
            print(f"[to-mp3] 完成 {os.path.basename(mp3)}")
        except Exception as e:
            fail += 1
            print(f"[to-mp3] 失败 {f}: {e}", file=sys.stderr)
    return ok, fail


def fmt_size(nbytes):
    if nbytes is None:
        return "-"
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f}{unit}"
        nbytes /= 1024
    return f"{nbytes:.1f}TB"


def fmt_duration(seconds):
    if not seconds:
        return "-"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def write_manifest(out_dir, album_title, album_id, tracks, url):
    """生成 Markdown 格式专辑目录清单：<专辑名>_清单.md。返回清单路径。"""
    mf_name = f"{album_title}_清单.md"
    mf_path = os.path.join(out_dir, mf_name)
    lines = [
        f"# {album_title}",
        "",
        f"- 专辑链接：{url}",
        f"- 专辑 ID：{album_id}",
        f"- 共 {len(tracks)} 集",
        "",
        "| 集号 | 标题 | 时长 | 文件 | 大小 |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for t in tracks:
        idx = t["index"]
        title = t["title"] or ""
        fname = None
        size = None
        # 在目录中查找该集的实际文件
        for cand in os.listdir(out_dir):
            if cand.startswith(f"{idx:0{len(str(len(tracks))) if len(tracks) >= 10 else 3}d}_") or cand.startswith(f"{idx}_"):
                if cand.lower().endswith((".m4a", ".mp3")):
                    fname = cand
                    size = os.path.getsize(os.path.join(out_dir, cand))
                    break
        if fname:
            fname = f"`{fname}`"
        else:
            fname = "-"
        lines.append(f"| {idx} | {title} | {fmt_duration(t['duration'])} | {fname} | {fmt_size(size)} |")
    with open(mf_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return mf_path


def main():
    global PAGE_SIZE
    ap = argparse.ArgumentParser(description="喜马拉雅免费专辑下载器（含 m4a→mp3 可选转换与 MD 清单）")
    ap.add_argument("url", help="专辑链接，如 https://www.ximalaya.com/album/72503439")
    ap.add_argument("-o", "--output", default=None, help="输出目录（默认: 桌面/Downloads）")
    ap.add_argument("--start", type=int, default=None, help="起始集号（1-based，可选）")
    ap.add_argument("--end", type=int, default=None, help="结束集号（1-based，可选）")
    ap.add_argument("--only-list", action="store_true", help="仅列出曲目，不下载")
    ap.add_argument("--to-mp3", action="store_true", help="下载后用 ffmpeg 把 m4a 转成 mp3（默认不转）")
    ap.add_argument("--no-manifest", action="store_true", help="不生成 Markdown 目录清单（默认生成）")
    ap.add_argument("--page-size", type=int, default=PAGE_SIZE, help="列表页大小")
    args = ap.parse_args()

    PAGE_SIZE = args.page_size

    album_id = get_album_id(args.url)
    headers_pc = {"User-Agent": UA_PC, "Referer": f"https://www.ximalaya.com/album/{album_id}"}
    headers_mobile = {"User-Agent": UA_MOBILE, "Referer": "https://m.ximalaya.com/"}

    print(f"[专辑ID] {album_id}")
    tracks = fetch_all_tracks(album_id, headers_pc, args.start, args.end)
    if not tracks:
        print("未获取到任何曲目，可能专辑为空或区间无效。")
        sys.exit(1)
    print(f"[曲目数] 共 {len(tracks)} 集（区间内）")

    # 专辑标题：从第一集 data 的 albumTitle 获取
    album_title = f"album_{album_id}"
    try:
        _, first_info = fetch_audio_url(tracks[0]["trackId"], headers_mobile)
        if first_info.get("album_title"):
            album_title = sanitize_filename(first_info["album_title"])
    except Exception:
        pass
    album_dir = sanitize_filename(album_title)
    print(f"[专辑名] {album_title}")

    if args.only_list:
        for t in tracks:
            print(f"{t['index']:>3}  {t['title']}")
        return

    # 输出目录
    if args.output:
        out_root = args.output
    else:
        out_root = os.path.join(os.path.expanduser("~"), "Downloads")
    out_dir = os.path.join(out_root, album_dir)
    os.makedirs(out_dir, exist_ok=True)
    print(f"[下载到] {out_dir}")

    total_all = len(tracks) if (args.start is not None or args.end is not None) else len(tracks)
    width = len(str(total_all))
    ok = fail = skipped = 0
    for t in tracks:
        idx = t["index"]
        title = sanitize_filename(t["title"] or f"track_{t['trackId']}")
        fname = f"{idx:0{width}d}_{title}.m4a"
        fpath = os.path.join(out_dir, fname)
        # 兼容已存在的补零/非补零命名，避免区间下载时重复下载
        exists = os.path.exists(fpath) and os.path.getsize(fpath) > 0
        if not exists:
            alt = f"{idx}_{title}.m4a"
            if os.path.exists(alt) and os.path.getsize(alt) > 0:
                exists = True
        if exists:
            print(f"[跳过] 已存在 {os.path.basename(fpath)}")
            skipped += 1
            continue
        try:
            link, _ = fetch_audio_url(t["trackId"], headers_mobile)
            HTTP.download(link, fpath, headers_mobile)
            ok += 1
            print(f"[{ok+skipped:>3}/{len(tracks)}] 完成 {fname}")
        except Exception as e:
            fail += 1
            print(f"[失败] {fname}: {e}", file=sys.stderr)

    # 可选转 mp3
    if args.to_mp3:
        conv_ok, conv_fail = convert_m4a_to_mp3(out_dir, width)
        print(f"[to-mp3] 转换完成: 成功 {conv_ok}，失败 {conv_fail}")

    # 默认生成 MD 清单
    if not args.no_manifest:
        mf_path = write_manifest(out_dir, album_title, album_id, tracks, args.url)
        print(f"[清单] 已生成: {mf_path}")

    print(f"\n完成: 成功 {ok}，跳过 {skipped}，失败 {fail}，目录: {out_dir}")


if __name__ == "__main__":
    main()
