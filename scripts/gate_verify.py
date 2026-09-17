#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AI视频生产规范 — 送审前确定性合规门 gate_verify（脚本层）。

把"确定性判据"从"靠模型自觉"变成"脚本硬拦"——不调 LLM、跳不掉。
合并自两次实测中子代理各自自发写的机检脚本：
  · 字数上限/产品名位置/分层禁用正则/必加项  （门诊险前贴 compliance_check.py）
  · strip_parens 括号深度法剥离警示语/警示语配平/硬禁用词  （中老年成片 gen_scripts.py）

用法：
  python gate_verify.py --product 中老年 --type 成片 --file 脚本.txt
  python gate_verify.py --product 门诊险 --type 前贴 --text "……脚本文本……"
  cat 脚本.md | python gate_verify.py --product 长钱保 --type 成片
选项：--duration 目标秒数(前贴默认15)；--strict 有 ERROR 时 exit 1。

覆盖范围：脚本层（禁用串/必加项/警示语括号配平/字数/产品名位置/前贴零利益点）。
不覆盖：视频层（ffprobe 时长、ASR 发音、压底 logo）——需接实际出片链路，另做。
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

CN = re.compile(r"[一-鿿]")

# ── 通用硬红线（所有产品 ERROR；合并①BAN + ②BANNED，去重分类）──────────
GENERIC_BAN = [
    (r"一定能|保证赔|必定赔|稳赚|确诊就赔|秒赔|包赔", "承诺类用语", "trigger_conditions §1"),
    (r"唯一|首选|独家|第一|最好|最划算|最贴心|最实用|顶级|最强", "误导/极限词", "通用+new_solo_014"),
    (r"比.{0,6}(更|强|好)(?!医保)|远超|甩.{0,3}几条街|智商税", "比较/拉踩贬低", "new_solo_024"),
    (r"医保(没用|不管用|报得少|报销范围太窄|起付线高|太鸡肋)", "贬低医保", "门诊医疗险-合规"),
    (r"都能赔|都能报|花多少报多少|看病不花钱|[0０]自费|零自费|全额报销|全报(?!销比例)", "都能赔类绝对承诺", "new_solo_060/095"),
    (r"生病.{0,4}(也能买|赶紧买)|住院.{0,4}赶紧买|带病(可投|也能投)|先别去检查|先买.{0,3}再体检", "带病投保暗示", "new_solo_070"),
    (r"因病返贫|倾家荡产|家破人亡|拖垮全家|砸锅卖铁|人财两空", "卖惨/焦虑营销", "new_solo_085"),
    (r"裁员|失业|经济下行|工资停发|行业.{0,3}完了|越想越慌", "经济环境焦虑", "new_solo_047"),
    (r"月光族|穷人|穷鬼|屌丝|不指望你|拖累家里|不孝|老古董", "人群贴签/家庭对立", "new_solo_017/097"),
    (r"停售|限时|抢购|秒杀|最后\d+天|错过不再|不买就后悔|末班车|再不买", "虚假炒售/饥饿促销", "new_solo_019"),
    (r"就够了|一款解决|什么(病)?都能保|万能|保障全了", "产品万能化", "new_solo_021"),
    (r"医生|护士|白大褂|主任医师|护士长|专家说|钟南山", "医护/名人形象背书", "通用禁医生宣传"),
    (r"\d+[wW]", "禁用 w 代替万", "通用"),
]
# 绝对化软词（WARN：多为标记+人工复核，白名单 最高/最低/最长 不告警）
SOFT_BAN = re.compile(r"[都均]|(?<!最)最(?!高|低|长)|(?<![公责])全(?!勤|额报销比例)")

