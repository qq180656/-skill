#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Seedance 批量视频生成引擎 (batch_generate.py)

通用引擎——与具体保险产品/业务无关，任何需要 Seedance text2video /
reference2video 的项目都能用。

用法 A (Python 导入):
    from batch_generate import BatchRunner
    runner = BatchRunner(output_dir="./成片", keys=[...], max_workers=10)
    result = runner.run(tasks)

用法 B (CLI):
    python batch_generate.py --tasks tasks.json --output ./成片 --workers 10
    python batch_generate.py --tasks tasks.json --dry-run   # 只打印不调API

task 格式:
    {
        "tag": "JCX-260914脚本01-V1日系",
        "segments": [
            {"type": "text2video",      "prompt": "...", "duration": "20"},
            {"type": "reference2video", "prompt": "...", "duration": "20"}
        ],
        "wm_id": "001"   # 可选
    }
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── 尝试从 skill_config 导入默认值，找不到就用内置 fallback ──
try:
    _cfg_dir = str(Path(__file__).resolve().parent)
    if _cfg_dir not in sys.path:
        sys.path.insert(0, _cfg_dir)
    from skill_config import (
        BASE_DOUBAO as _DEFAULT_BASE,
        GW_KEYS as _DEFAULT_KEYS,
        VIDEO_MODEL as _DEFAULT_MODEL,
        CSV_HEADERS as _DEFAULT_CSV_HEADERS,
    )
except ImportError:
    _DEFAULT_BASE = "https://bmc-model-openapi.bluemediagroup.cn/api/doubao"
    _DEFAULT_KEYS = []
    _DEFAULT_MODEL = "doubao-seedance-2-5-260628"
    _DEFAULT_CSV_HEADERS = [
        "序号", "tag", "段数", "时长", "状态", "费用(元)",
        "文件名", "日期", "task_ids",
    ]

# ── ffmpeg 默认路径 ──
_FFMPEG_CANDIDATES = [
    r"C:\Users\A\Desktop\build_video\tools\ffmpeg.exe",
    "ffmpeg",
]


def _find_ffmpeg():
    for p in _FFMPEG_CANDIDATES:
        if Path(p).is_file():
            return p
    return "ffmpeg"


import requests  # noqa: E402 (after path setup)


# ============================================================
# 数据类
# ============================================================

@dataclass
class SegResult:
    url: Optional[str] = None
    cost: float = 0.0
    task_id: str = ""
    status: str = ""
    local_file: Optional[Path] = None


@dataclass
class TaskResult:
    tag: str = ""
    status: str = "pending"
    cost: float = 0.0
    seg_results: list = field(default_factory=list)
    output_file: Optional[Path] = None


# ============================================================
# BatchRunner
# ============================================================

