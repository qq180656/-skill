<!-- v1.0 | 2026-09-17 -->
# 平台适配层 (Platform Adapter)

> 本文件是外部API调用与平台原生工具之间的映射规范。技能中引用的外部服务（火山ASR、BMC relay LLM、mega_tts、BlueAI网关等）在平台环境中需替换为对应原生工具或替代方案。

## 一、工具映射总表

| 技能原始引用 | 平台原生替代 | 适配说明 |
|-------------|-------------|----------|
| 火山ASR词级识别 | `sandbox_read`（读取视频/音频文件，平台自动返回ASR数据） | 平台读取音视频文件时自动提供内容描述和ASR数据，无需独立ASR接口 |
| BMC relay LLM（字幕断句） | 平台内置LLM能力（Agent自身完成断句） | Agent直接按语义断句规则处理，无需外部relay；字幕SRT的断句由Agent在沙盒内完成 |
| mega_tts 声音复刻 | `sandbox_generate_audio`（Type=tts） | 平台TTS工具支持音色描述和参考音频，可替代mega_tts的独立训练流程 |
| BlueAI网关 text2video | `sandbox_generate_video` | 平台原生视频生成工具，支持text2video/image2video/extend/edit/keyframe |
| BlueAI网关 text2image | `sandbox_generate_image` | 平台原生图片生成工具，支持文生图/图生图 |
| BlueAI网关 image2image | `sandbox_generate_image`（ImageList传参考图） | 图生图通过ImageList引用原图实现 |
| ffmpeg拼接/音频替换 | `render_video`（视频拼接）+ `sandbox_bash`（ffmpeg命令） | 简单拼接用render_video；音频替换/crossfade/转码等用sandbox_bash执行ffmpeg |
| 暗水印嵌入 | `sandbox_bash`（执行Python脚本） | 使用scripts/下的blind_watermark脚本，在sandbox Python环境中运行 |
| ffprobe视频校验 | `sandbox_bash`（ffprobe命令） | 直接在sandbox中执行ffprobe |
| `_视频日志.csv` 费用提取 | `check_credit_quote` | 平台积分查询工具替代手动费用记录 |

## 二、Key管理替换为积分管理

### 原始方案（不适用）
3把BlueAI Key按月/日额度轮转，超限自动切换。

### 平台方案
- 使用 `check_credit_quote` 在生成前查询积分余额和预计费用
- 积分不足时暂停并通知用户充值，不自动切换Key
- 生成后从工具返回中提取实际消耗，记入 `_视频日志.csv`
- **不再需要** config_matrix.md 中的Key池表和轮转策略

### 适配后的流程
1. 批量生成前：调用 `check_credit_quote` 确认积分充足
2. 生成中：每个镜头生成后记录实际消耗
3. 积分不足时：暂停（对应原E014），通知用户，保留快照可续跑

## 三、ASR校验链路适配

### 原始方案（不适用）
调用火山VC返回utterance + words词级时间戳，精度要求词准确率>99%、时间戳误差<0.1秒。

### 平台方案
- 使用 `sandbox_read` 读取生成的视频文件，平台返回视频元信息和内容描述（含ASR数据）
- **词级时间戳精度**取决于平台ASR能力；若平台不提供词级时间戳，降级为句级时间戳
- 逐字稿格式保持不变（SRT + JSON），但时间戳粒度按平台实际能力调整
- **同音异形判定**：若平台ASR不返回拼音信息，降级为"单字差异默认不跳过（宁多报不漏报）"，不强制依赖pypinyin

### 降级矩阵

| ASR能力 | 逐字稿格式 | DIFF精度 | 字幕断句 |
|---------|-----------|---------|---------|
| 词级时间戳（理想） | 每字一条SRT + JSON | 同音异形判定可用 | LLM语义断句 + 词时间戳锚定 |
| 句级时间戳（降级） | 每句一条SRT + JSON | 按句Diff，不做单字级 | 句级SRT直接使用 |
| 仅文本（最低） | 纯文本逐字稿 | 按句文本Diff | Agent按≤13字规则手动断句 |

## 四、模型参数对齐

### 视频生成参数

