# 视频生成子流程

## 前置条件
- 原子脚本列表已就绪
- 合规校验已通过
- 分镜（storyboard.md）已获用户确认
- READY 状态生成前最终确认已通过

## 依赖知识库
- `knowledge/templates/prompt_craft_guide.md` — Prompt编写指南（四层分层结构+运镜+起幅落幅+音频符号+失败兜底）
- `knowledge/templates/prompt_patterns.md` — 常见场景 Prompt 模式库（单镜头重做时按场景类型选择对应Prompt骨架）
- `knowledge/templates/character_lock_protocol.md` — 角色锁定协议（参考图逐镜头重复传参+音色锚定逐镜头传参）
- `knowledge/templates/character_asset_pipeline.md` — 角色资产产线（S1验脸→S2面部四视图→S3全身四视图逐级传递出图+自检）
- `knowledge/templates/multi_character_layout_spec.md` — 多角色布局控制方案（多角色镜头ImageList排列+方位词约束+融合修复）
- `knowledge/templates/multi_scene_director/` — 多人场景执行引导技能（多人Prompt骨架+ImageList排列规范+约束写法）
- `knowledge/templates/batch_fission_playbook.md` — 批量裂变操作手册（共享镜头校验+批量并发生成+按版本交付）
- `knowledge/video_parameters/segmentation_packaging.md` — 句子流分段打包（时长/停顿/场景对齐）
- `outputs/intermediate_artifacts.md` — 中间产物路径（音色样本/末帧截图/快照）
- `core/platform_adapter.md` — 平台适配（积分管理+render_video合成规范）

## 执行步骤

### Step 1: 时长预算
- 公式: **总预估时长 = 口播总字数(去括号后) ÷ 基准语速 + 纯动作镜头总时长 + 2秒段末缓冲**（台词说完后留2秒收尾/衔接）
- 基准语速：好医保系列（中老年52973/门诊险36866/少儿53408）= **7字/秒**；长钱保 = **6字/秒**；其他产品通用默认 = 7字/秒
- **纯动作镜头计入**：无台词的 establishing(2-3s) / 反应(1.5-2s) / 转场(1.5-3s) 镜头，时长直接取 storyboard.md 的 `duration` 字段，**不参与字数÷语速计算**；有台词的镜头动作与台词共享时间轴、不叠加（停顿类型化与余韵规则见 wf_storyboard.md §1b）
- 单段/extend 判定基于**修正后总时长**（含纯动作镜头 + 段末缓冲），不是仅口播时长
- 修正后总时长 ≤ 30s → 单段模式（一次 text_to_video 工具调用）
- 30s < 修正后总时长 ≤ 60s → extend模式（前30s text_to_video + 后30s reference2video + ffmpeg拼接）
- 修正后总时长 > 60s → 多段extend模式（按30s分段，首段 text_to_video，后续各段以上一段末帧为参考做 reference2video，最后统一 ffmpeg 拼接）；或建议用户拆分为多条短视频
- **extend分段台词边界保护（硬约束）**：
  - 分段点必须落在句读边界（。！？）之后，**禁止切半句**
  - 30s 落点在句中 → 前推到最近句末（该段可缩到 25-29s，`duration` 取 10/15/20/25/30 的5s步进档位）
  - 单句超30s（无法在句末切）→ 在逗号处切：前段以逗号语气收束，后段从完整语义单元开始
  - 分段完成后**重算各段字数÷语速时长**并与该段 `duration` 匹配，超出上限205字/段的重新打包（目标190字/段，句子流均匀打包，见 knowledge/video_parameters/segmentation_packaging.md）

### Step 2: Prompt构造
- **台词来源（硬约束）**：第3层"台词"必须逐字取自 `atomic_scripts.json` 对应原子（已完成去括号/删除级词删除/空格注入/"（2026版）"省略），**禁止从原始脚本重组或改写**，否则原子化成果在喂模型前丢失（复现产品名连读、"2026版"被念出等）。分镜阶段 `wf_storyboard.md` 已构造的镜头 Prompt 应直接复用，不重复另造。
- 遵循四层分层结构（完整规范见 `prompt_craft_guide.md`）:
  1. 素材与音色绑定层 — 按 `character_lock_protocol.md` 配置 ImageList：**每个镜头/每段都重复传入**该镜出场角色参考图（工具无状态，不能只在首镜传一次）；有音色锚定的角色同时通过 AudioList 传入 voice mp3
  2. 全局概述层（一句话）
  3. 画面阶段描述层（含时间锚点/台词/动作/音效）
  4. 通用约束层（画质/防水印/无字幕/时长比例）
