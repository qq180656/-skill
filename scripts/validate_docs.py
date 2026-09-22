#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AI视频生产规范 — 文档结构校验器（借鉴 ECC 的 validate-* CI 思路）。

四类检查（默认 WARN 只报告不阻塞；--strict 时任一 ERROR → exit 1）：

1. 孤儿文件   规范根内 .md 没有被任何其他 md 以文件名引用。
              豁免：元文件白名单 + 险种专项/*-合规要求.md（靠 rules.md §1
              的 `{险种}-合规要求.md` 约定动态加载，不点名不算孤儿）。
2. 悬空引用   md 里引用的 `xxx.md` / 相对路径目标不存在（跳过含占位符的模式）。
3. 产品三方一致  skill_config.PRODUCT_ID（权威）↔ 产品专属/文件名ID
                 ↔ trigger_conditions §2.2 映射表 ↔ SKILL.md §6 速查表。
4. 个人路径   硬编码 C:\\Users\\<name> / /Users/<name> / /home/<name>。

规范根自动从脚本位置推断（scripts/ 的父目录），不硬编码个人路径。
用法： python scripts/validate_docs.py [--strict] [--skill 路径]
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

# Windows 控制台默认 GBK，强制 stdout/stderr 用 UTF-8 输出中文与符号
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

SPEC_ROOT = Path(__file__).resolve().parent.parent
COMPLIANCE = SPEC_ROOT / "knowledge" / "compliance"
PRODUCT_DIR = COMPLIANCE / "产品专属"
TRIGGER = COMPLIANCE / "trigger_conditions.md"
SKILL_CONFIG = SPEC_ROOT / "scripts" / "skill_config.py"
DEFAULT_SKILL = Path.home() / ".claude" / "skills" / "ai-video-production" / "SKILL.md"

# 元文件：本就不该被功能引用，孤儿检查豁免
META_WHITELIST = {
    "README.md",
    "meta/changelog.md",
    "meta/glossary.md",
    "meta/_skill_revision_context.md",
    "knowledge/templates/index.md",
    "knowledge/compliance/产品专属/README_产品拒审点索引.md",
}
# 占位用户名：命中不算硬编码个人路径
PLACEHOLDER_USERS = {"example", "me", "user", "username", "you",
                     "yourname", "yourusername", "your-username", "name"}
# 已知未登记产品：体验版历史批次，有真实拒审数据但不在 skill_config 主产品线（有意豁免）
KNOWN_UNREGISTERED = {"45173", "52980"}

ID_RE = re.compile(r"(?<!\d)(\d{5})(?!\d)")


class Report:
    """收集分级结果。level ∈ ERROR/WARN/INFO。"""
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str]] = []  # (level, where, msg)

    def add(self, level: str, where: str, msg: str) -> None:
        self.items.append((level, where, msg))

    def section(self, title: str, rows: list[tuple[str, str, str]]) -> None:
        print(f"\n=== {title} ===")
        if not rows:
            print("  [OK] 无问题")
            return
        for level, where, msg in rows:
            print(f"  [{level}] {where}: {msg}")

    @property
    def errors(self) -> int:
        return sum(1 for lv, _, _ in self.items if lv == "ERROR")

    @property
    def warns(self) -> int:
        return sum(1 for lv, _, _ in self.items if lv == "WARN")


def rel(p: Path) -> str:
    try:
        return p.relative_to(SPEC_ROOT).as_posix()
    except ValueError:
        return str(p)


def all_md() -> list[Path]:
    return sorted(SPEC_ROOT.rglob("*.md"))


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


# ── 检查 1：孤儿文件 ─────────────────────────────────────
def check_orphans(rep: Report) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    mds = all_md()
    corpus = {p: read(p) for p in mds}
    for p in mds:
        relpath = rel(p)
        if relpath in META_WHITELIST:
            continue
        # 险种专项/*-合规要求.md、通用-合规补充规则.md：约定式加载，豁免
        if "险种专项/" in relpath and relpath.endswith(".md"):
            continue
        stem = p.stem  # 去 .md
        # 在“除自己外”的所有 md 里找 stem；排除仅出现在 README/index 的罗列
        referenced_by = [
            q for q in mds
            if q != p and stem in corpus[q]
            and rel(q) not in ("README.md", "knowledge/templates/index.md")
        ]
        if not referenced_by:
            rows.append(("WARN", relpath, "孤儿：无任何工作流/知识文件按文件名引用它"))
    for r in rows:
        rep.add(*r)
    return rows


# ── 检查 2：悬空引用（断链）────────────────────────────────
# 只认两种“真引用”：行内反引号包文件名、Markdown 链接。命令行示例(`` `cli --flag x.md` ``
# 整段反引号)不算——那是可执行示例,不是文档导航链接。
BACKTICK_RE = re.compile(r"`([^`\n]+?)`")
MDLINK_RE = re.compile(r"\]\(([^)\n]+?\.md[^)]*)\)")
PLACEHOLDER = re.compile(r"[{}<>*]")
# 运行时产物（项目 _session/ 下生成，非静态文档）：引用它们不算断链
RUNTIME_ARTIFACTS = {"creative_design.md", "storyboard.md"}
# 外部/跨 skill 资源：本库不含，属有意引用，不当断链
EXTERNAL_PREFIXES = ("fashion-film-studio/", "http://", "https://")
# 仅“对标/平台原生/外部名”语境下提到的文件名：是外部平台的文件名，非本库链接
EXTERNAL_NAME_CONTEXT = ("对标", "平台原生", "外部")
# 运行时 _session 产物：路径含 _session/ 或文件名在运行时清单
RUNTIME_PATH_MARK = "_session/"
# 命令行标志：出现在反引号段且含这些 → 是 CLI 示例，整段跳过
CLI_FLAG_RE = re.compile(r"(^|\s)(--?|python|node|pippit-tool-cli|npm|npx)\b")


def _extract_refs(seg: str):
    """从一段反引号文本/链接目标里抽出 .md 引用；命令行示例返回空。"""
    if CLI_FLAG_RE.search(seg):
        return []  # `python xxx.py --file y.md` → CLI 示例，非文档引用
    refs = re.findall(r"[A-Za-z0-9_./\\\-]+\.md", seg)
    return refs


def check_broken_links(rep: Report) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for p in all_md():
        text = read(p)
        for i, line in enumerate(text.splitlines(), 1):
            refs: list[str] = []
            # 反引号段：逐段判断是 CLI 示例还是文件名引用
            for seg in BACKTICK_RE.findall(line):
                refs.extend(_extract_refs(seg))
            # Markdown 链接 ](xxx.md)
            for seg in MDLINK_RE.findall(line):
                refs.append(seg.strip().split()[0])

            for ref in refs:
                ref = ref.strip()
                if not ref or PLACEHOLDER.search(ref):
                    continue  # 跳过 {产品名} / <对应险种> 等模式
                if Path(ref).name.startswith("_") and not ref.startswith("./"):
                    continue  # `_53408.md` 是文件名后缀模式说明,非真实链接
                if ref.startswith(EXTERNAL_PREFIXES) or RUNTIME_PATH_MARK in ref:
                    continue  # 跨 skill / URL / 运行时 _session 产物
                if any(ctx in line for ctx in EXTERNAL_NAME_CONTEXT):
                    continue  # “对标平台原生 xxx.md”——外部文件名,非本库链接
                # 临时排查文件（C:\\tmp 等）：正文语境为排查/台账路径，非文档链接
                if "tmp" in ref or "mtx_" in ref:
                    continue
                if Path(ref).name in RUNTIME_ARTIFACTS:
                    continue  # 运行时产物，非静态文档
                # 依次尝试：相对该文件目录 / 相对规范根 / 相对 compliance / 仅按 basename 全库
                cands = [p.parent / ref, SPEC_ROOT / ref, COMPLIANCE / ref]
                if any(c.exists() for c in cands):
                    continue
                base = Path(ref).name
                if any(q.name == base for q in all_md()):
                    continue  # basename 能在库里找到，视为可解析
                rows.append(("ERROR", f"{rel(p)}:{i}", f"悬空引用 → {ref}"))
    for r in rows:
        rep.add(*r)
    return rows


# ── 检查 3：产品三方一致 ─────────────────────────────────
def parse_product_id() -> dict[str, str]:
    """从 skill_config.py 抓 PRODUCT_ID = {...} 里的 名:ID（不执行文件）。"""
    text = read(SKILL_CONFIG)
    m = re.search(r"PRODUCT_ID\s*=\s*\{(.*?)\}", text, re.S)
    out: dict[str, str] = {}
    if not m:
        return out
    for name, pid in re.findall(r'"([^"]+)"\s*:\s*"(\d{5})"', m.group(1)):
        out[name] = pid
    return out


def ids_in_file(p: Path) -> set[str]:
    return set(ID_RE.findall(read(p)))


def ids_in_product_filenames() -> set[str]:
    ids: set[str] = set()
    if PRODUCT_DIR.is_dir():
        for f in PRODUCT_DIR.glob("*.md"):
            ids |= set(ID_RE.findall(f.name))
    return ids


def check_products(rep: Report) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    cfg = parse_product_id()                 # 权威产品清单
    cfg_ids = set(cfg.values())
    file_ids = ids_in_product_filenames()    # 产品专属/ 文件名里的 ID
    trigger_ids = ids_in_file(TRIGGER)       # trigger §2.2 出现的 ID

    # 3a. skill_config 有的产品，产品专属/ 应有对应文件
    for name, pid in cfg.items():
        if pid not in file_ids:
            rows.append(("WARN", "skill_config.PRODUCT_ID",
                         f"{name}({pid}) 无对应 产品专属/ 文件"))
    # 3b. 产品专属/ 有文件，但没进 trigger §2.2 映射表
    for pid in sorted(file_ids):
        if pid in KNOWN_UNREGISTERED or pid in trigger_ids:
            continue
        rows.append(("WARN", "trigger_conditions.md §2.2",
                     f"产品 {pid} 有专属文件但未进映射表 → 严格照文档定位会 file-not-found"))
    # 3c. 产品专属/ 有文件，但不在 skill_config（幽灵产品 ID）
    for pid in sorted(file_ids - cfg_ids):
        if pid in KNOWN_UNREGISTERED:
            continue
        rows.append(("INFO", "产品专属/",
                     f"文件 ID {pid} 不在 skill_config.PRODUCT_ID（幽灵/副本？）"))
    for r in rows:
        rep.add(*r)
    return rows


# ── 检查 4：硬编码个人路径 ───────────────────────────────
USER_RES = [
    re.compile(r"[A-Za-z]:[\\/]Users[\\/]([^\\/\s\"'`)]+)"),
    re.compile(r"/Users/([^/\s\"'`)]+)"),
    re.compile(r"/home/([^/\s\"'`)]+)"),
]


def check_personal_paths(rep: Report, skill_path: Path | None) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    targets = list(SPEC_ROOT.rglob("*.md")) + list(SPEC_ROOT.rglob("*.py"))
    if skill_path and skill_path.exists():
        targets.append(skill_path)
    for p in targets:
        if p.name == "validate_docs.py":
            continue  # 校验器自身含正则/占位，豁免
        if skill_path and p == skill_path:
            continue  # skill 入口的规范根绝对路径是功能必需（本机定位），单独维护
        text = read(p)
        for i, line in enumerate(text.splitlines(), 1):
            for rgx in USER_RES:
                for m in rgx.finditer(line):
                    if m.group(1).lower() in PLACEHOLDER_USERS:
                        continue
                    where = rel(p) if SPEC_ROOT in p.parents or p == SPEC_ROOT else str(p)
                    rows.append(("WARN", f"{where}:{i}",
                                 f"硬编码个人路径 → {m.group(0)}"))
    for r in rows:
        rep.add(*r)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="AI视频生产规范 文档结构校验器")
    ap.add_argument("--strict", action="store_true", help="有 ERROR 时 exit 1")
    ap.add_argument("--skill", type=Path, default=DEFAULT_SKILL,
                    help="ai-video-production/SKILL.md 路径（默认 ~/.claude/skills/...）")
    args = ap.parse_args()

    print(f"规范根: {SPEC_ROOT}")
    print(f"SKILL.md: {args.skill}{'' if args.skill.exists() else '  (未找到，跳过其个人路径扫描)'}")

    rep = Report()
    rep.section("1. 孤儿文件（险种专项/约定式加载已豁免）", check_orphans(rep))
    rep.section("2. 悬空引用 / 断链", check_broken_links(rep))
    rep.section("3. 产品三方一致（skill_config ↔ 产品专属/ ↔ trigger §2.2）", check_products(rep))
    rep.section("4. 硬编码个人路径", check_personal_paths(rep, args.skill))

    print(f"\n{'='*48}\n汇总: {rep.errors} ERROR / {rep.warns} WARN")
    if args.strict and rep.errors:
        print("--strict: 存在 ERROR → exit 1")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
