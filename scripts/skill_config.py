#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AI视频生产规范 — 参数中心（唯一权威源）。
所有批量脚本 `from skill_config import *` 获取参数，不再各自硬编码。
skill文档更新时同步改此文件——参数只改一处。

对应skill文档：
- config_matrix.md §语速/Key/并发/前贴/模型
- 暗水印编号追踪规范.md §编号/参数
- wf_verification.md §LLM模型/降级策略
- pronunciation_rules.md §删除级/空格级
"""

# ============================================================
# 一、视频生成
# ============================================================

# Seedance 模型
VIDEO_MODEL = "doubao-seedance-2-5-260628"
VIDEO_RESOLUTION = "720p"
VIDEO_RATIO = "9:16"

# 语速（字/秒）——按产品区分
SPEED = {
    "好医保·中老年长期医疗": 7,
    "好医保·门诊险": 7,
    "好医保·少儿长期医疗": 7,
    "好医保·长期医疗(旗舰版)": 7,
    "长钱保·五年领年金": 6,
    "长钱保·分红增额寿": 6,
    "default": 7,
}

# 前贴参数
PREROLL_DURATION_MIN = 15
PREROLL_DURATION_MAX = 25
PREROLL_PRODUCT_NAME_POSITION = 0.75  # 产品名出现在总时长的75-85%处

# 成片extend
EXTEND_THRESHOLD_SEC = 30  # 预估时长>此值走extend
SEGMENT_DURATION_MIN = 20
SEGMENT_DURATION_MAX = 30
SEGMENT_DURATION_BUFFER = 2  # 台词秒数+缓冲

# 并发
VIDEO_CONCURRENCY = 4

# ============================================================
# 二、Key管理
# ============================================================

# 视频生成Key池（Seedance）+ LLM断句Key池（relay）
# 从环境变量读，不硬编码（防上传泄露）。本机设一次（逗号分隔多把 key）：
#   setx BLUEAI_GW_KEYS  "blueai-xxx,blueai-yyy,blueai-zzz"
#   setx BLUEAI_LLM_KEYS "blueai-aaa,blueai-bbb,blueai-ccc"
# 变量名/格式见仓库根 .env.example；设完重开终端生效。
import os as _os
GW_KEYS = [k.strip() for k in _os.environ.get("BLUEAI_GW_KEYS", "").split(",") if k.strip()]
LLM_KEYS = [k.strip() for k in _os.environ.get("BLUEAI_LLM_KEYS", "").split(",") if k.strip()]
LLM_URL = "https://bmc-llm-relay.bluemediagroup.cn/v1/chat/completions"
LLM_MODEL = "Doubao-Seed-2.0-mini"  # 硬约定，禁止用Evolving

# BMC网关
BASE_DOUBAO = "https://bmc-model-openapi.bluemediagroup.cn/api/doubao"

# ============================================================
# 三、盲水印
# ============================================================

WATERMARK_D1 = 10
WATERMARK_D2 = 5
WATERMARK_WINDOW_HIGH_BR = 100   # 源码率≥3Mbps
WATERMARK_WINDOW_LOW_BR = 50     # 源码率<3Mbps
WATERMARK_PER_WINDOW = 1
WATERMARK_LOW_BR_THRESHOLD = 3_000_000  # 3Mbps
WATERMARK_LOW_BR_BITRATE = "4M"
WATERMARK_LOW_BR_BUFSIZE = "8M"

# 编号缩写表
PROJECT_ABBR = {
    "好医保中老年": "HYB",
    "好医保门诊险": "MZX",
    "好医保少儿": "HYB",
    "好医保旗舰版": "HYB",
    "长钱保": "CQB",
    "健康福": "JKF",
    "家财险": "JCX",
}

# 产品ID（编号中缩写+ID连写防撞号）
PRODUCT_ID = {
    "好医保·中老年长期医疗(2026版)": "52973",
    "好医保·中老年长期医疗(体验版)": "52978",
    "好医保·少儿长期医疗": "45750",
    "好医保·少儿长期医疗(2026版)": "53408",
    "好医保·长期医疗(旗舰版2026)": "52975",
    "好医保·门诊险": "36866",
    "长钱保·五年领年金": "47711",
    "长钱保·分红增额寿(尊享版)": "53375",
    "家财险·家庭综合保险": "39894",
    "健康福·少儿百万重疾险": "43117",
    "健康福·百万重疾(长期版)": "38933",
}

# ============================================================
# 四、发音规避
# ============================================================

# 删除级：口播整词删除，prompt显式禁止补词
PRONOUNCE_DELETE = ["息肉", "超声"]

# 空格级：前后加空格帮助TTS正确断词
PRONOUNCE_SPACE = [
    "意外", "门诊险", "符合条件", "免赔额", "好医保",
    "保证续保", "恶性肿瘤", "甲状腺", "投保", "赔付",
]

# prompt通用发音约束（拼在每条prompt末尾）
PRONOUNCE_CONSTRAINT = (
    "对白逐字朗读，产品名念准，不得吞字、改读、自由发挥。"
    f"绝不允许念出{'和'.join(PRONOUNCE_DELETE)}这{'两' if len(PRONOUNCE_DELETE)==2 else '几'}个词。"
    "人物对话口型对齐，连贯不停顿。"
)

# ============================================================
# 五、字幕SRT
# ============================================================

SRT_MAX_CHARS_PER_LINE = 13  # LLM断句每行上限
SRT_MIN_CHARS_PER_LINE = 3   # 最小行字数（防残字）
SRT_DELIVERY_MAX = 14         # 最终交付字幕每行上限

# LLM断句降级策略：换key重试→WAITING_USER，禁止本地机械切字
SRT_LLM_FALLBACK = "WAITING_USER"

# ============================================================
# 六、飞书字段枚举
# ============================================================

FEISHU_TYPE_OPTIONS = ["营销号", "剧情"]
FEISHU_STATUS_OPTIONS = ["ok", "失败"]
FEISHU_VERSION_OPTIONS = ["v1", "v2", "v3", "v4"]

# ============================================================
# 七、交付
# ============================================================

CSV_HEADERS = [
    "序号", "项目名称", "水印编号", "名称", "类型", "版本", "时长(秒)",
    "提交时间", "完成时间", "状态", "task_id_p1", "task_id_p2",
    "本地文件", "费用(元)", "备注", "模型",
]

# 文件命名规范：{产品缩写}-{YYMMDD}脚本{N}-{版本}.mp4
# 示例：HYB-260908脚本1-v1.mp4

# ============================================================
# 八、工具函数
# ============================================================

def get_speed(product_name: str) -> int:
    """获取产品语速。"""
    for key, val in SPEED.items():
        if key in product_name:
            return val
    return SPEED["default"]


def seg_duration(chars: int, speed: int = 7) -> str:
    """计算单段视频时长（字符串，20-30秒clamp）。"""
    return str(max(SEGMENT_DURATION_MIN,
                   min(SEGMENT_DURATION_MAX,
                       int(round(chars / speed + SEGMENT_DURATION_BUFFER)))))


def watermark_id(abbr: str, product_id: str, date_yymmdd: str, seq: int) -> str:
    """生成水印编号。如 HYB52973-260908-001。"""
    return f"{abbr}{product_id}-{date_yymmdd}-{seq:03d}"


def _fmt_ts(sec: float) -> str:
    """秒→SRT时间戳 HH:MM:SS,mmm。"""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def words_to_transcript_srt(words) -> str:
    """ASR词列表→逐字稿SRT（每字一行+精确时间戳）。

    words: ASR返回的WordTime列表，每个有 .text .start_sec .end_sec
    返回SRT格式字符串。
    """
    lines = []
    for i, w in enumerate(words, 1):
        t = w.text.strip()
        if not t:
            continue
        lines.append(f"{i}\n{_fmt_ts(w.start_sec)} --> {_fmt_ts(w.end_sec)}\n{t}\n")
    return "\n".join(lines)


def words_to_json(words) -> list:
    """ASR词列表→逐字稿JSON数组。

    返回 [{"text":"阿","start":0.32,"end":0.36}, ...]
    """
    return [{"text": w.text, "start": round(w.start_sec, 3), "end": round(w.end_sec, 3)}
            for w in words if w.text.strip()]