- **多角色镜头 ImageList 排列**：当镜头包含2个及以上角色同框时，按 `multi_character_layout_spec.md` 的角色解耦引用法排列 ImageList（[角色A_Sheet, 角色B_Sheet, 场景参考图]），Prompt 中用方位词（左侧/右侧/前景/背景）显式绑定各角色位置
- **多人场景 Prompt 骨架**：当镜头为多人对话/街采/群戏场景时，参照 `multi_scene_director/` 的场景模板 Prompt 骨架（含素材绑定格式+画面阶段描述+180度轴线约束+道具归属写法），确保生成参数与分镜阶段设计一致
- **角色资产生成**（分镜标注缺失参考图时）：若分镜 Step 1d 标注的参考图尚未生成，按 `character_asset_pipeline.md` 的 S1验脸→S2面部四视图→S3全身四视图流程逐级出图，每步出完等用户确认后再走下一步；用户已上传角色照片时直接用作参考图，不再生成四视图
- **单镜头重做时 Prompt 微调**：VIDEO_REDO 模式下微调 Prompt 时，参照 `prompt_patterns.md` 选择对应场景类型的 Prompt 骨架模板，确保重做后的 Prompt 结构完整且台词逐字不变

### Step 3: 音色锚定 (AUDIO_ANCHOR) — 条件触发
- **触发判定（按优先级从上到下，命中即定，消除"多角色前贴"歧义）**：
  1. 用户明确要求"不做音色锚定" / 单人口播 → **不触发**
  2. 用户明确要求角色音色统一或指定音色 → **触发**
  3. 前贴（含多人对话前贴）→ **默认不触发**（前贴以场景引入为主，音色一致性非硬需求）；用户显式要求则按第2条触发
  4. 成片 且 脚本包含 2 个及以上角色 → **触发**
  5. 其余（单人口播成片）→ 不触发 → 直接跳到 Step 4
- **旁白穿插模式（画外旁白 + 场景化画面）**：
  - 触发音色锚定，但**仅锚定旁白音色**，画面中无台词的角色（路人/患者/演示人物）**不需要音色锚定**
  - 旁白音色卡从 creative_design.md 的视觉调性推断：温馨向 → 温和中年女声；专业向 → 沉稳男中音；调性混合时以主基调为准并在 `_session/` 记录推断依据
  - 旁白仍用 `@VOX_旁白` 六维音色卡在镜头 Prompt 中锚定，与出镜角色台词区分
- 动作：
  1. 从 SCRIPT_PARSE 元信息中提取角色列表（角色名/性别/年龄/方言/说话风格）
  2. 为每个角色调用音频工具生成音色样本 `voice_{role}.mp3`
  3. 存入 `{project}/_session/` 目录（对应 intermediate_artifacts.md 的音色样本路径）
- 音色样本用途：
  - 若视频生成接口支持参考音频传入：作为角色音色参考随视频生成请求提交
  - 若不支持：作为后期发音修复（wf_repair.md）时 TTS 克隆的首选参考音（优于从原视频截取）
- 异常处理：AUDIO_ANCHOR 失败（E012）→ **不阻断**视频生成，记录警告，后期修复时回退到从原视频提取参考音

### Step 4: 视频生成调用
- 单段模式: 一次 text_to_video 工具调用
- extend模式(30-60s): 前30s text_to_video + 后30s reference2video + ffmpeg拼接
- 多段extend模式(>60s): 按30s分段，首段 text_to_video，后续各段以上一段末帧为参考做 reference2video，最后统一 ffmpeg 拼接
- 积分管理: 生成前调用 `check_credit_quote` 确认积分余额充足；积分不足时暂停（E014）并通知用户充值，保留快照可续跑。详见 `core/platform_adapter.md` §二
- 并发调度: 视频生成并发4，采用动态调度（完成一个立即启动下一个），不按固定批次等待；TTS克隆串行
- **批量裂变场景**：多版本并发生成时，参考 `batch_fission_playbook.md` 的共享镜头校验规则（共享镜头只生成一次，各版本复用同一文件）和批量并发调度策略（按版本矩阵组织任务队列，共享镜头优先生成）
- **失败重试的并发占用**：
  - 重试**占用原任务槽位，不新增并发**；实际在跑任务数始终 ≤ 4
  - 原任务在 `snapshot.json` 标记 `FAILED_RETRIES` 并释放槽位，重试作为**新任务排队**（继承原镜头/分段标识与 `retry_counters` 计数）
  - 同一任务的重试与原任务**不得并发**（避免同 prompt 双份产出与重复扣费）
  - 重试上限 2 次耗尽 → 标 `FINAL_FAILED`（E006），槽位释放给队列中下一个任务，并通知用户