# ── 产品配置 ────────────────────────────────────────────────────────
PRODUCTS = {
    "门诊险": {
        "id": "36866", "name": "好医保·门诊险", "speed": 7, "pronoun": "它",
        "ban": [
            (r"线上问诊|在线问诊|网上问诊|视频问诊", "严禁线上问诊(需互联网医院资质)", "36866审核红线"),
            (r"[0０]免赔(?!额)|零免赔(?!额)|无免赔", "0免赔缺'额'字", "门诊医疗险"),
            (r"搜(一下)?支付宝|支付宝搜|上支付宝搜|应用商店搜", "禁引导支付宝搜索", "36866审核红线"),
        ],
        # 成片触发词：出现即该行必须跟警示语括号
        "trigger": r"报销|比例|免赔额|日限额|保额|保费|\d+元|\d+成|等待期|线上买药|在线上拿药",
        "must_full": r"支付宝上的\s*好医保\s*[·，,]?\s*门诊险",
    },
    "中老年": {
        "id": "52973", "name": "好医保·中老年长期医疗", "speed": 7, "pronoun": "它",
        "ban": [
            (r"痛风|骨折|胰腺|冠心病|脑中风|帕金森|尿毒症", "病种越界(非白名单病种,只可提高血压/糖尿病/结节)", "new_solo_058/078"),
            (r"[0０]免赔(?!额)|零免赔(?!额)", "0免赔缺'额'字", "门诊医疗险"),
        ],
        "trigger": r"400万|保额|保障|\d+\.?\d*元|保费|\d+岁|高血压|糖尿病|结节|免赔额|比例|报销|续保|7大|七大|新发部位|理赔|健康告知|投保条件",
        "must_full": r"好医保\s*[·，,]?\s*中老年长期医疗",
    },
    "长钱保": {
        "id": "47711", "name": "长钱保·五年领年金", "speed": 6, "pronoun": "它",
        "ban": [
            (r"存钱|攒钱|攒个|小金库|储蓄|预存|存钱罐|强制储蓄", "金融混同:储蓄化表达", "new_solo_013"),
            (r"理财|定投|基金|投基金|利息|领利息|收益(?!率以)|回本|翻倍|复利|本金安全", "金融混同:理财/收益化", "new_solo_013/026"),
            (r"比.{0,4}银行|存银行|银行(利息|存款).{0,4}(低|差)", "不当类比银行", "new_solo_077"),
            (r"长钱宝|常钱保|偿钱宝|偿钱保", "产品名错字", "审核红线"),
        ],
        "trigger": r"领取|现金价值|年金|保费|\d+元|满\d+年",
        "must_full": r"长钱保\s*[·，,]?\s*五年领年金",
    },
    "default": {
        "id": "", "name": "", "speed": 7, "pronoun": "它",
        "ban": [], "trigger": r"保额|保费|免赔额|比例|报销|等待期|续保", "must_full": "",
    },
}

# 前贴不该出现的利益点关键词
PREROLL_BENEFIT = re.compile(r"\d+万|\d+\.?\d*元起|报销比例|赔付比例|免赔额|日限额|保额|\d+%|保证续保|\d+岁也能")

OPEN, CLOSE = set("([（【"), set(")]）】")


def strip_parens(text: str):
    """括号深度法剥离警示语（兼容混合括号）→ (口播正文, 警示语列表)。源自②。"""
    spoken, warnings, depth, buf = [], [], 0, []
    for ch in text:
        if ch in OPEN:
            if depth == 0 and buf:
                spoken.append("".join(buf)); buf = []
            depth += 1
            if depth == 1:
                warnings.append([])
        elif ch in CLOSE:
            if depth > 0:
                depth -= 1
                if depth > 0 and warnings:
                    warnings[-1].append(ch)
        else:
            (warnings[-1].append(ch) if depth > 0 else buf.append(ch))
    if buf:
        spoken.append("".join(buf))
    return "".join(spoken), ["（" + "".join(w) + "）" for w in warnings]


def cn(text: str) -> int:
    return len(CN.findall(text))


class Finding:
    __slots__ = ("level", "cat", "detail", "src")
    def __init__(self, level, cat, detail, src=""):
        self.level, self.cat, self.detail, self.src = level, cat, detail, src


