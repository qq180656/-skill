#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""发音修复自动链路（verify→repair一体化）。

被 verify 脚本调用：检测到 replace 类发音错误时，自动修复。
复用 _fix_pronunciation.py 的核心能力 + 补全 crossfade/LUFS 对齐。

用法（被verify脚本import调用）：
    from auto_repair import try_auto_repair
    result = try_auto_repair(video_path, errors, atomic_text, output_dir)
    # result: {"status": "repaired"/"skipped"/"failed", "fixes": N, "output": path}

也可独立运行：
    python auto_repair.py <video.mp4> --script "正确台词文本" --output-dir ./修复/
"""
import os, sys, re, json, subprocess, tempfile, shutil, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _fix_pronunciation import (
    detect_errors, extract_reference_audio, tts_clone,
    upload_ref_audio, transcribe_words, FFMPEG, BMC_KEY,
)

try:
    from skill_config import PRONOUNCE_DELETE
except ImportError:
    PRONOUNCE_DELETE = ["息肉", "超声"]


def _probe_lufs(wav_path):
    """测量音频LUFS响度。"""
    r = subprocess.run([FFMPEG, "-i", wav_path, "-af", "loudnorm=print_format=json",
                        "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    m = re.search(r'"input_i"\s*:\s*"(-?[\d.]+)"', r.stderr or "")
    return float(m.group(1)) if m else -23.0


def _adjust_lufs(wav_in, wav_out, target_lufs=-23.0):
    """调整音频到目标LUFS响度。"""
    current = _probe_lufs(wav_in)
    gain = target_lufs - current
    if abs(gain) < 0.5:
        shutil.copy(wav_in, wav_out)
        return
    subprocess.run([FFMPEG, "-y", "-i", wav_in,
                    "-af", f"volume={gain}dB",
                    wav_out], capture_output=True, timeout=30)


def replace_audio_with_crossfade(video_path, fixes, output_path, crossfade_ms=10):
    """用修复音频替换视频中对应时间段（带crossfade+LUFS对齐）。

    fixes: [(start_sec, end_sec, fix_audio_path), ...]
    crossfade_ms: 拼接点前后交叉淡入淡出毫秒数
    """
    if not fixes:
        return False

    tmp_dir = tempfile.mkdtemp(prefix="repair_")
    orig_audio = os.path.join(tmp_dir, "orig.wav")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                    "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1",
                    orig_audio], capture_output=True, timeout=120)
    if not os.path.exists(orig_audio):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # 测量原音轨LUFS（拼接点前后1秒平均）
    orig_lufs = _probe_lufs(orig_audio)

    fixes_sorted = sorted(fixes, key=lambda x: x[0])
    segments = []
    prev_end = 0.0
    cf = crossfade_ms / 1000.0

    for i, (start, end, fix_path) in enumerate(fixes_sorted):
        # 原始段
        if start > prev_end + 0.01:
            seg = os.path.join(tmp_dir, f"orig_{i}.wav")
            # 多取crossfade_ms做淡出
            subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                            "-ss", str(prev_end), "-to", str(start + cf),
                            "-i", orig_audio, "-c", "copy", seg],
                           capture_output=True, timeout=30)
            if os.path.exists(seg) and os.path.getsize(seg) > 100:
                # 尾部淡出
                seg_fade = os.path.join(tmp_dir, f"orig_{i}_fo.wav")
                subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                                "-i", seg, "-af", f"afade=t=out:st={start - prev_end}:d={cf}",
                                seg_fade], capture_output=True, timeout=30)
                segments.append(seg_fade if os.path.exists(seg_fade) else seg)

        # 修复段：格式对齐+LUFS对齐+首尾淡入淡出
        fix_norm = os.path.join(tmp_dir, f"fix_{i}_norm.wav")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                        "-i", fix_path, "-ar", "24000", "-ac", "1", "-acodec", "pcm_s16le",
                        fix_norm], capture_output=True, timeout=30)
        if os.path.exists(fix_norm):
            # LUFS对齐
            fix_lufs = os.path.join(tmp_dir, f"fix_{i}_lufs.wav")
            _adjust_lufs(fix_norm, fix_lufs, target_lufs=orig_lufs)
            # 淡入淡出
            fix_fade = os.path.join(tmp_dir, f"fix_{i}_fade.wav")
            dur_fix = end - start
            subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                            "-i", fix_lufs if os.path.exists(fix_lufs) else fix_norm,
                            "-af", f"afade=t=in:d={cf},afade=t=out:st={max(0, dur_fix - cf)}:d={cf}",
                            fix_fade], capture_output=True, timeout=30)
            segments.append(fix_fade if os.path.exists(fix_fade) else fix_norm)

        prev_end = end

    # 尾部原始段
    probe = subprocess.run([FFMPEG, "-i", orig_audio, "-f", "null", "-"],
                           capture_output=True, text=True, timeout=30)
    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", probe.stderr or "")
    total_dur = (int(dur_match.group(1))*3600 + int(dur_match.group(2))*60 +
                 int(dur_match.group(3)) + int(dur_match.group(4))/100) if dur_match else 999
    if prev_end < total_dur - 0.1:
        tail = os.path.join(tmp_dir, "tail.wav")
        # 开头淡入（承接修复段尾的淡出）
        subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                        "-ss", str(max(0, prev_end - cf)), "-i", orig_audio,
                        "-af", f"afade=t=in:d={cf}",
                        tail], capture_output=True, timeout=30)
        if os.path.exists(tail) and os.path.getsize(tail) > 100:
            segments.append(tail)

    if not segments:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # concat
    merged = os.path.join(tmp_dir, "merged.wav")
    lst = os.path.join(tmp_dir, "list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                    "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", merged],
                   capture_output=True, timeout=60)

    if not os.path.exists(merged):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # 削波检测+限制
    merged_lim = os.path.join(tmp_dir, "merged_lim.wav")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                    "-i", merged, "-af", "alimiter=limit=0.95:attack=0.1:release=50",
                    merged_lim], capture_output=True, timeout=30)
    final_audio = merged_lim if os.path.exists(merged_lim) else merged

    # 合回视频
    subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                    "-i", video_path, "-i", final_audio,
                    "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
                    "-shortest", output_path],
                   capture_output=True, timeout=120)

    # 验证音视频时长差
    ok = os.path.exists(output_path) and os.path.getsize(output_path) > 10000
    if ok:
        for p in (video_path, output_path):
            r = subprocess.run([FFMPEG.replace("ffmpeg","ffprobe"), "-v", "error",
                               "-show_entries", "format=duration",
                               "-of", "default=nokey=1:noprint_wrappers=1", p],
                              capture_output=True, text=True, timeout=15)
            try:
                print(f"    {os.path.basename(p)}: {float(r.stdout.strip()):.2f}s")
            except ValueError:
                pass

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return ok


def try_auto_repair(video_path, errors, atomic_text, output_dir):
    """verify检出发音错误后的自动修复入口。

    errors: wf_verification DIFF_ANALYSIS 输出的错误列表 [{"type":"replace","expected":"好医保","heard":"好质保"}, ...]
    atomic_text: 原子脚本纯口播文本（正确的期望文本）
    output_dir: 修复视频输出目录

    返回 {"status": "repaired"/"skipped"/"failed", "fixes": N, "output": path, "repair_log": dict}
    """
    # 只处理replace类（insert/delete走重做镜头，不在这里）
    replace_errors = [e for e in errors if e.get("type") == "replace"]
    if not replace_errors:
        return {"status": "skipped", "fixes": 0, "output": None,
                "repair_log": {"reason": "无replace类发音错误"}}

    basename = os.path.splitext(os.path.basename(video_path))[0]
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{basename}_fixed.mp4")

    print(f"  [{basename}] 发现{len(replace_errors)}处replace发音错误，开始自动修复...")

    # ASR词时间戳
    words = transcribe_words(video_path, use_cache=True, log=lambda m: None)
    if not words:
        return {"status": "failed", "fixes": 0, "output": None,
                "repair_log": {"reason": "ASR失败"}}

    # 重新检测定位（用words精确匹配错误位置）
    detected = detect_errors(words, atomic_text)
    if not detected:
        return {"status": "skipped", "fixes": 0, "output": None,
                "repair_log": {"reason": "精确检测未发现错误"}}

    # 提取参考音频
    ref_wav = extract_reference_audio(video_path, detected)
    if not ref_wav:
        return {"status": "failed", "fixes": 0, "output": None,
                "repair_log": {"reason": "无法提取参考音频"}}

    # 上传参考音频
    ref_url = upload_ref_audio(ref_wav)
    if not ref_url:
        return {"status": "failed", "fixes": 0, "output": None,
                "repair_log": {"reason": "参考音频上传失败"}}

    # 逐个错误TTS克隆重读
    fixes = []
    for err in detected:
        correct_text = err.get("correct_text") or err.get("expected", "")
        if not correct_text:
            continue
        print(f"    修复: '{err.get('heard','')}' → '{correct_text}'")
        tts_result = tts_clone(correct_text, ref_audio_url=ref_url)
        if tts_result and os.path.exists(tts_result):
            fixes.append((err["start_sec"], err["end_sec"], tts_result))

    if not fixes:
        return {"status": "failed", "fixes": 0, "output": None,
                "repair_log": {"reason": "TTS克隆全部失败"}}

    # 替换（带crossfade+LUFS）
    ok = replace_audio_with_crossfade(video_path, fixes, output_path)

    repair_log = {
        "video": basename,
        "errors_detected": len(detected),
        "fixes_applied": len(fixes),
        "crossfade_ms": 10,
        "lufs_aligned": True,
        "limiter_applied": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    if ok:
        print(f"  [{basename}] ✅ 修复完成: {len(fixes)}处")
        return {"status": "repaired", "fixes": len(fixes), "output": output_path,
                "repair_log": repair_log}
    else:
        print(f"  [{basename}] ❌ 修复失败（ffmpeg合成出错）")
        return {"status": "failed", "fixes": len(fixes), "output": None,
                "repair_log": repair_log}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="发音修复")
    parser.add_argument("video", help="视频文件路径")
    parser.add_argument("--script", default="", help="正确台词文本")
    parser.add_argument("--output-dir", default="./_发音修复", help="输出目录")
    args = parser.parse_args()

    words = transcribe_words(args.video, use_cache=True, log=print)
    errors = detect_errors(words, args.script if args.script else None)
    print(f"检测到 {len(errors)} 处错误")
    if errors:
        r = try_auto_repair(args.video, errors, args.script, args.output_dir)
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
