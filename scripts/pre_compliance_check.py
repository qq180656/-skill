#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""预测性合规校验门 (Pre-Compliance Gate)

核心定位：在 PLANNING 阶段（脚本刚写完、还没进 STORYBOARD）就跑全量校验，
把合规问题消灭在分镜生成之前，避免"生完视频才发现违规再返工"。

与 gate_verify.py 的关系：
  - gate_verify.py   = 送审前最终门（成片/前贴出片前最后一道，exit 1 硬拦）
  - pre_compliance_check.py = 生成前预测门（脚本阶段，输出结构化修复建议）
  - 两者共享禁用词/产品配置，但本脚本额外输出 fix_action 字段，
    告诉上层工作流"这个错误该怎么修"，而不只是"这里有错"。

输出格式（JSON）：
  {
    "status": "PASS" | "FAIL",
    "summary": {"errors": N, "warns": N, "suggestions": N},
    "product": "好医保·中老年长期医疗",
    "type": "成片",
    "findings": [
      {
        "level": "ERROR",
        "category": "禁用串",
        "detail": "'一定能赔' — 承诺类用语",
        "source": "trigger_conditions §1",
        "line": 3,
        "context": "有这份保险就一定能赔",
        "fix_action": {
          "action": "REPLACE",
          "target": "一定能赔",
          "replacement": "审核通过后可按条款约定赔付",
          "auto": true
        }
      },
      ...
    ],
    "meta": {"口播字数": 156, "语速": 7, "估算台词秒": 22.3, ...}
  }

fix_action 类型：
  - REPLACE   : 自动替换禁用词/表述（auto=true 时上层可自动执行）
  - ADD_WARN  : 自动补挂警示语（auto=true，附完整警示语文本）
  - FIX_FORMAT: 格式修正（如"0免赔"→"0免赔额"）
  - USER_DECIDE: 需用户决策（边界模糊/多种替换方案，auto=false）
  - REMOVE    : 删除该表述（auto=true）

用法：
  python pre_compliance_check.py --product 中老年 --type 成片 --file 脚本.txt
  python pre_compliance_check.py --product 门诊险 --type 前贴 --text "脚本文本" --duration 15
  echo "脚本文本" | python pre_compliance_check.py --product 长钱保 --type 成片

退出码：
  0 = PASS（无 ERROR）
  1 = FAIL（有 ERROR，需修复后再进分镜）
  2 = 系统错误
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

CN = re.compile(r"[一-鿿]")

# ── 通用硬红线 ──────────────────────────────────────────────────────
# 每条增加 fix_replace 字段：自动替换建议
GENERIC_BAN = [
    {
        "pat": r"一定能|保证赔|必定赔|稳赚|确诊就赔|秒赔|包赔",
        "desc": "承诺类用语", "src": "trigger_conditions §1",
        "fix": "审核通过后可按条款约定赔付",
    },
    {
        "pat": r"唯一|首选|独家|第一|最好|最划算|最贴心|最实用|顶级|最强",
        "desc": "误导/极限词", "src": "通用+new_solo_014",
        "fix": "性价比较高、保障范围较广",
    },
    {
        "pat": r"比.{0,6}(更|强|好)(?!医保)|远超|甩.{0,3}几条街|智商税",
        "desc": "比较/拉踩贬低", "src": "new_solo_024",
        "fix": "客观描述产品特点，不做对比贬低",
    },
    {
        "pat": r"医保(没用|不管用|报得少|报销范围太窄|起付线高|太鸡肋)",
        "desc": "贬低医保", "src": "门诊医疗险-合规",
        "fix": "医保的补充",
    },
    {
        "pat": r"都能赔|都能报|花多少报多少|看病不花钱|[0０]自费|零自费|全额报销|全报(?!销比例)",
        "desc": "都能赔类绝对承诺", "src": "new_solo_060/095",
        "fix": "在保险责任范围内可按条款约定申请理赔",
    },
    {
        "pat": r"生病.{0,4}(也能买|赶紧买)|住院.{0,4}赶紧买|带病(可投|也能投)|先别去检查|先买.{0,3}再体检",
        "desc": "带病投保暗示", "src": "new_solo_070",
        "fix": "符合条件可投保",
    },
    {
        "pat": r"因病返贫|倾家荡产|家破人亡|拖垮全家|砸锅卖铁|人财两空",
        "desc": "卖惨/焦虑营销", "src": "new_solo_085",
        "fix": "提前规划，减轻家庭经济压力",
    },
    {
        "pat": r"裁员|失业|经济下行|工资停发|行业.{0,3}完了|越想越慌",
        "desc": "经济环境焦虑", "src": "new_solo_047",
        "fix": "未来存在不确定性，合理规划可以更安心",
    },
    {
        "pat": r"月光族|穷人|穷鬼|屌丝|不指望你|拖累家里|不孝|老古董",
        "desc": "人群贴签/家庭对立", "src": "new_solo_017/097",
        "fix": "去除人群标签，正面表述产品价值",
    },
    {
        "pat": r"停售|限时|抢购|秒杀|最后\d+天|错过不再|不买就后悔|末班车|再不买",
        "desc": "虚假炒售/饥饿促销", "src": "new_solo_019",
        "fix": "去除限时/饥饿表述，正常介绍产品",
    },
    {
        "pat": r"就够了|一款解决|什么(病)?都能保|万能|保障全了",
        "desc": "产品万能化", "src": "new_solo_021",
        "fix": "主要用于解决XX风险，可搭配其他产品完善保障",
    },
    {
        "pat": r"医生|护士|白大褂|主任医师|护士长|专家说|钟南山",
        "desc": "医护/名人形象背书", "src": "通用禁医生宣传",
        "fix": "改用保险公司专业人员/规划师/客服形象",
    },
    {
        "pat": r"\d+[wW]",
        "desc": "禁用 w 代替万", "src": "通用",
        "fix": "用'万'字规范表述",
    },
]

