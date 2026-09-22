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
# 字幕强制单行:软上限14字(规范 subtitle_burnin Step2),超了切句
SINGLE_LINE_MAX = 14


def _tokenize_for_split(s: str) -> list[str]:
    """把台词切成"词单元":数字+量词/英文/中文各一词;
    标点绑定到它**后面**的词(如 "、超声" 一体),首词无前随标点。
    换行时标点跟词走,不出现在行首,也不产生"词、"残句。
    """
    WORD = r"\d+(?:\.\d+)?%?[万亿千百十点元年岁]?|[A-Za-z0-9]+|[一-鿿]+"
    TOKEN_RE = re.compile(rf"([，、；。！？,.!?]*)?(?:{WORD})")
    tokens = []
    for m in TOKEN_RE.finditer(s):
        lead = m.group(1) or ""
        tokens.append(m.group(0))  # 含前随标点
    return tokens


def _group_coord_parts(tokens: list[str]) -> list[str]:
    """把"顿号连接的相邻短词"合并成不可拆并列组。

    如 ['CT', '、超声', '、胃肠镜'] → ['CT、超声、胃肠镜']。
    逗号/分号/句号是强停顿,不跨;合并后整块超 SINGLE_LINE_MAX 则拆开(保持各词)。
    """
    groups: list[str] = []
    buf = ""
    for tok in tokens:
        lead = re.match(r"[，、；。！？,.!?]*", tok).group(0)
        # 仅顿号连接才并入;其它标点(，；。)断开
        if buf and set(lead) == {"、"} and len(_strip_punct(buf + tok)) <= SINGLE_LINE_MAX:
            buf += tok
        else:
            if buf:
                groups.append(buf)
            buf = tok
    if buf:
        groups.append(buf)
    return groups


def _split_one_line(line: str) -> list[str]:
    """把一句超长台词打包成多条 ≤SINGLE_LINE_MAX 的单行。

    两�步:
    1. 顿号连接的并列短词先粘成"并列组"(CT、超声、胃肠镜 同行,不被行边界拆散)。
    2. 各组逐个进行;下一组放不下 → 当前行收口、下一组整体移到新行;
       组的前随标点(逗号等强停顿)贴在上一行尾,词不开标点行首。
    一个组自身超14字(罕见)→ 拆回单词;词也超 → 硬切。
    """
    tokens = _tokenize_for_split(line)
    groups = _group_coord_parts(tokens)
    segs: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf.strip():
            segs.append(buf.strip())
        buf = ""

    for grp in groups:
        n = len(_strip_punct(grp))
        if n > SINGLE_LINE_MAX:
            flush()
            # 组超长 → 拆回单词重切
            for tok in _tokenize_for_split(grp):
                w = _strip_punct(tok)
                if len(w) <= SINGLE_LINE_MAX:
                    segs.append(tok)
                else:
                    for i in range(0, len(w), SINGLE_LINE_MAX):
                        segs.append(w[i:i + SINGLE_LINE_MAX])
            continue
        if len(_strip_punct(buf)) + n <= SINGLE_LINE_MAX:
            buf += grp
        else:
            # 组移下行:前随标点贴上句尾(停顿属于上句),组词开新行
            lead = re.match(r"[，、；。！？,.!?]*", grp).group(0)
            word = grp[len(lead):]
            if lead and buf:
                buf += lead
            flush()
            buf = word
    flush()
    return segs


def _split_long_lines(lines: list[str]) -> list[str]:
    """超 SINGLE_LINE_MAX 的台词切成多条单行。

    保证:① 数字+单位/英文不拆断 ②标点不出现行首 ③无 ≤2字独立残句
    ④每条 ≤14字、尽量语义完整。
    """
    out: list[str] = []
    for line in lines:
        if len(_strip_punct(line)) <= SINGLE_LINE_MAX:
            out.append(line)
        else:
            out.extend(_split_one_line(line))
    return out



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
    # 字幕强制单行:超 SINGLE_LINE_MAX 的台词先切成多条,不挤进一行/不靠ASS折行。
    script_lines = _split_long_lines(script_lines)

    # 换行边界:条目前导标点(，、；)是上一句停顿 → 移到上一条结尾,
    # 绝不让字幕以标点开头(根因:tokenize 把标点绑给了后词)
    relocated: list[str] = []
    for line in script_lines:
        m = re.match(r"[，、；,.!?]+", line)
        if m and relocated:
            lead = m.group(0)
            relocated[-1] += lead            # 标点贴上一条尾
            line = line[len(lead):]
        relocated.append(line)
    script_lines = relocated

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

    # 相邻条目零间隙 → 结束提前 GAP;结尾逗号/顿号剥掉(停顿由间隙表达,
    # 防止同帧叠显",下句"的残影)
    GAP = 0.06
    fixed: list[tuple[float, float, str]] = []
    for i, (s, e, txt) in enumerate(entries):
        nxt = entries[i + 1][0] if i + 1 < len(entries) else None
        if nxt is not None and e >= nxt - 0.001:
            e = nxt - GAP
            if txt and txt[-1] in "，、,.":
                txt = txt[:-1]
        fixed.append((s, e, txt))
    entries = fixed

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
        # Dialogue 字段: Layer,Start,End,Style,Name,MarginL,MarginR,Effect,Text
        # Name/Effect 留空(,,),不填多余 0(否则逗号被 libass 当文本开头)
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,,{body}")
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
Style: Default,思源黑体,75,&H00FFFFFF,&H00000000,&H00000000,0,0,1,3,1,2,480,1
Style: Warn,思源黑体,27,&H00CCCCCC,&H00000000,&H00000000,0,0,1,1,0,2,10,1

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
        # Dialogue 字段: Layer,Start,End,Style,Name,MarginL,MarginR,Effect,Text
        # Name/Effect 留空(,,),不填多余的 0(否则逗号被 libass 当文本开头)
        events.insert(0,
            "Dialogue: 0,0:00:00.00,9:00:00.00,Warn,,0,0,," + warning)
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
        load_words(v)   # 有缓存直接命中,无则跑 ASR(不强制重跑)
        align(v, args.script)
        burn(v, args.warn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
