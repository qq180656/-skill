#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""字幕链路:逐字稿 → 原稿对齐 → 烧录 + 警示语。

把"加字幕/警示语"收口到本规范工程的统一入口。三阶段:

  ① asr    火山 ASR 出逐字稿(每字时间戳) —— 复用 paddleocr_subtile/asr_volcano.py
  ② align  客户原稿作文字、逐字稿作时间轴,对齐出观众看的句级 SRT
  ③ burn   ffmpeg 烧入口播字幕 + 底部常驻警示语,出 *_带字幕.mp4

用法:
  python scripts/subtitle_pipeline.py asr   --video V.mp4
  python scripts/subtitle_pipeline.py align --video V.mp4 --script 客户稿.txt
  python scripts/subtitle_pipeline.py burn  --video V.mp4 [--warn "警示语文本"]
  python scripts/subtitle_pipeline.py all   --video V.mp4 --script 客户稿.txt [--warn "..."]

设计:
- 不重写火山 ASR 客户端(凭据/接口复用老工程 asr_volcano)。
- 字幕文字 = 客户原稿(ASR 会错认"好医保",不能直接用识别结果);
  时间轴 = ASR 逐字稿(每字何时念,精确)。
- 警示语底部全程常驻、灰色、不跟口播时间轴。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Windows 控制台默认 GBK,强制 UTF-8 输出(✓ 与中文)
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

# ── 路径与复用 ────────────────────────────────────────────
SPEC_ROOT = Path(__file__).resolve().parent.parent
ASR_SOURCE_DIR = Path(r"C:/Users/A/Desktop/paddleocr_subtitle")
# asr_volcano.py 所在目录(其 venv 带 requests 等依赖)
ASR_VENV_PY = ASR_SOURCE_DIR / ".venv" / "Scripts" / "python.exe"

# 缓存/产物子目录
ASR_WORDS_DIR = "cache_asr_words"
SRT_OUT_DIR = "cache_srt"
SUBTITLE_SUFFIX = "_带字幕"


