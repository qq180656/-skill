#!/usr/bin/env python3
"""storyboard.md 机械验算工具。

用法：
  python3 validate_storyboard.py <storyboard.md> --model-name MODEL --max-duration L [--target N] [--mode hard|soft|budget]

一次性输出所有机械违规项，分级：
  [ERROR] 硬规则且判定确定，必须修
  [WARN]  规则硬但检测可能误报，附证据自行判断
  [INFO]  软规则/建议，酌情采纳
  [SKIP]  该项无法解析或无法从文本核验，已跳过（不算违规）
全部无 ERROR/WARN/INFO 时输出 PASS。
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from count_chars import SpeechUnits, estimate_speech, format_speech_units


FW_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")

issues = []


def mixed_assets_over_limit(image_count, video_count, limit):
    """mixed 上限只约束同时包含图片和视频的调用。"""
    return (
        image_count > 0
        and video_count > 0
        and image_count + video_count > limit
    )


def resolve_profile(model_name):
    """按模型名解析素材能力；时长不参与素材上限判断。"""
    normalized = str(model_name or "").strip().lower()
    if normalized == "seedance_2.5" or normalized.startswith("seedance_2.5_"):
        return {
            "label": "Seedance 2.5",
            "img": 30,
            "vid": 10,
            "aud": 10,
            "mixed": 20,
            "audio_only": True,
        }
    label = str(model_name or "未知模型").strip() or "未知模型"
    return {
        "label": f"{label}（保守默认）",
        "img": 9,
        "vid": 3,
        "aud": 3,
        "mixed": 12,
        "audio_only": False,
    }


def add(level, msg, fix=None):
    """fix 为处置建议：同 (level, fix) 的多条会在输出时聚合为一类，处置只打一次。"""
    issues.append((level, msg, fix))


def parse_num(cell):
    """从单元格提取数值，容忍 '12s' '12秒' '约12' 全角数字。"""
    if cell is None:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", str(cell).translate(FW_DIGITS))
    return float(m.group(1)) if m else None


def parse_link(cell):
    """衔接单元格 → shot 号或 None。容忍 '⇐01' '⇐ shot_01' '—' '-' 空。"""
    if not cell:
        return None
    m = re.search(r"⇐\s*(?:shot[_ ]?)?0*(\d+)", str(cell).translate(FW_DIGITS))
    return int(m.group(1)) if m else None


def parse_table(text):
    """解析总览表：返回 [{shot, duration, link}]，列按表头模糊匹配。

    只解析第一张总览表：锁定表头后遇到下一个 `##` 小节标题即停止收行，
    避免「导演方案」等后续小节的表格行污染总览表（否则段号翻倍报假不一致）。
    """
    lines = text.splitlines()
    header, rows = None, []
    for line in lines:
        if header is not None and line.lstrip().startswith("##"):
            break
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        low = [c.lower() for c in cells]
        if header is None:
            if any("shot" in c or "段号" in c or "镜号" in c for c in low):
                header = low
            continue
        if set(line.replace("|", "").strip()) <= set("-: "):
            continue
        if not any("shot" in c.lower() or re.search(r"\d", c) for c in cells):
            continue
        rows.append(cells)

    def col(*keys):
        if header is None:
            return None
        for idx, h in enumerate(header):
            if any(k in h for k in keys):
                return idx
        return None

    c_shot = col("shot", "段号", "镜号")
    c_dur = col("duration", "时长")
    c_link = col("衔接")
    out = []
    for cells in rows:
        def get(idx):
            return cells[idx] if idx is not None and idx < len(cells) else None

        sn = get(c_shot)
        m = re.search(r"(\d+)", str(sn).translate(FW_DIGITS)) if sn else None
        if not m:
            continue
        out.append({
            "shot": int(m.group(1)),
            "duration": parse_num(get(c_dur)),
            "link": parse_link(get(c_link)),
            "link_cell": get(c_link),
        })
    return out


def parse_shots(text):
    """按 `## shot_NN` 切小节，返回 [{num, header, body, images, videos, audios, prompt}]。"""
    parts = re.split(r"^(##\s*shot[_ ]?\d+[^\n]*)$", text, flags=re.M | re.I)
    shots = []
    for i in range(1, len(parts), 2):
        header, body = parts[i], parts[i + 1] if i + 1 < len(parts) else ""
        m = re.search(r"shot[_ ]?0*(\d+)", header, re.I)
        if not m:
            continue
        shots.append({
            "num": int(m.group(1)),
            "header": header,
            "body": body,
            "images": parse_list(body, "ImageList"),
            "videos": parse_list(body, "VideoList"),
            "audios": parse_list(body, "AudioList"),
            "prompt": parse_prompt(body),
        })
    return shots


KEY_LINE = re.compile(r"\s*-\s*(ImageList|VideoList|AudioList|Prompt)\s*[:：]", re.I)


def parse_list(body, key):
    """提取 `- ImageList:` 下的条目；`[]` 或缺失返回空列表，容忍内联 `[a, b]`。"""
    lines = body.splitlines()
    start = None
    for i, line in enumerate(lines):
        m = re.match(rf"\s*-\s*{key}\s*[:：]\s*(.*)$", line, re.I)
        if m:
            rest = m.group(1).strip()
            if rest.startswith("["):
                inner = rest.strip("[]").strip()
                return [x.strip() for x in inner.split(",") if x.strip()] if inner else []
            start = i + 1
            break
    if start is None:
        return []
    items = []
    for line in lines[start:]:
        if KEY_LINE.match(line) or line.startswith("##"):
            break
        m = re.match(r"\s*-\s+(\S.*)$", line)
        if m:
            items.append(m.group(1).strip())
        elif line.strip():
            break
    return items


def parse_prompt(body):
    m = re.search(r"-\s*Prompt\s*[:：]\s*\|?\s*\n?", body)
    return body[m.end():].strip() if m else ""


DIALOGUE_RE = re.compile(r"(?:说|旁白|画外音|独白|唱)[^：:{｛\n]{0,25}[：:]\s*[{｛]([^}｝]+)[}｝]")

STAGE_RE = re.compile(r"阶段\s*\d+\s*[（(]\s*(\d+(?:\.\d+)?)\s*[-–~至]\s*(\d+(?:\.\d+)?)\s*秒?\s*[）)]\s*[：:]")


def extract_dialogue(prompt):
    """返回每句台词的分语种计数与耗时区间。"""
    out = []
    for t in DIALOGUE_RE.findall(prompt):
        units, lower, upper = estimate_speech(t)
        out.append({
            "text": t,
            "units": units,
            "lower": lower,
            "upper": upper,
        })
    return out


def dialogue_totals(lines):
    """合并多句台词的计数与耗时，保持与 count_chars.py 同源。"""
    units = SpeechUnits(
        sum(line["units"].chars for line in lines),
        sum(line["units"].digits for line in lines),
        sum(line["units"].english_words for line in lines),
    )
    lower = round(sum(line["lower"] for line in lines), 1)
    upper = round(sum(line["upper"] for line in lines), 1)
    return units, lower, upper


def parse_stages(prompt):
    """解析 `阶段N (a-b秒)：` 标注，返回 [(a, b, 该窗口文本)]；无标注返回空列表。"""
    text = prompt.translate(FW_DIGITS)
    marks = [(m.start(), float(m.group(1)), float(m.group(2))) for m in STAGE_RE.finditer(text)]
    out = []
    for i, (pos, a, b) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        out.append((a, b, text[pos:end]))
    return out


def check(fn):
    """每个检查项独立容错：异常降级为 SKIP，不中断其他检查。"""
    try:
        fn()
    except Exception as e:
        add("SKIP", f"检查项 {fn.__name__} 解析异常已跳过（{type(e).__name__}: {e}）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--model-name", required=True)
    ap.add_argument("--max-duration", type=float, required=True)
    ap.add_argument("--target", type=float, default=None)
    ap.add_argument("--mode", choices=["hard", "soft", "budget"], default=None)
    args = ap.parse_args()

    L = args.max_duration
    prof = resolve_profile(args.model_name)
    model_label = prof["label"]

    if not os.path.exists(args.file):
        print(f"[ERROR] 文件不存在：{args.file}")
        sys.exit(2)
    with open(args.file, encoding="utf-8") as f:
        text = f.read()

    table = []
    shots = []

    def _parse():
        nonlocal table, shots
        table = parse_table(text)
        shots = parse_shots(text)
    check(_parse)

    if not shots:
        add("SKIP", "未解析到任何 `## shot_NN` 小节，仅能执行总览表检查")

    # 结构完整性
    def structure():
        nums = [s["num"] for s in shots]
        if nums != sorted(nums):
            add("WARN", f"shot 小节顺序非递增：{nums}")
        expect = list(range(1, max(nums) + 1)) if nums else []
        missing = sorted(set(expect) - set(nums))
        if missing:
            add("ERROR", f"段号不连续，缺 shot_{missing} → 补齐或修正编号")
        dup = sorted({n for n in nums if nums.count(n) > 1})
        if dup:
            add("ERROR", f"段号重复：shot_{dup}")
        if table and shots:
            t_nums = sorted(r["shot"] for r in table)
            if t_nums != sorted(nums):
                add("ERROR", f"总览表段 {t_nums} 与 shot 小节 {sorted(nums)} 不一致 → 两边对齐")
        for s in shots:
            if len(s["prompt"]) < 30:
                add("ERROR", f"shot_{s['num']:02d}: Prompt 为空或过短（{len(s['prompt'])} 字符）", fix="补写完整 Prompt")
    check(structure)

    # 时长
    def durations():
        if not table:
            add("SKIP", "总览表未解析到 Duration，时长检查跳过")
            return
        total = 0.0
        for r in table:
            d = r["duration"]
            if d is None:
                add("SKIP", f"shot_{r['shot']:02d}: 总览表时长无法解析")
                continue
            total += d
            if d < 4:
                add("ERROR", f"shot_{r['shot']:02d}: Duration {d:g}s < 4s", fix="设为 4 或并入相邻段")
            if d > L:
                add("ERROR", f"shot_{r['shot']:02d}: Duration {d:g}s > 上限 {L:g}s", fix="必须拆段")
        if args.target:
            t = args.target
            if "超载兜底" in text and total > t:
                by_num = {s["num"]: s for s in shots}
                lower_sum = round(sum(dialogue_totals(extract_dialogue(by_num[r["shot"]]["prompt"]))[1]
                                      for r in table if r["shot"] in by_num), 1)
                if lower_sum > t:
                    add("INFO", f"总时长 {total:g}s 超 {t:g}s，但总览表已注明超载兜底且台词耗时下限 {lower_sum:g}s 确实无法压入 → 合法突破，不再按约束报错")
                else:
                    add("ERROR", f"总览表注明了超载兜底，但台词耗时下限 {lower_sum:g}s 未超过约束 {t:g}s → 超载注明不成立，压缩动作/收束时间将总时长压回 {t:g}s 内")
            elif args.mode == "hard" and total > t:
                # 兜底账目：只有台词能免举证地解释超预算时间
                by_num = {s["num"]: s for s in shots}
                lower_sum = 0.0
                parsed_all = bool(shots)
                for r in table:
                    s = by_num.get(r["shot"])
                    if s is None:
                        parsed_all = False
                        break
                    lower_sum += dialogue_totals(extract_dialogue(s["prompt"]))[1]
                explained = round(lower_sum + len(table) * 3, 1)
                lower_sum = round(lower_sum, 1)
                if parsed_all and total > max(t, explained):
                    gap = round(total - max(t, explained), 1)
                    add("ERROR", f"总时长 {total:g}s 超硬约束 {t:g}s，且超出部分无法由台词解释（全片台词耗时下限 {lower_sum:g}s + 每段 3s 缓冲 = {explained:g}s）→ 至少压缩 {gap:g}s 无台词时间；压缩后仍超 {t:g}s 且剩余空余有 creative_design.md 用户指定动作/事件依据 → 禁止静默突破，回技能 §0.2 台词超载拦截问卷让用户裁决")
                else:
                    add("ERROR", f"总时长 {total:g}s 超硬约束 {t:g}s，全片台词耗时下限 {lower_sum:g}s 无法压入 → 按超载兜底规则在总览表下注明原因后突破，或回技能 §0.2 台词超载拦截问卷让用户裁决")
            elif args.mode == "hard" and total < t * 0.8:
                add("WARN", f"总时长 {total:g}s 显著低于用户指定的 {t:g}s（-{round((1-total/t)*100)}%）→ 确认是内容量确实不足，还是漏排了场次")
            elif args.mode == "soft" and not (t * 0.8 <= total <= t * 1.2):
                add("WARN", f"总时长 {total:g}s 超出软约束 {t:g}s 的 ±20% 范围（{t*0.8:g}~{t*1.2:g}s）")
            elif args.mode == "budget" and total > t:
                add("WARN", f"总时长 {total:g}s 超预算 {t:g}s")
        else:
            add("SKIP", f"未传 --target，总时长（实测 {total:g}s）不做约束检查")
    check(durations)

    # 衔接序列
    def links():
        rows = table if table else None
        if rows is None:
            # 退回从 shot 标题解析
            rows = [{"shot": s["num"], "link": parse_link(s["header"])} for s in shots]
            if rows:
                add("SKIP", "总览表无衔接列，已退回从 shot 标题解析衔接标记")
        seq = sorted(rows, key=lambda r: r["shot"])
        prev_linked = False
        for r in seq:
            n, ln = r["shot"], r["link"]
            if ln is not None:
                if ln != n - 1:
                    add("ERROR", f"shot_{n:02d}: 衔接 ⇐{ln:02d} 跨段（只允许 ⇐{n-1:02d}）", fix="改 — 并在 Prompt 开头补环境锚点与主体位置/朝向")
                elif prev_linked:
                    add("ERROR", f"shot_{n:02d}: 与 shot_{n-1:02d} 连续两个 ⇐（三级链）", fix="本段改 — 并补环境锚点")
                prev_linked = True
            else:
                prev_linked = False
        # ⇐ 段素材与开头
        by_num = {s["num"]: s for s in shots}
        for r in seq:
            n, ln = r["shot"], r["link"]
            if ln is None or n not in by_num:
                continue
            s = by_num[n]
            lastframe = f"shot_{ln:02d}_lastframe"
            hits = [i for i, p in enumerate(s["images"]) if lastframe in p]
            if not hits:
                add("ERROR", f"shot_{n:02d}: 标 ⇐{ln:02d} 但 ImageList 无 {lastframe}.png", fix="将尾帧图加为 ImageList 第一张")
            elif hits[0] != 0:
                add("WARN", f"shot_{n:02d}: {lastframe}.png 在 ImageList 第 {hits[0]+1} 位（应为第一张）")
            if not s["prompt"].startswith("@图片1"):
                add("INFO", f"shot_{n:02d}: ⇐ 段 Prompt 未以「@图片1 作为该次视频前的画面状态」开头")
    check(links)

    # 当前模型素材上限
    def assets():
        for s in shots:
            n, ni, nv, na = s["num"], len(s["images"]), len(s["videos"]), len(s["audios"])
            if ni > prof["img"]:
                add("ERROR", f"shot_{n:02d}: 图片 {ni} 张 > {model_label} 上限 {prof['img']}", fix="删减素材到当前模型上限内")
            if nv > prof["vid"]:
                add("ERROR", f"shot_{n:02d}: 参考视频 {nv} 个 > {model_label} 上限 {prof['vid']}", fix="删减素材到当前模型上限内")
            if na > prof["aud"]:
                add("ERROR", f"shot_{n:02d}: 参考音频 {na} 段 > {model_label} 上限 {prof['aud']}", fix="删减素材到当前模型上限内")
            if mixed_assets_over_limit(ni, nv, prof["mixed"]):
                add("ERROR", f"shot_{n:02d}: 图片+视频合计 {ni+nv} > {model_label} 上限 {prof['mixed']}", fix="删减素材到当前模型上限内")
            if na and not ni and not prof["audio_only"]:
                add("ERROR", f"shot_{n:02d}: {model_label} 禁止只传 AudioList 不传图片", fix="至少传入角色或场景参考图")
            for kind, cnt, tag in (("图片", ni, "图片"), ("视频", nv, "视频"), ("音频", na, "音频")):
                refs = [int(x) for x in re.findall(rf"@{tag}(\d+)", s["prompt"])]
                expected = set(range(1, cnt + 1))
                actual = set(refs)
                if actual != expected:
                    missing = sorted(expected - actual)
                    invalid = sorted(actual - expected)
                    detail = []
                    if missing:
                        detail.append(f"缺少 {missing}")
                    if invalid:
                        detail.append(f"越界 {invalid}")
                    target = f"1~{cnt}" if cnt else "空集"
                    add(
                        "ERROR",
                        f"shot_{n:02d}: {kind}引用编号应完整覆盖 {target}（{'；'.join(detail)}）",
                        fix="逐项引用素材并同步重编号",
                    )
            m = re.search(r"\b[\w\-/]+\.(?:png|jpe?g|mp3|wav|mp4)\b", s["prompt"])
            if m:
                add("WARN", f"shot_{n:02d}: Prompt 疑似出现原始文件名「{m.group(0)}」", fix="改用 @图片N/@视频N/@音频N 引用")
        if shots and any(len(s["videos"]) for s in shots):
            add("SKIP", "参考视频/音频的单个及总时长无法从文本核验，请自查是否超档位时长限制")
    check(assets)

    # 台词密度（下限 - 1 > 段时长 = ERROR，留 1s 预留避免边界误杀；窗口装不下 = ERROR；疏密点名 = WARN）
    def density():
        durs = {r["shot"]: r["duration"] for r in table}
        for s in shots:
            n = s["num"]
            d = durs.get(n)
            if d is None:
                continue
            lines = extract_dialogue(s["prompt"])
            units, lower, upper = dialogue_totals(lines)
            unit_label = format_speech_units(units)
            if lines and lower - 1 > d:
                detail = "；逐句：" + "、".join(
                    f"「{line['text'][:14]}{'…' if len(line['text']) > 14 else ''}」"
                    f"{format_speech_units(line['units'])}/下限{line['lower']}s"
                    for line in lines)
                if lower - 1 > L:
                    add("ERROR", f"shot_{n:02d}: 台词 {unit_label}耗时下限 {lower}s 超出单段上限 {L:g}s 逾 1s，加长无效{detail}", fix="把台词按自然断点拆到相邻段（按逐句下限规划落点，勿再调 count_chars）")
                else:
                    add("ERROR", f"shot_{n:02d}: 台词 {unit_label}耗时下限 {lower}s 超出段时长 {d:g}s 逾 1s{detail}", fix=f"加长该段（不超过 {L:g}s）或把台词按自然断点拆到相邻段（按逐句下限规划落点，勿再调 count_chars）")

            # 阶段窗口密度：含台词阶段的窗口必须装得下该窗口台词的耗时下限
            stages = parse_stages(s["prompt"])
            for a, b, seg in stages:
                win = b - a
                if win <= 0:
                    continue
                window_lines = extract_dialogue(seg)
                if window_lines:
                    w_units, w_lower, _ = dialogue_totals(window_lines)
                    w_label = format_speech_units(w_units)
                    if w_lower - 1 > win:
                        add("ERROR", f"shot_{n:02d}: 阶段窗口 ({a:g}-{b:g}秒) 仅 {win:g}s，装不下窗口内台词 {w_label}（耗时下限 {w_lower}s）", fix="扩大该阶段窗口或把台词挪到相邻阶段")

            # 疏密点名：段时长超过台词耗时上限 + 1s（最慢语速念完仍空 ≥1s）→ 交语义自审举证；无台词段不点名
            if lines and d > upper + 1:
                slack = round(d - upper, 1)
                add("WARN", f"shot_{n:02d}: 段时长 {d:g}s 超台词耗时上限 {upper}s 约 {slack:g}s", fix="超出部分必须对应 creative_design.md 的独立动作/事件（与说话不并行），无支撑则缩短段时长")
    check(density)

    # 可合并段（贪心：相邻段时长之和 ≤ 上限且素材并集不超当前模型上限 → 提示合并）
    def mergeable():
        if not table or not shots:
            return
        durs = {r["shot"]: r["duration"] for r in table}
        by_num = {s["num"]: s for s in shots}
        seq = [r["shot"] for r in sorted(table, key=lambda r: r["shot"])]

        def fits(window):
            """window 内素材并集是否全维度不超当前模型上限。"""
            imgs, vids, auds = set(), set(), set()
            for n in window:
                s = by_num.get(n)
                if s is None:
                    return False
                imgs.update(s["images"])
                vids.update(s["videos"])
                auds.update(s["audios"])
            return (
                len(imgs) <= prof["img"]
                and len(vids) <= prof["vid"]
                and len(auds) <= prof["aud"]
                and not mixed_assets_over_limit(len(imgs), len(vids), prof["mixed"])
            )

        i = 0
        while i < len(seq):
            window, total = [seq[i]], durs.get(seq[i]) or 0
            j = i + 1
            while j < len(seq):
                d = durs.get(seq[j])
                if d is None:
                    break
                cand = window + [seq[j]]
                if total + d <= L and fits(cand):
                    window, total = cand, total + d
                    j += 1
                else:
                    break
            if len(window) >= 2:
                span = f"shot_{window[0]:02d}~{window[-1]:02d}"
                add("WARN", f"{span}: {len(window)} 段合计 {total:g}s ≤ 单段上限 {L:g}s 且素材并集不超当前模型上限", fix="疑似可合并为一次生成调用，除非密度门判定超载才保留拆分")
            i = j if j > i + 1 else i + 1
    check(mergeable)

    # 通用尾注重复
    def tail():
        m = re.search(r"^##\s*通用尾注\s*$([\s\S]*?)(?=^##\s)", text, re.M)
        if not m:
            return
        frags = [ln.strip() for ln in m.group(1).splitlines() if len(ln.strip()) >= 6 and not ln.strip().startswith("{")]
        for s in shots:
            for fr in frags:
                if fr in s["prompt"]:
                    add("INFO", f"shot_{s['num']:02d}: 尾注约束「{fr[:20]}…」在段内重复", fix="从段 Prompt 删去，尾注只写一次")
                    break
    check(tail)

    mixed_summary = f"≤{prof['mixed']}"
    print(f"模型能力：{model_label}（Duration 4~{L:g}s，图≤{prof['img']}，视频≤{prof['vid']}，音频≤{prof['aud']}，混合图+视频{mixed_summary}，仅音频{'允许' if prof['audio_only'] else '禁止'}）")
    order = {"ERROR": 0, "WARN": 1, "INFO": 2, "SKIP": 3}
    counts = {k: 0 for k in order}
    # 聚合：同 (level, fix) 的条目归为一类（fix=None 不聚合），保持级别序、类内保持产生序
    groups = []
    gindex = {}
    for level, msg, fix in issues:
        key = (level, fix) if fix else None
        if key and key in gindex:
            groups[gindex[key]][2].append(msg)
        else:
            if key:
                gindex[key] = len(groups)
            groups.append((level, fix, [msg]))
    for level, fix, msgs in sorted(groups, key=lambda g: order[g[0]]):
        counts[level] += len(msgs)
        if fix is None:
            print(f"[{level}] {msgs[0]}")
        elif len(msgs) == 1:
            print(f"[{level}] {msgs[0]} → {fix}")
        else:
            print(f"[{level}] 共 {len(msgs)} 段同类 → {fix}")
            for m in msgs:
                print(f"  - {m}")
    if counts["ERROR"] + counts["WARN"] + counts["INFO"] == 0:
        print("PASS")
    else:
        print(f"共 {counts['ERROR']} ERROR / {counts['WARN']} WARN / {counts['INFO']} INFO / {counts['SKIP']} SKIP")
    sys.exit(1 if counts["ERROR"] else 0)


if __name__ == "__main__":
    main()
