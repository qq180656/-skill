# AI视频批量生产规范 Agent执行总纲 v4.1

## 目录结构

```
AI视频生产规范/
├── README.md                          ← 本文件（总览+架构+入口）
├── core/                              ← 内核层
│   ├── state_machine.md               状态机: 主干状态+子状态+分支+暂停
│   ├── router.md                      路由逻辑: A/B/C/EDIT分流（含完整性判定阈值，唯一权威）
│   ├── task_registry.md               任务注册表: 原子任务I/O+重试属性
│   └── error_handler.md               异常处理: FATAL/RECOVERABLE/USER_INPUT_NEEDED/SKIP
├── workflows/                         ← 执行流（调用关系见文末「workflow依赖图」）
│   ├── entry_direct_script.md         路径A: 完整脚本直入（STORYBOARD→生成）
│   ├── entry_brief_only.md            路径B: Brief驱动（创意设计→分镜→生成）
│   ├── entry_mixed.md                 路径C: 混合输入处理
│   ├── wf_creative_design.md          创意设计工作流
│   ├── wf_storyboard.md              分镜规划工作流（Step1拆1a-1e）
│   ├── wf_generation.md               视频生成: text2video/reference2video/extend/拼接
│   ├── wf_verification.md             校验: ASR/标点/Diff/警示语/SRT
│   ├── wf_repair.md                   修复: TTS克隆/音频替换
│   ├── wf_edit.md                     修改: 音频级/字幕级/镜头级/台词级/脚本级修改流程
│   └── wf_delivery.md                 交付: 质检/归档/用户确认
├── knowledge/                         ← 知识库（每个文件头部带版本号/更新日期）
│   ├── compliance/                    合规规则
│   │   ├── rules.md                   三层叠加规则+警示语映射+前贴豁免
│   │   ├── trigger_conditions.md      触发时机/阻断行为
│   │   ├── 通用合规/                   全险种适用
│   │   ├── 险种专项/                   按险种叠加（原渠道+险种合并）
│   │   └── 产品专属/                   按产品叠加（含驳回案例提炼规则）
│   ├── video_parameters/              视频参数
│   │   ├── config_matrix.md           模型/语速/时长/Key管理/前贴参数/多版本矩阵
│   │   ├── asr_processing.md          ASR逐字稿处理（火山格式/标点恢复/同音纠错/占位符/diff/逐字稿导出SRT+JSON/口播字幕派生）
│   │   ├── segmentation_packaging.md  句子流分段打包算法（时长/停顿/场景/extend，唯一权威）
│   │   ├── image_generation.md        参考图生成（Seedream文生图/图生图、四视图/场景/首帧）
│   │   ├── subtitle_burnin.md         字幕烧录规范（硬字幕双层ASS/42pt/品牌色/逐字稿铁律/双版本交付）
│   │   └── 06-Seed-Audio声音工程与音频驱动系统.md  六维音色VOX LOCK/无BGM/音频先行
│   ├── tts_optimization/              TTS优化
│   │   ├── pronunciation_rules.md     发音规避词表（删除级+空格级+CAR-T卡替+验证状态）
│   │   ├── voice_clone_tts.md         音色复刻mega_tts（S_音色训练+独立TTS合成）
│   │   ├── script_writing_rules.md    脚本撰写通用规则
│   │   └── fallback_strategies.md     TTS降级策略
│   └── templates/                     模板与参考知识
│       ├── creative_design_template.md 创意文档模板
│       ├── storyboard_template.md     分镜表格式模板
│       ├── prompt_craft_guide.md      Prompt编写指南（分层+运镜起幅落幅+VOX+失败兜底）
│       ├── character_lock_protocol.md 角色锁定协议（参考图逐镜重复传参）
│       ├── style_reference.md         风格速查表
│       ├── narrative_arc.md           故事弧线与节奏
│       ├── quality_control.md         质量管控（KEEP/CHANGE+出片自检）
│       └── index.md                   脚本/ASR/通知输出模板
├── outputs/                           ← 交付标准
│   ├── delivery_standard.md           交付物清单+目录结构+命名规范
│   ├── intermediate_artifacts.md      中间产物/上下文/恢复规则
│   ├── asset_management.md            资产管理API（vendor_asset_id+byteplus真人LivenessFace认证）
│   └── 暗水印编号追踪规范.md          暗水印（低码率片源4M/win50）+_视频日志.csv映射
├── scripts/                           ← 可执行脚本（自包含，不依赖 build_video）
│   ├── skill_config.py                参数中心（唯一权威源：语速/Key/模型/水印/并发/枚举，所有批量脚本import此文件）
│   ├── image_to_video.py              生图→图生视频完整链路（Seedream 5.0 + Seedance 2.5 image2video）
│   ├── auto_repair.py                 发音修复自动链路（verify→detect→TTS克隆→crossfade替换→输出fixed.mp4）
│   ├── blind_watermark_util.py        图片盲水印（DWT+DCT+SVD）
│   └── blind_watermark_video.py       视频盲水印（抽帧+分段关键帧重编码+校验）
└── meta/                              ← 架构管理
    ├── changelog.md                   变更记录
    ├── glossary.md                    术语表
    └── _skill_revision_context.md    跨文档修订共享标准（内部参考）
```

