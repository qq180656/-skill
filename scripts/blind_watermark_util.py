"""图片盲水印封装（DWT+DCT+SVD），自包含，不依赖 build_video。
基于 blind_watermark 库（pip install blind-watermark）。
"""
import os
from typing import Optional

import cv2
import numpy as np
import blind_watermark
from blind_watermark import WaterMark

blind_watermark.bw_notes.close()

DEFAULT_WATERMARK_TEXT = "DM-品效-刘伟杰"
DEFAULT_PASSWORD_WM = 1
DEFAULT_PASSWORD_IMG = 1


class WatermarkCapacityError(Exception):
    """图片尺寸太小，容纳不下水印。"""


def _imread_unicode(path: str) -> Optional[np.ndarray]:
    try:
        data = np.fromfile(path, dtype=np.uint8)
    except OSError:
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_UNCHANGED)


def _imwrite_unicode(path: str, img: np.ndarray) -> bool:
    ext = os.path.splitext(path)[1] or '.png'
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        return False
    buf.tofile(path)
    return True


def compute_wm_length(text: str, password_wm: int = DEFAULT_PASSWORD_WM) -> int:
    bwm = WaterMark(password_wm=password_wm, password_img=DEFAULT_PASSWORD_IMG)
    bwm.read_wm(text, mode='str')
    return len(bwm.wm_bit)


def embed_watermark(
    src_path: str, dst_path: str,
    text: str = DEFAULT_WATERMARK_TEXT,
    password_wm: int = DEFAULT_PASSWORD_WM,
    password_img: int = DEFAULT_PASSWORD_IMG,
) -> int:
    os.makedirs(os.path.dirname(dst_path) or '.', exist_ok=True)
    src_img = _imread_unicode(src_path)
    if src_img is None:
        raise ValueError(f"图片读取失败: {src_path}")
    bwm = WaterMark(password_wm=password_wm, password_img=password_img)
    bwm.bwm_core.d1 = 10
    bwm.bwm_core.d2 = 5
    bwm.read_img(img=src_img)
    bwm.read_wm(text, mode='str')
    try:
        embed_img = bwm.embed()
    except AssertionError as e:
        raise WatermarkCapacityError(f"图片尺寸太小: {e}") from e
    if not _imwrite_unicode(dst_path, embed_img):
        raise OSError(f"图片写入失败: {dst_path}")
    return len(bwm.wm_bit)


def verify_watermark(
    image_path: str,
    expected_text: str = DEFAULT_WATERMARK_TEXT,
    password_wm: int = DEFAULT_PASSWORD_WM,
    password_img: int = DEFAULT_PASSWORD_IMG,
) -> bool:
    img = _imread_unicode(image_path)
    if img is None:
        return False
    wm_length = compute_wm_length(expected_text, password_wm)
    bwm = WaterMark(password_wm=password_wm, password_img=password_img)
    bwm.bwm_core.d1 = 10
    bwm.bwm_core.d2 = 5
    try:
        extracted = bwm.extract(embed_img=img, wm_shape=wm_length, mode='str')
    except Exception:
        return False
    return extracted == expected_text
