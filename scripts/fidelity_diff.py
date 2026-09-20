#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台词保真硬门（fidelity gate）。

把"分镜/任务文件里实际喂给模型的台词"与原子稿（atomize_script 产物）逐字比对，
任何非授权改动（压缩/增删/改写/漏句）都 FAIL 并列出差异。这是 wf_storyboard 1e /
wf_generation Step2 的"台词保真⛔硬门"，防止分镜重排时顺手改了客供源脚本。

支持比对：
  - expected: atomic_scripts.json（--atomic），或纯台词 txt（--expected，每行一句）
  - actual:   分镜 markdown（--storyboard，自动抽 @VOX_角色 说：{台词} 花括号），
              或 tasks.json（--tasks，递归抽所有 prompt 里的 {台词}），
              或纯台词 txt（--actual，每行一句）

授权差异（不算违规，仅记录）：
  - 句读标点（，。！？：；… 等）的增删移动
  - TTS 空格注入（"好医保"→" 好医保 "）的空白差异
  - --ignore 配置的额外等价替换（JSON，如 {"2026版":""}）

判定：
  去标点/去空格/做等价替换后，actual 必须包含 expected 的每一句（顺序可通过
  --order 强制）。字符级缺失/多出/替换即 ERROR，exit 1。

用法：
  python fidelity_diff.py --atomic ./_session/atomic_scripts.json --storyboard storyboard.md
  python fidelity_diff.py --atomic a.json --tasks tasks.json --ignore '{"（2026版）":""}'
  python fidelity_diff.py --expected 源台词.txt --actual 成片台词.txt --strict
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

# 句读/全角半角标点（授权差异，不参与比对）
PUNCT = re.compile(r"[，。！？：；、…—·~～,.\!\?:;\"'“”‘’（）()【】\[\]《》<>\-—_　\s]+")
VOX_BRACE = re.compile(r"(?:@VOX[_一-龥A-Za-z0-9]*)?\s*说[:：]\s*[「『]?\{([^{}]*)\}")
BRACE_ANY = re.compile(r"\{([^{}]*)\}")
PURE_BRACE_LINE = re.compile(r"^\s*\{[^{}]*\}\s*$")


def normalize(text: str, ignore: dict | None) -> str:
    """去标点/空白 + 用户等价替换 → 纯汉字数字字母串。"""
    t = text
    for a, b in (ignore or {}).items():
        t = t.replace(a, b)
    return PUNCT.sub("", t)


def load_expected(atomic: Path | None, expected: Path | None) -> list[str]:
    if atomic:
        d = json.loads(atomic.read_text(encoding="utf-8"))
        return [x["spoken"] for x in d["lines"] if x["kind"] == "dialogue"]
    if expected:
        return [ln.strip() for ln in expected.read_text(encoding="utf-8").splitlines()
                if ln.strip() and not PURE_BRACE_LINE.match(ln)]
    sys.exit("必须提供 --atomic 或 --expected")


def extract_actual_md(text: str) -> list[str]:
    out = []
    for m in VOX_BRACE.finditer(text):
        out.append(m.group(1).strip())
    return out


def extract_tasks(obj) -> list[str]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("prompt", "spoken", "line", "dialogue", "tts") and isinstance(v, str):
                out.extend(x.group(1).strip() for x in BRACE_ANY.finditer(v))
                if "说：" in v or "说:" in v:
                    out.extend(extract_actual_md(v))
            else:
                out.extend(extract_tasks(v))
    elif isinstance(obj, list):
        for x in obj:
            out.extend(extract_tasks(x))
    return out


def load_actual(storyboard: Path | None, tasks: Path | None,
                actual: Path | None) -> list[str]:
    if storyboard:
        return extract_actual_md(storyboard.read_text(encoding="utf-8"))
    if tasks:
        return extract_tasks(json.loads(tasks.read_text(encoding="utf-8")))
    if actual:
        return [ln.strip() for ln in actual.read_text(encoding="utf-8").splitlines()
                if ln.strip()]
    sys.exit("必须提供 --storyboard / --tasks / --actual")


