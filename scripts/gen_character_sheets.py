#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""角色四视图设定稿批量生成（Seedream 5.0-lite，16:9 横排：大头肩 + 正/侧/背全身）。

通用、自包含——任何项目写一份角色配置 JSON 即可批量出图，不必再写 py：

    python gen_character_sheets.py --config my_chars.json --output D:/项目/参考图

配置 JSON 格式（descriptions 即"由头到脚物理白描"，不要带"四视图"等画面指令）：
{
  "model": "seedream-5.0-lite",          // 可选，默认此值
  "width": 2560, "height": 1440,         // 可选，16:9 且总像素>=3686400
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
    "四视图角色设定稿，同一角色的人物正面头肩特写、正面、侧面、背面三个完整全身视图横向排列，"
    "人物特写只显示头部至肩部，不显示腰部、腿部和脚，"
    "三个全身视图从头顶完整展示到脚尖，自然站立、双足平踏地面、平视镜头，"
    "四视图角色特征与服装细节完全一致，色彩准确统一。"
    "纯白色背景，均匀平光照明，无明显阴影。"
    "真人写实风格，中国当代普通人质感，皮肤纹理与发丝细节清晰。"
    "人物面部与手部皮肤干净，无痣、无黑痣、无明显色素痣点。"
    "正面、侧面、背面三个全身视图严禁裁切下半身，人物特写禁止生成成全身视图，"
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
    ok = fail = 0
    for ch in chars:
        if generate_one(ch, cfg, out_dir, key, args.force, ledger):
            ok += 1
        else:
            fail += 1
        time.sleep(2)  # QPM 礼貌间隔
    log(f"完成：成功{ok} 失败{fail}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