# 格式修正项（FIX_FORMAT）：可自动修复的格式问题
FORMAT_FIXES = [
    {
        "pat": r"[0０]免赔(?!额)|零免赔(?!额)",
        "desc": "0免赔缺'额'字",
        "src": "门诊医疗险",
        "fix": "0免赔额",
    },
    {
        "pat": r"100%(?!比例)(?!的)(?!报销比例)(?!赔付)(?!责任内)",
        "desc": "100%未写'比例报销/比例赔付'",
        "src": "险种专项-表述规范",
        "fix": "100%比例报销",
    },
    {
        "pat": r"(?<![你我他它她们这那ang])[他她](?!们)",
        "desc": "保险代词应统一用'它'",
        "src": "代词校验",
        "fix": "它",
    },
]

# 绝对化软词（WARN）
SOFT_BAN = re.compile(r"[都均]|(?<!最)最(?!高|低|长)|(?<![公责])全(?!勤|额报销比例)")

# ── 产品配置 ────────────────────────────────────────────────────────
PRODUCTS = {
    "门诊险": {
        "id": "36866", "name": "好医保·门诊险", "speed": 7, "pronoun": "它",
        "ban": [
            {"pat": r"线上问诊|在线问诊|网上问诊|视频问诊", "desc": "严禁线上问诊(需互联网医院资质)", "src": "36866审核红线", "fix": "去除线上问诊相关表述"},
            {"pat": r"[0０]免赔(?!额)|零免赔(?!额)|无免赔", "desc": "0免赔缺'额'字", "src": "门诊医疗险", "fix": "0免赔额"},
            {"pat": r"搜(一下)?支付宝|支付宝搜|上支付宝搜|应用商店搜", "desc": "禁引导支付宝搜索", "src": "36866审核红线", "fix": "点击视频下方链接"},
        ],
        "trigger": r"报销|比例|免赔额|日限额|保额|保费|\d+元|\d+成|等待期|线上买药|在线上拿药",
        "must_full": r"支付宝上的\s*好医保\s*[·，,]?\s*门诊险",
        "must_full_fix": "支付宝上的好医保·门诊险",
        "extra_checks": [
            {"condition": "must_contain", "target": "支付宝上的", "desc": "门诊险须说'支付宝上的好医保·门诊险'（'上的'二字必加）", "src": "36866"},
        ],
    },
    "中老年": {
        "id": "52973", "name": "好医保·中老年长期医疗", "speed": 7, "pronoun": "它",
        "ban": [
            {"pat": r"痛风|骨折|胰腺|冠心病|脑中风|帕金森|尿毒症", "desc": "病种越界(非白名单病种,只可提高血压/糖尿病/结节)", "src": "new_solo_058/078", "fix": "只提高血压/糖尿病/结节"},
            {"pat": r"[0０]免赔(?!额)|零免赔(?!额)", "desc": "0免赔缺'额'字", "src": "门诊医疗险", "fix": "0免赔额"},
        ],
        "trigger": r"400万|保额|保障|\d+\.?\d*元|保费|\d+岁|高血压|糖尿病|结节|免赔额|比例|报销|续保|7大|七大|新发部位|理赔|健康告知|投保条件",
        "must_full": r"好医保\s*[·，,]?\s*中老年长期医疗",
        "must_full_fix": "好医保·中老年长期医疗",
        "extra_checks": [],
    },
    "长钱保": {
        "id": "47711", "name": "长钱保·五年领年金", "speed": 6, "pronoun": "它",
        "ban": [
            {"pat": r"存钱|攒钱|攒个|小金库|储蓄|预存|存钱罐|强制储蓄", "desc": "金融混同:储蓄化表达", "src": "new_solo_013", "fix": "资金规划/财富管理"},
            {"pat": r"理财|定投|基金|投基金|利息|领利息|收益(?!率以)|回本|翻倍|复利|本金安全", "desc": "金融混同:理财/收益化", "src": "new_solo_013/026", "fix": "资金增值/风险转移"},
            {"pat": r"比.{0,4}银行|存银行|银行(利息|存款).{0,4}(低|差)", "desc": "不当类比银行", "src": "new_solo_077", "fix": "去除与银行的对比"},
            {"pat": r"长钱宝|常钱保|偿钱宝|偿钱保", "desc": "产品名错字", "src": "审核红线", "fix": "长钱保"},
        ],
        "trigger": r"领取|现金价值|年金|保费|\d+元|满\d+年",
        "must_full": r"长钱保\s*[·，,]?\s*五年领年金",
        "must_full_fix": "长钱保·五年领年金",
        "extra_checks": [],
    },
    "default": {
        "id": "", "name": "", "speed": 7, "pronoun": "它",
        "ban": [], "trigger": r"保额|保费|免赔额|比例|报销|等待期|续保",
        "must_full": "", "must_full_fix": "", "extra_checks": [],
    },
}

