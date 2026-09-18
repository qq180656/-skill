# 状态机定义 (State Machine) v3.1

## 架构模型：四层状态
- 主干状态：线性串联的主流程节点
- 子状态：主干状态内部的并行/串行细分子任务
- 分支状态：任意主干状态均可跳转的修复通道
- 暂停状态：任意主干状态均可跳转的用户交互通道

## 1. 主干状态定义

| 状态 | 名称 | 进入条件 | 退出条件 | 失败出口 |
|------|------|----------|----------|----------|
| INPUT_PARSE | 输入解析 | 接收到用户输入 | 路由判定完成,确定路径 | -> WAITING_USER(信息不足) |
| CREATIVE_DESIGN | 创意设计 | 用户意图已明确（仅路径B） | creative_design.md产出并获用户确认 | -> WAITING_USER(需修改创意) |
| PLANNING | 脚本就绪 | 路径A:用户脚本已解析 / 路径B:creative_design.md已确认 / 路径C:片段+需求合并脚本已确认 | 原子脚本列表+合规报告就绪；成片需脚本标注文档获用户确认 | -> WAITING_USER(合规需决策/脚本需修改) |
| STORYBOARD | 分镜规划 | PLANNING完成（原子脚本列表+合规报告已就绪） | storyboard.md产出并获用户确认 | -> WAITING_USER(需修改分镜) |
| ASSET_PREP | 资产准备 | storyboard.md已确认 | 分镜所需参考图/场景图/首帧、音色、厂商资产ID全部就绪（缺则生成/训练/上传，见image_generation/voice_clone_tts/asset_management） | -> WAITING_USER(真人认证/素材确认) |
| READY | 就绪 | ASSET_PREP完成、素材齐全 | 用户确认分镜和脚本标注文档后进入生成（固定的生成前确认门，非临时暂停；注：审核文档是生成后ASR版产物，不在此门确认，READY 确认的是脚本标注文档=警示语确认版） | -> WAITING_USER(需确认) |
| GENERATING | 生成中 | 用户确认 | 所有镜头视频文件就绪 | -> REPAIRING(单镜头失败) |
| VERIFYING | 校验中 | 视频文件就绪 | 前贴:ASR+发音Diff通过 / 成片:ASR+发音Diff+警示语全部通过 | -> REPAIRING(发音错误) |
| DELIVERING | 交付中 | 校验通过 | 产物组装+质检完成 | -> WAITING_USER(质检异常) |
| DONE | 完成 | 交付产物归档 | (终态) | (无) |

> **⛔ STORYBOARD 是必经状态，禁止跳过（出片路径：前贴/成片）。** 直接从口播文本套模板生成数据文件（不做场景推断/景别设计/运镜规划）会导致画面千篇一律。必须走 wf_storyboard.md 1a-1e 全流程。**例外：纯脚本出口（SCRIPT_ONLY，仅交付口播脚本、不出片）在三层合规+原子化+用户确认齐全后合法早退，不经 STORYBOARD 及之后。**

## 2. 子状态（GENERATING 内部）

GENERATING 内部按镜头序列拆分为独立子状态,支持并行执行:

| 子状态 | 说明 | 并行性 | 独立失败处理 |
|--------|------|--------|--------------|
| SHOT_1 | 第1个镜头生成 | 可与SHOT_2..N并行 | 失败只重做SHOT_1,不影响其他 |
| SHOT_2 | 第2个镜头生成 | 可与SHOT_1..N并行 | 失败只重做SHOT_2 |
| SHOT_N | 第N个镜头生成 | 可并行 | 失败只重做SHOT_N |
| SHOT_MERGE | 镜头拼接 | 依赖所有SHOT_i完成 | 失败重做拼接,不重做镜头 |

### 子状态跳转规则
- READY -> SHOT_1..N (并行启动)
- SHOT_i 成功 -> 标记完成,等待MERGE
- SHOT_i 失败 -> 进入 REPAIRING(仅针对SHOT_i)
- REPAIRING 完成 -> 回到 SHOT_i 重试
- 所有 SHOT_i 完成 -> SHOT_MERGE
- SHOT_MERGE 完成 -> 退出 GENERATING,进入 VERIFYING

## 3. 分支状态（REPAIRING）

