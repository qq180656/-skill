<!-- v3.4 | 2026-09-10 -->
# 音色克隆与独立 TTS（mega_tts 声音复刻）

> 区分两条发音链路：
> - **视频内发声**（默认）：Seedance `generate_audio=true`，角色按 prompt 的 @VOX 六维卡直接念白，适合绝大多数剧情/口播。
> - **音色资产化 / 独立配音**（本文）：先上传样本训练专属音色（`speaker_id` S_ 开头），再用 TTS 合成独立音频。适合：①发音反复修不对、需要稳定同一把声音；②后期配音/替换整条音轨；③方言/特定真人音色锁定；④长旁白后期铺。

## 一、能力与接口（火山，经 BlueAI 网关）

base：`https://bmc-model-openapi.bluemediagroup.cn`，Bearer Token 鉴权。
HTTP 状态恒为 200，成败看响应体 `code`（0=成功）。

| 步骤 | 接口 | 说明 |
|------|------|------|
| 1 上传训练 | `POST /v1/mega_tts/audio/upload` | 传 speaker_id + 音频样本，启动训练 |
| 2 查状态 | `POST /v1/mega_tts/status` | 轮询到训练完成 |
| 3 合成 | `POST /v1/tts` | voice_type=S_音色ID，文本转语音 |
| 音色库 | `GET /v1/template/list` | 查可用系统音色 |

异步任务提交返回 `TS_PENDING`，用 `/v1/cv_get_result` 轮询（返回不带 TS_ 前缀：PENDING/PROCESSING/SUCCEED/FAILED）。

## 二、训练音色（声音复刻）

`POST /v1/mega_tts/audio/upload`：
- `speaker_id`：自定义，**S_ 开头**（如 `S_yisheng01`）
- `audios`：训练样本数组（URL）
- `source=2`（固定）
- `language`：0中文(默认)/1英/2日/3西/4印尼/5葡
- `model_type`：
  - `1` ICL1.0 声音复刻（推荐，还原用户音色）
  - `2` DiT标准版（音色，不还原风格）
  - `3` DiT还原版（音色+口音+语速风格全还原，方言/特定人选这个）
  - `0` MEGA旧效果（不推荐）
- `extra_params`（JSON字符串）：`enable_audio_denoise` 降噪（样本噪声大时开）

训练样本要求（参考音频质量，也是 wf_repair 选段标准）：
- 单人、干声、SNR≥15dB，无BGM/无他人串音
- 时长按官方要求（通常10s-数分钟清晰语料）；可从成片中提取同说话人无错段
- 样本只承担音色，不含要规避的错误念法

`POST /v1/mega_tts/status` 轮询 `status`：0未发现/1训练中/2完成/3失败/4已启用；完成后 `speaker_id` 可用于合成，`demo_audio` 可试听。

## 三、TTS 合成

`POST /v1/tts`（app/user/audio/request 四段）：
- `audio.voice_type`：S_复刻音色ID，或 /v1/template/list 的系统音色
- `audio.encoding`：wav/mp3；`rate` 采样率；`loudness_ratio` 音量[0.5,2]默认1；`speed_ratio` 语速[0.2,3]默认1（好医保系列对齐0.86、长钱保0.86的相对节奏时按实际校准）
- `audio.explicit_language`：zh 中文为主；不给则中英混
- `request.text`：合成文本，**≤1024字节**（超长分段合成后ffmpeg拼接）
- `request.text_type=plain`（DiT不支持ssml）
- `request.reqid`：每次唯一UUID
- `request.operation=query`（HTTP非流式）
- `request.split_sentence=1`：解决1.0复刻语速过快
- `request.with_timestamp=1`：返回原文时间戳（保留阿拉伯数字/符号，供字幕对齐）
- 句尾静音：`enable_trailing_silence_audio=true` + `silence_duration`(0-30000ms)

## 四、典型用法与流程接线

1. **发音错误修不掉**（wf_repair 的 AUDIO_REPAIR 升级路径）：取同说话人清晰段→upload训练S_→tts合成正确句→ffmpeg交叉淡入替换（拼接点±10ms crossfade、响度对齐±1 LUFS、采样率/声道一致）
2. **整片后期配音**：为每个角色训练S_音色→按 atomic_scripts 分段tts→合成音轨与画面对齐（注意口型，重配音适合旁白/画外音，正脸特写对白重生视频更自然）
3. **方言资产化**：model_type=3 上传方言母语者样本，得到稳定方言S_，比在视频prompt里描述"四川口音"更可控；同一campaign跨条复用
4. 训练好的 `voice_{role}.mp3` / speaker_id 登记到 `_session/`，AUDIO_ANCHOR 阶段复用，全项目不漂移

## 五、与视频内 @VOX 的取舍

| 维度 | generate_audio（视频内） | mega_tts 独立音色 |
|------|------------------------|------------------|
| 口型同步 | 原生同步 | 需后期对齐，正脸特写吃亏 |
| 音色稳定/跨条一致 | 靠prompt六维卡，有漂移 | speaker_id锁定，最稳 |
| 成本/周期 | 零额外步骤 | 需训练+合成+混音 |
| 适用 | 剧情对白/口播（默认） | 反复修不好、后期旁白、方言/真人锁定 |

默认走视频内发声；仅当 wf_repair AUDIO_REPAIR×3 失败、或明确需要音色资产时才升级到本链路。