# 前贴不该出现的利益点关键词
PREROLL_BENEFIT = re.compile(r"\d+万|\d+\.?\d*元起|报销比例|赔付比例|免赔额|日限额|保额|\d+%|保证续保|\d+岁也能")

OPEN, CLOSE = set("([（【"), set(")]）】")

# ── 警示语模板库（按触发词分类，实际以产品专属文件为准）──────────────
# 这里存的是"通用兜底"模板，具体产品警示语以 rules.md 各产品小节为准
WARNING_TEMPLATES = {
    "中老年": {
        # key = 触发词正则, value = 警示语完整文本
        r"400万|保额.{0,4}400万": "（责任内400万医疗保障，具体保险金额以实际投保页保险合同为准）",
        r"\d+\.?\d*元起|保费.{0,4}\d+": "（有医保）（保费随不同年龄、有无社保等情况变化）（具体费率以实际投保页为准）",
        r"不贵|便宜": "（首年最低保费15.08元/月起（有医保），以55岁老人举例，基础保障参考保费，首年最低保费122.99元/月(有医保)，保费随不同年龄、有无社保等情况变化。具体费率以实际投保页为准）",
        r"\d+岁也能买|\d+岁可投保|70岁也能买": "（符合健告/投保条件可投保）",
        r"保证续保终身|最长保终身": "（一般医疗保证续保20年，重度恶性肿瘤治疗/7大新发结节等手术治疗/指定术后复筛查责任保证续保终身）",
        r"保证续保20年|续保20年": "（一般医疗保证续保20年，重度恶性肿瘤治疗/7大新发结节等手术治疗/指定术后复筛查责任保证续保终身）",
        r"0免赔额|一元起赔|100%比例报销|100%比例赔付": "（一般医疗2万免赔额,重度恶性肿瘤治疗/先进医药责任/7大新发结节等手术治疗/指定术后复筛查责任0免赔额,责任内最高100%比例报销）（符合条款约定可赔付）",
        r"高血压.{0,6}可投|糖尿病.{0,6}可投|三高.{0,6}可投": "（由高血压或糖尿病引发的并发症需关注健康告知要求，乳腺结节≥4级、肺结节＞3mm有除外承保，具体以健康告知、核保结论为准）（符合条件可投保）",
        r"结节.{0,6}可投": "（由高血压或糖尿病引发的并发症需关注健康告知要求，乳腺结节≥4级、肺结节＞3mm有除外承保，具体以健康告知、核保结论为准）",
        r"7大新发部位|七大新发部位": "（责任内）（7大新发部位保障需满足疾病定义、治疗方式和医院范围等要求）（部分结节可能存在特定疾病责任除外）",
        r"复筛查|CT超声胃肠镜": "（责任内）（复筛查责任仅限符合条件的指定手术后复筛查，不等同于普通体检报销）（符合条款约定可赔付）",
    },
    "门诊险": {
        r"报销比例|赔付比例": "（具体报销比例以实际投保页保险条款为准）",
        r"免赔额|日限额": "（具体免赔额和日限额以实际投保页保险条款为准）",
        r"线上买药|在线上拿药": "（以实际投保页保险条款约定的药品目录和赔付条件为准）",
    },
    "长钱保": {
        # 年金险主要是禁用表述，警示语较少
        r"领取|现金价值": "（具体领取金额和现金价值以实际投保页保险合同为准）",
    },
}


