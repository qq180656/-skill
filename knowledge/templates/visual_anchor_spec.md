# 视觉锚点描述集 (Visual Anchor Descriptor Set) v1.0
# 补丁文件：补充 wf_edit.md 镜头级修改的接缝校验执行层
# 目的：将 KEEP/CHANGE 接缝校验从模糊的"外貌/光影/空间一致"转为可执行的具体比对项
# 解决问题：Agent 无法做像素级视觉比对，但可通过结构化描述+参考图传入+描述级比对实现近似校验

# ============================================================
# 1. 问题诊断
# ============================================================
# wf_edit.md 现有规范要求镜头级修改后校验：
#   - 角色外貌一致：脸型/服装/发型 无跳变
#   - 光影连续：不得由暖色突变冷色
#   - 空间关系一致：人物站位/朝向/相对位置连贯
#
# Agent 实际能力边界：
#   ❌ 无法做像素级 face-matching 或 color histogram 比对
#   ❌ 无法量化"暖色突变冷色"的具体色温差值
#   ✅ 可以读取图片内容并生成结构化描述（sandbox_read 图片 caption）
#   ✅ 可以把 KEEP 末帧作为参考图传入 CHANGE 镜头的 ImageList
#   ✅ 可以在 Prompt 中用结构化锚点描述替代模糊的"保持一致"
#
# 解决方案：三步走
#   Step A: 生成前 — 锚点描述注入（把 KEEP 末帧描述写入 CHANGE 的 Prompt）
#   Step B: 生成后 — 描述级比对（读 CHANGE 首帧 vs KEEP 末帧的描述做差异检查）
#   Step C: 不一致时 — 补偿策略矩阵（具体可执行的修正动作）

# ============================================================
# 2. 视觉锚点描述模板（生成前注入）
# ============================================================
# 在 CHANGE 镜头的 Prompt 中，追加以下结构化锚点段（替代"保持一致"类模糊指令）：
#
# === VISUAL_ANCHOR（接缝约束）===
# 接缝参考：@图片N 是前一镜头（KEEP_{shot_id}）的末帧截图
# 请确保本镜头开头与该参考帧在以下维度连续：
#
# 【角色锚点】
# - 面部特征：{从角色锁定卡提取：面型/眼型/肤色/标志特征}
# - 服装状态：{当前形象的关键服装词，如"白色衬衫+藏蓝裙"，非全身描述}
# - 发型状态：{发型关键词，如"齐肩直发无变化"}
# - 体态姿势：{末帧中角色的姿态，如"面朝右前方站立、左手微抬"}
#
# 【光影锚点】
# - 主光源方向：{如"左上方自然光"}（与末帧一致或平滑过渡）
# - 色温基调：{如"暖通透3200K"}（禁止突变到冷蓝）
# - 曝光水平：{如"高调通透、阴影提亮"}（与末帧同档）
# - 环境光特征：{如"诊室白荧光底光+窗外日光侧照"}
#
# 【空间锚点】
# - 人物站位：{如"画面右1/3处，面朝左"}（与末帧位置衔接）
# - 场景布局：{如"身后是诊室白墙+蓝色门牌"}
# - 镜头距离：{如"中景，腰部以上"}（与末帧景别一致或平滑推拉）
# - 运镜方向：{如"末帧在缓慢右摇，本镜头从右摇停止位开始"}
# === END VISUAL_ANCHOR ===
#
# 使用规则：
#   - 锚点描述从 KEEP 镜头的 storyboard.md Prompt + 生成产物截图的 caption 提取
#   - 每个维度只写 1 句关键约束，不超过 20 字（控制 Prompt 信息密度）
#   - 末帧截图通过 ffmpeg 从 KEEP 镜头视频最后一秒截取（-sseof -1 -frames:v 1）

