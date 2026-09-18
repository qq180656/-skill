# 纠正子流程 (Correction Workflow)

## 定位
VERIFYING(校验)检出差异后进入本流程。**自动纠正能修的,修不了的才报用户**。纠正完成后回 VERIFYING 复检,零差异才放行进 DELIVERING。

## 前置条件
- VERIFYING 阶段已完成检测,产出检测报告(差异类型/位置/时间轴/严重度)
- 检测报告含至少一项差异(零差异直通 DELIVERING,不进本流程)

## 纠正策略总表

| 差异类型 | 自动纠正动作 | 上限 | 超限处理 |
|----------|-------------|------|---------|
| **replace**(念错词) | Step 1~3: TTS克隆重读+音频替换(AUDIO_REPAIR) | 同一处累计3次 | 升级 VIDEO_REDO |
| **insert/delete**(漏念/多念) | Step 4: 重做镜头(VIDEO_REDO) | 同一镜头2次 | 换脚本表达(需用户确认) |
| **E007**(警示语缺失/错位) | Step 5: 调时间轴重挂 | 2次 | 进 WAITING_USER |
| 全部超限 | — | — | FATAL 通知用户 |

## 依赖知识库
- `knowledge/tts_optimization/fallback_strategies.md` — TTS降级策略
- `knowledge/tts_optimization/pronunciation_rules.md` — TTS规避词表
- `knowledge/templates/quality_control.md` — KEEP/CHANGE修改协议（镜头重做时）

## 执行步骤

### Step 1: 提取参考音频
- 从原视频中提取同说话人的无错误段（8秒）
- 参考音频必须避开错误段
- **参考音频质量校验**：
  - 信噪比 SNR ≥15dB，低于则不可用（环境噪声过大）
  - 不含 BGM（生成阶段若违反无BGM铁律混入音乐的段不可用）
  - 必须单人片段，不含其他说话人声音
  - 不合格 → 前后滑动时间窗找同说话人其他无错误段；整条都找不到 → 用 AUDIO_ANCHOR 阶段预生成的 voice_{role}.mp3（见 wf_generation Step3）

### Step 2: TTS克隆重读
- 调用音频生成工具（text_to_audio_plus / audio_to_audio_plus），传入参考音频和正确文本
- **正确文本来源优先级**：
  1. 用户明确提供的纠正文本（最高，直接用）
  2. atomic_scripts.json 对应原子的文本（脚本原始意图，ASR检出的是读错）
  3. ASR差异分析推断的正确文本（最低，须用户确认）
  - 来源2/3时，修复前展示"原视频念XX，正确应为YY，是否确认？"
- 输出格式: wav

### Step 3: 音频替换
- ffmpeg切割原音轨
- 拼入修复音频段
- **拼接平滑**：拼接点前后各10ms交叉淡入淡出(crossfade)防爆音；修复段响度(LUFS)与拼接点前后±1s均值对齐(偏差≤±1 LUFS)；全轨查削波(clipping)有则峰值限制(limiter)；平滑参数记入repair_log
- **技术参数对齐**：修复音频采样率与原音轨一致(通常48k/44.1k，不一致重采样)、声道数一致；合回后ffprobe查音视频时长差≤50ms
- 合回视频
- 验证音画同步

### Step 4: 音频纠正产物
- 修复后视频: 素材/{序号}_{名称}_seg{NN}_fixed.mp4（或成片/{序号}_{名称}_fixed.mp4）
- **修复后局部ASR复检（不跑全片）**：仅对修复段+前后各1秒ASR，校验发音匹配及拼接是否影响相邻；未修复段沿用原VERIFYING结论不重新ASR；若局部检出新错误→拼接引入的回Step3调拼接参数，否则走新的replace纠正
- 修复串行执行（BMC音频接口偶发500错误）

### Step 5: 镜头重做纠正（insert/delete 类差异）
- **触发**：VERIFYING 检出 insert(漏念3字以上) / delete(多念5字以上) / 整句漏念/多念
- **动作**：仅重新生成指定镜头 SHOT_i（可换模型/降分辨率/缩短时长/微调Prompt），其余镜头复用原文件不动
- **降级自动判定**：
  - 第 1 次重试：仅微调 Prompt（补约束、强化台词逐字念），不换模型不降分辨率
  - 第 2 次重试：自动降一档分辨率（1080p→720p），通知用户已降级
  - 2 次均失败 → 标最终失败(E006)并通知用户
- 重做后 → 重新 SHOT_MERGE → **回 VERIFYING 全量复检**

### Step 6: 警示语纠正（E007 类差异）
- **触发**：VERIFYING 检出警示语缺失/错位
- **动作**：调整时间轴重新挂载（精确匹配→模糊匹配→手动匹配）
- 重挂后 → **回 VERIFYING 复检 WARN_MATCH**
- 2次仍无法挂载 → 进 WAITING_USER

### Step 7: 纠正上限与升级（防无限循环）
- 同一处错误的纠正次数**跨"纠正→复检→再纠正"回环累计**，不因每次进入本流程而清零
- 升级链：`AUDIO_REPAIR 累计3次 → 升级 VIDEO_REDO(上限2次) → 换脚本表达(须用户确认+重跑合规) → FATAL`
- **升级时间成本提示**（每次升级前展示）：AUDIO_REPAIR约1-3分钟、VIDEO_REDO约5-15分钟、换表达+合规约15-30分钟
- 计数纳入 `snapshot.json` 的 `retry_counters`（复合键结构见 `core/retry_counters_spec.md`），跨断点持久不清零
- 每次尝试写入 `_session/repair_log_{NN}.json`

### Step 8: 人工审核（纠正后兜底）
- **自动纠正全部成功**（复检零差异）→ 标"纠正完成·自动通过"，展示纠正摘要（改了哪几处/策略/耗时），**直接进 DELIVERING**
- **部分纠正成功、部分需人工**→ 展示：已自动修复的项 + 仍需人工决策的项，等用户确认
- **镜头逻辑复核**（镜头重做后执行）：参考 `shot_logic_review.md` 的场景状态表+保险视频特化检查项，复核重做镜头与相邻镜头的连续性（角色位置/银幕侧/朝向/道具状态/环境锚点）
- 用户确认通过 → 进 DELIVERING；用户要求再改 → 回对应 Step 继续纠正
- 每次尝试写入 `_session/repair_log_{NN}.json`（attempt/strategy/result/**error_position**(如00:12.3-00:13.1)/**error_text**/**edit_reason**/before_snapshot/after_snapshot）；升级判定按 error_position 查同一位置累计尝试次数；NN全局递增、内部 error_position 支持按位置聚合；snapshot.json 的 retry_counters 以 error_position 为key累计（非按视频），**断点恢复后不清零**（否则会绕过上限造成无限重试）。
- **升级判定逻辑**采用复合计数规则，具体实现详见 `core/retry_counters_spec.md` §3