def strip_parens(text: str):
    """括号深度法剥离警示语（兼容混合括号）→ (口播正文, 警示语列表)。"""
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


def find_line_number(text: str, pos: int) -> int:
    """根据字符位置返回行号。"""
    return text[:pos].count("\n") + 1


def get_context(text: str, pos: int, radius: int = 15) -> str:
    """获取匹配位置周围的文本上下文。"""
    start = max(0, pos - radius)
    end = min(len(text), pos + radius)
    return text[start:end].replace("\n", " ").strip()


class Finding:
    __slots__ = ("level", "category", "detail", "source", "line", "context", "fix_action")

    def __init__(self, level, category, detail, source="", line=0, context="", fix_action=None):
        self.level = level
        self.category = category
        self.detail = detail
        self.source = source
        self.line = line
        self.context = context
        self.fix_action = fix_action

    def to_dict(self):
        d = {
            "level": self.level,
            "category": self.category,
            "detail": self.detail,
        }
        if self.source:
            d["source"] = self.source
        if self.line:
            d["line"] = self.line
        if self.context:
            d["context"] = self.context
        if self.fix_action:
            d["fix_action"] = self.fix_action
        return d


def _make_replace_action(match_text, replacement, auto=True):
    """构造 REPLACE 类型的 fix_action。"""
    return {
        "action": "REPLACE",
        "target": match_text,
        "replacement": replacement,
        "auto": auto,
    }


def _make_add_warning_action(warning_text, trigger_word, auto=True):
    """构造 ADD_WARN 类型的 fix_action。"""
    return {
        "action": "ADD_WARN",
        "warning_text": warning_text,
        "trigger_word": trigger_word,
        "auto": auto,
    }


def _make_format_fix_action(target, replacement, auto=True):
    """构造 FIX_FORMAT 类型的 fix_action。"""
    return {
        "action": "FIX_FORMAT",
        "target": target,
        "replacement": replacement,
        "auto": auto,
    }


def _make_user_decide_action(reason, options=None):
    """构造 USER_DECIDE 类型的 fix_action。"""
    return {
        "action": "USER_DECIDE",
        "reason": reason,
        "options": options or [],
        "auto": False,
    }


def _make_remove_action(target, auto=True):
    """构造 REMOVE 类型的 fix_action。"""
    return {
        "action": "REMOVE",
        "target": target,
        "auto": auto,
    }