# ============================================================
# 3. 描述级比对清单（生成后校验）
# ============================================================
# CHANGE 镜头生成后，执行以下比对流程：
#
# Step B-1: 截取 CHANGE 镜头首帧（ffmpeg -frames:v 1）
# Step B-2: 用 sandbox_read 读取 KEEP 末帧 和 CHANGE 首帧的图片描述
# Step B-3: 按以下清单逐项比对：
#
# | 比对维度 | 比对方法 | 不一致阈值 | 补偿动作 |
# |----------|----------|-----------|----------|
# | 角色面部 | 两帧 caption 中的面部描述词差异 | >2个关键特征词不同 | 重做CHANGE，在Prompt中强化@图片N的面部引用 |
# | 服装 | 两帧 caption 中的服装颜色/款式词 | 颜色词或款式词不同 | 重做CHANGE，在Prompt中明确"穿着与@图片N完全相同的{服装词}" |
# | 发型 | 两帧 caption 中的发型描述词 | 发型词不同 | 重做CHANGE，在VISUAL_ANCHOR中加粗发型约束 |
# | 光影色调 | 两帧 caption 中的色调/光源描述 | 色温方向相反(暖→冷) | 非重做：用ffmpeg对CHANGE段做色彩校准(颜色映射到KEEP) |
# | 曝光水平 | 两帧 caption 中的明暗描述 | 高调→低调(或反向) | 非重做：用ffmpeg亮度/对比度微调 |
# | 人物位置 | 两帧 caption 中的空间位置描述 | 左右互换或距离突变 | 重做CHANGE，在VISUAL_ANCHOR中明确站位 |
# | 景别 | 两帧 caption 中的景别描述 | 全景→特写(跳两级) | 可接受(可能是分镜设计)，标注但不阻断 |
#
# 比对结果分级：
#   GREEN: 0-1 项不一致 → 通过，记录比对报告
#   YELLOW: 2-3 项不一致 → 通过但标注警告，在交付质检文档中标记"建议人工确认接缝"
#   RED: 4+ 项不一致或面部+服装同时不一致 → 不通过，触发补偿策略

# ============================================================
# 4. 补偿策略矩阵（不一致时的修正动作）
# ============================================================
#
# | 不一致类型 | 首选补偿 | 备选补偿 | 上限 |
# |-----------|----------|----------|------|
# | 面部不一致 | 重做：强化@图片N引用+角色锁定卡关键词 | 重做：同时传角色四视图+末帧(双参考) | 2次重做后→接受差异，标注人工确认 |
# | 服装不一致 | 重做：Prompt明确"穿着与参考帧完全相同的{具体服装词}" | 重做：在ImageList中追加该角色的服装参考图 | 1次重做后→接受，标注 |
# | 发型不一致 | 重做：在VISUAL_ANCHOR发型行加粗约束 | 通常模型自纠正概率高，1次即可 | 1次重做后→接受 |
# | 光影突变(暖→冷) | ffmpeg色彩校准：从KEEP末帧提取LUT应用到CHANGE段 | 重做：在Prompt光影锚点中明确色温关键词 | 优先用ffmpeg不重做(省额度) |
# | 曝光跳变 | ffmpeg亮度/对比度微调(±10%范围) | 重做：在Prompt光影锚点中明确曝光描述 | 优先用ffmpeg不重做 |
# | 人物位置跳变 | 重做：在空间锚点中明确"从{位置}开始" | 可接受(如果是运镜设计意图) | 1次重做后→检查storyboard是否设计如此 |
# | 景别跳变(跳2级) | 不补偿，标注"景别跳变"供人工确认 | - | 不阻断(可能是分镜设计的 dramatic cut) |
#
# 补偿执行优先级：
#   1. ffmpeg类补偿（色彩/曝光）优先于重做（省额度、不占生成槽位）
#   2. 重做补偿使用 VIDEO_REDO 流程，计数纳入 retry_counters（但用独立的 "SEAM_CHECK" 策略键）
#   3. SEAM_CHECK 策略上限 = 2 次（与 VIDEO_REDO 共享该镜头的重做总上限）

# ============================================================
# 5. ffmpeg 色彩/曝光补偿脚本模板
# ============================================================
#
# 场景：KEEP 末帧暖色高调，CHANGE 首帧冷色暗调，需要把 CHANGE 段校准到 KEEP 色调
#
# Step 1: 从 KEEP 末帧提取色彩特征
#   ffmpeg -i keep_shot.mp4 -sseof -1 -frames:v 1 keep_endframe.png
#
# Step 2: 从 CHANGE 首帧提取色彩特征
#   ffmpeg -i change_shot.mp4 -frames:v 1 change_startframe.png
#
# Step 3: 生成色彩映射 LUT（需安装 ffmpeg 的 lut3d 或使用 curves 滤镜近似）
#   方案A（精确但复杂）: 用 keep_endframe 和 change_startframe 生成差异 LUT
#   方案B（简单实用）: 用 ffmpeg curves/eq 滤镜手动调参
#
# Step 3B（推荐方案）:
#   ffmpeg -i change_shot.mp4 -vf \
#     "eq=brightness={delta_b}:contrast={delta_c}:saturation={delta_s}:gamma={delta_g}" \
#     -c:a copy change_shot_colorcorrected.mp4
#
#   参数估算：
#     delta_b = keep_avg_brightness - change_avg_brightness (±0.1范围)
#     delta_c = keep_avg_contrast / change_avg_contrast (0.8-1.2范围)
#     delta_s = keep_avg_saturation / change_avg_saturation (0.8-1.2范围)
#     delta_g = keep_avg_gamma / change_avg_gamma (0.9-1.1范围)
#
#   粗略估算方法（无需专业色彩分析工具）：
#     ffmpeg -i frame.png -vf "signalstats" -f null - 2>&1 | grep YAVG
#     YAVG = 亮度均值（0-255），两帧 YAVG 差值 / 255 = delta_b 近似值
#
# Step 4: 替换原 CHANGE 段
#   mv change_shot_colorcorrected.mp4 change_shot.mp4
#   重新做 SHOT_MERGE