def verify(text: str, product: str, vtype: str, duration: float):
    p = PRODUCTS.get(product, PRODUCTS["default"])
    f: list[Finding] = []
    spoken_full, _ = strip_parens(text)          # 全文口播（剥掉所有警示语括号）

    # 1. 禁用串（通用 + 产品专属）→ 在口播正文里扫（警示语括号内的官方话术不算）
    for pat, desc, src in GENERIC_BAN + p["ban"]:
        for m in re.finditer(pat, spoken_full):
            f.append(Finding("ERROR", "禁用串", f"'{m.group(0)}' — {desc}", src))
    # 软词（WARN）
    for m in SOFT_BAN.finditer(spoken_full):
        f.append(Finding("WARN", "绝对化软词", f"'{m.group(0)}'（人工复核；最高/最低/最长=官方话术不算）", "trigger_conditions §1"))

    # 2. 必加项
    if p["must_full"] and not re.search(p["must_full"], text):
        f.append(Finding("ERROR", "必加项缺失", f"产品名未按完整格式出现（应含'{p['name']}'及规范写法）", p["id"]))
    if product == "门诊险" and "支付宝上的" not in text:
        f.append(Finding("ERROR", "必加项缺失", "门诊险须说'支付宝上的好医保·门诊险'（'上的'二字必加）", "36866"))
    if re.search(r"(?<![你我他它她们这那ang])[他她](?!们)", spoken_full):
        f.append(Finding("WARN", "代词", "保险代词应统一用'它'（疑似出现'他/她'指代保险）", p["id"]))

    # 3. 警示语配平（成片）：含触发词的行必须跟警示语括号
    trig = re.compile(p["trigger"])
    if vtype == "成片":
        for i, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            sp, wn = strip_parens(line)
            if trig.search(sp) and not wn:
                f.append(Finding("ERROR", "警示语缺挂",
                                 f"第{i}行含利益点/触发词但无警示语括号: {sp.strip()[:32]}…", "rules.md 警示语映射"))

    # 4. 前贴：零利益点
    if vtype == "前贴":
        for m in PREROLL_BENEFIT.finditer(spoken_full):
            f.append(Finding("WARN", "前贴利益点",
                             f"前贴应零利益点(只引产品名),出现: '{m.group(0)}'", "rules.md 前贴豁免"))

    # 5. 数值门：字数上限（前贴按 (时长-2)×语速）
    n = cn(spoken_full)
    if vtype == "前贴":
        cap = int((duration - 2) * p["speed"])
        if n > cap:
            f.append(Finding("ERROR", "字数超限", f"口播{n}字 > 上限{cap}字((时长{duration:.0f}-2)×{p['speed']}字/秒)", "entry_brief_only"))
        # 产品名位置 75-85%
        if p["name"]:
            pos = spoken_full.find(p["name"].split("·")[0])
            if pos >= 0:
                pct = cn(spoken_full[:pos]) / n * 100 if n else 0
                if not (70 <= pct <= 88):
                    f.append(Finding("WARN", "产品名位置", f"产品名在{pct:.0f}%处(建议75-85%)", "config_matrix"))
    est = n / p["speed"]
    return f, {"口播字数": n, "语速": p["speed"], "估算台词秒": round(est, 1),
               "产品": p["name"] or product, "类型": vtype}


def main() -> int:
    ap = argparse.ArgumentParser(description="送审前确定性合规门 gate_verify（脚本层）")
    ap.add_argument("--product", default="default", choices=list(PRODUCTS), help="产品(门诊险/中老年/长钱保/default)")
    ap.add_argument("--type", dest="vtype", default="成片", choices=["前贴", "成片", "纯脚本"], help="出口类型")
    ap.add_argument("--duration", type=float, default=15.0, help="前贴目标秒数(默认15)")
    ap.add_argument("--file", type=Path, help="脚本文件路径")
    ap.add_argument("--text", help="直接传脚本文本")
    ap.add_argument("--strict", action="store_true", help="有 ERROR 时 exit 1")
    args = ap.parse_args()

    if args.file:
        text = args.file.read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()
    if not text.strip():
        print("空输入", file=sys.stderr); return 2

    vtype = "成片" if args.vtype == "纯脚本" else args.vtype  # 纯脚本按内容走成片级警示语检查
    findings, meta = verify(text, args.product, vtype, args.duration)

    print(f"gate_verify | 产品={meta['产品']} 类型={args.vtype} | 口播{meta['口播字数']}字 ≈{meta['估算台词秒']}s")
    errs = [x for x in findings if x.level == "ERROR"]
    warns = [x for x in findings if x.level == "WARN"]
    if not findings:
        print("  [PASS] 脚本层检查全部通过")
    else:
        for x in errs + warns:
            print(f"  [{x.level}] {x.cat}: {x.detail}" + (f"  <- {x.src}" if x.src else ""))
    print(f"{'='*56}\n结果: {'FAIL' if errs else 'PASS'}  ({len(errs)} ERROR / {len(warns)} WARN)")
    return 1 if (args.strict and errs) else 0


if __name__ == "__main__":
    sys.exit(main())
