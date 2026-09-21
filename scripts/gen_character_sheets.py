#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""角色四视图设定稿批量生成（Seedream 5.0-lite，16:9 横排：大头肩 + 正/侧/背全身）。

通用、自包含——任何项目写一份角色配置 JSON 即可批量出图，不必再写 py：

    python gen_character_sheets.py --config my_chars.json --output D:/项目/参考图

配置 JSON 格式（descriptions 即"由头到脚物理白描"，不要带"四视图"等画面指令）：
{
  "model": "seedream-5.0-lite",          // 可选，默认此值
  "width": 3840, "height": 2160,         // 可选，16:9 且总像素>=3686400，默认4K
  "characters": [
    {"name": "character_A_mama", "desc": "32岁中国都市职场女性，窄长瓜子脸……雾霾蓝V领针织开衫……"},
    {"name": "group_baby", "kind": "custom",
     "prompt": "完整的自定义出图提示词（kind=custom 时整段逐字使用，不套四视图模板）"}
  ]
}

Key 解析顺序：环境变量 MULTIMODAL_API_KEY / BLUEAI_MEDIA_KEY →
build_video/config/ai_voice_api.json 的 blueai_media_key/blueai_key。

用法：
    python gen_character_sheets.py --config chars.json            # 全量（已存在自动跳过）
    python gen_character_sheets.py --config chars.json --only mama  # 只跑名字含 mama 的
    python gen_character_sheets.py --config chars.json --force      # 删图重出
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = "https://bmc-model-openapi.bluemediagroup.cn/api/doubao"
IMG_MODELS = {
    "seedream-4.5": ("doubao-seedream-4-5-251128", "/text2image_v4_5"),
    "seedream-5.0-lite": ("doubao-seedream-5-0-260128", "/text2image_v5_0"),
}
MIN_PIXELS = 3_686_400  # Seedream 2K+ 端点下限
TIMEOUT = (10, 90)

SHEET_SUFFIX = (
    "四视图角色设定稿，同一角色的人物正面头肩特写、正面、侧面、背面三个无头全身视图横向排列，"
    "人物特写只显示头部至肩部（锁定五官发型配饰），不显示腰部、腿部和脚，"
    "三个全身视图只显示肩膀衣领以下到脚尖（不画头部，头由特写负责），自然站立、双足平踏地面，"
    "四视图服装细节完全一致，特写衣领与全身衣领自然衔接，色彩准确统一。"
    "纯白色背景，均匀平光照明，无明显阴影。"
    "真人写实风格，中国当代普通人质感，皮肤纹理与发丝细节清晰。"
    "人物面部与手部皮肤干净，无痣、无黑痣、无明显色素痣点。"
    "三个全身视图严禁裁切下半身、严禁画出头部，人物特写禁止生成成全身视图，"
    "禁止生成任何背景、文本、标注、字幕。比例:16:9"
)


def log(msg: str):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", "replace").decode("ascii", "replace"), flush=True)


def resolve_key() -> str:
    k = (os.environ.get("MULTIMODAL_API_KEY") or
         os.environ.get("BLUEAI_MEDIA_KEY") or "").strip()
    if k:
        return k
    for cfg in (
        r"C:\Users\A\Desktop\build_video\config\ai_voice_api.json",
    ):
        try:
            d = json.load(open(cfg, encoding="utf-8"))
            k = (d.get("blueai_media_key") or d.get("blueai_key") or "").strip()
            if k:
                return k
        except OSError:
            continue
    sys.exit("未找到 BlueAI key：设 MULTIMODAL_API_KEY 或检查 build_video/config/ai_voice_api.json")


def post(path: str, payload: dict, key: str, retries: int = 4) -> dict:
    url = f"{BASE}{path}"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    for attempt in range(1, retries + 1):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
            if r.status_code == 429:
                wait = min(30 * attempt, 90)
                log(f"  [429] 等{wait}s 重试 {attempt}/{retries}")
                time.sleep(wait)
                continue
            if 500 <= r.status_code < 600:
                time.sleep(min(10 * attempt, 30))
                continue
            r.raise_for_status()
            return r.json() or {}
        except (requests.Timeout, requests.ConnectionError) as e:
            log(f"  [网络] {type(e).__name__}，15s 后重试 {attempt}/{retries}")
            time.sleep(15)
    raise RuntimeError(f"POST {path} 连续 {retries} 次失败")


