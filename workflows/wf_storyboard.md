# 分镜规划工作流

## 适用场景
支持两种输入模式：

**入口路由判定**：
- 当前项目目录存在 `creative_design.md` → **路径B**
- 否则存在原子脚本列表（parsed/atomic JSON）→ **路径A**
- 两者都没有 → 暂停，提示用户先完成创意设计或脚本编写（entry_brief_only / entry_direct_script）

- **路径B模式**：已通过创意设计环节，拥有明确的 creative_design.md
- **路径A模式**：已有原子脚本列表（来自 entry_direct_script.md Step 2 输出），直接基于口播文本做分镜，不依赖 creative_design.md

## 依赖知识库
- `knowledge/templates/storyboard_template.md` — 分镜表格式模板
- `knowledge/templates/prompt_craft_guide.md` — Prompt编写指南（分层结构+运镜+起幅落幅+音频符号+失败兜底）
- `knowledge/templates/character_lock_protocol.md` — 角色锁定协议（参考图逐镜头重复传参）
- `knowledge/templates/narrative_arc.md` — 故事弧线
- `knowledge/templates/style_reference.md` — 风格速查表
- `knowledge/video_parameters/config_matrix.md` — 模型/语速/extend
- `knowledge/video_parameters/segmentation_packaging.md` — 句子流分段打包（时长/停顿/场景对齐）
- `knowledge/tts_optimization/pronunciation_rules.md` — TTS空格注入
- `knowledge/templates/broll_skills/` — 场景空镜 skill（按场景加载）：`landmark_scene.md` 地标/著名景点、`hospital_broll.md` 医院、`family_daily_broll.md` 家庭日常、`broll_scene.md` 通用空镜

## 执行步骤

### Step 1：分镜拆解（拆成 1a-1e 子步骤，逐项产出，避免跳步）

#### 1a：镜头序列拆解 + 场景推断
- **路径B**：依据 creative_design.md 叙事结构拆解；**路径A**：依据原子脚本口播语义拆解（一个镜头对应 1-3 句）
- 场景推断决策树：
  1. 脚本有明确场景描述 → 直接使用
  2. 有地点关键词（医院/家/办公室/超市/餐厅等）→ 推断对应场景
  3. 有人物关系关键词（母女/夫妻/同事等）→ 推断常见生活场景
  4. 无线索（纯口播/产品讲解）→ 中性室内场景，标注"场景为推断，建议用户确认"
- **多场景冲突处理**：若脚本前后段指向不同场景（如前半在家、后半在医院），按语义边界切分为不同**场景组**，每组独立标注场景；跨场景镜头注明转场方式（硬切/淡入淡出/空镜过渡），并在分段时把场景边界对齐到段边界（见 segmentation_packaging）。
- **场景 skill 加载**：识别到地标/著名景点、医院、家庭日常等场景时，加载 `knowledge/templates/broll_skills/` 下对应文件（landmark_scene/hospital_broll/family_daily_broll/broll_scene），按其写法构造空镜/场景 Prompt（如地标必须写可辨识视觉特征，不能只写名字）。
- 产出：镜头序列（镜头号/角色/场景/画面/台词）

#### 1b：时长估算与分段策略
- 纯念词 = 口播字数 ÷ 语速（好医保系列7字/秒、长钱保6字/秒，见 config_matrix）
- 停顿：逗号0.3s、句末0.6-0.8s、角色切换1.0-1.3s
- **纯动作/无台词镜头**（establishing shot/反应镜头/转场空镜）不参与字数÷语速，单独给动作预算：establishing 2-3s、反应1.5-2s、转场空镜1.5-3s，标注时长来源="动作预算"
- 动作与台词**共享时间轴**（边做边说不叠加）；段末留1.5-2s余韵、段首不留
- 按 segmentation_packaging 句子流打包（目标190字/硬上限205字），判定单段/extend，确定每段 duration（10/15/20/25/30）
- 产出：分段方案 + 每段时长

#### 1c：画面模式判定与 Prompt 构造
- 口播模式（对镜说话）→ 口播规范；对话模式（多人互动）→ 对话规范+正反打+景别切换节奏；旁白穿插 → prompt_craft_guide「旁白型画面分镜规则」
- 每个镜头按分层结构构造完整、**自包含**的 Prompt（光影含时间锚点、运镜含起幅落幅、台词随镜头+@VOX锚定）
- 产出：各镜头 Prompt

#### 1d：角色锁定与素材绑定
- **素材就绪前置门控**：配置 ImageList 前，检查所需参考图（角色面部/全身、场景图、道具图）是否已在项目目录存在；**缺失素材先生成，再进入 Prompt 构造**，不得带着缺失参考图往下走。
- 按 character_lock_protocol 配置 ImageList：**每个镜头/每段都重复传入**该镜出场角色参考图（工具无状态，不能只在首镜传一次），prompt 每镜写明"参考@图片N的形象作为XX"
- 产出：每镜头 ImageList 绑定表

#### 1e：TTS 空格注入与台词校对
- 应用 pronunciation_rules 的空格注入（删除级词、空格级词、CAR-T读"卡替"等），确保 Prompt 台词与原子脚本一致
- 用 storyboard_template 输出 storyboard.md

### Step 2：校验与优化（按优先级，P0 必须卡住）

**P0（不通过不出产物）**：
- 台词时长超限（单段超约205字/30s）
- Prompt 非自包含（依赖别段上下文才能理解）
- 角色参考图缺失或未逐镜绑定
- 多段场景未对齐段边界

**P1（强烈建议修复）**：
- 镜头间转场不连贯（缺连续元素/无转场提示）
- 风格关键词跨段不一致（对照 style_reference）
- 运镜缺起幅落幅、组合运镜超过两种

**P2（有则更好）**：
- 警示语挂载点核对（仅成片需要，前贴跳过）
- 景别切换节奏（避免连续同景别同角色）

**Prompt 字数自检**：逐个镜头核对字数区间——纯动作/空镜120-200字、单人台词200-300字、多人对话300-400字；超400压缩重复约束，不足则补光影/运镜/景别。

### Step 3：用户确认与修改分级
- 展示 storyboard.md（场景为推断的单独提示确认）
- 用户确认 → READY 生成前最终门 → wf_generation.md
- **修改分级处理**（不必一律回 Step 1 重拆）：
  - **微调**（单镜头台词/运镜/景别）→ 直接改对应镜头 Prompt，不重拆
  - **结构性修改**（增删镜头/调顺序/改场景）→ 回 Step 1 对应子步骤（1a/1b）重拆
  - **风格性修改**（整体风格/语速/画面模式）→ 回 Step 1c 重构所有 Prompt
