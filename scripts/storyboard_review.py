#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分镜 LLM 语义审查（写完提示词后的 AI 验证关口）。

机械门（字数/时长/合规词/保真diff）抓不到语义矛盾，本脚本把分镜 md 喂 LLM
审查：台词-画面冲突、伤病锚缺失、时间线倒错、情绪-镜头错位、听者蜡像、
跨空间未拆段、长台词未拆正反打、多人镜头无方位点名。

LLM：relay（skill_config.LLM_URL/LLM_MODEL/LLM_KEYS，蓝标网关）；长文档按
脚本分章送审（每章独立上下文，避免超窗），汇总成问题清单。

用法：
    python storyboard_review.py --file 分镜.md [--out report.md] [--strict]
    python storyboard_review.py --file sb.md --script 3   # 只审脚本3
退出码：有 ERROR 级问题 exit 1（--strict），否则 0。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from skill_config import LLM_KEYS, LLM_URL, LLM_MODEL
except ImportError:
    LLM_KEYS, LLM_URL, LLM_MODEL = [], \
        "https://bmc-llm-relay.bluemediagroup.cn/v1/chat/completions", "Doubao-Seed-2.0-mini"

# 兜底：build_video 的 blueai_key（relay 同网关账号体系）
if not LLM_KEYS:
    try:
        cfg = Path(r"C:\Users\A\Desktop\build_video\config\ai_voice_api.json")
        LLM_KEYS = [json.loads(cfg.read_text(encoding="utf-8"))["blueai_key"]]
    except Exception:
        pass

SYSTEM = """你是保险短视频分镜的语义审查员。下面是「口播文案+分镜Prompt」文档（按脚本分章）。
你的任务不是夸奖，是抓【正则抓不到的语义矛盾】。逐镜通读，按以下清单审查，输出问题清单：

1. 台词-画面语义冲突：台词讲的伤病/金额/事件必须在画面成立——讲"孩子骨折住院"时孩子出场镜头必须带伤病锚（石膏/纱布/吊带/卧床/探头），讲"花了32万8"时画面应有单据/缴费语境；台词与画面矛盾=ERROR。
2. 剧情伤病状态跨镜一致：伤病锚在角色所有出场镜头保持一致，不消失/换侧/换肢体；住院期间的孩子不得出现在家蹦跳（在家=已睡/石膏养伤/不入画）。
3. 时间线自洽：日常引子→事发→当晚/次日→收束不倒错；时间跳跃段首有光线/着装变化锚。
4. 跨空间未拆段：同一生成段（**段N｜**块）内出现两个及以上不同空间（如"病房谈话位…切到手术室门口"）=ERROR（模型会裸硬切）。相邻可达空间（走廊→病房门口）有跟随运镜桥接的不算。
5. 长台词未拆正反打：单个镜头台词>15字且画面只有一个说话人视角、无听者反应镜=ERROR（切点会吞台词）。拆过正反打（说话人→听者反应→说话人/画外音续）的不算。
6. 听者蜡像：对话镜头里听者只有"听/看着"没有具体微表情或动作=ERROR。
7. 多人镜头无方位：三人及以上同框镜头没有逐人方位点名（左/中/右/前景）=WARN。
8. 裸"切到"：镜头描述里用"切到X"无运镜桥接=WARN。
9. 引子无动作闭环：B版引子（无台词首镜）末尾动作没写收束=WARN。
10. 医生台词含保险词=ERROR；产品名出现≠1次=ERROR。

输出格式（严格遵守，无问题的检查项不要输出）：
[ERROR|WARN] 脚本N-X版 段M 镜头K｜类别｜问题一句话｜修法一句话
最后加一行统计：ERROR x个 / WARN y个。没有问题就只输出：ALL PASS。"""


def call_llm(chapter: str, key: str) -> str:
    body = {"model": LLM_MODEL, "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": chapter[:60000]}], "temperature": 0.1}
    for a in range(3):
        try:
            r = requests.post(LLM_URL, json=body, timeout=120, headers={
                "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            if r.status_code == 429:
                time.sleep(30 * (a + 1)); continue
            r.raise_for_status()
            d = r.json()
            return d["choices"][0]["message"]["content"]
        except Exception as e:
            if a == 2:
                raise
            print(f"  [LLM retry {a+1}] {str(e)[:80]}", flush=True)
            time.sleep(15)
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="分镜 LLM 语义审查")
    ap.add_argument("--file", required=True, type=Path)
    ap.add_argument("--out", default="", help="报告输出路径（默认 {file}_审.md）")
    ap.add_argument("--script", default="", help="只审指定脚本号（如 3）")
    ap.add_argument("--strict", action="store_true", help="有 ERROR exit 1")
    args = ap.parse_args()

    if not LLM_KEYS:
        print("无 LLM key（LLM_KEYS/env）", file=sys.stderr)
        return 2
    text = args.file.read_text(encoding="utf-8")
    chapters = re.split(r"(?m)(?=^## 脚本\d+：)", text)
    head, chapters = chapters[0], chapters[1:]
    if args.script:
        chapters = [c for c in chapters if re.match(rf"## 脚本{args.script}：", c)]
    if not chapters:
        print("未找到脚本章", file=sys.stderr)
        return 2

    print(f"审查 {len(chapters)} 个脚本章 → {LLM_MODEL}")
    all_lines, n_err, n_warn = [], 0, 0
    for i, ch in enumerate(chapters, 1):
        title = re.match(r"## 脚本(\d+)：([^\n（（]*)", ch)
        tag = f"脚本{title.group(1)}" if title else f"章{i}"
        print(f"[{i}/{len(chapters)}] {tag} 审查中……", flush=True)
        try:
            out = call_llm(ch, LLM_KEYS[0])
        except Exception as e:
            out = f"[ERROR] {tag}｜LLM调用失败｜{str(e)[:80]}｜换key或稍后重试"
        clean = out.strip()
        all_lines.append(f"### {tag}\n\n{clean}\n")
        errs = len(re.findall(r"^\[ERROR\]", clean, re.M))
        warns = len(re.findall(r"^\[WARN\]", clean, re.M))
        n_err += errs; n_warn += warns
        status = "ALL PASS" if "ALL PASS" in clean else f"ERROR {errs} / WARN {warns}"
        print(f"  → {status}", flush=True)
        time.sleep(2)

    report = f"# 分镜语义审查报告\n\n源：{args.file.name}｜{time.strftime('%Y-%m-%d %H:%M')}\n\n"
    report += f"总计：ERROR {n_err} / WARN {n_warn}（{len(chapters)}章）\n\n---\n\n"
    report += "\n".join(all_lines)
    outp = Path(args.out) if args.out else args.file.with_name(args.file.stem + "_审.md")
    outp.write_text(report, encoding="utf-8")
    print(f"\n报告 → {outp}")
    print(f"总计：ERROR {n_err} / WARN {n_warn}")
    if args.strict and n_err:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
