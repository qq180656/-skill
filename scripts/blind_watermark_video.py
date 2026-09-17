"""视频盲水印：按窗口抽帧嵌入 + 分段强制关键帧回编码（自包含版）。

H.264 的 P/B 帧靠运动预测编码，水印这种细微像素差异会被预测残差吃掉——
实测同一帧不强制关键帧，CRF23 编码一轮回来水印就解不出来了；强制成关键帧
（帧内预测，编码方式类似 JPEG）才扛得住。

所以每个窗口单独编码成一个小片段（起始帧天然是关键帧，用 force_key_frames
再钉住窗口内其余被选中的帧），最后用流拷贝拼接——这样可以避免单次编码
整段视频时 force_key_frames 表达式过长撞上 Windows 命令行长度上限（长视频
强制关键帧数量可能上千，直接拼进一条 ffmpeg 命令行会超限）。

码率分流（规范 §3.1.1）：
- 源码率 < 3Mbps（如 Seedance 720p 仅 ~1.5M）→ 固定 CBR 4M + bufsize 8M，
  且窗口收窄到 ≤50（提高水印帧密度）。低码率源按默认 CBR 编码会把水印
  d1=10 的细微差异直接压没。
- 源码率 ≥ 3Mbps → CBR = 源码率 × 1.2，bufsize 同值。

本文件为独立运行版：不依赖 build_video 的任何模块，ffmpeg/ffprobe 通过
环境变量 FFMPEG_PATH / FFPROBE_PATH 定位，找不到时回退 shutil.which。

命令行用法：
    python blind_watermark_video.py embed  <src.mp4> <dst.mp4> [--text TEXT]
    python blind_watermark_video.py verify <video.mp4> [--text TEXT] [--max-check N]
"""

import argparse
import glob
import json
import logging
import os
import random
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, Dict, List, Optional, Tuple

from blind_watermark_util import (
    DEFAULT_WATERMARK_TEXT,
    WatermarkCapacityError,
    embed_watermark,
    verify_watermark,
)

logger = logging.getLogger(__name__)

FRAME_NAME = "frame_%06d.png"
LOW_BR_THRESHOLD = 3_000_000  # 3Mbps，规范 §3.1.1 低码率分界线


# ---------------------------------------------------------------------------
# ffmpeg / ffprobe 定位与基础命令封装（内联，替代 utils.process / utils.ffmpeg）
# ---------------------------------------------------------------------------

def _find_tool(env_var: str, exe_name: str, sibling_of: Optional[str] = None) -> str:
    """按优先级定位可执行文件：环境变量 → 同目录 sibling → PATH。"""
    env_path = os.environ.get(env_var, "").strip()
    if env_path and os.path.isfile(env_path):
        return env_path
    if sibling_of:
        cand = os.path.join(os.path.dirname(sibling_of), exe_name)
        if os.path.isfile(cand):
            return cand
    found = shutil.which(exe_name)
    if found:
        return found
    raise RuntimeError(
        f"找不到 {exe_name}：请设置环境变量 {env_var} 指向其完整路径，"
        f"或将其加入 PATH"
    )


def _ffmpeg_exe() -> str:
    return _find_tool("FFMPEG_PATH", "ffmpeg.exe" if os.name == "nt" else "ffmpeg")


def _ffprobe_exe() -> str:
    return _find_tool(
        "FFPROBE_PATH",
        "ffprobe.exe" if os.name == "nt" else "ffprobe",
        sibling_of=_ffmpeg_exe(),
    )


def run_cmd(cmd: List[str]) -> subprocess.CompletedProcess:
    """运行 FFmpeg/FFprobe 命令，隐藏子进程窗口（Windows）。"""
    creationflags = 0
    startupinfo = None
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            startupinfo=startupinfo,
        )
    except Exception as e:  # noqa: BLE001 - 统一转成失败结果，由调用方判断
        class _FailedResult:
            returncode = -1
            stdout = ""
            stderr = str(e)
        return _FailedResult()


def ffprobe_info(path: str) -> Dict:
    """获取视频流/容器信息（JSON）。失败返回空 dict。"""
    cmd = [_ffprobe_exe(), "-v", "error", "-print_format", "json",
           "-show_streams", "-show_format", path]
    proc = run_cmd(cmd)
    if proc.returncode == 0:
        try:
            return json.loads(proc.stdout)
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug("ffprobe 输出解析失败: %s", e)
    return {}