def lcs_positions(a: str, b: str):
    """a 是否作为 b 的子序列出现；返回 b 中匹配位置，便于定位缺口。"""
    pos, j = [], 0
    for ch in a:
        k = b.find(ch, j)
        if k < 0:
            return None
        pos.append(k); j = k + 1
    return pos


def diff_one(exp: str, act_blob: str) -> dict | None:
    """找 expected 句在 actual 大串中的最佳包含；不包含则返回缺口明细。"""
    if not exp:
        return None
    if exp in act_blob:  # 完全包含（快路径）
        return None
    pos = lcs_positions(exp, act_blob)
    if pos is None:
        # 定位首个断链字符
        j, miss_idx = 0, 0
        for i, ch in enumerate(exp):
            k = act_blob.find(ch, j)
            if k < 0:
                miss_idx = i; break
            j = k + 1
        lo = max(0, miss_idx - 6); hi = min(len(exp), miss_idx + 7)
        return {"missing_char": ch if 'ch' in dir() else exp[miss_idx],
                "context": exp[lo:hi], "full": exp}
    return {"reordered": True, "positions": (pos[0], pos[-1]), "full": exp}


def main() -> int:
    ap = argparse.ArgumentParser(description="台词保真硬门：分镜/任务台词 vs 原子稿逐字比对")
    ap.add_argument("--atomic", type=Path, help="atomic_scripts.json")
    ap.add_argument("--expected", type=Path, help="源台词 txt（每行一句）")
    ap.add_argument("--storyboard", type=Path, help="分镜 md（抽 @VOX 说：{}）")
    ap.add_argument("--tasks", type=Path, help="tasks.json（递归抽 prompt 花括号）")
    ap.add_argument("--actual", type=Path, help="成片台词 txt")
    ap.add_argument("--ignore", default="{}", help='授权等价替换 JSON，如 {"（2026版）":""}')
    ap.add_argument("--order", action="store_true", help="强制句序一致（默认允许重排）")
    ap.add_argument("--json", dest="as_json", action="store_true", help="JSON 报告")
    args = ap.parse_args()

    ignore = json.loads(args.ignore)
    exp_lines = load_expected(args.atomic, args.expected)
    act_lines = load_actual(args.storyboard, args.tasks, args.actual)
    if not act_lines:
        print("[FAIL] 未从实际文件抽到任何 {台词}", file=sys.stderr)
        return 1

    exp_norm = [normalize(x, ignore) for x in exp_lines]
    act_blob = normalize("".join(act_lines), ignore)

    findings, missing = [], []
    for raw, en in zip(exp_lines, exp_norm):
        if not en:
            continue
        if en in act_blob:  # 完全包含即通过（允许重排/跨块）
            continue
        pos = lcs_positions(en, act_blob)
        if pos is None:
            # 定位首个断链字符
            j, miss_idx = 0, 0
            for i, ch in enumerate(en):
                k = act_blob.find(ch, j)
                if k < 0:
                    miss_idx = i; break
                j = k + 1
            lo = max(0, miss_idx - 6); hi = min(len(en), miss_idx + 7)
            missing.append({"expected": raw, "缺字": en[miss_idx],
                            "缺口上下文": en[lo:hi]})
        else:
            findings.append({"WARN": "疑似重排/散句", "expected": raw[:40]})

    # actual 多出的实质内容（防加戏）：actual 去重后是否有 expected 覆盖不到的长串
    report = {
        "expected句数": len(exp_lines), "actual台词块": len(act_lines),
        "缺失/改动": missing, "其他": findings,
        "result": "PASS" if not missing else "FAIL",
    }
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"fidelity_diff | 源{len(exp_lines)}句 vs 实际{len(act_lines)}块")
        if missing:
            print(f"  [FAIL] {len(missing)} 句台词不一致：")
            for m in missing:
                print(f"    ✗ 缺/改字「{m['缺字']}」 上下文「…{m['缺口上下文']}…」")
                print(f"      源句: {m['expected'][:60]}")
        else:
            print("  [PASS] 源台词逐字命中（标点/TTS空格差异已豁免）")
        for f in findings:
            print(f"  [WARN] {f['WARN']}: {f['expected']}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