- **模型不可用降级**：
  - 返回**非额度类**服务不可用（模型下线/5xx/服务繁忙，非 E014 额度超限）→ 等待 30s 后**原模型原样重试 1 次**
  - 仍不可用 → 通知用户并**暂停该任务**（其余任务不受影响，继续按并发4调度）
  - 用户可选：等待服务恢复 / 指定切换其他模型（**需用户确认，禁止自动降级换模型**，切换后按新模型重新构造 Prompt 约束）

### Step 5: 任务记录
- 每条视频写入 `_task_ids.jsonl`，字段: tag/task_id/model/prompt/payload/status/timestamp
- **extend分段记录规范**：
  - 一个**逻辑视频**（用户视角的一条成片）在 `_task_ids.jsonl` 只写**一行**，`task_id` 字段填各分段 task_id 的 **JSON 数组**（如 `["t_aaa","t_bbb"]`），`status` 取拼接后成片状态
  - `_视频日志.csv` 同样**一行**：费用 = 各分段费用之和；时长 = **拼接后总时长**（非单段时长）
  - 类型区分：**单段模式 `task_id` 为字符串；extend/多段模式为数组**，下游统计按类型分支解析
- **同时写入 `_视频日志.csv`**（交付必须产物）：从 API 响应提取 费用(details.remaining_cny 差值/计费)/生成时间/视频URL，字段至少含 序号/task_id/model/时长/费用/生成时间/URL/状态。缺此步则交付 QC 的"`_视频日志.csv` 存在"必然失败或被迫编造数据

