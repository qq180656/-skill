# 中间态产物定义

本文档定义链路中间各阶段产物的格式和存储规范
用于链路中断后的恢复和调试

## 1. CREATIVE_DESIGN 阶段产物

| 产物 | 格式 | 路径 | 说明 |
|------|------|------|------|
| 创意设计文档 | Markdown | {project}/_session/creative_design.md | CREATIVE_DESIGN输出（仅路径B） |

## 2. PLANNING 阶段产物

| 产物 | 格式 | 路径 | 说明 |
|------|------|------|------|
| 结构化脚本 | JSON | {project}/_session/parsed_script.json | SCRIPT_PARSE输出 |
| 原子脚本列表 | JSON | {project}/_session/atomic_scripts.json | SCRIPT_ATOMIZE输出；其 text 字段=**期望朗读文本(expected_readback_text)**，是 VERIFYING/DIFF_ANALYSIS 的唯一比对基准（非原始脚本） |
| 合规报告 | Markdown | {project}/_session/compliance_report.md | COMPLIANCE_CHECK输出 |
| 脚本标注文档 | Markdown | {project}/{YYYY-MM-DD}/脚本标注/{序号}_{名称}.md | 成片才有，生成前用户确认 |

## 3. STORYBOARD 阶段产物

| 产物 | 格式 | 路径 | 说明 |
|------|------|------|------|
| 分镜表 | Markdown | {project}/_session/storyboard.md | STORYBOARD输出 |

## 4. GENERATING 阶段产物

| 产物 | 格式 | 路径 | 说明 |
|------|------|------|------|
| 分段素材视频 | MP4 | {project}/{YYYY-MM-DD}/素材/{序号}_{名称}_seg{NN}.mp4 | VIDEO_GEN输出（中间产物,分段裸视频;seg01=首段,seg02=extend第2段…;单段模式无seg后缀直接进成片/） |
| 分段末帧截图 | PNG | {project}/{YYYY-MM-DD}/素材/{序号}_{名称}_seg{NN}_endframe.png | extend承接用,拼接完成前不删 |
| 拼接成片(无字幕) | MP4 | {project}/{YYYY-MM-DD}/成片/{序号}_{名称}.mp4 | SHOT_MERGE输出(多段拼接后;单段直出也存这里) |
| 成片(带字幕) | MP4 | {project}/{YYYY-MM-DD}/成片_带字幕/{序号}_{名称}.mp4 | 烧入口播字幕后的投放版 |
| 音色样本 | MP3 | {project}/_session/voice_{role}.mp3 | AUDIO_ANCHOR输出（多角色=多文件，每角色一个；命名与 wf_generation Step3/task_registry 统一，不用 voice_anchor.mp3 单数） |

## 5. VERIFYING 阶段产物

| 产物 | 格式 | 路径 | 说明 |
|------|------|------|------|
| ASR逐字稿（中间态） | JSON | {project}/_session/asr_words_{NN}.json | ASR_TRANS输出（ASR words 直出，不经LLM、不断句/合并/纠错）；**最终交付版**为 `{project}/{日期}/字幕/{序号}_{名称}_逐字稿.srt` + `{序号}_{名称}_words.json`（SRT+JSON 两份，见 delivery_standard.md） |
| 口播字幕（中间态） | SRT | {project}/_session/clean_{NN}.srt | TEXT_CLEAN输出——**由逐字稿派生**（LLM语义断句 + 逐字稿词时间戳锚定），不是独立再跑一次ASR |
| 发音差异报告 | JSON | {project}/_session/diff_{NN}.json | DIFF_ANALYSIS输出 |
| 警示语匹配报告 | JSON | {project}/_session/warn_match_{NN}.json | WARN_MATCH输出 |

## 6. REPAIRING 阶段产物

| 产物 | 格式 | 路径 | 说明 |
|------|------|------|------|
| 修复音频 | WAV | {project}/_session/repair_{NN}.wav | AUDIO_REPAIR输出 |
| 修复日志 | JSON | {project}/_session/repair_log_{NN}.json | 含尝试次数/策略/结果 |

## 7. 状态快照

| 产物 | 格式 | 路径 | 说明 |
|------|------|------|------|
| 状态快照 | JSON | {project}/_session/snapshot.json | WAITING_USER前保存含状态ID/已完成镜头/中间产物路径/**retry_counters（复合键结构：shot_id→error_position→error_type→strategy→累计次数，跨断点持久不清零，防止恢复后绕过修复上限；结构定义详见 `core/retry_counters_spec.md`）** |

## 8. 恢复校验

从快照恢复时，必须先校验中间产物有效性，不得直接假设产物仍然可用：

1. **文件存在性**：快照中记录的所有中间产物路径必须存在
2. **文件完整性**：文件大小 > 0；视频文件需验证时长 > 0 且可正常解码
3. **时间戳一致性**：中间产物的修改时间必须早于快照时间（证明快照后未被篡改/覆盖）
4. **依赖链完整性**：当前状态所需的全部前置产物必须有效（如恢复到 GENERATING 需确认原子脚本列表和合规报告存在）

校验失败处理：
- 单个非关键产物失效 → 重新生成该产物，不全局回退
- 视频文件失效 → 重新生成对应镜头（SHOT_i），其他镜头复用
- 多个关键产物失效（如原子脚本+合规报告均丢失）→ 回退到上一个完整状态，或询问用户是否从头开始

## 9. 清理规则

- 交付归档后: 保留ASR逐字稿（交付版在 `{日期}/字幕/`：`_逐字稿.srt` + `_words.json`）和执行日志,清理其他中间文件
- 用户主动终止: 保留全部中间产物供调试
- 磁盘空间不足: 优先清理音色样本和修复音频