def check_warnings_mapping(text, spoken_full, product_key, vtype, findings, p):
    """警示语映射校验：含触发词的行是否紧跟警示语。

    与 gate_verify 的差异：
    - 不只报"缺挂"，而是给出应该补挂的完整警示语文本
    - 如果触发了多个警示语模板，全部列出
    """
    if vtype != "成片":
        return

    trig = re.compile(p["trigger"])
    templates = WARNING_TEMPLATES.get(product_key, {})

    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        sp, wn = strip_parens(line)
        if trig.search(sp) and not wn:
            # 有触发词但无警示语 → 查找应该挂哪个警示语
            matched_warnings = []
            for trig_pat, warn_text in templates.items():
                if re.search(trig_pat, sp):
                    matched_warnings.append(warn_text)

            if matched_warnings:
                # 找到匹配的警示语模板
                for wt in matched_warnings:
                    findings.append(Finding(
                        "ERROR", "警示语缺挂",
                        f"第{i}行含触发词但无警示语，应补挂: {wt[:40]}...",
                        "rules.md 警示语映射",
                        line=i,
                        context=sp.strip()[:50],
                        fix_action=_make_add_warning_action(wt, sp.strip()[:20])
                    ))
            else:
                # 没有匹配到具体模板，标记为需用户决策
                findings.append(Finding(
                    "ERROR", "警示语缺挂",
                    f"第{i}行含触发词但无警示语，且无自动匹配模板",
                    "rules.md 警示语映射",
                    line=i,
                    context=sp.strip()[:50],
                    fix_action=_make_user_decide_action(
                        "无法自动匹配警示语，需参考产品专属文件手动补挂",
                        ["查阅 产品专属/ 目录对应产品文件", "参考 rules.md 警示语映射表"]
                    )
                ))


def check_responsibility_prefix(text, spoken_full, findings):
    """检查'责任内'前缀规则。

    口播说了"责任内" → 警示语不重复加
    口播没说"责任内" → 警示语须加（责任内）前缀
    """
    if "责任内" not in spoken_full:
        # 口播没说"责任内"，检查警示语里是否有"责任内"前缀
        _, warnings = strip_parens(text)
        for w in warnings:
            if "责任内" not in w and ("赔付" in w or "报销" in w):
                findings.append(Finding(
                    "WARN", "责任内前缀",
                    f"口播未说'责任内'，该警示语可能需加（责任内）前缀: {w[:30]}...",
                    "rules.md 核心原则4",
                    fix_action=_make_user_decide_action(
                        "口播未说'责任内'，警示语是否需要加前缀需确认",
                    )
                ))


def check_preroll_benefit(spoken_full, findings):
    """前贴零利益点检查。"""
    for m in PREROLL_BENEFIT.finditer(spoken_full):
        findings.append(Finding(
            "WARN", "前贴利益点",
            f"前贴应零利益点(只引产品名),出现: '{m.group(0)}'",
            "rules.md 前贴豁免",
            fix_action=_make_remove_action(m.group(0))
        ))


def check_must_contain(text, spoken_full, p, product_key, findings):
    """必加项检查：产品名完整格式、额外必加项。"""
    # 产品名完整格式
    if p["must_full"] and not re.search(p["must_full"], text):
        findings.append(Finding(
            "ERROR", "必加项缺失",
            f"产品名未按完整格式出现（应含'{p['name']}'及规范写法）",
            p["id"],
            fix_action=_make_replace_action(p["name"] or "产品名", p.get("must_full_fix", ""), auto=False)
        ))

    # 产品额外必加项
    for ec in p.get("extra_checks", []):
        if ec["condition"] == "must_contain" and ec["target"] not in text:
            findings.append(Finding(
                "ERROR", "必加项缺失",
                ec["desc"],
                ec["src"],
                fix_action=_make_user_decide_action(
                    f"需添加 '{ec['target']}' 到脚本中",
                )
            ))


def check_banned_words(spoken_full, p, findings):
    """禁用词扫描：通用 + 产品专属。"""
    for item in GENERIC_BAN + p["ban"]:
        pat = item["pat"]
        desc = item["desc"]
        src = item["src"]
        fix = item.get("fix", "")
        for m in re.finditer(pat, spoken_full):
            # 判断 auto 级别
            # 承诺类/极限词/拉踩 → 可自动替换
            # 医护形象/饥饿促销 → 需用户决策（涉及场景重构）
            auto = True
            if "医护" in desc or "名人" in desc:
                auto = False
            if "饥饿" in desc or "炒售" in desc:
                auto = False

            action = _make_replace_action(m.group(0), fix, auto=auto) if fix else _make_user_decide_action(
                f"需移除'{m.group(0)}'并替换为合规表述", [fix] if fix else []
            )
            findings.append(Finding(
                "ERROR", "禁用串",
                f"'{m.group(0)}' — {desc}",
                src,
                context=get_context(spoken_full, m.start()),
                fix_action=action,
            ))


