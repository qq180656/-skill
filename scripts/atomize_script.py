#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""脚本原子化（TTS 前置处理）。

把"角色：台词"形式的原始脚本加工成可直送 TTS / 视频提示词的原子稿：
  1) 剥离括号警示语（复用 gate_verify.strip_parens 括号深度法，中英括号混用安全）
  2) 角色标签内的情绪提示（妈妈（哭泣）：）识别为角色名，不入口播
  3) 删除级词整词删除（skill_config.PRONOUNCE_DELETE，如 息肉/超声）
  4) 空格级词前后注入空格（skill_config.PRONOUNCE_SPACE，如 意外/免赔额/好医保），
     不切开数字+单位、不在标点旁加空格、产品名间隔号"·"前不加
  5) 字数（中文）/语速/预估时长统计（skill_config.get_speed）

用法：
    python atomize_script.py --file 原始脚本.txt --product 好医保少儿 --output ./_session/
    python atomize_script.py --file s.txt --product 长钱保 --no-space   # 只去括号不注空格
    python atomize_script.py --file s.md --keep-stage                   # 保留场景/舞台说明行

输出（--output 目录下）：
    atomic_scripts.json   逐句结构化 + 汇总（口播全文/字数/秒数/被删词/警示语清单）
    原始脚本.csv           交付台账副本（可选，--no-csv 关闭）
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

try:
    from gate_verify import strip_parens
    from skill_config import (PRONOUNCE_DELETE, PRONOUNCE_SPACE,
                              SPEED, get_speed)
except ImportError:  # 脱离规范库单文件兜底
    def strip_parens(text: str):
        spoken, warns, depth, buf = [], [], 0, []
        open_c, close_c = "（(【[", "）)】]"
        for ch in text:
            if ch in open_c:
                if depth == 0 and buf:
                    spoken.append("".join(buf)); buf = []
                depth += 1
                if depth == 1:
                    warns.append([])
            elif ch in close_c:
                if depth > 0:
                    depth -= 1
            else:
                (warns[-1].append(ch) if depth > 0 else buf.append(ch))
        if buf:
            spoken.append("".join(buf))
        return "".join(spoken), ["（" + "".join(w) + "）" for w in warns]

    PRONOUNCE_DELETE, PRONOUNCE_SPACE = ["息肉", "超声"], []
    SPEED, get_speed = {"default": 7}, (lambda p: 7)

CN = re.compile(r"[一-鿿]")
# 注空格时不加空格的相邻字符：空白/中英文标点/间隔号
NO_SPACE = set(" \t，。！？：；、…—·~～\"'“”‘’（）()【】[]《》<>")
# 台词行：角色：台词（角色后可跟（情绪）提示）
ROLE_LINE = re.compile(
    r"^\s*(?:[-—*=]{1,3}\s*)?"
    r"(?P<lead>【[^】]{1,20}】\s*)?"                          # 可选场景/段落前缀
    r"(?P<role>[一-鿿][一-鿿 A-Za-z0-9·/]{0,8}?)"
    r"\s*(?:[（(][^）)]{0,12}[）)])?\s*[:：]\s*(?P<line>.+?)\s*$"
)
# 明确不是台词的行（纯舞台/结构标记）
STAGE_HINT = re.compile(r"^(?:[-—=]{3,}|【[^】]+】\s*$|场景|画面|镜头|分镜|字幕|备注|注[:：])")


def inject_spaces(text: str, words: list[str]) -> str:
    """空格级词前后注空格：相邻是会粘连的字符（非空白非标点）时才加。"""
    for w in words:
        out, i = [], 0
        while True:
            j = text.find(w, i)
            if j < 0:
                out.append(text[i:]); break
            out.append(text[i:j])
            prev_c = text[j - 1] if j > 0 else ""
            next_c = text[j + len(w)] if j + len(w) < len(text) else ""
            if prev_c and prev_c not in NO_SPACE:
                out.append(" ")
            out.append(w)
            if next_c and next_c not in NO_SPACE:
                out.append(" ")
            i = j + len(w)
        text = "".join(out)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def parse_line(raw: str):
    """返回 (kind, role, content)。kind = dialogue/stage/narration/blank。"""
    s = raw.strip()
    if not s:
        return ("blank", "", "")
    m = ROLE_LINE.match(raw)
    if m:
        lead = (m.group("lead") or "").strip()
        role = (m.group("role") or "").strip()
        # 场景前缀【…】单独成行=stage；与台词同行则记录但不当角色
        if lead and not role:
            return ("stage", "", lead)
        if role and not STAGE_HINT.match(s) and len(role) <= 8:
            return ("dialogue", role, m.group("line").strip())
    if STAGE_HINT.search(s):
        return ("stage", "", s)
    return ("narration", "", s)