# ════════════════════════════════════════════════════════
# 阶段 ① : ASR 逐字稿
# ════════════════════════════════════════════════════════
def run_asr(video: Path) -> list[dict]:
    """调老工程 asr_volcano.transcribe_words,返回 [{text,start_sec,end_sec}]。

    通过其子解释器执行(自带 requests + 火山凭据),返回 JSON 到 stdout。
    """
    if not ASR_VENV_PY.exists():
        sys.exit(f"找不到 ASR venv: {ASR_VENV_PY}")
    code = (
        "import sys,json; sys.path.insert(0, r'%s');"
        "from asr_volcano import transcribe_words;"
        "ws = transcribe_words(r'%s', log=lambda *a: None);"
        "print(json.dumps([w.__dict__ for w in ws], ensure_ascii=False))"
        % (str(ASR_SOURCE_DIR), str(video))
    )
    r = subprocess.run([str(ASR_VENV_PY), "-c", code],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        sys.exit(f"ASR 失败: {r.stderr.strip()[:300]}")
    words = json.loads(r.stdout.strip().splitlines()[-1])
    outdir = video.parent / ASR_WORDS_DIR
    outdir.mkdir(exist_ok=True)
    (outdir / f"{video.stem}.json").write_text(
        json.dumps(words, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"✓ 逐字稿 {len(words)} 词 → {outdir / (video.stem + '.json')}")
    return words


def load_words(video: Path) -> list[dict]:
    """读已缓存的逐字稿;没有则先跑 ASR。"""
    cp = video.parent / ASR_WORDS_DIR / f"{video.stem}.json"
    if cp.exists():
        return json.loads(cp.read_text(encoding="utf-8") or "[]")
    return run_asr(video)


# ════════════════════════════════════════════════════════
# 阶段 ② : 原稿对齐(文字=客户稿,时间轴=逐字稿)
# ════════════════════════════════════════════════════════
def _strip_punct(s: str) -> str:
    """去标点/空白,只留字,便于把原稿对齐到逐字稿。"""
    return re.sub(r"[^\w\u4e00-\u9fff]", "", s)


def extract_script_lines(script_path: Path) -> list[str]:
    """从客户原稿抽台词行:跳过 markdown 标记/舞台说明,只留口播句。

    支持格式:
    - 角色：台词   → 取冒号后
    - 纯台词行
    - 跳过 # 标题、| 表格、> 引用、空行
    """
    lines: list[str] = []
    for raw in script_path.read_text(encoding="utf-8").splitlines():
        t = raw.strip()
        if not t or t[0] in "#>|-" or t.startswith("---"):
            continue
        # 纯加粗元信息行 / 含管道或全角分隔的说明行
        if re.fullmatch(r"\*+.+\*+", t) and ("文案" in t or len(t) < 12):
            continue
        if "|" in t or "｜" in t or t.startswith("[") or t.startswith("**"):
            continue
        # 角色：台词
        m = re.match(r"^(?:老爸|儿子|妈妈|爸爸|角色|[^一-鿿]{0,6})[：:](.+)$", t)
        if m:
            t = m.group(1).strip()
        # 去尾部舞台/合规括注
        t = re.sub(r"[（(][^）)]*[）)]", "", t).strip()
        if len(_strip_punct(t)) >= 2:
            lines.append(t)
    return lines


def align(video: Path, script_path: Path) -> Path:
    """把原稿台词逐句对齐到逐字稿时间轴,产出句级 SRT。"""
    words = load_words(video)
    if not words:
        sys.exit("无逐字稿,先跑 asr")
    script_lines = extract_script_lines(script_path)
    if not script_lines:
        sys.exit("客户原稿未抽出台词,检查格式")

    # 全局字指针:顺序消费逐字稿。一句原稿消耗对应字数,起止取首末词时间。
    entries: list[tuple[float, float, str]] = []
    wi = 0
    for line in script_lines:
        n = len(_strip_punct(line))
        if wi >= len(words):
            break
        start = float(words[wi]["start_sec"])
        end_wi = min(wi + n, len(words)) - 1
        end = float(words[end_wi]["end_sec"])
        entries.append((start, end, line))
        wi += n

    srt = "".join(
        f"{i}\n{_ts(s)} --> {_ts(e)}\n{txt}\n\n"
        for i, (s, e, txt) in enumerate(entries, 1)
    )
    outdir = video.parent / SRT_OUT_DIR
    outdir.mkdir(exist_ok=True)
    out = outdir / f"{video.stem}.srt"
    out.write_text(srt, encoding="utf-8")
    print(f"✓ 对齐 SRT {len(entries)} 句 → {out}")
    return out


def _ts(sec: float) -> str:
    """秒 → SRT 时间戳 HH:MM:SS,mmm。"""
    if sec < 0:
        sec = 0
    h = int(sec // 3600); m = int(sec % 3600 // 60)
    s = int(sec % 60); ms = round((sec - int(sec)) * 1000)
    if ms == 1000:
        ms = 0; s += 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def load_srt(video: Path) -> Path:
    p = video.parent / SRT_OUT_DIR / f"{video.stem}.srt"
    if not p.exists():
        sys.exit(f"无对齐 SRT: {p},先跑 align")
    return p


# ════════════════════════════════════════════════════════
# 阶段 ③ : 烧录 + 警示语
# ════════════════════════════════════════════════════════
def _esc_subtitle_path(p: Path) -> str:
    """Windows subtitles 滤镜路径:盘符冒号转义,正斜杠。"""
    s = p.resolve().as_posix()
    s = re.sub(r"^([A-Za-z]):/", r"\1\\:/", s)
    return s


def _srt_to_ass_events(srt_path: Path) -> list[str]:
    """读口播 SRT,转成 ASS Dialogue 事件(沿用默认样式 Default)。"""
    text = srt_path.read_text(encoding="utf-8")
    events: list[str] = []
    # 按空行分块
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.strip().splitlines()
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        times = lines[1].split("-->")
        start = _ass_t(times[0].strip())
        end = _ass_t(times[1].strip())
        body = "\\N".join(lines[2:]).replace(",", "，")
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{body}")
    return events


def _ass_t(srt_ts: str) -> str:
    """SRT 时间戳(HH:MM:SS,mmm) → ASS( H:MM:SS.cc )。"""
    h, m, rest = srt_ts.split(":")
    s, ms = rest.split(",")
    cs = int(round(int(ms) / 10))
    if cs == 100:
        cs = 0; s = str(int(s) + 1)
    return f"{int(h)}:{m}:{s}.{cs:02d}"


_ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginV, Encoding
Style: Default,Arial,72,&H00FFFFFF,&H00000000,&H00000000,0,0,1,3,1,2,120,1
Style: Warn,Arial,38,&H00CCCCCC,&H00000000,&H00000000,0,0,1,1,0,2,28,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, Effect, Text
"""


def burn(video: Path, warning: str) -> Path:
    """ffmpeg 烧录:口播字幕 + (可选)底部全程常驻警示语。

    警示语用 ASS 事件(Warn 样式,0→结尾),不用 drawtext——drawtext 依赖
    fontconfig(本机未配置),而 ASS 走 libass/directwrite 可正常渲染。
    """
    srt = load_srt(video)
    workdir = srt.parent
    out = video.with_name(f"{video.stem}{SUBTITLE_SUFFIX}.mp4")

    # 生成含口播 + 警示语的 ASS
    events = _srt_to_ass_events(srt)
    if warning:
        events.insert(0,
            "Dialogue: 0,0:00:00.00,9:00:00.00,Warn,,0,0,0,," + warning)
    ass = workdir / f"{video.stem}.ass"
    ass.write_text(_ASS_HEADER + "\n".join(events) + "\n", encoding="utf-8")

    # 输入用硬链接放进 workdir(避开中文绝对路径),失败退回绝对路径
    rel_in = Path("__in.mp4")
    in_arg = rel_in
    cleanup_in = False
    try:
        if workdir.joinpath(rel_in).exists():
            workdir.joinpath(rel_in).unlink()
        import _winapi
        _winapi.CreateHardLink(str(workdir / rel_in), str(video.resolve()))
        cleanup_in = True
    except Exception:
        in_arg = video.resolve()

    rel_out = Path(out.name)
    cmd = ["ffmpeg", "-y", "-i", str(in_arg),
           "-vf", f"ass='{ass.name}'", "-c:a", "copy", str(rel_out)]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(workdir))
    if cleanup_in and workdir.joinpath(rel_in).exists():
        workdir.joinpath(rel_in).unlink()
    if r.returncode != 0:
        sys.exit(f"烧录失败: {r.stderr[-400:]}")
    final = workdir / rel_out
    print(f"✓ 烧录完成(警示语:{'有' if warning else '无'}) → {final}")
    return final


# ════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="字幕链路:逐字稿→对齐→烧录")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("asr", "align", "burn", "all"):
        p = sub.add_parser(name)
        p.add_argument("--video", required=True, type=Path)
        if name in ("align", "all"):
            p.add_argument("--script", required=True, type=Path)
        if name in ("burn", "all"):
            p.add_argument("--warn", default=None, help="底部常驻警示语")
    args = ap.parse_args()

    v: Path = args.video
    if args.cmd == "asr":
        run_asr(v)
    elif args.cmd == "align":
        align(v, args.script)
    elif args.cmd == "burn":
        burn(v, args.warn)
    else:  # all
        run_asr(v)
        align(v, args.script)
        burn(v, args.warn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