def check_soft_words(spoken_full, findings):
    """绝对化软词检查（WARN）。"""
    for m in SOFT_BAN.finditer(spoken_full):
        findings.append(Finding(
            "WARN", "绝对化软词",
            f"'{m.group(0)}'（人工复核；最高/最低/最长=官方话术不算）",
            "trigger_conditions §1",
            context=get_context(spoken_full, m.start()),
            fix_action=_make_user_decide_action(
                "绝对化词需人工判断是否为官方合规话术",
                ["如为官方话术（最高/最低/最长）可保留", "否则替换为'可''能''部分'"]
            )
        ))


def check_format_fixes(spoken_full, findings):
    """格式修正检查（FIX_FORMAT）。"""
    for item in FORMAT_FIXES:
        for m in re.finditer(item["pat"], spoken_full):
            findings.append(Finding(
                "WARN", "格式修正",
                f"'{m.group(0)}' — {item['desc']}，建议改为 '{item['fix']}'",
                item["src"],
                context=get_context(spoken_full, m.start()),
                fix_action=_make_format_fix_action(m.group(0), item["fix"])
            ))


def check_word_count(spoken_full, p, vtype, duration, findings):
    """字数上限检查。"""
    n = cn(spoken_full)
    if vtype == "前贴":
        cap = int((duration - 2) * p["speed"])
        if n > cap:
            findings.append(Finding(
                "ERROR", "字数超限",
                f"口播{n}字 > 上限{cap}字((时长{duration:.0f}-2)×{p['speed']}字/秒)",
                "entry_brief_only",
                fix_action=_make_user_decide_action(
                    f"需精简口播至{cap}字以内（当前{n}字，超出{n-cap}字）",
                )
            ))
        # 产品名位置 75-85%
        if p["name"]:
            pos = spoken_full.find(p["name"].split("·")[0])
            if pos >= 0:
                pct = cn(spoken_full[:pos]) / n * 100 if n else 0
                if not (70 <= pct <= 88):
                    findings.append(Finding(
                        "WARN", "产品名位置",
                        f"产品名在{pct:.0f}%处(建议75-85%)",
                        "config_matrix",
                        fix_action=_make_user_decide_action(
                            f"建议调整产品名位置到全文75-85%处（当前{pct:.0f}%）",
                        )
                    ))


def pre_check(text: str, product: str, vtype: str, duration: float = 15.0) -> dict:
    """主校验函数：返回结构化 JSON 结果。

    与 gate_verify.verify() 的区别：
    1. 输出 fix_action（不只是"有错"，还有"怎么修"）
    2. 警示语缺挂时自动匹配模板并给出完整警示语文本
    3. 检查"责任内"前缀规则
    4. 格式修正项单独分类
    """
    p = PRODUCTS.get(product, PRODUCTS["default"])
    findings: list[Finding] = []
    spoken_full, _ = strip_parens(text)

    # 1. 禁用词扫描
    check_banned_words(spoken_full, p, findings)

    # 2. 软词（WARN）
    check_soft_words(spoken_full, findings)

    # 3. 格式修正（WARN，可自动修复）
    check_format_fixes(spoken_full, findings)

    # 4. 必加项
    check_must_contain(text, spoken_full, p, product, findings)

    # 5. 警示语映射校验（成片）
    check_warnings_mapping(text, spoken_full, product, vtype, findings, p)

    # 6. "责任内"前缀规则
    check_responsibility_prefix(text, spoken_full, findings)

    # 7. 前贴零利益点
    if vtype == "前贴":
        check_preroll_benefit(spoken_full, findings)

    # 8. 字数上限
    check_word_count(spoken_full, p, vtype, duration, findings)

    # 汇总
    errs = [f for f in findings if f.level == "ERROR"]
    warns = [f for f in findings if f.level == "WARN"]
    auto_fixable = [f for f in findings if f.fix_action and f.fix_action.get("auto")]
    user_decisions = [f for f in findings if f.fix_action and not f.fix_action.get("auto")]

    n = cn(spoken_full)
    meta = {
        "口播字数": n,
        "语速": p["speed"],
        "估算台词秒": round(n / p["speed"], 1),
        "产品": p["name"] or product,
        "类型": vtype,
        "自动可修复数": len(auto_fixable),
        "需用户决策数": len(user_decisions),
    }

    return {
        "status": "PASS" if not errs else "FAIL",
        "summary": {
            "errors": len(errs),
            "warns": len(warns),
            "auto_fixable": len(auto_fixable),
            "user_decisions": len(user_decisions),
        },
        "product": p["name"] or product,
        "type": vtype,
        "findings": [f.to_dict() for f in findings],
        "meta": meta,
    }


