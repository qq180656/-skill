# retry_counters 复合计数规范 v1.0
# 补丁文件：升级 snapshot.json 的 retry_counters 结构
# 目的：从按视频/镜头计数升级为按 error_position+error_type 复合计数
# 解决问题：长批次/断点续跑时同一位置反复重试烧额度，或计数清零绕过修复上限

# ============================================================
# 1. 旧结构（已废弃）
# ============================================================
# 旧 snapshot.json 的 retry_counters：
# {
#   "retry_counters": {
#     "shot_01": 2,
#     "shot_03": 1
#   }
# }
# 问题：
#   - 只按镜头计数，无法区分同一镜头内不同位置的错误
#   - 一个镜头可能有多处发音错误，每处独立修复但共享计数
#   - 断点恢复后如果只恢复镜头级计数，位置级修复进度丢失
#   - 升级链判定（AUDIO_REPAIR×3→VIDEO_REDO×2→换表达→FATAL）无法按位置精确触发

# ============================================================
# 2. 新结构（复合键）
# ============================================================
# 新 snapshot.json 的 retry_counters：
# {
#   "retry_counters": {
#     "shot_01": {
#       "00:12.3-00:13.1": {
#         "replace": {
#           "AUDIO_REPAIR": 2,
#           "VIDEO_REDO": 0,
#           "EXPR_CHANGE": 0
#         }
#       },
#       "00:25.0-00:26.5": {
#         "insert": {
#           "AUDIO_REPAIR": 1,
#           "VIDEO_REDO": 1,
#           "EXPR_CHANGE": 0
#         }
#       }
#     },
#     "shot_03": {
#       "00:05.0-00:08.0": {
#         "delete": {
#           "AUDIO_REPAIR": 0,
#           "VIDEO_REDO": 2,
#           "EXPR_CHANGE": 0
#         }
#       }
#     }
#   }
# }
#
# 键层级：
#   Level 1: shot_id (镜头标识，如 "shot_01")
#   Level 2: error_position (时间区间字符串 "MM:SS.m-MM:SS.m"，来自 ASR 词级时间戳)
#   Level 3: error_type ("replace" | "insert" | "delete")
#   Level 4: repair_strategy ("AUDIO_REPAIR" | "VIDEO_REDO" | "EXPR_CHANGE")
#   Value:   累计尝试次数（整数，跨断点持久不清零）

# ============================================================
# 3. 升级链判定逻辑（伪代码）
# ============================================================
#
# def check_escalation(shot_id, error_position, error_type, snapshot):
#     """
#     判定当前修复应使用哪种策略，或是否应升级/终止。
#     返回: (strategy, action) 其中 action ∈ {"execute", "escalate", "fatal"}
#     """
#     counters = snapshot.get_counter(shot_id, error_position, error_type)
#
#     audio_count = counters.get("AUDIO_REPAIR", 0)
#     redo_count = counters.get("VIDEO_REDO", 0)
#     expr_count = counters.get("EXPR_CHANGE", 0)
#
#     # 升级链: AUDIO_REPAIR×3 → VIDEO_REDO×2 → EXPR_CHANGE×1 → FATAL
#
#     if error_type == "replace":
#         if audio_count < 3:
#             return ("AUDIO_REPAIR", "execute")
#         elif redo_count < 2:
#             return ("VIDEO_REDO", "escalate")
#         elif expr_count < 1:
#             return ("EXPR_CHANGE", "escalate")
#         else:
#             return (None, "fatal")
#
#     elif error_type in ("insert", "delete"):
#         # insert/delete 不走 AUDIO_REPAIR，直接 VIDEO_REDO
#         # 但单/双字 insert 可先尝试 AUDIO_REPAIR 补
#         if error_type == "insert" and audio_count < 1 and word_count <= 2:
#             return ("AUDIO_REPAIR", "execute")  # 单/双字先补一次
#         if redo_count < 2:
#             return ("VIDEO_REDO", "execute")
#         elif expr_count < 1:
#             return ("EXPR_CHANGE", "escalate")
#         else:
#             return (None, "fatal")
#
# def increment_counter(shot_id, error_position, error_type, strategy, snapshot):
#     """修复尝试后调用，递增对应计数器"""
#     key = f"{shot_id}:{error_position}:{error_type}:{strategy}"
#     snapshot.retry_counters[shot_id][error_position][error_type][strategy] += 1
#     snapshot.save()  # 立即落盘，防止崩溃丢失

# ============================================================
# 4. EXPR_CHANGE（换表达）的计数特殊性
# ============================================================
# 换表达是升级链最后一环，要求用户确认后才执行：
#   - 计数上限 = 1（只允许一次换表达尝试）
#   - 执行前必须：展示同义替换候选 → 用户确认 → 重新 COMPLIANCE_CHECK → 重构 Prompt → VIDEO_REDO
#   - 换表达后如果仍失败，直接 FATAL，不再循环
#   - 换表达产生的新的 error_position 视为新错误，不继承旧位置计数