# ============================================================
# 6. 接缝校验报告格式
# ============================================================
# 校验完成后输出 seam_check_{shot_id}.json：
#
# {
#   "keep_shot_id": "shot_02",
#   "change_shot_id": "shot_03",
#   "keep_endframe_path": "_session/keep_end_shot02.png",
#   "change_startframe_path": "_session/change_start_shot03.png",
#   "comparison": {
#     "face": {"status": "GREEN", "keep_desc": "鹅蛋脸、大杏眼", "change_desc": "鹅蛋脸、大杏眼"},
#     "clothing": {"status": "GREEN", "keep_desc": "白色衬衫", "change_desc": "白色衬衫"},
#     "hair": {"status": "GREEN", "keep_desc": "齐肩直发", "change_desc": "齐肩直发"},
#     "lighting": {"status": "YELLOW", "keep_desc": "暖通透自然光", "change_desc": "中性白光"},
#     "exposure": {"status": "GREEN", "keep_desc": "高调明亮", "change_desc": "高调明亮"},
#     "position": {"status": "GREEN", "keep_desc": "画面右1/3面朝左", "change_desc": "画面右侧面朝左"},
#     "framing": {"status": "GREEN", "keep_desc": "中景腰部以上", "change_desc": "中景腰部以上"}
#   },
#   "overall": "YELLOW",
#   "compensation_applied": null,
#   "note": "光影轻微差异在可接受范围，建议人工确认",
#   "timestamp": "2026-09-17T10:35:00Z"
# }

# ============================================================
# 7. 集成到 wf_edit.md 的位置
# ============================================================
# 在 wf_edit.md 的"镜头级修改"章节中，KEEP/CHANGE 接缝校验部分：
#
# 现有文本：
#   "不一致的处理：给 CHANGE 镜头的 Prompt 加对 KEEP 镜头的参考约束
#    （把 KEEP 末帧作参考图传入），或对 KEEP 镜头做轻微调色以统一影调"
#
# 替换为：
#   "接缝校验执行视觉锚点协议（见 scripts/visual_anchor_spec.md）：
#    1. 生成前：从 KEEP 末帧提取锚点描述，注入 CHANGE 镜头 Prompt 的 VISUAL_ANCHOR 段
#    2. 生成后：截取 CHANGE 首帧与 KEEP 末帧做描述级比对（7维度清单）
#    3. 不一致时：按补偿策略矩阵执行（ffmpeg色彩校准优先于重做）
#    4. 输出 seam_check_{shot_id}.json 校验报告"
#
# 在 wf_edit.md 的"修改后校验"表格中，镜头级行追加：
#   "接缝校验报告 seam_check_{shot_id}.json 存在且 overall ≠ RED"

# ============================================================
# 8. 能力边界声明
# ============================================================
# 本规范明确承认以下能力边界，不做虚假承诺：
#
#   1. 描述级比对 ≠ 像素级比对
#      - sandbox_read 返回的图片描述是语义级概括，不包含精确色彩数值
#      - 对于细微但关键的差异（如肤色偏黄0.5个色阶），描述级比对可能漏检
#      - 补偿：ffmpeg signalstats 做数值级亮度/饱和度补充检查（粗略但可量化）
#
#   2. LUT 色彩校准是近似而非精确
#      - eq 滤镜只能做全局亮度/对比度/饱和度/gamma 调整
#      - 无法做分区域色彩映射（如只调人脸不调背景）
#      - 复杂光影差异（如KEEP有窗光斑CHANGE没有）无法通过滤镜补偿，需重做
#
#   3. 重做不保证一致
#      - 即使传入了末帧参考图+锚点描述，模型仍可能生成有差异的画面
#      - 这就是为什么 SEAM_CHECK 上限 = 2 次后接受差异+标注人工确认
#      - 不做无限重试（成本控制优先于完美一致）