### Step 6: 产物存储
- 裸视频: `{项目名}/{YYYY-MM-DD}/成片/{序号}_{名称}.mp4`（以交付目录为准；历史路径 `<用户桌面>\{项目名}_出片\` 仅作参考，实际使用时替换）
- **extend中间帧管理**：
  - 各分段末帧截图 `shot_NN_endframe.png` 在**拼接完成前必须保留**（下一段 reference2video 的输入，误删会导致后续段无法承接）
  - 拼接完成后属中间文件，按 ARCHIVE 归档规则清理（时机以 intermediate_artifacts.md §9 为准）
  - 若用户可能改某一分段（REPAIRING / wf_edit / 待用户确认中），可选择**保留末帧**以支持从该段起重跑，不必从首段重新生成
- 中间文件: **交付归档(ARCHIVE)后**再清理，不在拼接后立即清理（拼接后~交付前仍处 WAITING_USER，shot_NN 需保留供断点恢复/单镜头重做复用；清理时机以 intermediate_artifacts.md §9 为准）

## 单镜头重做模式 (VIDEO_REDO) — 供 REPAIRING / wf_edit 调用
- **触发**：VERIFYING 检出 insert/delete（漏念/多念），或 GENERATING 单镜头失败，或 wf_edit 镜头级修改。
- **动作**：仅重新生成指定镜头 SHOT_i（可换模型/降分辨率/缩短时长/微调Prompt），其余镜头复用原文件不动。
- **降级自动判定（自动重试路径）**：
  - 第 1 次重试：**仅微调 Prompt**（补约束、明确光影/运镜/构图、强化台词逐字念），**不换模型、不降分辨率**
  - 第 2 次重试：**自动降一档分辨率**（1080p → 720p），仍不换模型，并**通知用户已降级**
  - 2 次均失败 → 标最终失败（`FINAL_FAILED`/E006）并通知用户，附两次失败原因
  - **用户主动重做**：按用户指定参数执行，**不触发自动降级**（分辨率/模型/时长均尊重指定值）
- **台词来源**：仍逐字取自 `atomic_scripts.json` 对应原子，**禁止从原始脚本重组或改写**。
- **重做后**：重新 SHOT_MERGE（仅拼接，不重做其他镜头）→ 回 VERIFYING 复检。
- 重试上限 2 次（E006），计数纳入 `snapshot.json` 的 `retry_counters`（跨断点持久）。

## 成片合成规范 (render_video) — 平台适配

> 平台使用 `render_video` 工具完成多镜头拼接、BGM合入和字幕叠加，替代原ffmpeg手动拼接+ASS烧录链路。完整适配说明见 `core/platform_adapter.md` §五。

### 合成参数

| 参数 | 用途 | 保险项目用法 |
|------|------|-------------|
| `video_paths` | 多镜头按播放顺序拼接 | 传入各镜头 `shot_NN.mp4` 路径列表 |
| `output_path` | 最终成片输出 | `assets/{project}/output.mp4` |
| `bgm_audio_path` | BGM音频路径 | 由 `sandbox_generate_audio` Type=music 生成后传入；前贴通常不需要BGM |
| `show_subtitle` | 自动语音转写字幕 | `true` 时平台自动识别视频/音频原声生成字幕；保险成片需手动生成警示语SRT，建议另存 |
| `storyboard_path` | 从分镜JSON渲染 | 有storyboard.md时可直接传入渲染 |
| `shot_ids` | 指定渲染分镜 | 重做部分镜头时只渲染指定ID |
| `subtitle_scene` | 字幕模板 | 选择合适模板，不改变字幕文字/字号/位置 |
| `pipeline_name` | 渲染模式 | MV模式传"mv"，普通视频不传 |

### 合成流程

1. **多镜头拼接**：所有镜头生成完成后，将 `shot_NN.mp4` 路径列表传入 `video_paths`，调用 `render_video` 拼接成片
2. **BGM合入**（按需）：前贴一般不加BGM（生活场景自然音）；成片如需BGM，先用 `sandbox_generate_audio` Type=music 生成，再传入 `bgm_audio_path`
3. **字幕叠加**（按需）：
   - 口播字幕：`show_subtitle: true` 让平台自动转写生成
   - 警示语字幕：平台不识别保险警示语，需Agent在沙盒内手动生成SRT文件，不通过render_video烧录
4. **双版本交付**：无字幕原版 + 有字幕版本分别保存

### 与原ffmpeg链路的差异

| 原方案 | 平台方案 | 说明 |
|--------|---------|------|
| ffmpeg concat拼接 | `render_video` video_paths | 平台原生拼接，更稳定 |
| ASS双层字幕烧录 | `render_video` show_subtitle=true | 平台自动字幕替代手动ASS |
| ffmpeg音频替换/crossfade | `sandbox_bash` 执行ffmpeg | 修复场景仍用ffmpeg命令 |
| ffprobe校验 | `sandbox_bash` 执行ffprobe | QC校验不变 |

### 成片BGM生成规范 — 平台适配

> 多段成片的配乐由 `sandbox_generate_audio`（Type=music）生成一条统一音轨，经 `render_video` 的 `bgm_audio_path` 合入。各段 Prompt 通用尾注写"禁止生成BGM"，段内禁、成片整体加。单段视频的 BGM 由视频模型随画面自带。

**歌词判定（带唱 vs 纯音乐）**：
- 保险视频几乎全部为纯音乐（含口播人声，不能被歌词盖住）
- 用户明示要歌/带唱 → 带唱（Lyrics必传）
- 成片任一段含台词/旁白 → 纯音乐（人声歌词会盖住说话）
- 全片无人声且总时长≥20s且内容是情绪叙事线 → 可带唱

**参数构造**：
| 参数 | 取值 |
|------|------|
| Type | "music" |
| MusicPrompt | 中文叙事句式，按成片节拍表逐段描述音乐本身，不写歌词 |
| Lyrics | 带唱时传歌词；纯音乐不传 |
| DurationSec | 成片总时长 |
| OutputPath | `assets/{project}/bgm.mp3`；重配用 `bgm_v2.mp3` 递增 |

**MusicPrompt写法**：
1. 先建成片节拍表：从分镜表各段Prompt的阶段描述+时长，换算成片绝对秒数，逐段记情绪/能量/有无台词/命中点
2. 按节拍表组句：中文叙事句式，段落行与节拍表一一对应，相邻段落至少一项可听变化
3. 保险项目典型调性：温暖治愈(indie folk, acoustic guitar, warm piano) / 专业信赖(minimal piano, ambient electronic) / 紧急紧张(dark ambient, pulsing bass)

**执行约束**：
- 全片只生成一条BGM，一次调用，时机在所有视频段生成完成后、render_video前
- 生成失败不重试、不阻塞成片：按无BGM合成交付，告知用户可补配
- bgm_audio_path 只接受 music 类型产物或用户提供的音乐文件

### 成片状态账本

> 任何段被修改后产出 `shot_NN_v2.mp4`（递增 v3/v4…），禁止覆盖旧文件。每次重调 `render_video` 前必须完整继承当前成片状态。

**账本字段**：
- 段顺序与每段生效版本（段号 → 生效文件路径）
- show_subtitle 当前值
- bgm_audio_path 当前值（有则必须带上，防止删段/换序后丢音乐）

任一状态项在重拼时被遗漏 = 用户已确认的效果被静默回退，属违规。