def submit(prompt: str, model: str, w: int, h: int, key: str) -> str:
    model_id, endpoint = IMG_MODELS[model]
    data = post(endpoint, {
        "prompt": prompt,
        "model_id": model_id,
        "watermark": False,
        "size": f"{w}x{h}",
        "sequential_image_generation": "disabled",
    }, key)
    tid = data.get("task_id") or data.get("id")
    if not tid:
        raise RuntimeError(f"提交无 task_id：{str(data)[:200]}")
    return tid


def poll(tid: str, key: str, max_wait: float = 270, interval: float = 6):
    """轮询到成功，返回 (image_url, task_id)。"""
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        time.sleep(interval)
        try:
            d = post("/task_status", {"task_id": tid}, key, retries=2)
        except Exception as e:  # 单次轮询失败继续等
            log(f"  [轮询] {str(e)[:80]}")
            continue
        st = (d.get("status") or "").lower()
        if st in ("succeeded", "completed"):
            url = (d.get("video_url") or d.get("image_url")
                   or d.get("url") or d.get("image_urls"))
            if isinstance(url, list):
                url = url[0] if url else None
            if url:
                return url, tid
        if st in ("failed", "error"):
            raise RuntimeError(f"任务失败：{str(d.get('msg') or d)[:200]}")
    raise TimeoutError(f"生成超时({int(max_wait)}s)：{tid}")