# ============================================================
# 5. 断点恢复校验（补充 intermediate_artifacts.md §8）
# ============================================================
# 恢复 snapshot 时，retry_counters 校验规则：
#   1. 结构校验：检查 retry_counters 是否为嵌套 dict（非旧版扁平 int）
#      - 旧版结构检测：value 为 int → 触发迁移逻辑（见下方 §6）
#   2. 位置有效性：error_position 对应的 ASR words 文件是否存在
#      - 不存在 → 该位置计数清零（基准丢失无法继续修复）
#   3. 策略上限校验：任何 strategy 计数超过上限 → 标记为已耗尽，不再尝试
#   4. 跨视频隔离：不同视频的同一 shot_id 不共享计数
#      - snapshot.json 按视频文件名隔离（一个视频一个 snapshot）

# ============================================================
# 6. 旧版迁移逻辑
# ============================================================
# 检测到旧版 retry_counters（扁平 int 结构）时的迁移规则：
#
# def migrate_retry_counters(old_counters, current_errors):
#     """
#     old_counters: {"shot_01": 2, "shot_03": 1}
#     current_errors: 当前 ASR 检出的错误列表
#     返回: 新结构 dict
#     """
#     new_counters = {}
#     for shot_id, old_count in old_counters.items():
#         # 旧计数无法精确归因到位置，保守处理：
#         # 将旧计数全部归入 AUDIO_REPAIR（最常见策略）
#         # error_position 标为 "legacy_unknown"
#         # 如果旧计数 >= 3，直接标记该 shot 为 AUDIO_REPAIR 已耗尽
#         new_counters[shot_id] = {
#             "legacy_unknown": {
#                 "replace": {
#                     "AUDIO_REPAIR": old_count,
#                     "VIDEO_REDO": 0,
#                     "EXPR_CHANGE": 0
#                 }
#             }
#         }
#         # 下一轮 ASR 检出具体位置后，新建位置键，legacy_unknown 保留但不影响新位置判定
#     return new_counters
#
# 注意：迁移后第一次 ASR 复检会产生具体 error_position，新位置从 0 开始计数。
#       legacy_unknown 仅作为历史记录，不参与升级链判定。

# ============================================================
# 7. repair_log 同步规范
# ============================================================
# repair_log_{NN}.json 每条记录必须包含以下字段，与 retry_counters 可交叉验证：
#
# {
#   "attempt_id": "shot_01_00:12.3-00:13.1_replace_AUDIO_REPAIR_3",
#   "shot_id": "shot_01",
#   "error_position": "00:12.3-00:13.1",
#   "error_type": "replace",
#   "error_text": "故意",          # ASR 识别到的错误文本
#   "expected_text": "意外",        # atomic_scripts.json 中的期望文本
#   "strategy": "AUDIO_REPAIR",
#   "attempt_number": 3,            # 该位置该策略的第3次尝试
#   "result": "failed",            # "success" | "failed"
#   "edit_reason": "ASR将意外识别为故意",
#   "before_snapshot": "path/to/before.mp4",
#   "after_snapshot": "path/to/after.mp4",
#   "timestamp": "2026-09-17T10:30:00Z",
#   "escalated_to": null            # 升级时填下一策略名，未升级为 null
# }
#
# 校验规则：retry_counters 中某位置某策略的 count 必须等于
#           repair_log 中该位置该策略的 attempt 记录数。
#           不一致时以 repair_log 为准（更详细的日志可重建计数）。

# ============================================================
# 8. 集成点（需同步修改的文件清单）
# ============================================================
#
# 文件 | 修改内容
# -----|----------
# core/state_machine.md §3 修复约束 | 更新 retry_counters 描述为复合键结构，引用本文件
# outputs/intermediate_artifacts.md §7 状态快照 | 更新 retry_counters 字段说明为复合键
# workflows/wf_repair.md Step 5 | 升级判定逻辑引用本文件的 check_escalation() 规则
# workflows/wf_verification.md Step 3 | DIFF_ANALYSIS 输出必须包含 error_position（已有时间戳，需显式提取为区间字符串）
# core/error_handler.md | E005/E006 升级判定引用本文件的复合计数规则

# ============================================================
# 9. 边界情况处理
# ============================================================
#
# 场景1: 同一镜头同一位置先 replace 后 insert
#   → error_type 是独立键，各自独立计数，互不影响
#   → 但升级链按位置聚合：如果 replace 已耗尽 AUDIO_REPAIR×3，
#      新出现的 insert 直接从 VIDEO_REDO 开始（同位置已修复过多次说明模型有系统性问题）
#
# 场景2: 修复后 ASR 复检发现新位置的错（非原位置）
#   → 新位置新计数，从 AUDIO_REPAIR 开始
#   → 原位置如果复检通过，计数保留但不影响新位置
#
# 场景3: 用户手动修改了脚本（台词级编辑 wf_edit）
#   → 该镜头所有 retry_counters 清零（基准已变，旧计数无意义）
#   → repair_log 保留但标记 "invalidated_by_edit"
#
# 场景4: extend 分段的某段修复
#   → shot_id 包含分段标识，如 "shot_01_seg2"
#   → error_position 是该段内的相对时间（非全片时间）
#   → 段间拼接后做全片 ASR 时，position 需转换为全片时间用于字幕校验
#      但 retry_counters 内部用段内相对时间即可（与生成粒度一致）
