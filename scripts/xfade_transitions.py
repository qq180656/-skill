#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""段间 xfade 叠化后处理（治段间硬切观感，零生成成本，纯 ffmpeg 层）。

用法：
    python xfade_transitions.py --input 成片/ --output 成片_叠化/ --duration 0.4
    python xfade_transitions.py --input a.mp4 --output b.mp4   # 单文件

按成片里的 _segs/ 段文件重新拼接：段间加 xfade 叠化（默认0.4s），段内不动。
无 _segs 段文件的成品（单段）直接复制。
注意：叠化会吃掉两段各一半的叠化时长（总时长=Σ段长-n×duration），台词在切点处
若无缝衔接会轻微交叠——保险剧情片切点都在台词说完后+段尾留1.5-2s余韵，0.4s安全。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

FFMPEG = r"C:\Users\A\Desktop\build_video\tools\ffmpeg.exe"
if not Path(FFMPEG).is_file():
    FFMPEG = "ffmpeg"


def probe_dur(p: Path) -> float:
    r = subprocess.run(
        [FFMPEG, "-i", str(p), "-f", "null", "-"],
        capture_output=True, timeout=120)
    err = r.stderr
    if isinstance(err, bytes):
        err = err.decode("utf-8", errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err or "")
    if not m:
        raise RuntimeError(f"读不到时长: {p}")
    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mi * 60 + s


def build_xfade(seg_files: list, out: Path, d: float) -> bool:
    """多段 xfade 拼接（重编码，保证各段参数一致后才能叠化）。"""
    n = len(seg_files)
    if n == 1:
        subprocess.run([FFMPEG, "-y", "-i", str(seg_files[0]),
                        "-c", "copy", str(out)], check=True, timeout=600)
        return True

    inputs, filters = [], []
    for i, f in enumerate(seg_files):
        inputs += ["-i", str(f)]
    # 归一化每段（720p/fps统一）→ 逐级 xfade
    for i in range(n):
        filters.append(
            f"[{i}:v]scale=720:1280,fps=30,setsar=1[v{i}]")
    prev = "v0"
    offset_acc = probe_dur(seg_files[0]) - d
    for i in range(1, n):
        outlbl = f"x{i}" if i < n - 1 else "vout"
        filters.append(
            f"[{prev}][v{i}]xfade=transition=fade:duration={d}:offset={max(offset_acc, 0):.3f}[{outlbl}]")
        if i < n - 1:
            offset_acc += probe_dur(seg_files[i]) - d
        prev = outlbl
    # 音频：acrossfade 同步叠化
    afilters = []
    for i in range(n):
        afilters.append(f"[{i}:a]aresample=48000[a{i}]")
    aprev = "a0"
    for i in range(1, n):
        outlbl = f"ax{i}" if i < n - 1 else "aout"
        afilters.append(f"[{aprev}][a{i}]acrossfade=d={d}[{outlbl}]")
        aprev = outlbl

    fc = ";".join(filters + afilters)
    cmd = [FFMPEG, "-y", *inputs, "-filter_complex", fc,
           "-map", "[vout]", "-map", "[aout]",
           "-c:v", "libx264", "-crf", "20", "-preset", "fast",
           "-c:a", "aac", "-b:a", "128k", str(out)]
    r = subprocess.run(cmd, capture_output=True, timeout=1200)
    if r.returncode != 0:
        print(f"  [FFMPEG ERR] {r.stderr.decode(errors='replace')[-400:]}")
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description="段间 xfade 叠化后处理")
    ap.add_argument("--input", required=True, help="成片目录或单个mp4")
    ap.add_argument("--output", required=True, help="输出目录或mp4")
    ap.add_argument("--duration", type=float, default=0.4, help="叠化秒数(默认0.4)")
    ap.add_argument("--segs-dir", default="", help="段目录（默认 input/_segs）")
    args = ap.parse_args()

    inp, outp = Path(args.input), Path(args.output)
    if inp.is_file():
        outp.parent.mkdir(parents=True, exist_ok=True)
        seg_dir = Path(args.segs_dir) if args.segs_dir else inp.parent / "_segs"
        tag = inp.stem
        segs = sorted(seg_dir.glob(f"{tag}_seg*.mp4"))
        if segs and len(segs) > 1:
            ok = build_xfade(segs, outp, args.duration)
            print(f"{tag}: {'叠化OK' if ok else 'FAIL'} ({len(segs)}段)")
            sys.exit(0 if ok else 1)
        subprocess.run([FFMPEG, "-y", "-i", str(inp), "-c", "copy", str(outp)], check=True)
        print(f"{tag}: 单段直通")
        return

    seg_dir = Path(args.segs_dir) if args.segs_dir else inp / "_segs"
    outp.mkdir(parents=True, exist_ok=True)
    finals = sorted(inp.glob("*.mp4"))
    ok = fail = single = 0
    for f in finals:
        segs = sorted(seg_dir.glob(f"{f.stem}_seg*.mp4"))
        if not segs or len(segs) <= 1:
            subprocess.run([FFMPEG, "-y", "-i", str(f), "-c", "copy",
                            str(outp / f.name)], check=True)
            single += 1
            continue
        if build_xfade(segs, outp / f.name, args.duration):
            ok += 1
            print(f"{f.stem}: 叠化OK ({len(segs)}段)")
        else:
            fail += 1
            print(f"{f.stem}: FAIL")
    print(f"\n完成：叠化{ok} 单段直通{single} 失败{fail} → {outp}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
