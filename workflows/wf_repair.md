# 修复子流程

## 前置条件
- VERIFYING阶段检测到 **replace 类型**发音错误（同位置念错，音频替换即可纠正）
- ⚠️ 本流程**只处理 replace**。insert/delete（漏念/多念）不走本流程，改走 VIDEO_REDO 重做镜头（见 `wf_generation.md` 单镜头重做模式）

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

### Step 4: 产物输出
- 修复后视频: _发音修复/{序号}_{名称}_fixed.mp4
- **修复后局部ASR复检（不跑全片）**：仅对修复段+前后各1秒ASR，校验发音匹配及拼接是否影响相邻；未修复段沿用原VERIFYING结论不重新ASR；若局部检出新错误→拼接引入的回Step3调拼接参数，否则走新的replace修复
- 修复串行执行（BMC音频接口偶发500错误）

### Step 5: 修复上限与升级（防无限循环）
- 同一处 replace 错误的修复次数**跨"修复→ASR复检→再修复"回环累计**，不因每次进入本流程而清零。
- 升级链：`AUDIO_REPAIR 累计3次仍未纠正 → 升级 VIDEO_REDO 重做该镜头（上限2次）→ 仍失败 → 换脚本表达（同义替换须用户确认后重跑合规校验，见 fallback_strategies.md）→ 仍失败 → FATAL 通知用户`。
- **升级时间成本提示**（每次升级前展示，让用户决定继续或接受）：AUDIO_REPAIR约1-3分钟、VIDEO_REDO约5-15分钟(单镜头重生)、换表达+合规约15-30分钟。
- **换表达操作流程**：定位错误词在 atomic_scripts.json 的原子 → 提供同义替换候选（参考 pronunciation_rules 删除级/空格级替换建议，如"超声"→"影像检查"）→ 展示候选给用户选（不自动替换，同义词可能改变合规触发关系）→ 用户确认后更新 atomic → 重新 COMPLIANCE_CHECK → 重构Prompt → VIDEO_REDO；新候选触发新警示语则补挂再确认。
- 每次尝试写入 `_session/repair_log_{NN}.json`（attempt/strategy/result/**error_position**(如00:12.3-00:13.1)/**error_text**/**edit_reason**/before_snapshot/after_snapshot）；升级判定按 error_position 查同一位置累计尝试次数；NN全局递增、内部 error_position 支持按位置聚合；snapshot.json 的 retry_counters 以 error_position 为key累计（非按视频），**断点恢复后不清零**（否则会绕过上限造成无限重试）。
- **升级判定逻辑**采用复合计数规则，具体实现详见 `core/retry_counters_spec.md` §3
