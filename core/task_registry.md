# 原子任务注册表 (Task Registry)

## 1. 注册原则
- 原子性：每个任务是不可再分的最小操作单元
- 幂等性：允许重复执行，输出结果保持一致
- 可追溯性：每个任务必须产生唯一 Task_ID 并记录至 _task_ids.jsonl

## 2. CREATIVE_DESIGN 阶段任务
| 任务ID | 名称 | 输入 | 逻辑 | 输出 | 可重试 | 异常映射 |
|--------|------|------|------|------|--------|----------|
| CREATIVE_DESIGN | 创意设计 | 产品Brief+合规规则 | 构思主题/调性/叙事/角色 | creative_design.md | Yes | -（创意不满意回修改流程，非系统异常） |

## 3. PLANNING 阶段任务
| 任务ID | 名称 | 输入 | 逻辑 | 输出 | 可重试 | 异常映射 |
|--------|------|------|------|------|--------|----------|
| SCRIPT_PARSE | 脚本解析 | 原始文本 | 提取口播/警示语/场景 | 结构化对象 | No | E011 |
| SCRIPT_ATOMIZE | 脚本拆解 | 结构化脚本 | 5-8字断句/空格注入/产品名拆分 | 原子脚本列表 | Yes | - |
| COMPLIANCE_CHECK | 合规扫描 | 脚本文本 | 禁用词/警示语匹配 | 合规报告 | No | E007/E008 |

## 4. STORYBOARD 阶段任务
| 任务ID | 名称 | 输入 | 逻辑 | 输出 | 可重试 | 异常映射 |
|--------|------|------|------|------|--------|----------|
| STORYBOARD | 分镜规划 | PLANNING输出（原子脚本列表+合规报告）+ 路径B需creative_design.md | 拆解镜头序列/构造画面Prompt/预估时长 | storyboard.md | Yes | E015 |

## 5. READY 阶段任务
| 任务ID | 名称 | 输入 | 逻辑 | 输出 | 可重试 | 异常映射 |
|--------|------|------|------|------|--------|----------|
| READY_CONFIRM | 生成前最终确认 | 分镜+脚本标注+合规报告 | 展示最终确认清单，用户确认后进入生成 | 确认记录 | No | -（用户未确认则暂停） |

## 6. GENERATING 阶段任务
| 任务ID | 名称 | 输入 | 逻辑 | 输出 | 可重试 | 异常映射 |
|--------|------|------|------|------|--------|----------|
| VIDEO_GEN | 视频生成 | 原子脚本 | 调用视频工具 | shot_NN.mp4 | Yes(3次) | E001/E002/E003 |
| AUDIO_ANCHOR | 音色锚定 | 角色描述 | 调用音频工具 | voice_{role}.mp3 | Yes(3次，接口失败重试，见E012) | E012 |
| VIDEO_EXTEND | 视频延长 | 前段视频 | extend模式 | 拼接长视频 | Yes(2次) | E001 |
| SHOT_MERGE | 镜头拼接 | 各镜头视频 | ffmpeg拼接 | merged.mp4 | Yes(2次) | E009 |

## 7. VERIFYING 阶段任务
| 任务ID | 名称 | 输入 | 逻辑 | 输出 | 可重试 | 异常映射 |
|--------|------|------|------|------|--------|----------|
| ASR_TRANS | ASR识别 | 视频文件 | 火山词级识别 | WordTime_List + **逐字稿**（`字幕/{名称}_逐字稿.srt` + `{名称}_words.json`，words直出不经LLM） | Yes(2次) | E004 |
| TEXT_CLEAN | 文本清洗 | 逐字稿（`字幕/{名称}_words.json`） | 纠错/标点/对齐（LLM断句，时间戳取逐字稿） | 口播字幕SRT（**逐字稿SRT+JSON → LLM断句 → 口播字幕SRT** 的派生产物，非独立二次ASR） | No | - |
| DIFF_ANALYSIS | 发音分析 | 脚本vsASR | 文本Diff | 发音错误列表 | No | - |
| WARN_MATCH | 警示语匹配 | 脚本vsASR | 检查挂载 | 匹配状态 | No | E007 |

## 8. REPAIRING 阶段任务
| 任务ID | 名称 | 输入 | 逻辑 | 输出 | 可重试 | 异常映射 |
|--------|------|------|------|------|--------|----------|
| AUDIO_REPAIR | 音频修复 | 参考音+正确文本 | TTS克隆/ffmpeg替换 | fixed_shot_NN.mp4 | Yes(3次) | E005/E006/E012 |
| VIDEO_REDO | 镜头重做 | 原子脚本+新参数 | 调用视频工具重新生成 | shot_NN.mp4 | Yes(2次) | E006 |

## 9. DELIVERING 阶段任务
| 任务ID | 名称 | 输入 | 逻辑 | 输出 | 可重试 | 异常映射 |
|--------|------|------|------|------|--------|----------|
| ASSEMBLE | 产物组装 | 所有中间产物 | 按交付标准组装最终文件夹 | 交付目录 | No | - |
| WATERMARK_EMBED | 暗水印嵌入 | 成片+水印编号 | DWT+DCT+SVD 盲水印嵌入（规范见 `outputs/暗水印编号追踪规范.md`） | `成片_带水印/` + `_视频日志.csv` 水印编号列 | Yes(2次) | E006 |
| QC_CHECK | 质检 | 交付目录 | 检查文件完整性/命名/格式 | 质检报告 | No | - |
| ARCHIVE | 归档 | 质检通过的产物 | 移至最终存储路径+清理临时文件 | 最终路径 | No | E010 |
| BATCH_LOG | 批量日志 | 所有任务记录 | 汇总本次批量执行的任务ID/状态/耗时/费用 | _batch_log.txt | No | - |

## 10. 记录规范
所有任务必须记录至 `_task_ids.jsonl`（**本表为 `_task_ids.jsonl` 字段的唯一权威**，wf_generation/config_matrix/delivery_standard 一律引用此处，不各自定义）：
- 必备字段：`timestamp / task_id / stage / status / output_ref / metadata`
- 视频生成任务附加：`tag / model / prompt / payload`（并入 metadata 或平铺）
- `shot_NN ↔ 交付 {序号}_{名称}` 的映射写入 metadata
- 注：`_视频日志.csv`（费用/URL/水印编号等）是**另一份产物**，字段以 `outputs/暗水印编号追踪规范.md` §4.1 为准，勿与 `_task_ids.jsonl` 混淆
