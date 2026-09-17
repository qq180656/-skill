#!/usr/bin/env python3
"""台词/旁白耗时计算工具。

用法：
  python3 count_chars.py "台词或旁白1" "台词或旁白2" ...
  python3 count_chars.py --mode slow "诗句1" "诗句2" ...

输出每条文本的中文字数、数字数、英文词数和耗时区间。
默认中文按 3.5~2.8 字/秒、英文按 2.5~2.2 词/秒，中英混排分别计时后相加。
--mode slow 为吟诵慢速口径（2 字/秒），
目前仅诗词体裁的诗句原文使用，自创文本/讲解词仍用默认口径。
"""

import sys
import unicodedata
from typing import NamedTuple


CHAR_FAST_RATE = 3.5
CHAR_SLOW_RATE = 2.8
ENGLISH_FAST_RATE = 2.5
ENGLISH_SLOW_RATE = 2.2
RECITAL_CHAR_RATE = 2.0
RECITAL_ENGLISH_RATE = 1.5


class SpeechUnits(NamedTuple):
    chars: int
    digits: int
    english_words: int


def count_speech_units(text):
    """分开统计逐字发音单位与英文词。

    CJK 等 Lo 字符逐字计数，数字默认逐位计数，连续拉丁字母按一个词计数。
    缩写的实际读法有歧义，如需逐字母朗读，输入中应用空格显式拆开。
    """
    if not text:
        return SpeechUnits(0, 0, 0)

    chars = 0
    digits = 0
    english_words = 0
    in_word = False

    def flush_word():
        nonlocal english_words, in_word
        if in_word:
            english_words += 1
            in_word = False

    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("Lo"):
            flush_word()
            chars += 1
        elif cat == "Nd":
            flush_word()
            digits += 1
        elif cat.startswith("L"):
            in_word = True
        elif cat.startswith("M") and in_word:
            # 保留分解形态的重音组合符，不切断当前词。
            continue
        elif ch in ("'", "’") and in_word:
            # don't / we're 等缩写仍是一个词。
            continue
        else:
            flush_word()
    flush_word()
    return SpeechUnits(chars, digits, english_words)


def estimate_speech(text, mode="normal"):
    """返回 (SpeechUnits, 耗时下限秒, 耗时上限秒)。"""
    if mode not in ("normal", "slow"):
        raise ValueError("mode 取值只能是 normal 或 slow")

    units = count_speech_units(text)
    char_units = units.chars + units.digits
    if mode == "slow":
        seconds = char_units / RECITAL_CHAR_RATE + units.english_words / RECITAL_ENGLISH_RATE
        rounded = round(seconds, 1)
        return units, rounded, rounded

    lower = char_units / CHAR_FAST_RATE + units.english_words / ENGLISH_FAST_RATE
    upper = char_units / CHAR_SLOW_RATE + units.english_words / ENGLISH_SLOW_RATE
    return units, round(lower, 1), round(upper, 1)


def format_speech_units(units):
    """将分语种计数格式化为人可读标签。"""
    parts = []
    if units.chars:
        parts.append(f"{units.chars}字")
    if units.digits:
        parts.append(f"{units.digits}数字")
    if units.english_words:
        parts.append(f"{units.english_words}英文词")
    return "+".join(parts) if parts else "0字"


def count_effective_chars(text):
    """返回发音单位总数，耗时计算使用 estimate_speech。"""
    units = count_speech_units(text)
    return units.chars + units.digits + units.english_words


if __name__ == "__main__":
    args = sys.argv[1:]
    mode = "normal"
    if "--mode" in args:
        i = args.index("--mode")
        if i + 1 >= len(args) or args[i + 1] not in ("normal", "slow"):
            print("错误：--mode 取值只能是 normal 或 slow")
            sys.exit(1)
        mode = args[i + 1]
        del args[i:i + 2]
    texts = args
    if not texts:
        print("用法：python3 count_chars.py [--mode slow] \"台词1\" \"台词2\" ...")
        sys.exit(1)

    slow = mode == "slow"
    total_units = SpeechUnits(0, 0, 0)
    total_fast = 0.0
    total_slow = 0.0
    for text in texts:
        units, fast, slow_t = estimate_speech(text, mode=mode)
        total_units = SpeechUnits(
            total_units.chars + units.chars,
            total_units.digits + units.digits,
            total_units.english_words + units.english_words,
        )
        total_fast += fast
        total_slow += slow_t
        # 截取前20字作为标识，超长加省略号
        label = text if len(text) <= 20 else text[:20] + "…"
        unit_label = format_speech_units(units)
        if slow:
            print(f"「{label}」{unit_label}，吟诵耗时[{fast}s]")
        else:
            print(f"「{label}」{unit_label}，耗时[{fast}s~{slow_t}s]")

    if len(texts) > 1:
        total_label = format_speech_units(total_units)
        if slow:
            print(f"【合计】{len(texts)}段共{total_label}，吟诵耗时累加[{round(total_fast, 1)}s]")
        else:
            print(
                f"【合计】{len(texts)}段共{total_label}，"
                f"耗时累加[{round(total_fast, 1)}s~{round(total_slow, 1)}s]"
            )