| 来源状态 | 修复动作 | 修复完成后 |
|----------|----------|------------|
| GENERATING/SHOT_i | 换模型/降分辨率/缩短时长后重新生成 | 回到 SHOT_i |
| VERIFYING(replace) | TTS克隆重读+ffmpeg替换(AUDIO_REPAIR) | 回到 VERIFYING 重新ASR |
| VERIFYING(insert/delete) | 重做镜头(VIDEO_REDO)→重新SHOT_MERGE | 回到 VERIFYING 重新ASR |
| DELIVERING | (一般不进入修复,质检异常走WAITING_USER) | - |

### 修复约束
- 重试上限3次（具体任务可能更少，如ASR/拼接/归档为2次、音色锚定接口重试3次见E012，以 error_handler.md 和 task_registry.md 为准），超过上限则升级为 FATAL 异常。replace 发音错误的完整升级链：`AUDIO_REPAIR×3 → VIDEO_REDO×2 → 换脚本表达(用户确认) → FATAL`
- 每次重试记录日志(尝试次数/策略/结果)，并写入 `snapshot.json` 的 `retry_counters`；**计数跨断点恢复持久保留，不清零**（防止恢复后绕过上限造成无限重试）
- **retry_counters 采用复合键结构**（shot_id → error_position → error_type → strategy → 累计次数），升级链判定按位置+类型精确触发，结构定义与升级逻辑详见 `core/retry_counters_spec.md`
- 修复仅针对失败的具体镜头/片段,不全局回退

## 4. 暂停状态（WAITING_USER）

| 来源状态 | 暂停原因 | 用户响应后 |
|----------|----------|------------|
| INPUT_PARSE | 输入信息不足以判定路由 | 补充信息后回到 INPUT_PARSE |
| READY | 需用户确认分镜/脚本标注文档（对齐 task_registry.md:READY_CONFIRM=分镜+脚本标注+合规报告） | 确认后进入 GENERATING,修改后回到 READY 重新校验 |
| DELIVERING | 质检发现异常,需用户决策 | 用户确认后继续/用户修改后回退 |
| 任意状态 | FATAL异常 | 用户决定终止或调整参数后重试 |

### 暂停约束
- 暂停时必须保存当前上下文(所有中间产物路径+状态快照)
- 用户响应后从快照恢复,不从头开始
- 暂停无超时限制,等待用户主动响应

## 5. 状态转移图

INPUT_PARSE -> CREATIVE_DESIGN -> PLANNING -> STORYBOARD -> ASSET_PREP -> READY -> GENERATING -> VERIFYING -> DELIVERING -> DONE

路径A(完整脚本): INPUT_PARSE -> PLANNING -> STORYBOARD -> ASSET_PREP -> READY -> GENERATING -> ...（跳过CREATIVE_DESIGN）
路径B(Brief):   INPUT_PARSE -> CREATIVE_DESIGN -> PLANNING -> STORYBOARD -> ASSET_PREP -> READY -> GENERATING -> ...
路径C(混合):    INPUT_PARSE -> PLANNING -> STORYBOARD -> ASSET_PREP -> READY -> GENERATING -> ...（片段+需求合并后按路径A处理，跳过CREATIVE_DESIGN）

> ASSET_PREP 说明：分镜确认后、READY 前，按需准备素材（默认 reuse/skip，不是每条都生）：
> - 缺角色/场景/首帧图且用户未提供 → Seedream 生图（`knowledge/video_parameters/image_generation.md`）
> - 渠道只认 vendor_asset_id 或真人版权素材 → 资产管理/真人认证（`outputs/asset_management.md`）
> - 发音需稳定音色/方言资产/后期独立配音 → mega_tts 训练（`knowledge/tts_optimization/voice_clone_tts.md`）
> 用户已给图/视频内发声即可满足时，ASSET_PREP 快速通过不额外生成。

GENERATING 内部子状态:
  READY -> SHOT_1..N (并行) -> SHOT_MERGE -> VERIFYING
              |                    ^
              v                    |
           REPAIRING --------------+

任意状态 -> WAITING_USER -> 回到来源状态
任意状态 -> REPAIRING -> 回到来源状态(VERIFYING/GENERATING)
DONE/交付后 -> EDIT -> 按修改类型回退对应阶段（音频级/字幕级→就地修改后回 VERIFYING；镜头级→GENERATING 单镜头重做(VIDEO_REDO)；台词级→STORYBOARD；脚本级→INPUT_PARSE 按路径A/B重走）；EDIT 的定位/KEEP-CHANGE/版本(_v2)语义见 wf_edit.md，产物从磁盘(_task_ids.jsonl/交付目录)定位