def format_report(result: dict) -> str:
    """格式化终端输出（人类可读）。"""
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"预测性合规校验 | 产品={result['product']} 类型={result['type']}")
    lines.append(f"口播{result['meta']['口播字数']}字 ≈{result['meta']['估算台词秒']}s")
    lines.append(f"{'='*60}")

    if result["status"] == "PASS" and not result["findings"]:
        lines.append("  [PASS] 脚本层检查全部通过，可进入分镜阶段")
    else:
        for f in result["findings"]:
            icon = {"ERROR": "❌", "WARN": "⚠️"}.get(f["level"], "ℹ️")
            line_str = f"  {icon} [{f['level']}] {f['category']}: {f['detail']}"
            if f.get("source"):
                line_str += f"  <- {f['source']}"
            if f.get("line"):
                line_str += f"  (第{f['line']}行)"
            lines.append(line_str)

            # 输出 fix_action
            fa = f.get("fix_action")
            if fa:
                action_icon = "🔧" if fa.get("auto") else "✋"
                action_type = fa["action"]
                if action_type == "REPLACE":
                    lines.append(f"      {action_icon} 修复: '{fa['target']}' → '{fa['replacement']}'" + (" [自动]" if fa["auto"] else " [需确认]"))
                elif action_type == "ADD_WARN":
                    lines.append(f"      {action_icon} 补挂警示语: {fa['warning_text'][:50]}..." + (" [自动]" if fa["auto"] else " [需确认]"))
                elif action_type == "FIX_FORMAT":
                    lines.append(f"      {action_icon} 格式修正: '{fa['target']}' → '{fa['replacement']}'" + (" [自动]" if fa["auto"] else " [需确认]"))
                elif action_type == "REMOVE":
                    lines.append(f"      {action_icon} 删除: '{fa['target']}'" + (" [自动]" if fa["auto"] else " [需确认]"))
                elif action_type == "USER_DECIDE":
                    lines.append(f"      ✋ 需用户决策: {fa['reason']}")
                    for opt in fa.get("options", []):
                        lines.append(f"         - {opt}")

    lines.append(f"{'='*60}")
    s = result["summary"]
    lines.append(f"结果: {result['status']}  ({s['errors']} ERROR / {s['warns']} WARN)")
    lines.append(f"自动可修复: {s['auto_fixable']}  需用户决策: {s['user_decisions']}")
    if result["status"] == "FAIL":
        lines.append("⚠ 请修复所有 ERROR 后再进入分镜阶段（STORYBOARD）")
    else:
        lines.append("✓ 可进入分镜阶段（STORYBOARD）")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="预测性合规校验门 (Pre-Compliance Gate)")
    ap.add_argument("--product", default="default", choices=list(PRODUCTS), help="产品(门诊险/中老年/长钱保/default)")
    ap.add_argument("--type", dest="vtype", default="成片", choices=["前贴", "成片", "纯脚本"], help="出口类型")
    ap.add_argument("--duration", type=float, default=15.0, help="前贴目标秒数(默认15)")
    ap.add_argument("--file", type=Path, help="脚本文件路径")
    ap.add_argument("--text", help="直接传脚本文本")
    ap.add_argument("--json", action="store_true", help="输出 JSON 格式（供上层工作流解析）")
    ap.add_argument("--strict", action="store_true", help="有 ERROR 时 exit 1")
    args = ap.parse_args()

    if args.file:
        text = args.file.read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()
    if not text.strip():
        print("空输入", file=sys.stderr)
        return 2

    vtype = "成片" if args.vtype == "纯脚本" else args.vtype
    result = pre_check(text, args.product, vtype, args.duration)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result))

    return 1 if (args.strict and result["status"] == "FAIL") else 0


if __name__ == "__main__":
    sys.exit(main())
