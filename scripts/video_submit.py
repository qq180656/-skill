#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seedance 视频提交通用客户端（参考图双方案：CDN URL 优先，本地 base64 兜底）。

定位：batch_generate.py 是"多任务分段并发引擎"，本脚本是它缺失的**参考图能力层**——
角色锁定路径每镜要传四视图/场景图，而网关 reference2video 的 image_urls 既吃公网 URL，
也吃 data:image/png;base64,... 本地图（已实测受理，锁脸有效）。

图来源解析（resolve_image，每个参考图独立决策）：
  1) 入参直接是 http(s)://  → 直接用（CDN URL）
  2) 入参是本地文件名/路径：
     a. 先查输出目录的 _image_urls.json 台账（gen_character_sheets.py 生图时落盘的CDN URL）
     b. 台账没有 → 读本地文件转 base64 data URI（兜底，零重新生图）
  3) 本地文件也不存在 → 抛错列出缺图

key 解析：env BLUEAI_GW_KEYS / MULTIMODAL_API_KEY / BLUEAI_MEDIA_KEY
        → build_video/config/ai_voice_api.json。

用法 A（库）：
    from video_submit import submit_segment, resolve_images
    r = submit_segment(prompt, duration="25", images=["character_A_mama.png","scene_A_ward.png"],
                       ref_dir=Path("参考图"), video_urls=None, output="a.mp4")
    # r = {"task_id","video_url","local_path","cost_cny","image_via":{"character_A_mama.png":"url|base64"}}

用法 B（CLI，单段）：
    python video_submit.py --prompt-file p1.txt --duration 25 \
        --images character_A_mama.png scene_A_ward.png --ref-dir ./参考图 --output a.mp4
    python video_submit.py --prompt-file p2.txt --duration 30 --video-urls https://....mp4 \
        --images c1.png --ref-dir ./参考图   # extend 段
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://bmc-model-openapi.bluemediagroup.cn/api/doubao"
MODEL = "doubao-seedance-2-5-260628"
TIMEOUT = (10, 120)


def log(msg: str):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", "replace").decode("ascii", "replace"), flush=True)


def resolve_key(explicit: str = "") -> str:
    if explicit:
        return explicit
    for env in ("BLUEAI_GW_KEYS", "MULTIMODAL_API_KEY", "BLUEAI_MEDIA_KEY"):
        v = (os.environ.get(env, "") or "").split(",")[0].strip()
        if v:
            return v
    cfg = Path(r"C:\Users\A\Desktop\build_video\config\ai_voice_api.json")
    if cfg.exists():
        d = json.loads(cfg.read_text(encoding="utf-8"))
        return (d.get("blueai_media_key") or d.get("blueai_key") or "").strip()
    raise RuntimeError("无可用 key")


def load_url_ledger(ref_dir: Path) -> dict:
    """gen_character_sheets.py 落盘的 {name: {url,...}} 台账。"""
    p = ref_dir / "_image_urls.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _to_data_uri(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".") or "png"
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    b = path.read_bytes()
    return f"data:image/{mime};base64,{base64.b64encode(b).decode()}"


def resolve_image(ref: str, ref_dir: Path, ledger: dict) -> tuple[str, str]:
    """单张参考图 → (可提交的 image_urls 元素, 来源 'url'|'base64')。"""
    if ref.startswith("http://") or ref.startswith("https://"):
        return ref, "url"
    # 文件名或路径
    p = Path(ref)
    if not p.is_absolute():
        p = ref_dir / ref
    name = p.name
    entry = ledger.get(name) or ledger.get(p.stem)
    if isinstance(entry, dict) and entry.get("url"):
        return entry["url"], "url"                      # 方案A：台账CDN URL优先
    if p.exists() and p.stat().st_size > 1000:
        return _to_data_uri(p), "base64"                # 方案B：本地base64兜底
    raise FileNotFoundError(f"参考图既无CDN URL也无本地文件：{ref}（查 {p}）")


def resolve_images(refs: list[str], ref_dir) -> tuple[list[str], dict]:
    ref_dir = Path(ref_dir)
    ledger = load_url_ledger(ref_dir)
    urls, via = [], {}
    for r in refs:
        u, how = resolve_image(r, ref_dir, ledger)
        urls.append(u); via[r] = how
    return urls, via