| 参数 | 技能原始值 | 平台实际值 | 适配说明 |
|------|-----------|-----------|----------|
| 模型 | Seedance 2.5 (doubao-seedance-2-5-260628) | 以 `list_capabilities` 返回为准 | 不硬编码模型名，运行时查询 |
| 单段时长 | 20-30秒 | 4-30秒 | 下限从20s改为4s，短段也可生成 |
| 分辨率 | 720p / 1080p | 480p / 720p_lite / 720p / 1080p | 平台多两档可选 |
| 比例 | 固定16:9或9:16 | 16:9 / 9:16 / 4:3 / 3:4 / 21:9 / 1:1 / adaptive | 平台支持更多比例 |
| 参考图片上限 | 未明确 | ≤30张（Seedance 2.5） | 以 `list_capabilities` 为准 |
| 参考视频上限 | 未明确 | ≤10个（Seedance 2.5） | 以 `list_capabilities` 为准 |
| 参考音频上限 | 未明确 | ≤10段（Seedance 2.5） | 以 `list_capabilities` 为准 |
| 混合输入上限 | 未明确 | 图片+视频合计≤20个 | 以 `list_capabilities` 为准 |

### 图片生成参数

| 参数 | 技能原始值 | 平台实际值 | 适配说明 |
|------|-----------|-----------|----------|
| 模型 | Seedream 5.0-lite / 5.0-pro | 以 `list_capabilities` 返回为准 | 平台支持多种生图模型 |
| 组图 | sequential_image_generation=auto | 平台不支持组图，逐张生成 | 四视图需分别生成或用单图多视图描述 |
| 比例 | 3:4（角色）/ 9:16（场景） | 1:1 / 16:9 / 4:3 / 9:16 | 角色图改用4:3或9:16 |
| 水印 | watermark=false | 平台默认无水印 | 无需额外设置 |

### 音频生成参数

| 参数 | 技能原始值 | 平台实际值 | 适配说明 |
|------|-----------|-----------|----------|
| TTS模型 | mega_tts（需训练音色ID） | `sandbox_generate_audio` Type=tts | 平台TTS支持VoiceDesc音色描述，无需独立训练 |
| 音乐生成 | 无 | `sandbox_generate_audio` Type=music | 平台支持BGM生成，可替代外部音乐库 |
| 音色复刻 | upload训练→S_音色ID→/v1/tts | TTS + VoiceDesc描述 | 不需要独立训练流程，通过音色描述实现 |

## 五、视频合成与字幕

### render_video 使用规范

| 场景 | 参数 | 说明 |
|------|------|------|
| 多镜头拼接成片 | `video_paths` + `output_path` | 按播放顺序传入各镜头视频路径 |
| 成片加BGM | `bgm_audio_path` | BGM由 `sandbox_generate_audio` Type=music 生成后传入 |
| 成片加字幕 | `show_subtitle: true` | 平台自动语音识别生成字幕，替代手动SRT烧录 |
| MV模式 | `pipeline_name: "mv"` | 启用MV草稿类型与自动字幕 |
| 指定渲染分镜 | `storyboard_path` + `shot_ids` | 从分镜JSON渲染指定镜头 |

### 字幕方案适配

| 原始方案 | 平台方案 | 说明 |
|---------|---------|------|
| ASR逐字稿 → LLM断句 → 口播字幕SRT | `render_video` show_subtitle=true | 平台自动语音转写字幕，替代手动SRT链路 |
| 手动ASS烧录（42pt/28pt双层） | `render_video` show_subtitle=true + `subtitle_scene` | 平台字幕模板替代手动ASS |
| 警示语SRT独立生成 | Agent在沙盒内生成SRT文件 | 警示语字幕仍需手动生成（平台不识别保险警示语） |
| 逐字稿SRT + words.json | `sandbox_read` 读取视频获取ASR数据后由Agent生成 | 逐字稿仍需产出（审核/合规需要），但数据源改为平台ASR |

## 六、扩展品类指引

当从保险扩展到教育/电商等其他品类时：
- **可直接复用**：状态机、路由、分镜模板、prompt_craft_guide、生成/校验/修复/交付子流程
- **需替换**：`knowledge/compliance/`（换目标品类合规规则）、`tts_optimization/pronunciation_rules.md`（换品类发音规避词）、`config_matrix.md`（换语速/时长/模型参数）
- **需重新定义**：storyboard_template / prompt_guide 中的保险特化红线
- **平台原生可补充**：creative_agent创意发散、generate_shot_video_prompt_plan分镜规划、14+体裁知识ref（短剧/MV/诗词/VFX等）
