#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生图→图生视频 完整链路（Seedream 5.0 + Seedance 2.5 image2video）。

> **平台适配声明**：本脚本设计于外部 BlueAI 网关环境。在小云雀平台环境中，
> 生图应使用 `sandbox_generate_image`，图生视频应使用 `sandbox_generate_video`
> （ImageList 传首帧图），音色克隆应使用 `sandbox_generate_audio`（Type=tts）。
> 见 `core/platform_adapter.md` 工具映射表。本脚本可作为链路逻辑参考。

流程：
1. Seedream text2image → 角色四视图设定稿（16:9横版）
2. 裁出正面头肩特写（单张）
3. Seedance image2video → 首帧图+prompt+audio → 视频（角色锁定）
4. reference2video extend → 承接延长

API端点：
- 生图：POST /api/doubao/text2image_v5_0（Seedream 5.0 lite）
- 图生图：POST /api/doubao/image2image_v5_0
- 图生视频：POST /api/doubao/image2video（Seedance 2.5，首帧图）
- 视频延长：POST /api/doubao/reference2video
- 轮询：POST /api/doubao/task_status

用法：
    from image_to_video import generate_character_sheet, image2video, full_pipeline
"""
import os, sys, re, json, time, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from skill_config import GW_KEYS, BASE_DOUBAO, VIDEO_MODEL
except ImportError:
    import os as _os
    GW_KEYS = [k.strip() for k in _os.environ.get("BLUEAI_GW_KEYS", "").split(",") if k.strip()]
    BASE_DOUBAO = "https://bmc-model-openapi.bluemediagroup.cn/api/doubao"
    VIDEO_MODEL = "doubao-seedance-2-5-260628"

SEEDREAM_MODEL = "doubao-seedream-5-0-260128"  # 5.0-lite（支持组图）


def _headers(key):
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _submit(endpoint, payload, key, max_retry=5):
    """提交任务，返回task_id。"""
    for a in range(max_retry):
        try:
            r = requests.post(f"{BASE_DOUBAO}/{endpoint}", json=payload,
                              headers=_headers(key), timeout=(10, 60))
            d = r.json()
            tid = d.get("task_id")
            if tid:
                return tid
            if r.status_code == 429 or d.get("code") == 2402:
                time.sleep(8 + a * 5); continue
            if r.status_code == 400:
                print(f"  审核400: {str(d.get('msg') or d.get('message'))[:100]}")
                return None
            time.sleep(3)
        except Exception as e:
            time.sleep(5)
    return None


def _poll(tid, key, interval=10, max_wait=600):
    """轮询任务状态，返回完整响应dict。"""
    for _ in range(max_wait // interval):
        try:
            d = requests.post(f"{BASE_DOUBAO}/task_status", json={"task_id": tid},
                              headers=_headers(key), timeout=30).json()
            st = d.get("status")
            if st == "succeeded":
                return d
            if st == "failed":
                print(f"  任务失败: {str(d.get('msg'))[:80]}")
                return None
        except Exception:
            pass
        time.sleep(interval)
    return None


def _download(url, path):
    """下载文件。"""
    r = requests.get(url, stream=True, timeout=120)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    os.replace(tmp, path)


# ============================================================
# Step 1: 生图（Seedream 5.0 文生图/图生图）
# ============================================================

def generate_character_sheet(
    character_desc: str,
    style: str = "写实",
    key: str = "",
    size: str = "2K",
    output_path: str = "",
) -> str:
    """生成角色四视图设定稿。返回图片URL。

    character_desc: 角色物理白描（从头到脚：骨相→面部→发型→配饰→上衣→下装→鞋履）
    style: 风格关键词
    """
    if not key:
        key = GW_KEYS[0]

    prompt = (
        f"{character_desc}的四视图角色设定稿，\n"
        f"同一角色的人物正面头肩特写、正面、侧面、背面三个无头全身视图横向排列，"
        f"人物特写只显示头部至肩部（锁定五官发型配饰），不显示腰部腿部和脚，\n"
        f"三个全身视图只显示肩膀衣领以下到脚尖（不画头部，头由特写负责），"
        f"自然站立、双足平踏地面，\n"
        f"四视图服装细节完全一致，特写衣领与全身衣领自然衔接，色彩准确统一。\n"
        f"纯白色背景，均匀平光照明，无明显阴影。\n"
        f"{style}。\n"
        f"三个全身视图严禁裁切下半身、严禁画出头部，人物特写禁止生成成全身视图，"
        f"面部禁止出现痣、黑点、斑点、疤痕、胎记，"
        f"禁止生成任何背景、文本、标注、字幕。\n"
        f"比例:16:9"
    )

    tid = _submit("text2image_v5_0", {
        "model_id": SEEDREAM_MODEL,
        "prompt": prompt,
        "size": size,
        "watermark": False,
    }, key)
    if not tid:
        raise RuntimeError("四视图生成提交失败")

    result = _poll(tid, key, interval=5, max_wait=120)
    if not result:
        raise RuntimeError("四视图生成轮询失败")

    # 提取图片URL（网关统一用video_url字段返回，即使是生图任务）
    image_url = None
    for field in ("video_url", "image_url", "image_urls", "images"):
        val = result.get(field)
        if val:
            image_url = val[0] if isinstance(val, list) else val
            break
    if not image_url:
        raise RuntimeError(f"四视图结果无图片URL: {list(result.keys())}")

    if output_path:
        _download(image_url, output_path)
        print(f"  四视图已下载: {output_path}")

    return image_url


def generate_scene_image(
    scene_desc: str,
    ratio: str = "9:16",
    key: str = "",
    output_path: str = "",
) -> str:
    """生成场景空镜参考图。返回图片URL。"""
    if not key:
        key = GW_KEYS[0]

    prompt = (
        f"高角度俯拍的纯空镜场景，从上方约45度角俯瞰{scene_desc}整体布局。\n"
        f"强化俯视空间布局感，材质物理质感清晰。\n"
        f"无人物、无人影、无剪影、纯空镜场景，禁止生成任何文本、标注、字幕。\n"
        f"比例:{ratio}"
    )

    tid = _submit("text2image_v5_0", {
        "model_id": SEEDREAM_MODEL,
        "prompt": prompt,
        "size": "2K",
        "watermark": False,
    }, key)
    if not tid:
        raise RuntimeError("场景图生成提交失败")

    result = _poll(tid, key, interval=5, max_wait=120)
    if not result:
        raise RuntimeError("场景图生成轮询失败")

    image_url = None
    for field in ("video_url", "image_url", "image_urls", "images"):
        val = result.get(field)
        if val:
            image_url = val[0] if isinstance(val, list) else val
            break
    if not image_url:
        raise RuntimeError("场景图结果无URL")

    if output_path:
        _download(image_url, output_path)

    return image_url


# ============================================================
# Step 2: 图生视频（Seedance 2.5 image2video）
# ============================================================

def image2video(
    image_url: str,
    prompt: str,
    duration: str = "25",
    key: str = "",
    ratio: str = "9:16",
    generate_audio: bool = True,
    output_path: str = "",
) -> dict:
    """首帧图+prompt→视频。返回 {"task_id", "video_url", "cost_cny"}。

    image_url: 首帧图片的公网URL（从四视图裁出的正面头肩特写，或场景图）
    prompt: 视频画面+台词描述（同text2video格式）
    """
    if not key:
        key = GW_KEYS[0]

    tid = _submit("image2video", {
        "model_id": VIDEO_MODEL,
        "image_urls": [image_url],
        "prompt": prompt,
        "duration": duration,
        "resolution": "720p",
        "ratio": "adaptive",  # image2video必须用adaptive（9:16会报TaskTypeConstraint）
        "generate_audio": generate_audio,
        "return_last_frame": True,
    }, key)
    if not tid:
        return {"task_id": None, "video_url": None, "cost_cny": 0}

    result = _poll(tid, key, interval=15, max_wait=900)
    if not result:
        return {"task_id": tid, "video_url": None, "cost_cny": 0}

    video_url = result.get("video_url")
    if isinstance(video_url, list):
        video_url = video_url[0]
    cost = float(result.get("cost_cny") or 0)
    last_frame = result.get("last_frame_url")

    if output_path and video_url:
        _download(video_url, output_path)

    return {
        "task_id": tid,
        "video_url": video_url,
        "cost_cny": cost,
        "last_frame_url": last_frame,
    }


def reference2video_mm(
    image_urls: list,
    prompt: str,
    duration: str = "10",
    key: str = "",
    ratio: str = "9:16",
    generate_audio: bool = True,
    video_urls: list = None,
    output_path: str = "",
) -> dict:
    """多模态参考生视频（/doubao/reference2video，Seedance 2.5 支持 1~30 张参考图）。

    与 image2video 的区别：image2video 把单图当**首帧**硬动起来；本函数把 image_urls
    当**多模态参考**（角色/场景/风格），prompt 用 [图1][图2] 标记引用，模型综合生成——
    这才是文档 prompt_craft_guide「参考@图片1的形象作为XX」的正确执行方式。

    image_urls: 参考图 URL 数组（角色三视图/场景图等），prompt 里用 [图1][图2] 引用
    video_urls: 可选，做视频延长/编辑时传前段视频（此时 ratio 应为 adaptive）
    返回 {"task_id","video_url","cost_cny","last_frame_url"}。
    """
    if not key:
        key = GW_KEYS[0]
    payload = {
        "model_id": VIDEO_MODEL, "prompt": prompt, "duration": duration,
        "resolution": "720p", "ratio": ratio,
        "generate_audio": generate_audio, "return_last_frame": True,
    }
    if image_urls:
        payload["image_urls"] = image_urls
    if video_urls:
        payload["video_urls"] = video_urls
    tid = _submit("reference2video", payload, key)
    if not tid:
        return {"task_id": None, "video_url": None, "cost_cny": 0}
    result = _poll(tid, key, interval=15, max_wait=900)
    if not result:
        return {"task_id": tid, "video_url": None, "cost_cny": 0}
    v = result.get("video_url")
    if isinstance(v, list):
        v = v[0]
    if output_path and v:
        _download(v, output_path)
    return {"task_id": tid, "video_url": v,
            "cost_cny": float(result.get("cost_cny") or 0),
            "last_frame_url": result.get("last_frame_url")}


# ============================================================
# 完整管线：生图→图生视频→extend
# ============================================================

def full_pipeline(
    character_desc: str,
    scene_desc: str,
    dialogue_p1: str,
    dialogue_p2: str = "",
    style: str = "写实生活风格，日系透亮明亮通透高调自然光暖色柔和",
    duration_p1: str = "25",
    duration_p2: str = "25",
    key: str = "",
    output_dir: str = ".",
    tag: str = "test",
    ref_dir: str = "",
) -> dict:
    """生图→图生视频→extend 完整链路。

    参考图存到 ref_dir/（默认 output_dir/参考图/），并写索引到 output_dir/_参考图索引.jsonl。
    返回 {"character_sheet_url", "character_sheet_local", "video_p1", "video_p2", "final_video", "total_cost"}
    """
    if not key:
        key = GW_KEYS[0]
    os.makedirs(output_dir, exist_ok=True)
    if not ref_dir:
        ref_dir = os.path.join(output_dir, "参考图")
    os.makedirs(ref_dir, exist_ok=True)

    # Step 1: 生角色四视图
    print(f"[{tag}] Step1: 生成角色四视图...")
    sheet_local = os.path.join(ref_dir, f"character_{tag}.jpg")
    sheet_url = generate_character_sheet(
        character_desc, style=style, key=key,
        output_path=sheet_local,
    )
    print(f"[{tag}] 四视图: {sheet_url[:60]}...")

    # 写参考图索引（追加模式，跨日期复用）
    index_path = os.path.join(os.path.dirname(output_dir.rstrip("/\\")), "_参考图索引.jsonl")
    with open(index_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "tag": tag, "type": "character_sheet",
            "url": sheet_url, "local": sheet_local,
            "desc": character_desc[:50], "style": style[:30],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, ensure_ascii=False) + "\n")

    # Step 1: 生角色四视图
    print(f"[{tag}] Step1: 生成角色四视图...")
    sheet_url = generate_character_sheet(
        character_desc, style=style, key=key,
        output_path=os.path.join(output_dir, f"{tag}_character_sheet.jpg"),
    )
    print(f"[{tag}] 四视图URL: {sheet_url[:60]}...")

    # Step 2: 首帧图→视频（P1）
    # 四视图的正面头肩特写在图片左1/4区域，但Seedance image2video会自动识别人物
    # 直接传四视图整张让模型选人物，或传单独裁切的特写
    prompt_p1 = (
        f"参考图片中的角色形象，{style}，竖屏9:16。\n"
        f"人物从第0秒开口说话，全程口型对齐台词，连贯不停顿。\n"
        f"台词：\"{dialogue_p1}\"\n"
        f"五官清晰不变形、人体结构正常、服装发型一致。"
        f"禁止明星脸。禁止电子屏幕。禁止医生护士。无字幕无logo。\n"
        f"时长{duration_p1}秒。"
    )

    print(f"[{tag}] Step2: image2video P1 ({duration_p1}s)...")
    p1 = image2video(
        image_url=sheet_url,
        prompt=prompt_p1,
        duration=duration_p1,
        key=key,
        output_path=os.path.join(output_dir, f"{tag}_p1.mp4"),
    )
    total_cost = p1["cost_cny"]
    print(f"[{tag}] P1完成: ¥{p1['cost_cny']:.1f}")

    result = {
        "character_sheet_url": sheet_url,
        "character_sheet_local": sheet_local,
        "video_p1": p1,
        "video_p2": None,
        "final_video": os.path.join(output_dir, f"{tag}_p1.mp4"),
        "total_cost": total_cost,
    }

    # Step 3: extend P2（如果有后半段台词）
    if dialogue_p2 and p1["video_url"]:
        prompt_p2 = (
            f"@视频1是需要向后延长的原视频。承接视频1结尾画面和人物，"
            f"同样的人物、服装、场景继续对话。\n"
            f"从第0秒立刻继续开口，与前段无缝衔接，绝不空窗沉默。\n"
            f"台词继续：\"{dialogue_p2}\"\n"
            f"保持人物场景一致。无字幕无logo。时长{duration_p2}秒。"
        )
        print(f"[{tag}] Step3: reference2video P2 ({duration_p2}s)...")
        tid2 = _submit("reference2video", {
            "model_id": VIDEO_MODEL,
            "video_urls": [p1["video_url"]],
            "prompt": prompt_p2,
            "duration": duration_p2,
            "ratio": "adaptive",
            "generate_audio": True,
        }, key)
        if tid2:
            r2 = _poll(tid2, key, interval=15, max_wait=900)
            if r2:
                url2 = r2.get("video_url")
                if isinstance(url2, list): url2 = url2[0]
                cost2 = float(r2.get("cost_cny") or 0)
                total_cost += cost2
                p2_path = os.path.join(output_dir, f"{tag}_p2.mp4")
                if url2:
                    _download(url2, p2_path)
                result["video_p2"] = {"task_id": tid2, "video_url": url2, "cost_cny": cost2}
                print(f"[{tag}] P2完成: ¥{cost2:.1f}")

                # concat
                import subprocess
                ffmpeg = os.environ.get("FFMPEG_PATH") or "ffmpeg"
                final = os.path.join(output_dir, f"{tag}.mp4")
                lst = os.path.join(output_dir, f"_{tag}_concat.txt")
                with open(lst, "w") as f:
                    f.write(f"file '{tag}_p1.mp4'\nfile '{tag}_p2.mp4'\n")
                subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", lst,
                               "-c:v", "libx264", "-crf", "20", "-preset", "fast",
                               "-c:a", "aac", final],
                              capture_output=True, timeout=120, cwd=output_dir)
                try:
                    os.remove(lst)
                except OSError:
                    pass
                if os.path.exists(final):
                    result["final_video"] = final
                    print(f"[{tag}] ✅ 拼接完成")

    result["total_cost"] = total_cost
    print(f"[{tag}] 总费用: ¥{total_cost:.1f}")
    return result


if __name__ == "__main__":
    # 测试：生一个30岁女性角色→图生视频
    r = full_pipeline(
        character_desc="30岁中国女性，圆脸微胖，齐肩黑发扎低马尾，穿浅蓝色碎花棉麻衬衫、卡其色九分裤、白色平底鞋，清爽自然",
        scene_desc="明亮的医院走廊，浅绿色瓷砖墙，窗户阳光充足",
        dialogue_p1="你这喷嚏打一上午了，感冒都拖三天了吧，还不去医院看看？",
        dialogue_p2="",  # 不extend，单段测试
        duration_p1="15",
        key=GW_KEYS[0],
        output_dir="./test_i2v",
        tag="test01",
    )
    print(json.dumps({k: str(v)[:80] for k, v in r.items()}, ensure_ascii=False, indent=2))