def _post(path: str, payload: dict, key: str, retries: int = 5) -> dict:
    last = None
    for a in range(retries):
        try:
            r = requests.post(f"{BASE}{path}", json=payload,
                              headers={"Authorization": f"Bearer {key}",
                                       "Content-Type": "application/json"},
                              timeout=TIMEOUT)
            if r.status_code == 429:
                time.sleep(min(30 * (a + 1), 90)); continue
            if 500 <= r.status_code < 600:
                time.sleep(10 * (a + 1)); continue
            r.raise_for_status()
            return r.json()
        except (requests.Timeout, requests.ConnectionError) as e:
            last = e; log(f"  [网络重试{a+1}] {type(e).__name__}"); time.sleep(15)
    raise RuntimeError(f"POST {path} 失败: {last}")


def submit_segment(prompt: str, duration="25", images=None, ref_dir=".",
                   video_urls=None, output: str | Path = "", key: str = "",
                   ratio: str = "9:16", model: str = MODEL,
                   poll_interval: int = 12, max_wait_s: float = 900,
                   download: bool = True, verbose: bool = True) -> dict:
    """提交一个视频生成段并轮询到终态。

    images: 参考图（文件名/本地路径/URL 混合列表，逐张 URL优先→base64兜底）
    video_urls: extend 时传前段视频 URL（此时 ratio 自动建议 adaptive）
    返回 dict(task_id/video_url/local_path/cost_cny/image_via/endpoint)。
    """
    key = key or resolve_key()
    image_via, image_urls = {}, []
    if images:
        image_urls, image_via = resolve_images(images, ref_dir)

    # 有前段视频=extend/reference2video；纯参考图多模态也走 reference2video；
    # 两者皆无才是纯 text2video。
    endpoint = "text2video" if (not image_urls and not video_urls) else "reference2video"
    use_ratio = "adaptive" if video_urls else ratio
    payload = {"model_id": model, "prompt": prompt, "duration": str(duration),
               "generate_audio": True, "return_last_frame": True, "ratio": use_ratio}
    if endpoint == "text2video":
        payload["resolution"] = "720p"
    else:
        payload["resolution"] = "720p"
        if image_urls:
            payload["image_urls"] = image_urls
        if video_urls:
            payload["video_urls"] = list(video_urls)

    if verbose:
        via_summary = {k: v for k, v in image_via.items()}
        n_url = sum(1 for v in image_via.values() if v == "url")
        n_b64 = sum(1 for v in image_via.values() if v == "base64")
        log(f"  图来源: URL {n_url} 张 / base64 {n_b64} 张  端点={endpoint}")

    d = _post(f"/{endpoint}", payload, key)
    tid = d.get("task_id") or d.get("id")
    if not tid:
        raise RuntimeError(f"提交无 task_id：{json.dumps(d, ensure_ascii=False)[:200]}")
    if verbose:
        log(f"  task_id={tid} 轮询中…")

    deadline = time.monotonic() + max_wait_s
    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        try:
            st = _post("/task_status", {"task_id": tid}, key, retries=2)
        except Exception:
            continue
        status = (st.get("status") or "").lower()
        if status in ("succeeded", "completed"):
            v = st.get("video_url") or st.get("url")
            if isinstance(v, list): v = v[0]
            local = ""
            if v and download and output:
                local = str(output)
                r = requests.get(v, timeout=180)
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                Path(output).write_bytes(r.content)
            return {"task_id": tid, "video_url": v, "local_path": local,
                    "cost_cny": float(st.get("cost_cny") or 0),
                    "image_via": image_via, "endpoint": endpoint,
                    "last_frame_url": st.get("last_frame_url")}
        if status in ("failed", "error"):
            raise RuntimeError(f"生成失败 {tid}: {str(st.get('msg'))[:200]}")
    raise TimeoutError(f"超时：{tid}")


def main():
    ap = argparse.ArgumentParser(description="Seedance 单段提交（参考图URL优先/base64兜底）")
    ap.add_argument("--prompt-file", required=True, type=Path)
    ap.add_argument("--duration", default="25")
    ap.add_argument("--images", nargs="*", default=[])
    ap.add_argument("--ref-dir", default=".")
    ap.add_argument("--video-urls", nargs="*", default=[], help="extend前段视频URL")
    ap.add_argument("--output", default="")
    ap.add_argument("--ratio", default="9:16")
    args = ap.parse_args()
    prompt = args.prompt_file.read_text(encoding="utf-8")
    r = submit_segment(prompt, duration=args.duration, images=args.images,
                       ref_dir=args.ref_dir, video_urls=args.video_urls or None,
                       output=args.output, ratio=args.ratio)
    print(json.dumps({k: v for k, v in r.items() if k != "image_via"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