class BatchRunner:
    """Seedance 批量生成引擎。"""

    def __init__(
        self,
        output_dir: str,
        keys: Optional[list] = None,
        max_workers: int = 10,
        model: str = "",
        ffmpeg_path: str = "",
        base_url: str = "",
        dry_run: bool = False,
        stagger_sec: float = 2.0,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.keys = list(keys or _DEFAULT_KEYS)
        if not self.keys:
            raise ValueError("No API keys provided and skill_config has none")

        self.max_workers = max_workers
        self.model = model or _DEFAULT_MODEL
        self.ffmpeg = ffmpeg_path or _find_ffmpeg()
        self.base_url = base_url or _DEFAULT_BASE
        self.dry_run = dry_run
        self.stagger_sec = stagger_sec

        self._task_log = self.output_dir.parent / "_task_ids.jsonl"
        self._csv_log = self.output_dir.parent / "_视频日志.csv"
        self._seg_cache = self.output_dir / "_seg_urls.json"

        self._dead_keys: set = set()
        self._dead_keys_lock = threading.Lock()
        self._seg_url_cache: dict = {}
        self._cache_lock = threading.Lock()

        self._load_seg_cache()

    # ── seg URL 缓存（断点续跑核心） ──

    def _load_seg_cache(self):
        if self._seg_cache.exists():
            try:
                with open(self._seg_cache, "r", encoding="utf-8") as f:
                    self._seg_url_cache = json.load(f)
            except Exception:
                self._seg_url_cache = {}

    def _save_seg_cache(self):
        with self._cache_lock:
            with open(self._seg_cache, "w", encoding="utf-8") as f:
                json.dump(self._seg_url_cache, f, ensure_ascii=False, indent=2)

    def _cache_seg_url(self, tag: str, seg_idx: int, url: str):
        with self._cache_lock:
            self._seg_url_cache[f"{tag}__seg{seg_idx}"] = url
        self._save_seg_cache()

    def _get_cached_seg_url(self, tag: str, seg_idx: int) -> Optional[str]:
        return self._seg_url_cache.get(f"{tag}__seg{seg_idx}")

    # ── key 管理 ──

    def _pick_key(self, index: int) -> str:
        alive = [k for k in self.keys if k not in self._dead_keys]
        if not alive:
            raise RuntimeError("All keys exhausted (day/month budget exceeded)")
        return alive[index % len(alive)]

    def _kill_key(self, key: str, reason: str):
        with self._dead_keys_lock:
            if key not in self._dead_keys:
                self._dead_keys.add(key)
                _log(f"  [KEY DOWN] ...{key[-8:]} -> {reason}")

    # ── HTTP helpers ──

    @staticmethod
    def _headers(key: str) -> dict:
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def _submit(self, endpoint: str, payload: dict, key: str,
                stagger: float = 0) -> Optional[str]:
        if stagger > 0:
            time.sleep(stagger)

        url = f"{self.base_url}/{endpoint}"
        for attempt in range(10):
            try:
                r = requests.post(url, json=payload,
                                  headers=self._headers(key), timeout=60)
                d = r.json()
                tid = d.get("task_id")
                if tid:
                    return tid

                code = d.get("code")
                details = d.get("details", {})

                if r.status_code == 429 or code == 2402:
                    period = details.get("period", "")
                    remaining = float(details.get("remaining_cny", 0) or 0)
                    if period == "month" and remaining <= 0:
                        self._kill_key(key, f"month budget exceeded")
                        alive = [k for k in self.keys
                                 if k not in self._dead_keys]
                        if not alive:
                            _log("  [ALL KEYS DEAD]")
                            return None
                        key = alive[attempt % len(alive)]
                        _log(f"  month-dead, switch to ...{key[-8:]}")
                        continue
                    _log(f"  [429] {period} limit, remaining={remaining:.0f}, "
                         f"retry {attempt+1}/10 in 30s")
                    time.sleep(30)
                    alive = [k for k in self.keys
                             if k not in self._dead_keys]
                    if alive:
                        key = alive[(attempt + 1) % len(alive)]
                    continue

                if r.status_code == 400:
                    msg = d.get("msg", d.get("message", ""))
                    if "copyright" in msg.lower():
                        _log(f"  [COPYRIGHT] attempt {attempt+1}")
                        alive = [k for k in self.keys
                                 if k not in self._dead_keys]
                        if alive:
                            key = alive[(attempt + 1) % len(alive)]
                        time.sleep(5)
                        continue
                    _log(f"  [400] {msg}")
                    return None

                _log(f"  [?] HTTP {r.status_code}: "
                     f"{json.dumps(d, ensure_ascii=False)[:200]}")
                time.sleep(10)

            except Exception as e:
                _log(f"  [submit ERR] {e}")
                time.sleep(10)
        return None

    def _poll(self, task_id: str, key: str,
              interval: int = 15, timeout_iter: int = 400
              ) -> tuple:
        """Returns (url, cost, status). status = succeeded/failed/timeout."""
        for _ in range(timeout_iter):
            try:
                d = requests.post(
                    f"{self.base_url}/task_status",
                    json={"task_id": task_id},
                    headers=self._headers(key),
                    timeout=30,
                ).json()
                st = d.get("status")
                if st == "succeeded":
                    vurl = d.get("video_url", d.get("url"))
                    if isinstance(vurl, list):
                        vurl = vurl[0]
                    cost = float(d.get("cost_cny", 0) or 0)
                    return (vurl, cost, "succeeded")
                if st == "failed":
                    msg = d.get("msg", d.get("message", ""))
                    return (None, 0.0, f"failed: {msg}")
            except Exception:
                pass
            time.sleep(interval)
        return (None, 0.0, "timeout")

    def _download(self, url: str, out_path: Path):
        part = str(out_path) + ".part"
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(part, "wb") as f:
                for chunk in r.iter_content(32768):
                    if chunk:
                        f.write(chunk)
        os.replace(part, str(out_path))

    def _concat(self, files: list, out_path: Path) -> bool:
        if len(files) == 1:
            os.replace(str(files[0]), str(out_path))
            return True

        lst_file = str(out_path) + ".lst"
        with open(lst_file, "w", encoding="utf-8") as f:
            for p in files:
                abs_p = str(Path(p).resolve()).replace("\\", "/")
                f.write(f"file '{abs_p}'\n")

        result = subprocess.run(
            [self.ffmpeg, "-y",
             "-f", "concat", "-safe", "0",
             "-protocol_whitelist", "file,pipe",
             "-i", lst_file,
             "-c:v", "libx264", "-crf", "20", "-preset", "fast",
             "-c:a", "aac",
             str(out_path)],
            capture_output=True, timeout=300,
        )

        try:
            os.remove(lst_file)
        except OSError:
            pass

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")[-500:]
            _log(f"  [FFMPEG ERR] rc={result.returncode}: {stderr}")
            return False

        for p in files:
            try:
                os.remove(str(p))
            except OSError:
                pass
        return True

    # ── 日志 ──

    def _log_task(self, tag, task_id, status, cost=0, prompt_preview=""):
        entry = {
            "tag": tag, "task_id": task_id, "model": self.model,
            "prompt": prompt_preview[:200], "status": status,
            "cost_cny": cost,
            "timestamp": datetime.now().isoformat(),
        }
        with open(self._task_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _log_csv(self, row: list):
        exists = self._csv_log.exists()
        with open(self._csv_log, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(_DEFAULT_CSV_HEADERS)
            w.writerow(row)

    # ── 单条生成 ──

    def _generate_one(self, task: dict, task_idx: int) -> TaskResult:
        tag = task["tag"]
        segments = task["segments"]
        out_file = self.output_dir / f"{tag}.mp4"
        res = TaskResult(tag=tag)

        if out_file.exists() and out_file.stat().st_size > 100_000:
            _log(f"[SKIP] {tag} ({out_file.stat().st_size // 1024}KB)")
            res.status = "skipped"
            res.output_file = out_file
            return res

        if self.dry_run:
            for i, seg in enumerate(segments):
                _log(f"[DRY] {tag} seg{i}: {seg['type']} "
                     f"dur={seg.get('duration','?')}s "
                     f"prompt={seg['prompt'][:80]}...")
            res.status = "dry_run"
            return res

        key = self._pick_key(task_idx)
        stagger = (task_idx % self.max_workers) * self.stagger_sec

        _log(f"\n[START] {tag} (key ...{key[-8:]}, "
             f"{len(segments)} segs)")

        seg_files = []
        prev_url = None

        for i, seg in enumerate(segments):
            seg_type = seg["type"]
            prompt = seg["prompt"]
            duration = seg.get("duration", "25")
            seg_file = self.output_dir / f"_{tag}_p{i+1}.mp4"

            cached_url = self._get_cached_seg_url(tag, i)
            if cached_url and seg_file.exists() and \
               seg_file.stat().st_size > 100_000:
                _log(f"  seg{i+1} cached, skip")
                prev_url = cached_url
                seg_files.append(seg_file)
                continue

            payload = {
                "model_id": self.model,
                "prompt": prompt,
                "duration": str(duration),
                "generate_audio": True,
            }

            if seg_type == "text2video":
                payload["resolution"] = "720p"
                payload["ratio"] = "9:16"
            elif seg_type == "reference2video":
                if prev_url:
                    payload["video_urls"] = [prev_url]
                payload["ratio"] = "adaptive"

            _log(f"  seg{i+1} ({seg_type}, {duration}s) submitting...")
            tid = self._submit(seg_type, payload, key,
                               stagger=stagger if i == 0 else 0)
            if not tid:
                _log(f"  [FAIL] seg{i+1} submit failed")
                self._log_task(tag, "", "submit_failed")
                res.status = "failed"
                return res

            self._log_task(tag, tid, "submitted", prompt_preview=prompt)
            _log(f"  seg{i+1} task_id={tid}, polling...")

            url, cost, st = self._poll(tid, key)
            sr = SegResult(url=url, cost=cost, task_id=tid, status=st)
            res.seg_results.append(sr)
            res.cost += cost

            if not url:
                _log(f"  [FAIL] seg{i+1}: {st}")
                self._log_task(tag, tid, f"failed:{st}")
                res.status = "failed"
                return res

            self._download(url, seg_file)
            sr.local_file = seg_file
            seg_files.append(seg_file)
            prev_url = url
            self._cache_seg_url(tag, i, url)
            _log(f"  seg{i+1} done ({cost:.2f} yuan)")

        _log(f"  concat {len(seg_files)} files...")
        ok = self._concat(seg_files, out_file)
        if not ok:
            _log(f"  [FAIL] concat failed, source files kept")
            res.status = "concat_failed"
            return res

        res.status = "done"
        res.output_file = out_file
        _log(f"  OK! {tag} total={res.cost:.2f} yuan")

        tids = [sr.task_id for sr in res.seg_results]
        self._log_task(tag, "+".join(tids), "done", cost=res.cost)
        self._log_csv([
            task_idx + 1, tag, len(segments), "",
            "done", f"{res.cost:.2f}",
            out_file.name, datetime.now().strftime("%Y-%m-%d"),
            "+".join(tids),
        ])

        return res

    # ── 主入口 ──

    def run(self, tasks: list) -> dict:
        _log("=" * 60)
        _log(f"Seedance Batch: {len(tasks)} tasks, "
             f"{self.max_workers} workers, "
             f"{len(self.keys)} keys"
             f"{' [DRY RUN]' if self.dry_run else ''}")
        _log(f"Output: {self.output_dir}")
        _log("=" * 60)

        results = {"done": 0, "failed": 0, "skipped": 0,
                   "dry_run": 0, "total_cost": 0.0}

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self._generate_one, task, idx): task["tag"]
                for idx, task in enumerate(tasks)
            }
            finished = 0
            for future in as_completed(futures):
                name = futures[future]
                finished += 1
                try:
                    tr = future.result()
                    results[tr.status] = results.get(tr.status, 0) + 1
                    results["total_cost"] += tr.cost
                    _log(f"\n[{finished}/{len(tasks)}] {tr.tag}: "
                         f"{tr.status}")
                except Exception as e:
                    _log(f"\n[{finished}/{len(tasks)}] {name}: ERROR {e}")
                    results["failed"] += 1

        _log("\n" + "=" * 60)
        _log(f"Done! done={results['done']} "
             f"skipped={results['skipped']} "
             f"failed={results['failed']} "
             f"cost={results['total_cost']:.2f} yuan")
        _log("=" * 60)
        return results


# ============================================================
# 日志打印（ASCII 安全，不用 ¥ 等 GBK 不兼容字符）
# ============================================================

def _log(msg: str):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", errors="replace").decode("ascii", errors="replace"),
              flush=True)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Seedance batch video generator")
    parser.add_argument("--tasks", required=True,
                        help="JSON file with task list")
    parser.add_argument("--output", default="./output",
                        help="Output directory for videos")
    parser.add_argument("--workers", type=int, default=10,
                        help="Max concurrent workers (default 10)")
    parser.add_argument("--model", default="",
                        help="Model ID (default from skill_config)")
    parser.add_argument("--keys", nargs="*", default=None,
                        help="API keys (default from skill_config)")
    parser.add_argument("--ffmpeg", default="",
                        help="Path to ffmpeg binary")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompts without calling API")
    parser.add_argument("--stagger", type=float, default=2.0,
                        help="Seconds between first submits (default 2)")
    args = parser.parse_args()

    with open(args.tasks, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    runner = BatchRunner(
        output_dir=args.output,
        keys=args.keys,
        max_workers=args.workers,
        model=args.model,
        ffmpeg_path=args.ffmpeg,
        dry_run=args.dry_run,
        stagger_sec=args.stagger,
    )
    result = runner.run(tasks)
    sys.exit(0 if result["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