def has_audio_stream(input_path: str) -> bool:
    """检查视频是否有音轨。"""
    cmd = [_ffprobe_exe(), "-v", "error", "-select_streams", "a",
           "-show_entries", "stream=index", "-of", "csv=p=0", input_path]
    proc = run_cmd(cmd)
    return proc.returncode == 0 and proc.stdout.strip() != ""


def concat_videos_stream_copy(video_list: List[str], output_path: str) -> Tuple[bool, str]:
    """用 concat demuxer 流拷贝拼接同源分段视频（reencode=False 等价实现）。"""
    if not video_list:
        return False, "没有视频文件"
    if len(video_list) == 1:
        try:
            shutil.copy(video_list[0], output_path)
            return True, os.path.basename(output_path)
        except OSError as e:
            return False, str(e)

    list_fd, list_path = tempfile.mkstemp(suffix=".txt", prefix="bw_concat_")
    try:
        with os.fdopen(list_fd, "w", encoding="utf-8") as f:
            for v in video_list:
                # concat demuxer 要求转义单引号
                f.write(f"file '{os.path.abspath(v).replace(chr(39), chr(39) * 3)}'\n")
        cmd = [_ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0",
               "-i", list_path, "-c", "copy", output_path]
        proc = run_cmd(cmd)
        if proc.returncode != 0 or not os.path.exists(output_path):
            return False, proc.stderr[-300:]
        return True, os.path.basename(output_path)
    finally:
        try:
            os.remove(list_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# 水印帧选择与抽帧/编码
# ---------------------------------------------------------------------------

def pick_watermark_frames(
    total_frames: int,
    window: int = 100,
    per_window: int = 1,
    seed: Optional[int] = None,
) -> List[int]:
    """按窗口选出要加水印的帧号（0-based）。

    每个窗口的首帧、尾帧必选；不够 per_window 时从窗口内其余帧随机补足。
    规范默认 window=100, per_window=1（每 100 帧至少 1 帧带水印）。
    """
    if total_frames <= 0:
        return []
    rng = random.Random(seed)
    picked = set()
    for start in range(0, total_frames, window):
        end = min(start + window, total_frames) - 1
        if start > end:
            continue
        boundary = {start, end}
        candidates = [i for i in range(start + 1, end) if i not in boundary]
        need = max(0, per_window - len(boundary))
        extra = rng.sample(candidates, min(need, len(candidates))) if candidates else []
        picked.update(boundary)
        picked.update(extra)
    return sorted(picked)


def _get_frame_rate_str(video_path: str) -> str:
    info = ffprobe_info(video_path)
    for s in info.get("streams", []):
        if s.get("codec_type") == "video":
            return s.get("r_frame_rate") or "30/1"
    return "30/1"


def _probe_video_bitrate(video_path: str) -> int:
    """探测视频流码率（bps），拿不到返回 0。"""
    info = ffprobe_info(video_path)
    for s in info.get("streams", []):
        if s.get("codec_type") == "video" and s.get("bit_rate"):
            try:
                return int(s["bit_rate"])
            except (TypeError, ValueError):
                return 0
    # 流上没有 bit_rate 时回退容器级
    fmt_br = info.get("format", {}).get("bit_rate")
    if fmt_br:
        try:
            return int(fmt_br)
        except (TypeError, ValueError):
            return 0
    return 0


def _extract_frames(video_path: str, frame_dir: str) -> int:
    os.makedirs(frame_dir, exist_ok=True)
    # image2 输出默认从 1 开始编号，显式 -start_number 0 才能跟本模块全程的
    # 0-based 帧下标（pick_watermark_frames / _encode_window_segment）对上
    cmd = [_ffmpeg_exe(), "-y", "-i", video_path, "-vsync", "0", "-start_number", "0",
           os.path.join(frame_dir, FRAME_NAME)]
    proc = run_cmd(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"视频抽帧失败: {proc.stderr[-300:]}")
    return len(glob.glob(os.path.join(frame_dir, "frame_*.png")))


def _encode_window_segment(
    frame_dir: str, start: int, end: int, frame_rate: str,
    local_keyframes: List[int], seg_path: str,
    target_bitrate: str = "8M",
    target_bufsize: str = "",
) -> None:
    """把 [start, end] 这段帧编码成一个独立小片段。
    CBR锁定码率；低码率源用固定4M+8M bufsize（规范§3.1.1）。"""
    if not target_bufsize:
        target_bufsize = target_bitrate
    pattern = os.path.join(frame_dir, FRAME_NAME)
    expr_terms = sorted(set(local_keyframes) | {0, end - start})
    expr = "+".join(f"eq(n,{i})" for i in expr_terms)
    cmd = [
        _ffmpeg_exe(), "-y",
        "-framerate", frame_rate,
        "-start_number", str(start),
        "-i", pattern,
        "-frames:v", str(end - start + 1),
        "-c:v", "libx264", "-preset", "slow",
        "-b:v", target_bitrate, "-maxrate", target_bitrate, "-bufsize", target_bufsize,
        "-pix_fmt", "yuv420p",
        "-force_key_frames", f"expr:{expr}",
        "-an", seg_path,
    ]
    proc = run_cmd(cmd)
    if proc.returncode != 0 or not os.path.exists(seg_path):
        raise RuntimeError(f"窗口片段编码失败 [{start}-{end}]: {proc.stderr[-300:]}")


def _resolve_bitrate_plan(src_br_raw: int, window: int) -> Tuple[int, str, str]:
    """按规范 §3.1.1 决定 (effective_window, target_bitrate, target_bufsize)。"""
    if 0 < src_br_raw < LOW_BR_THRESHOLD:
        # 低码率源：收窄窗口提高密度 + 固定 CBR 4M / bufsize 8M
        return min(window, 50), "4M", "8M"
    if src_br_raw >= LOW_BR_THRESHOLD:
        br = str(int(src_br_raw * 1.2))
        return window, br, br
    # 码率探测失败：保守用 8M CBR
    return window, "8M", "8M"


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

def embed_watermark_video(
    src_video: str,
    dst_video: str,
    text: str = DEFAULT_WATERMARK_TEXT,
    window: int = 100,
    per_window: int = 1,
    check_cancelled: Optional[Callable[[], None]] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> Dict:
    """给视频按窗口抽样的若干帧嵌入隐形水印，其余帧原样保留，重新编码输出。

    码率分流在抽帧后立即探测源码率决定（见 _resolve_bitrate_plan）。
    返回 {'total_frames', 'target_frames', 'embedded', 'skipped', 'failed'}。
    """
    work_dir = tempfile.mkdtemp(prefix="bw_video_")
    frame_dir = os.path.join(work_dir, "frames")
    seg_dir = os.path.join(work_dir, "segments")
    os.makedirs(seg_dir, exist_ok=True)

    def _tick(p: float, msg: str = "") -> None:
        if progress_callback:
            progress_callback(p, msg)

    try:
        _tick(0, "正在抽帧...")
        total_frames = _extract_frames(src_video, frame_dir)
        if total_frames == 0:
            raise RuntimeError("视频抽帧失败：没有得到任何帧")

        # 探测源码率并分流（必须在 pick_watermark_frames 之前，window 会被自适应收窄）
        frame_rate = _get_frame_rate_str(src_video)
        src_br_raw = _probe_video_bitrate(src_video)
        effective_window, target_bitrate, target_bufsize = _resolve_bitrate_plan(
            src_br_raw, window
        )
        logger.info(
            "码率分流: src_br=%d bps → window=%d, bitrate=%s, bufsize=%s",
            src_br_raw, effective_window, target_bitrate, target_bufsize,
        )

        target_indices = pick_watermark_frames(total_frames, effective_window, per_window)
        embedded, skipped, failed = 0, 0, 0
        embedded_set = set()
        for done, idx in enumerate(target_indices, start=1):
            if check_cancelled:
                check_cancelled()
            frame_path = os.path.join(frame_dir, FRAME_NAME % idx)
            try:
                embed_watermark(frame_path, frame_path, text=text)
                embedded += 1
                embedded_set.add(idx)
            except WatermarkCapacityError:
                skipped += 1
            except Exception as e:  # noqa: BLE001 - 单帧失败不中断整条视频
                failed += 1
                logger.error(
                    "视频抽帧嵌入失败 idx=%d: %s: %s", idx, type(e).__name__, e,
                    exc_info=True,
                )
            _tick(done / max(len(target_indices), 1) * 70,
                  f"嵌入水印帧 {done}/{len(target_indices)}")

        segment_paths = []
        window_starts = list(range(0, total_frames, effective_window))
        for w_idx, start in enumerate(window_starts):
            if check_cancelled:
                check_cancelled()
            end = min(start + effective_window, total_frames) - 1
            local_keys = sorted(i - start for i in embedded_set if start <= i <= end)
            seg_path = os.path.join(seg_dir, f"seg_{w_idx:05d}.mp4")
            _encode_window_segment(frame_dir, start, end, frame_rate, local_keys, seg_path,
                                   target_bitrate=target_bitrate, target_bufsize=target_bufsize)
            segment_paths.append(seg_path)
            _tick(70 + (w_idx + 1) / max(len(window_starts), 1) * 20,
                  f"编码片段 {w_idx + 1}/{len(window_starts)}")

        video_only = os.path.join(work_dir, "video_only.mp4")
        ok, msg = concat_videos_stream_copy(segment_paths, video_only)
        if not ok:
            raise RuntimeError(f"片段拼接失败: {msg}")

        _tick(95, "合并音轨...")
        os.makedirs(os.path.dirname(dst_video) or ".", exist_ok=True)
        if has_audio_stream(src_video):
            cmd = [
                _ffmpeg_exe(), "-y", "-i", video_only, "-i", src_video,
                "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                "-shortest", "-movflags", "+faststart", dst_video,
            ]
            proc = run_cmd(cmd)
            if proc.returncode != 0:
                raise RuntimeError(f"合并音轨失败: {proc.stderr[-300:]}")
        else:
            shutil.copy(video_only, dst_video)

        _tick(100, "完成")
        return {
            "total_frames": total_frames, "target_frames": len(target_indices),
            "embedded": embedded, "skipped": skipped, "failed": failed,
        }
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def verify_watermark_video(
    video_path: str,
    expected_text: str = DEFAULT_WATERMARK_TEXT,
    max_check: int = 300,
    check_cancelled: Optional[Callable[[], None]] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> Dict:
    """从视频里检查是否存在能提取出 expected_text 的水印帧。

    超过 max_check 帧的视频会等距抽样检查，而不是每一帧都查（避免长视频校验太慢）。
    返回 {'total_frames', 'checked', 'matched', 'matched_frames'}。
    """
    work_dir = tempfile.mkdtemp(prefix="bw_verify_")
    frame_dir = os.path.join(work_dir, "frames")
    try:
        total_frames = _extract_frames(video_path, frame_dir)
        if total_frames == 0:
            return {"total_frames": 0, "checked": 0, "matched": 0, "matched_frames": []}

        if total_frames <= max_check:
            check_indices = list(range(total_frames))
        else:
            step = total_frames / max_check
            check_indices = sorted({int(i * step) for i in range(max_check)})

        matched_frames = []
        for done, idx in enumerate(check_indices, start=1):
            if check_cancelled:
                check_cancelled()
            frame_path = os.path.join(frame_dir, FRAME_NAME % idx)
            if verify_watermark(frame_path, expected_text):
                matched_frames.append(idx)
            if progress_callback:
                progress_callback(done / len(check_indices) * 100,
                                  f"校验帧 {done}/{len(check_indices)}")

        return {
            "total_frames": total_frames, "checked": len(check_indices),
            "matched": len(matched_frames), "matched_frames": matched_frames,
        }
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def _main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="视频盲水印嵌入/校验（自包含版）")
    sub = parser.add_subparsers(dest="action", required=True)

    p_embed = sub.add_parser("embed", help="嵌入水印")
    p_embed.add_argument("src")
    p_embed.add_argument("dst")
    p_embed.add_argument("--text", default=DEFAULT_WATERMARK_TEXT)
    p_embed.add_argument("--window", type=int, default=100)
    p_embed.add_argument("--per-window", type=int, default=1)

    p_verify = sub.add_parser("verify", help="校验水印")
    p_verify.add_argument("video")
    p_verify.add_argument("--text", default=DEFAULT_WATERMARK_TEXT)
    p_verify.add_argument("--max-check", type=int, default=300)

    args = parser.parse_args(argv)

    if args.action == "embed":
        result = embed_watermark_video(
            args.src, args.dst, text=args.text,
            window=args.window, per_window=args.per_window,
            progress_callback=lambda p, m: print(f"\r[{p:5.1f}%] {m}", end="", flush=True),
        )
        print()
        print(f"嵌入完成: {result}")
        return 0 if result["embedded"] > 0 else 1

    result = verify_watermark_video(
        args.video, expected_text=args.text, max_check=args.max_check,
        progress_callback=lambda p, m: print(f"\r[{p:5.1f}%] {m}", end="", flush=True),
    )
    print()
    print(f"校验结果: matched={result['matched']}/{result['checked']} "
          f"(总帧数 {result['total_frames']})")
    return 0 if result["matched"] > 0 else 1


if __name__ == "__main__":
    sys.exit(_main())
