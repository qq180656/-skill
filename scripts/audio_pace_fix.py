#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""音频语速后期校准（atempo 局部加速）。

背景（2026-09-21 ASR 实测）：Seedance 老人音色 TTS 比设计慢 ~12%（设计6字/s 实际5.3），
中青年正常（7字/s 实际7.8）。已生成批次不重跑，用本工具对慢速段局部加速。

原理：ASR 逐句测速 → 语速 < 阈值(默认6.5字/s) 的连续区间合并 → 对该区间音频做
atempo=ratio 加速（视频同步 trim 不动，纯音频替换；说话段加速、停顿保留原速）。

用法：
    python audio_pace_fix.py --input 成片/ --output 成片_校速/            # 目录批量
    python audio_pace_fix.py --input a.mp4 --output b.mp4                 # 单文件
    python audio_pace_fix.py --input a.mp4 --dry-run                      # 只报告不处理
依赖：paddleocr_subtitle/.venv 的 asr_volcano（火山ASR，缓存自动命中）
"""
from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASR_PY = r"C:\Users\A\Desktop\paddleocr_subtitle\.venv\Scripts\python.exe"
FFMPEG = r"C:\Users\A\Desktop\build_video\tools\ffmpeg.exe"
TARGET_RATE = 7.0      # 目标语速（字/秒）
MIN_RATE = 6.0         # 低于此值判为慢速段（实测老人音色 4.1-5.8）
MAX_TEMPO = 1.18       # 单次加速上限——>1.3 人声出现赶话/变调感（实测），老人段拉到~6字/s 即与音色老态匹配，不追满7


def probe_dur(p: Path) -> float:
    r = subprocess.run([FFMPEG, "-i", str(p), "-f", "null", "-"], capture_output=True, timeout=120)
    err = r.stderr.decode("utf-8", errors="replace") if isinstance(r.stderr, bytes) else (r.stderr or "")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mi * 60 + s


def asr_lines(video: Path) -> list:
    """调 paddleocr venv 跑 ASR，返回 [(start, end, text)]。子进程强制 UTF-8 防 GBK 乱码。"""
    code = (
        "import sys, json\n"
        "sys.stdout.reconfigure(encoding='utf-8')\n"
        f"sys.path.insert(0, r'C:\\Users\\A\\Desktop\\paddleocr_subtitle')\n"
        "from asr_volcano import transcribe_video\n"
        f"es = transcribe_video(r'{video}', use_cache=True)\n"
        "print(json.dumps([[e.start_sec, e.end_sec, e.text] for e in es], ensure_ascii=False))\n"
    )
    r = subprocess.run([ASR_PY, "-c", code], capture_output=True, timeout=600,
                       env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    out = r.stdout.decode("utf-8", errors="replace").strip().splitlines()
    for ln in reversed(out):  # 取最后一行 JSON
        if ln.startswith("[["):
            return [tuple(x) for x in __import__("json").loads(ln)]
    return []


def find_slow_spans(lines: list, gap: float = 1.0):
    """逐句测速，合并慢速句成连续区间。返回 [(start, end, avg_rate)]。"""
    slow = []
    for s, e, txt in lines:
        n = len(re.sub(r"\s", "", txt))
        dur = max(e - s, 0.3)
        rate = n / dur
        if rate < MIN_RATE and n >= 4:
            slow.append((s, e, rate, n))
    if not slow:
        return []
    # 合并相邻（间隔<gap 视为同段）
    spans = [[slow[0][0], slow[0][1], [slow[0][2]], [slow[0][3]]]]
    for s, e, rate, n in slow[1:]:
        if s - spans[-1][1] <= gap:
            spans[-1][1] = max(spans[-1][1], e)
            spans[-1][2].append(rate)
            spans[-1][3].append(n)
        else:
            spans.append([s, e, [rate], [n]])
    out = []
    for s, e, rates, ns in spans:
        total_n = sum(ns)
        total_t = e - s
        avg = total_n / max(total_t, 0.5)
        out.append((s, e, avg))
    return out


def fix_one(video: Path, output: Path, dry: bool) -> str:
    dur = probe_dur(video)
    lines = asr_lines(video)
    if not lines:
        return "ASR空，跳过"
    spans = find_slow_spans(lines)
    if not spans:
        return f"OK 全片≥{MIN_RATE}字/s（{len(lines)}句）"
    span_txt = "; ".join(f"{s:.1f}-{e:.1f}s({r:.1f}字/s)" for s, e, r in spans[:4])
    if dry:
        return f"[DRY] 慢速段 {len(spans)} 处: {span_txt}"
    # 构建 filter_complex：整条音频按段切速（慢段 atempo、其余原速）
    # 用 atrim/concat 拼接方案
    parts = []
    fc_parts = []
    idx = 0
    for s, e, rate in spans:
        ratio = min(MAX_TEMPO, round(TARGET_RATE / rate, 2))
        if s > idx:
            fc_parts.append(f"[0:a]atrim=0:{s:.3f},asetpts=PTS-STARTPTS[a{len(fc_parts)}]")
            parts.append(f"[a{len(fc_parts) if False else len(fc_parts)-0}]")
    # 简化实现：逐段顺序拼
    fc = []
    labels = []
    cur = 0
    for s, e, rate in spans:
        ratio = min(MAX_TEMPO, round(TARGET_RATE / rate, 2))
        if s > cur:
            fc.append(f"[0:a]atrim={cur:.3f}:{s:.3f},asetpts=PTS-STARTPTS[n{len(labels)}]")
            labels.append(f"[n{len(labels)}]")
        fc.append(f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS,atempo={ratio:.2f}[n{len(labels)}]")
        labels.append(f"[n{len(labels)}]")
        cur = e
    if cur < dur:
        fc.append(f"[0:a]atrim={cur:.3f},asetpts=PTS-STARTPTS[n{len(labels)}]")
        labels.append(f"[n{len(labels)}]")
    joined = "".join(labels)
    fc.append(f"{joined}concat=n={len(labels)}:v=0:a=1[aout]")
    filter_complex = ";".join(fc)
    cmd = [FFMPEG, "-y", "-i", str(video), "-filter_complex", filter_complex,
           "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
           str(output)]
    r = subprocess.run(cmd, capture_output=True, timeout=600)
    if r.returncode != 0:
        err = r.stderr.decode("utf-8", errors="replace")[-300:] if isinstance(r.stderr, bytes) else str(r.stderr)
        return f"FFMPEG失败: {err[:120]}"
    return f"OK 慢速段{len(spans)}处已加速（{span_txt}）"


def main():
    ap = argparse.ArgumentParser(description="音频语速后期校准（慢速段 atempo）")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    inp = Path(args.input)

    if inp.is_file():
        outp = Path(args.output) if args.output else inp.with_name(inp.stem + "_校速.mp4")
        outp.parent.mkdir(parents=True, exist_ok=True)
        print(inp.name, "->", fix_one(inp, outp, args.dry_run))
        return
    outdir = Path(args.output) if args.output else inp.parent / (inp.name + "_校速")
    outdir.mkdir(parents=True, exist_ok=True)
    ok = fixed = skip = fail = 0
    for f in sorted(inp.glob("*.mp4")):
        res = fix_one(f, outdir / f.name, args.dry_run)
        print(f"{f.name}: {res}", flush=True)
        if res.startswith("OK 全片"):
            skip += 1
        elif res.startswith("OK") or res.startswith("[DRY]"):
            ok += 1
        else:
            fail += 1
    print(f"\n完成：加速{ok} 无需{skip} 失败{fail} → {outdir}")


if __name__ == "__main__":
    main()