def load_ledger(out_dir: Path) -> dict:
    p = out_dir / "_image_urls.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_ledger(out_dir: Path, ledger: dict):
    (out_dir / "_image_urls.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_one(ch: dict, cfg: dict, out_dir: Path, key: str,
                 force: bool, ledger: dict) -> bool:
    name = ch["name"]
    out = out_dir / f"{name}.png"
    if out.exists() and out.stat().st_size > 50_000 and not force:
        has = "有URL台账" if name in ledger else "无URL台账(可--force重出补URL)"
        log(f"[SKIP] {name} 已存在（{out.stat().st_size // 1024}KB，{has}）")
        return True
    if force and out.exists():
        out.unlink()

    kind = ch.get("kind", "sheet")
    if kind == "custom":
        prompt = ch["prompt"]
    else:
        desc = ch["desc"].rstrip("。.")
        prompt = f"{desc}。{SHEET_SUFFIX}"

    for attempt in range(1, 5):
        log(f"[GEN] {name} 第{attempt}轮提交……")
        try:
            tid = submit(prompt, cfg.get("model", "seedream-5.0-lite"),
                         int(cfg.get("width", 2560)), int(cfg.get("height", 1440)), key)
            url, _ = poll(tid, key)
            img = requests.get(url, timeout=120).content
            out.write_bytes(img)
            ledger[name] = {"task_id": tid, "url": url,
                            "file": out.name, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
            save_ledger(out_dir, ledger)  # 每张落盘一次，中断不丢URL
            log(f"[OK] {name}（{len(img)//1024}KB）→ {out.name}（URL已入账）")
            return True
        except Exception as e:
            msg = str(e)
            log(f"[RETRY] {name}：{msg[:120]}")
            if any(k in msg for k in ("敏感", "违规", "moderation", "copyright")):
                return False  # 审核拦截不重试
            time.sleep(15)
    log(f"[FAIL] {name}：4轮均失败")
    return False


def main():
    ap = argparse.ArgumentParser(description="角色四视图批量生成")
    ap.add_argument("--config", required=True, help="角色配置 JSON")
    ap.add_argument("--output", default="", help="输出目录（默认取配置 output 字段或 ./参考图）")
    ap.add_argument("--only", default="", help="只处理 name 含此串的角色")
    ap.add_argument("--force", action="store_true", help="已存在也删图重出")
    args = ap.parse_args()

    cfg = json.load(open(args.config, encoding="utf-8"))
    chars = cfg.get("characters", [])
    if args.only:
        chars = [c for c in chars if args.only in c["name"]]
    out_dir = Path(args.output or cfg.get("output") or "参考图")
    out_dir.mkdir(parents=True, exist_ok=True)

    key = resolve_key()
    ledger = load_ledger(out_dir)
    log(f"角色 {len(chars)} 个 → {out_dir}（URL台账 {len(ledger)} 条）")

    # ── 阶段1: 并行提交全部任务,收集 task_id ──
    tasks = []  # [(ch, task_id, prompt)] 或 None(跳过/审核拦截)
    for ch in chars:
        name = ch["name"]
        out = out_dir / f"{name}.png"
        if out.exists() and out.stat().st_size > 50_000 and not args.force:
            has = "有URL台账" if name in ledger else "无URL台账(可--force重出补URL)"
            log(f"[SKIP] {name} 已存在（{out.stat().st_size // 1024}KB，{has}）")
            tasks.append(None)
            continue
        if args.force and out.exists():
            out.unlink()

        kind = ch.get("kind", "sheet")
        if kind == "custom":
            prompt = ch["prompt"]
        else:
            desc = ch["desc"].rstrip("。.")
            prompt = f"{desc}。{SHEET_SUFFIX}"

        try:
            tid = submit(prompt, cfg.get("model", "seedream-5.0-lite"),
                         int(cfg.get("width", 3840)), int(cfg.get("height", 2160)), key)
            log(f"[SUBMIT] {name} → task_id={tid[:16]}...")
            tasks.append((ch, tid, prompt))
        except Exception as e:
            log(f"[SUBMIT_FAIL] {name}: {str(e)[:120]}")
            tasks.append(None)
        time.sleep(1)  # 提交间隔(防瞬时并发过高)

    # ── 阶段2: 统一轮询全部任务 ──
    ok = fail = skip = 0
    pending = {i: t for i, t in enumerate(tasks) if t is not None}
    max_wait = 300  # 最长等5分钟
    deadline = time.monotonic() + max_wait
    MAX_RETRY = 5  # 同一张图自动重试上限(含所有错误类型)
    retry_counts = {}  # {name: {"count": N, "errors": [...]}}
    final_fail = []  # [(name, reason, detail)]

    while pending and time.monotonic() < deadline:
        time.sleep(6)
        done_ids = []
        for i, (ch, tid, prompt) in pending.items():
            name = ch["name"]
            out = out_dir / f"{name}.png"
            try:
                d = post("/task_status", {"task_id": tid}, key, retries=2)
            except Exception:
                continue  # 单次轮询失败继续等
            st = (d.get("status") or "").lower()
            if st in ("succeeded", "completed"):
                url = (d.get("video_url") or d.get("image_url")
                       or d.get("url") or d.get("image_urls"))
                if isinstance(url, list):
                    url = url[0] if url else None
                if url:
                    try:
                        img = requests.get(url, timeout=120).content
                        out.write_bytes(img)
                        ledger[name] = {"task_id": tid, "url": url,
                                        "file": out.name, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
                        save_ledger(out_dir, ledger)
                        log(f"[OK] {name}（{len(img)//1024}KB）→ {out.name}")
                        ok += 1
                    except Exception as e:
                        log(f"[DL_FAIL] {name}: {str(e)[:80]}")
                        fail += 1
                else:
                    log(f"[NO_URL] {name}: 任务成功但无图片URL")
                    fail += 1
                done_ids.append(i)
            elif st in ("failed", "error"):
                msg = str(d.get("msg") or d)[:200]
                log(f"[FAIL] {name}: {msg}")
                retry_info = retry_counts.get(name, {"count": 0, "errors": []})
                retry_info["count"] += 1
                retry_info["errors"].append(msg)
                retry_counts[name] = retry_info

                if any(k in msg.lower() for k in ("敏感", "违规", "moderation", "security")):
                    log(f"  → 审核拦截,不自动重试(用户决定)")
                    final_fail.append((name, "审核拦截", msg))
                    done_ids.append(i)
                elif any(k in msg.lower() for k in ("copyright", "版权")):
                    log(f"  → 版权拦截,不自动重试(用户决定)")
                    final_fail.append((name, "版权拦截", msg))
                    done_ids.append(i)
                elif retry_info["count"] >= MAX_RETRY:
                    log(f"  → 已重试{MAX_RETRY}次,放弃")
                    final_fail.append((name, f"重试{MAX_RETRY}次仍失败", msg))
                    done_ids.append(i)
                else:
                    wait = 10 * retry_info["count"]
                    log(f"  → 第{retry_info['count']}次失败,{wait}s后重试提交")
                    time.sleep(wait)
                    try:
                        new_tid = submit(prompt, cfg.get("model", "seedream-5.0-lite"),
                                         int(cfg.get("width", 2560)), int(cfg.get("height", 1440)), key)
                        log(f"  → 重试提交成功 task_id={new_tid[:16]}...")
                        pending[i] = (ch, new_tid, prompt)
                    except Exception as e2:
                        log(f"  → 重试提交也失败: {str(e2)[:80]}")
                        final_fail.append((name, "重试提交失败", str(e2)[:120]))
                        done_ids.append(i)
        for i in done_ids:
            del pending[i]

    # 超时未完成的——也尝试重试
    timeout_items = list(pending.items())
    for i, (ch, tid, prompt) in timeout_items:
        name = ch["name"]
        retry_info = retry_counts.get(name, {"count": 0, "errors": []})
        retry_info["count"] += 1
        retry_counts[name] = retry_info
        if retry_info["count"] >= MAX_RETRY:
            log(f"[TIMEOUT] {name}: 超时且已重试{MAX_RETRY}次,放弃")
            final_fail.append((name, "超时+重试耗尽", f"task_id={tid[:16]}"))
        else:
            log(f"[TIMEOUT] {name}: 超时,重新提交第{retry_info['count']}次...")
            try:
                new_tid = submit(prompt, cfg.get("model", "seedream-5.0-lite"),
                                 int(cfg.get("width", 2560)), int(cfg.get("height", 1440)), key)
                pending[i] = (ch, new_tid, prompt)
            except Exception:
                final_fail.append((name, "超时+重试提交失败", f"task_id={tid[:16]}"))
                del pending[i]

    # 如果有超时重试的,再跑一轮 poll
    if pending:
        log(f"超时重试 {len(pending)} 张,再等 {max_wait}s...")
        deadline2 = time.monotonic() + max_wait
        while pending and time.monotonic() < deadline2:
            time.sleep(6)
            done_ids = []
            for i, (ch, tid, prompt) in pending.items():
                name = ch["name"]
                out = out_dir / f"{name}.png"
                try:
                    d = post("/task_status", {"task_id": tid}, key, retries=2)
                except Exception:
                    continue
                st = (d.get("status") or "").lower()
                if st in ("succeeded", "completed"):
                    url = (d.get("video_url") or d.get("image_url")
                           or d.get("url") or d.get("image_urls"))
                    if isinstance(url, list):
                        url = url[0] if url else None
                    if url:
                        try:
                            img = requests.get(url, timeout=120).content
                            out.write_bytes(img)
                            ledger[name] = {"task_id": tid, "url": url,
                                            "file": out.name, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
                            save_ledger(out_dir, ledger)
                            log(f"[OK-RETRY] {name}（{len(img)//1024}KB）")
                            ok += 1
                        except Exception as e:
                            final_fail.append((name, "下载失败", str(e)[:80]))
                    else:
                        final_fail.append((name, "成功但无URL", ""))
                    done_ids.append(i)
                elif st in ("failed", "error"):
                    final_fail.append((name, "重试仍失败", str(d.get("msg") or "")[:120]))
                    done_ids.append(i)
            for i in done_ids:
                del pending[i]
        for i, (ch, tid, prompt) in pending.items():
            final_fail.append((ch["name"], "最终超时", f"task_id={tid[:16]}"))

    fail = len(final_fail)

    skip = sum(1 for t in tasks if t is None)
    log(f"完成：成功{ok} 失败{fail} 跳过{skip}（并行提交+统一轮询+自动重试上限{MAX_RETRY}次）")
    if final_fail:
        log("─── 失败详情 ───")
        for name, reason, detail in final_fail:
            retries = retry_counts.get(name, {}).get("count", 0)
            log(f"  {name}: {reason}（重试{retries}次）{detail[:80]}")
        log("─── 审核/版权拦截需用户决定:修改描述/换角色/放弃 ───")
    # 写重试日志到 _session
    retry_log_path = out_dir / "_image_retry_log.json"
    retry_log_path.write_text(json.dumps({
        "final_fail": [{"name": n, "reason": r, "detail": d} for n, r, d in final_fail],
        "retry_counts": retry_counts,
        "ok": ok, "fail": fail, "skip": skip,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