def atomize(text: str, product: str, do_space: bool,
            keep_stage: bool, keep_narration: bool):
    speed = get_speed(product)
    items, all_warns, deleted = [], [], []
    for ln_no, raw in enumerate(text.splitlines(), 1):
        kind, role, content = parse_line(raw)
        if kind == "blank":
            continue
        if kind == "stage" and not keep_stage:
            continue
        if kind == "narration" and not keep_narration:
            continue
        spoken, warns = strip_parens(content)
        for w in PRONOUNCE_DELETE:
            if w in spoken:
                deleted.append(w)
                spoken = spoken.replace(w, "")
        if do_space:
            spoken = inject_spaces(spoken, PRONOUNCE_SPACE)
        spoken = re.sub(r"\s+([，。！？：；、…—·])", r"\1", spoken).strip()
        all_warns.extend(warns)
        items.append({
            "index": len([x for x in items if x["kind"] == "dialogue"]) + 1
                     if kind == "dialogue" else None,
            "line_no": ln_no, "kind": kind, "role": role,
            "raw": content, "spoken": spoken,
            "warnings": warns, "chars": len(CN.findall(spoken)),
        })
    dialogue = [x for x in items if x["kind"] == "dialogue"]
    # 句间保留换行：TTS/句读需要停顿边界，不能黏句
    full = "\n".join(x["spoken"] for x in dialogue if x["spoken"])
    total_chars = len(CN.findall(full))
    return {
        "product": product,
        "speed_chars_per_sec": speed,
        "total_spoken_chars": total_chars,
        "est_duration_sec": round(total_chars / speed, 1),
        "deleted_words": sorted(set(deleted)),
        "space_injected_words": PRONOUNCE_SPACE if do_space else [],
        "stripped_warnings": all_warns,
        "full_spoken_text": full,
        "lines": items,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="原始脚本原子化（去括号/删词/注空格/计时长）")
    ap.add_argument("--file", required=True, type=Path, help="原始脚本 txt/md")
    ap.add_argument("--product", default="default",
                    help=f"产品名片段（语速选择），可选含: {sorted(set(SPEED) - {'default'})}")
    ap.add_argument("--output", default=".", type=Path, help="输出目录（默认当前）")
    ap.add_argument("--no-space", action="store_true", help="不做空格注入")
    ap.add_argument("--no-csv", action="store_true", help="不写 原始脚本.csv")
    ap.add_argument("--keep-stage", action="store_true", help="保留场景/舞台说明行")
    ap.add_argument("--keep-narration", action="store_true",
                    help="保留无角色的叙述句（默认丢弃，只保留角色台词）")
    args = ap.parse_args()

    text = args.file.read_text(encoding="utf-8")
    result = atomize(text, args.product, not args.no_space,
                     args.keep_stage, args.keep_narration)

    args.output.mkdir(parents=True, exist_ok=True)
    jpath = args.output / "atomic_scripts.json"
    jpath.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if not args.no_csv:
        cpath = args.output / "原始脚本.csv"
        with open(cpath, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["序号", "角色", "口播台词", "字数", "原行号", "警示语"])
            for x in result["lines"]:
                if x["kind"] == "dialogue":
                    w.writerow([x["index"], x["role"], x["spoken"],
                                x["chars"], x["line_no"], " ".join(x["warnings"])])

    print(f"[OK] {jpath}")
    print(f"台词{len([x for x in result['lines'] if x['kind']=='dialogue'])}句 "
          f"口播{result['total_spoken_chars']}字 ≈{result['est_duration_sec']}s "
          f"({result['speed_chars_per_sec']}字/秒)")
    if result["stripped_warnings"]:
        print(f"剥离括号警示语 {len(result['stripped_warnings'])} 处")
    if result["deleted_words"]:
        print(f"删除级词: {result['deleted_words']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