**项目运行时目录**（断点恢复产物）：

```
{项目名}/
├── _task_ids.jsonl
├── _视频日志.csv
└── _session/
    ├── snapshot.json              ← 状态快照（断点恢复，retry_counters按error_position累计）
    ├── repair_log_{NN}.json       ← 修复记录（含error_position/edit_reason/before-after_snapshot）
    ├── voice_{role}.mp3           ← AUDIO_ANCHOR 预生成音色样本
    ├── creative_design.md
    ├── storyboard.md
    ├── alignment_map.json         ← ASR对齐占位符映射
    └── tts_validation_log.json    ← TTS规避词验证状态
```

## 核心架构

### 状态机主干流程

```
INPUT_PARSE → CREATIVE_DESIGN → PLANNING → STORYBOARD → ASSET_PREP → READY → GENERATING → VERIFYING → DELIVERING → DONE
```

- 路径A（完整脚本）：跳过CREATIVE_DESIGN，从PLANNING开始
- 路径B（Brief）：从CREATIVE_DESIGN开始，完整走全链路
- ⚠️ 主干状态与转移**以 `core/state_machine.md` 为唯一权威**，本图仅作速览；如有出入以状态机为准
- 任意状态可跳转 WAITING_USER（暂停等用户）或 REPAIRING（修复后回来）

### 路由判定（Router）

> 完整性判定阈值（多少字算完整脚本/片段）**以 `core/router.md` 为唯一权威**，本表不重复写具体数值，避免多处维护不一致（曾出现总纲50字 vs entry_mixed 20字的冲突）。

| 路径 | 触发条件 | 流程 |
|------|----------|------|
| A | 用户给了完整脚本（完整性达 router.md 阈值的结构化文本） | PLANNING → STORYBOARD → ASSET_PREP → READY → ... |
| B | 用户只给了项目名+类型 | CREATIVE_DESIGN → PLANNING → STORYBOARD → ASSET_PREP → READY → ... |
| C | 部分脚本 + 部分需求说明 | 补齐（来源标记）→ 按A处理 |
| EDIT | 对已有产物的修改指令 | KEEP/CHANGE协议 |

### 前贴 vs 成片

| 维度 | 前贴 | 成片 |
|------|------|------|
| 利益点 | 无（只引产品名） | 有 |
| 时长 | 15-25s | 弹性（30s/60s） |
| 警示语 | 无需挂载 | 必须逐句挂载 |
| 合规 | 三层全读（禁用表述），不挂警示语 | 三层全读 + 警示语挂载 |
| 脚本标注文档 | 不生成 | 必须生成 |
| 警示语SRT / WARN_MATCH | 不生成 / 跳过 | 口播SRT+警示语SRT分别生成 / 必检 |
| QC警示语完整性检查 | 跳过 | 必检 |
| 产物目录 | `前贴/`（与成片物理分目录） | `成片/` |

### 视频生成模型

| 模型 | 单段上限 | 分辨率 | 音频 | API |
|------|----------|--------|------|-----|
| Seedance 2.5 (doubao-seedance-2-5-260628) | 30s（10-30可选，5s步进） | 720p / 1080p | generate_audio=true（声画一体） | text2video / reference2video |
| Seedance 2.0 | 15s | 720p / 1080p | generate_audio=true | text2video / reference2video |
| Seedream 5.0-lite (doubao-seedream-5-0-260128) | 静态图 | 2K/3K/4K | — | text2image / image2image（组图≤15张） |
| Seedream 5.0-pro (doubao-seedream-5-0-pro-260628) | 静态图 | 1K/2K | — | text2image / image2image（图层分解） |
| mega_tts 声音复刻 | — | — | S_音色ID | upload训练/status/tts合成 |

生图规范见 `image_generation.md`；音色复刻见 `voice_clone_tts.md`；只认厂商资产ID/真人版权素材见 `asset_management.md`。

超时处理：按 segmentation_packaging 句子流打包（目标190字/段、硬上限205字、句读边界切），首段 text2video + 后续 reference2video + ffmpeg拼接。

### 三层合规体系

```
第一层（通用合规，全险种）→ 第二层（险种专项，按险种）→ 第三层（产品专属，按具体产品）
高层覆盖低层，逐层叠加校验（产品规则以 `产品专属/` 目录为唯一事实源，三层合规体系无第四层）
```

### 交付目录结构

```
{项目名}/
├── _task_ids.jsonl       ← 跨日期汇总
├── _视频日志.csv          ← 跨日期汇总
├── {YYYY-MM-DD}/
│   ├── 成片/
│   ├── 字幕/              ← 逐字稿(SRT+JSON，ASR直出=唯一源头) + 口播字幕(由逐字稿派生) + 警示语，同一目录
│   ├── 审核文档/          ← 生成后（内嵌ASR逐字稿文本版）
│   └── 脚本标注/          ← 生成前（警示语确认版）
└── _发音修复/
```

### TTS发音规避

统一方案：所有问题词前后加空格（删除级词整词删除，详见 pronunciation_rules）。

**验证状态管理**：
- 待验证词在脚本撰写阶段可正常使用（加空格处理），VERIFYING 的 ASR DIFF 中标记为"待验证词发音"重点核对
- ASR验证通过 → 从"待验证"移入"已验证"，更新 pronunciation_rules.md
- 验证不通过 → 升级为删除级或提报新处理策略
- 验证记录存 `_session/tts_validation_log.json`；已验证/待验证清单以 pronunciation_rules.md 为准

### Key管理

3把Key按月/日额度轮转，超限自动切换下一把。全部超限→通知用户等待次月重置。

## 核心设计原则

0. **合规优先（最高优先级）**：合规校验阻断（FATAL / USER_INPUT_NEEDED）高于生成效率与并发调度；任何阶段合规未通过不得进入下游，不为赶进度跳过或弱化校验。
1. **四层状态模型**：主干状态+子状态+分支修复+暂停交互，支持并行生成与局部失败恢复
2. **四级异常分级**：FATAL/RECOVERABLE/USER_INPUT_NEEDED/SKIP 统一处理
3. **四种路由模式**：完整脚本(A)/Brief(B)/混合输入(C)/修改(EDIT) 自动识别
4. **知识库闭环**：规则+触发时机+降级策略+模板+参考知识，每个workflow显式声明依赖
5. **前贴/成片分流**：同一个架构支持两种合规深度
6. **断点恢复**：任意阶段暂停后从快照恢复，不从头开始
7. **产物标准化**：按日期分层归档，两份文档（脚本标注+审核文档）分工明确
8. **知识库版本化**：knowledge 各文件头部带版本号+更新日期（`<!-- vX.Y | YYYY-MM-DD -->`），变更在 changelog 记录涉及的知识库版本

## workflow 依赖图（执行链路）

```
路径A: entry_direct_script ─→ wf_storyboard ─┐
路径B: entry_brief_only ─→ wf_creative_design ─→ wf_storyboard ─┤
路径C: entry_mixed ─→（补齐后按A或B）──────────────────────────┘
                                                              ↓
                         ASSET_PREP（生图/音色训练/资产ID，按需reuse）
                                                              ↓
                              wf_generation ─→ wf_verification ─→ wf_delivery
                                                    ↑↓（replace发音错误）
                                                wf_repair（可升级voice_clone_tts）
wf_edit ─→ 按修改类型跳转到对应 workflow（字幕/镜头/台词/脚本）
```

## 品类扩展指引（保险 → 非保险）

体系当前深度绑定保险行业，扩展到教育/电商等新品类时：
- **可直接复用**：状态机、路由、分镜模板、prompt_craft_guide、生成/校验/修复/交付子流程、暗水印
- **需替换**：`knowledge/compliance/`（换目标品类合规规则）、`tts_optimization/pronunciation_rules.md`（换品类发音规避词）、`config_matrix.md`（换语速/时长/模型参数）
- **需重新定义**：storyboard_template / prompt_guide 中的保险特化红线（医护形象、医疗险警示语、固定画面风格）
