# 架构变更记录

## v4.4.0 (2026-09-17) 八技能深度融合：工业级管线驱动型升级

### 新增
- [NEW] `narrative_archetypes.md`：保险叙事原型库，含保险产品参与叙事的5种角色（关键证物/破局工具/关系证物/身份线索/状态触发）、产品介入节奏约束（0-20s纯剧情/20-25s自然出现/25-30s正式展示）、四大险种叙事原型库（重疾4原型/医疗3原型/意外3原型/养老3原型，每个含三锚点+产品角色）、七拍表（30-60s）和十拍表（90s-3min）节拍配平体系、翻盘铁律（第6拍翻盘钥匙必须第2-4拍埋过）、Logline先行公式（谁+目标+障碍+不可逆代价）、人物迷你弧光（错误信念→裂缝时刻→可见变化）、可证伪质量测试（换掉保险元素仍成立则叙事失败）、反AI自检四项
- [NEW] `visual_style_system.md`：视觉风格系统，含风格配方速选表（6种主语言+4种成像基底+胶片调味）、色彩命题一句话公式（主色域+唯一强调色+物理来源+变化路径）、60:30:10配色体系（主色组/辅助色组/强调色组+HEX量化写法）、四大险种12色方案模板（重疾/医疗/意外/养老各12色含HEX+比例+载体+光源）、五子层光影量化体系（光源角度/色温显色/视角机位/微观质感/大气介质+光比量化）、空泛词禁令、风格签名串机制（5种风格签名串+使用规则）
- [NEW] `director_shot_toolkit.md`：导演镜头技法库，含6种核心镜头技法（斯皮尔伯格推镜/希区柯克变焦/是枝裕和固定长镜/王家卫抽帧慢镜/格林格拉斯手持/狄金斯逆光剪影+竖屏适配）、构图由关系压力产生（6种主压力机制+视线流量检验）、对方存在证据规则（5种证据形式+连续三镜无证据回炉铁律）、动作闭环四拍（触发→反应→结果→释放+情绪转译为物理行为）、多镜切镜防贴片（切镜节奏+演活标准）、运镜/转场词库（8种运镜+8种转场）

### 修改
- [MOD] `prompt_craft_guide.md`：新增工业级提示词骨架升级模块——14区块骨架（B01-B14每段提示词完整结构+保险场景示例）、AU微表情强制注入准则（10个AU编号+肌肉动作+情绪含义+保险场景+A-E五级强度梯度+视线先导+纯产品特写转译）、动作闭环四拍（每镜必写+情绪编译为物理行为）、分级负面提示词体系（L1通用/L2叙事/L3保险合规/L4风格）、同步声锁铁律（No subtitles/No music/No BGM+例外条件）、多镜切镜防贴片、对方存在证据（双人戏强制）、空泛词禁令
- [MOD] `quality_control.md`：新增工业级质检门禁体系——G0-G4门禁协议（定档/剧本/资产/分镜/成片五阶段门禁+不过处理）、G3三大死症预检（贴片死/慢死/漂移死+检测方法+处理）、淘金制审片（不判整条过废+满意秒数裁金矿库+判定标准）、帧墙审片（PASS/TRIM/FAIL三级判定）、停线上报机制（脸变/场景变/物件错/ASR意外→故意误识→首次即停线）、反AI自检四项（CG/广告/电视剧/参考图翻版+症状+修复方向）、三个瞬间验收门、装配纪律五条
- [MOD] `narrative_arc.md`：新增熔炉五幕结构体系（定档→剧本→视觉定妆→分镜锻造→审片装配+各幕质检门+回炉不连锁纪律）、节拍配平与Logline先行引用指向narrative_archetypes.md（消除重复）、回炉纪律表（定档/Logline/风格/分镜/个别段五级回炉范围）
- [MOD] `character_asset_pipeline.md`：新增资产状态衍生体系——单一衍生源公理（禁止链式修改+面部骨相保护）、状态资产树（基准态→焦虑态/释然态/换装态/回忆态衍生结构）、保险场景常用状态资产表（妈妈焦虑/释然/爸爸疲惫/孩子病服/场景凌乱/夜间）、@命名字典（资产名=提示词@名=界面参考名）、分镜-资产匹配清单模板、参考槽纪律（只放资产级定妆图/叙事帧不进参考槽）、资产生命周期（创建→登记→匹配→验证→锁定→复用/新状态从基准态衍生）
- [MOD] `cinematic_narrative_tools.md`：新增可证伪质量测试（保险元素替换检验+依赖风险转移机制的4组对照写法）、保险叙事钩子公式（反常识/切身痛点/悬念缺口/情绪冲击4种公式+钩子自检）、翻盘道具埋设规则（4种常见翻盘道具+埋设段+翻转段+埋设方式+"短片没有篇幅天降神兵"铁律）
- [MOD] `index.md`：新增3个文件索引条目（narrative_archetypes/visual_style_system/director_shot_toolkit）

### 融合来源
- ugc-fan-zhuan-wei-duan-ju-dai-huo-shi-pin：产品5种叙事角色、三锚点改编规则、产品介入节奏、前20秒节奏约束 → narrative_archetypes.md
- ugc-dian-ying-rong-lu-cineforge：熔炉五幕结构、七拍/十拍节拍配平、Logline先行公式、人物迷你弧光、翻盘铁律、三大死症预检、淘金制审片、帧墙审片、反AI自检四项、三个瞬间验收、钩子拍自检 → narrative_archetypes.md + narrative_arc.md + quality_control.md + cinematic_narrative_tools.md
- ugc-quan-qiu-ding-niu-chuang-yi-guang-gao-pian-dao-yan：14区块骨架、G0-G4门禁、状态资产树、单一衍生源公理、@命名字典、分镜-资产匹配清单、参考槽纪律、同步声锁、风格配方体系 → prompt_craft_guide.md + quality_control.md + character_asset_pipeline.md + visual_style_system.md
- ugc-grwm-mei-zhuang-jiao-cheng-guang-gao-feng-ge：AU微表情强制注入、五子层光影量化、分级负面提示词、风格签名串、链式修改禁止公理 → prompt_craft_guide.md + visual_style_system.md + character_asset_pipeline.md
- ugc-da-tou-dao-yan-se-ka-tiao-se-300-wei-tong-yong-dao-yan：60:30:10配色体系、12色方案模板、色彩命题一句话、五子层光影量化 → visual_style_system.md
- vox-paper-director：可证伪质量测试方法论、风格签名串机制、钩子自检 → narrative_archetypes.md + cinematic_narrative_tools.md + visual_style_system.md
- material_fission：（已v4.3融入，本轮未新增内容）
- ugc-jue-se-chu-tu-chan-xian：（已v4.3融入，本轮未新增内容）
- ugc-ying-shi-bian-ju-skill：控制性理念、场景价值转变审计、因果性审计、双轨节奏标注、Hamartia人物缺陷、可拍性铁律、量化评分表、修改优先级规则、窄问题原则 → narrative_arc.md + quality_control.md

### 价值点统计
本轮共融入45个价值点，其中：
- 新建专项模块：3个文件（narrative_archetypes/visual_style_system/director_shot_toolkit），承载21个价值点
- 优化现有文件：7个文件（prompt_craft_guide/quality_control/narrative_arc/character_asset_pipeline/cinematic_narrative_tools/index/changelog），承载24个价值点（含影视编剧技能9个价值点）

## v4.3.0 (2026-09-17) 五技能融合：叙事深度+角色资产+批量裂变+流程管控

### 新增
- [NEW] `cinematic_narrative_tools.md`：电影化叙事工具箱，含命题先行写法（4种子品类命题模板）、道具状态链（设计模板+保险场景4个道具链示例）、信息目标驱动（6类信息目标+自检规则）、因果连续约束（错误/正确写法对照+旁白/回忆因果连接）、蒙太奇连接规则（6种连接方式+现实/回忆区分规则+密度控制）、色调对比叙事工具（4段色调模板+Prompt关键词）
- [NEW] `character_asset_pipeline.md`：角色资产产线，含S1验脸闸门→S2面部四视图→S3全身四视图三步逐级传递出图流程、四条铁律、三种入口判定、标准提示词（3段）、服装字段只抄不补规则、出图自检清单（5类核对）、保险多角色出图顺序建议、保险场景常见角色设定参考表
- [NEW] `batch_fission_playbook.md`：批量裂变操作手册，含8步完整流程（反解→定母版→定版本矩阵→定镜头方案→逐版本规划→共享校验→并发生成→合并交付）、6种裂变维度、版本矩阵模板、共享镜头判定规则与优化建议、R2V编辑/语义复刻分流选择建议、保险场景共享优化建议

### 修改
- [MOD] `narrative_arc.md`：新增旁白叙事型弧线（30秒4-5镜头模板）、回忆穿插型弧线（4镜头模板）、快问快答型弧线（10-11镜头模板）、道具状态链设计（设计原则+4个保险场景常用道具链示例）、信息目标驱动检查（3项自检规则）
- [MOD] `character_lock_protocol.md`：新增三步逐级传递出图流程引用（S1/S2/S3流程概述+与四视图设定稿的关系+验脸闸门自检+服装字段规则+多角色出图顺序建议）
- [MOD] `prompt_craft_guide.md`：新增电影级6大核心规则（专业风格术语/构图与镜头/光影/调色/视觉渲染/氛围与潜台词，含保险场景示例）、因果连续写法（错误/正确对照表）、蒙太奇连接写法（4种连接方式+现实/回忆区分写法）、旁白叙事型Prompt写法（声画分离原则+色调对比写法+道具情感锚点写法）
- [MOD] `quality_control.md`：新增阶段确认门机制（4个确认门+执行方式+权威来源与变更影响）、实体分离检查（5项检查+3条红线）、音频Preflight硬阻塞（2个校验时机+3种状态+失败处置）、批量裂变交付检查（版本对照表检查+共享片段一致性检查+裂变母版合规检查）
- [MOD] `index.md`：新增3个文件索引条目

### 融合来源
- story_short_film：阶段确认门、实体分离、音频preflight → quality_control.md
- ugc-jue-se-chu-tu-chan-xian：三步出图流程、验脸闸门、服装字段规则、出图自检 → character_asset_pipeline.md + character_lock_protocol.md
- cinematic-narrative-mv-pe：命题先行、道具状态链、信息目标、因果连续、蒙太奇、色调对比 → cinematic_narrative_tools.md + narrative_arc.md + prompt_craft_guide.md
- imitation_video + material_fission：R2V/语义复刻分流、母版定版、版本矩阵、共享镜头、批量并发 → batch_fission_playbook.md + quality_control.md

## v4.2.3 (2026-09-17) 第二批参考视频拆解融入

### 新增
- [NEW] `reference_video_analysis.md` 第十三节：9条新视频拆解，新增3种叙事模式（旁白叙事型/回忆穿插型/快问快答型），新增3种创作模板（模板G/H/I），新增色调对比叙事工具表、道具情感锚点表、产品植入时机3种新模式、旁白写法范例、各模式30秒镜头配置建议
- [NEW] `insurance_video_genres.md` 子品类D：旁白叙事型（含分镜模板/Prompt要点/回忆穿插变体/快问快答变体）

### 修改
- [MOD] `insurance_video_genres.md` 决策树：新增子品类D路由分支
- [MOD] `insurance_video_genres.md` 创作模板速查表：新增模板G/H/I
- [MOD] `insurance_video_genres.md` 底部引用：参考视频案例库描述更新为19条
- [MOD] `reference_video_analysis.md` 版本号：v1.0→v1.1

## v4.2.2 (2026-09-17) 穿搭审美能力融入

### 新增
- [NEW] `fashion-film-studio/references/industries/outfit-style-library.md` — 日常穿搭风格库：5大风格流派（韩系街拍/日系学院风/Y2K甜酷/森系清新/通勤休闲），每流派含色彩搭配逻辑、单品组合模式、配饰呼应规则、面料叠穿层次、氛围感关键词；跨风格通用审美逻辑（60-30-10配色法则、配饰呼应表、材质叠穿公式、氛围感四要素）；风格快速识别表；图片→Prompt转化规则（服装描述四维模型）

### 修改
- [MOD] `fashion-film-studio/SKILL.md` 路由表：新增 outfit-style-library.md 路由条目
- [MOD] `fashion-film-studio/references/INDEX.md`：新增 outfit-style-library 条目
- [MOD] `style_reference.md`：末尾新增「日常穿搭风格速查」板块（5风格×6维度表+穿搭描述四维模型+配色三原则）
- [MOD] `character_lock_protocol.md`：角色锁定卡「默认服装」字段从单行描述扩展为穿搭四维模型（色彩搭配/单品层次/配饰系统/氛围质感）
- [MOD] `index.md`：style_reference 描述追加「+日常穿搭风格速查」

## v4.2.1 (2026-09-17) 全量排查修复（图生视频提示词 + 其余文件）

### 图生视频提示词排查（6项）
- [MOD] `prompt_patterns.md`：对话剧情模式在单Prompt内写正反打（违反自身规则）→ 拆为两个独立镜头Prompt
- [MOD] `prompt_patterns.md`：一致性控制模式女儿出场但缺参考图 → 补充女儿参考图
- [MOD] `prompt_patterns.md`：旁白穿插模式角色无参考图 → 补参考图 + "无参考图改纯空镜"替代方案
- [MOD] `prompt_patterns.md`：产品讲解模式写手机屏幕特写（违反"禁止电子屏幕"质量约束）→ 改为纸质保单特写
- [MOD] `prompt_patterns.md`：口播/对话模式缺"不得自由发挥台词"约束 → 补充
- [MOD] `prompt_craft_guide.md` + `shot_logic_review.md`：空间锁定与互视轴规则适用边界冲突 → 双方文件均补充适用边界说明（口播用屏幕占位锁定；剧情对峙用互视轴）
- [MOD] 附带补充：手机道具"屏幕朝下"、extend段重复传角色参考图、首尾帧画幅一致性提示

### 其余文件排查（4项）
- [MOD] `scripts/skill_config.py`：SPEED字典补齐全部11个产品的语速条目（原仅6个，53408/52975/体验版/健康福/家财险缺失，靠模糊匹配兜底有隐患）
- [MOD] `core/error_handler.md`：E014 从"API Key额度超限/Key池轮转"改为"积分余额不足/check_credit_query确认"（与v4.2平台适配方向一致）
- [MOD] `scripts/batch_generate.py` + `scripts/image_to_video.py` + `scripts/skill_config.py`：文件头部加平台适配声明（外部BlueAI网关→平台工具映射说明，非API依赖配置仍可复用）
- [MOD] `knowledge/tts_optimization/voice_clone_tts.md` + `outputs/asset_management.md`：文件头部加平台适配声明（mega_tts→sandbox_generate_audio；vendor_asset_id→沙盒文件路径；真人版权合规要求仍适用）

## v4.2 (2026-09-17) 平台适配层补齐（查缺补漏）

### 新增
- [NEW] `core/platform_adapter.md` — 平台适配层：外部API→平台原生工具映射总表（火山ASR/mega_tts/BlueAI网关/BMC relay→sandbox_read/sandbox_generate_audio/sandbox_generate_video/sandbox_generate_image/render_video/check_credit_quote）；Key管理→积分管理；ASR降级矩阵（词级→句级→纯文本）；模型参数对齐（4-30s/多分辨率/素材上限）；render_video合成规范；字幕方案适配；扩展品类指引
- [NEW] `wf_edit.md` 保留式修改快速通道 — 用户对现有画面满意只做有界调整（换BGM/加字幕/删段/超分/擦字幕）不重生视频的快速通道；混合修改深度序增加保留式为最浅层
- [NEW] `wf_edit.md` 视频超分与擦字幕 — 平台 `sandbox_process_video` 原生能力接入（ToolName=video_super_resolution / erase_video_subtitle），含保险项目典型用法
- [NEW] `prompt_craft_guide.md` Prompt做减法原则 — 优先级排序+减法边界+保险特化硬约束
- [NEW] `prompt_craft_guide.md` 段数解耦规则 — 用户写的段数/每段秒数不决定总时长或调用次数+保险项目特例
- [NEW] `router.md` §4 用户交互规范 — 问卷效率约束（禁止连续>2轮追问/已确认不追问/不问字幕BGM）+下一步建议模板（4个关键节点）+确认门原则（花钱前门+≤2道门+跳过确认降级）
- [NEW] `meta/glossary.md` 面向用户术语转译表 — 25+内部术语→用户语映射+自检方法
- [NEW] `wf_edit.md` 段内区间局部编辑 — 单段直出视频/用户上传视频的中间时间段重做（ffmpeg切分→视频编辑→render_video拼接），多段项目走镜头级修改
- [NEW] `wf_generation.md` 成片BGM生成规范 — sandbox_generate_audio Type=music 生成统一音轨+歌词判定+节拍表写法+保险典型调性
- [NEW] `wf_generation.md` 成片状态账本 — 段顺序/字幕状态/BGM状态在每次重拼前必须完整继承
- [NEW] `prompt_craft_guide.md` 画面"可执行"深度自检表 — 四维（空间/表演/光影/音效）可执行级别对照+自检口诀+质感底料+镜头语言骨架
- [NEW] `quality_control.md` 关键帧辅助策略 — 尾帧作首帧/关键帧图片生成+衔接链重截判定

### 修改
- [MOD] `config_matrix.md`（v3.6→v3.7）：模型单段时长 20-30s→4-30s（平台实际下限）；Key池轮转→积分管理（check_credit_quote）；LLM relay→平台内置LLM；新增平台适配声明指向 platform_adapter.md
- [MOD] `wf_generation.md`：新增「成片合成规范 (render_video)」章节 — 合成参数表（video_paths/bgm/show_subtitle/storyboard_path/shot_ids/subtitle_scene/pipeline_name）+合成流程4步+与原ffmpeg链路差异对比表
- [MOD] `entry_brief_only.md`：Step 2.5 新增平台创意助手旁路（creative_agent可选加速）
- [MOD] `wf_storyboard.md`：新增 Step 0 分镜规划工具加速路径（generate_shot_video_prompt_plan）— 适用条件/使用方式/不适用条件
- [MOD] `README.md`：版本号 v4.1→v4.2；core目录增加 platform_adapter.md；router描述增加用户交互规范
- [MOD] `meta/glossary.md`：新增术语「保留式修改」
- [MOD] `character_lock_protocol.md`：新增音色锚定逐镜传参规则、用户原照例外、视觉锁定三类文字描述场景、单图不超4人、多形象共用身份锚点和音色文件

### 适配要点
- 模型名不硬编码，运行时以 `list_capabilities` 返回为准
- 素材上限以 `list_capabilities` 为准（Seedance 2.5: 图片≤30/视频≤10/音频≤10）
- ASR精度取决于平台能力，逐字稿格式不变但时间戳粒度按实际调整
- 警示语SRT仍需Agent手动生成（平台不识别保险警示语）
- 暗水印脚本在sandbox Python环境中运行，无需外部依赖

## v4.1 (2026-09-15) 逐字稿格式/路径/命名全库统一（消除矛盾）
> 承接 v4.0（subtitle_burnin 重写 + asr_processing 第10.5章「逐字稿导出」新增，当时未单独记录）；本次把全库对逐字稿的描述统一到一个标准。

**统一标准（唯一权威 = `knowledge/video_parameters/asr_processing.md` 第10.5章）**
- **格式**：SRT（每字一行，人看/播放器可加载）+ JSON（`[{"text":"字","start":0.32,"end":0.36}, ...]`，程序读取），两份缺一不可
- **路径**：`{项目}/{日期}/字幕/`（与口播字幕SRT同目录，**取消 `逐字稿/` 子目录**）
- **命名**：`{名称}_逐字稿.srt` + `{名称}_words.json`（交付目录带序号前缀）
- **来源**：ASR words 直出，**不经 LLM，不做任何断句/合并/纠错/加标点**
- **派生关系**：逐字稿是**唯一源头**，`逐字稿 → LLM断句 → 口播字幕SRT`；禁止二者各自独立从 ASR 生成两份

**逐文件修改**
- [MOD] `knowledge/video_parameters/asr_processing.md`（v3.4→**v4.1**）：第10.5章整章重写——旧 TAB 分隔 TXT 格式 + `逐字稿/` 目录**废弃**，改为 SRT+JSON 存 `字幕/`，补示例/编码规范/序号前缀/产物清单（必须4个 + 按需2个）；第2章流水线插入 **Step1.5 逐字稿导出**、Step7 改标"口播字幕SRT=逐字稿派生产物"+补「源头唯一」；第9章补前提；第10章补"审核文档内嵌的是加标点文本版、机器可读文件在 `字幕/`"；第12章红线新增 8/9 两条
- [MOD] `knowledge/video_parameters/subtitle_burnin.md`（v4.0→**v4.1**）：核心原则标明时间轴来源文件 `字幕/{名称}_words.json`；Step 2 输入格式由 TAB-TXT 改为 JSON（并注明人看版 SRT、程序一律读 JSON）；交付物表把旧 TXT 逐字稿行换成 `_逐字稿.srt` + `_words.json` 两行 + 统一存 `字幕/` 说明；异常表「逐字稿为空」补判定口径；红线新增第10条（时间轴只认逐字稿，禁止另取一份 ASR）
- [MOD] `outputs/intermediate_artifacts.md`：VERIFYING 中间产物 `asr_raw_{NN}.txt`(TXT) → `asr_words_{NN}.json`(JSON)，注明最终交付为 `字幕/` 的 SRT+JSON 两份；`clean_{NN}.srt` 改名"口播字幕（中间态）"并注明**由逐字稿派生**；清理规则指向 `字幕/` 交付版逐字稿
- [MOD] `outputs/delivery_standard.md`：交付物清单后新增「源头 ↔ 派生」原则块；目录结构示例 `字幕/` 补齐 `_逐字稿.srt`/`_words.json` 并把口播字幕文件名对齐清单（`{序号}_{名称}_口播字幕.srt`）；审核文档行/两份文档区别表标明"内嵌的是加标点文本版"；交付检查清单 +2 项；交付报告模板补逐字稿行
- [MOD] `workflows/wf_verification.md`：Step 1 输出补"直出落盘为逐字稿（`字幕/`）"；Step 2 改为"逐字稿 JSON → LLM 加标点/断句 → **派生**口播字幕，逐字稿本身不改写"；Step 5 抬头点明「源头 ↔ 派生」+ 统一目录；5a 补路径/编码/序号前缀/用途(烧录时间轴来源)/参考实现；5b 补"禁止另跑一次 ASR"+路径；审核文档行标明文本版
- [MOD] `workflows/wf_delivery.md`：前置条件补逐字稿（SRT+JSON）；目录树 `字幕/` 补 3 行（口播字幕/逐字稿SRT/words.json）并标注派生关系；`审核文档/` 注释改为"内嵌文本版，文件在 `字幕/`"；归档清理白名单「保留」项把 ASR逐字稿从 `审核文档/` **改到 `字幕/`**（原描述与交付标准矛盾）
- [MOD] `core/task_registry.md`：ASR_TRANS 输出补逐字稿 SRT+JSON；TEXT_CLEAN 输入=逐字稿 JSON、输出=口播字幕SRT 并注明派生关系（原 `Clean_Text_SRT` 含义不清）
- [MOD] `knowledge/video_parameters/config_matrix.md`（v3.5→**v3.6**）：「字幕SRT生成标准流程」Step 1 补"words 先直出落盘为逐字稿，2-8 步产出的口播字幕SRT 是逐字稿的派生产物（复用同一份 words，不另跑 ASR）"——此文档是 SRT 流程权威，不补会让读者以为口播字幕直接从 ASR 出
- [MOD] `meta/glossary.md`：新增术语「逐字稿」「口播字幕」，写明源头↔派生关系 + 文件名/路径/格式
- [MOD] `README.md`：总纲版本号 v3.5→**v4.1**；目录说明补"逐字稿导出SRT+JSON/口播字幕派生"；交付目录结构 `字幕/` 补注释（逐字稿+口播字幕+警示语同一目录）
- [MOD] `meta/_skill_revision_context.md`：新增逐字稿标准条目（防后续子代理修订回退到 TXT/独立目录）
- 验收：全库 grep 旧 TXT 逐字稿文件名（`_逐字稿` + `.txt`）= **0 结果**，旧 TAB 格式彻底清除；grep `逐字稿/` 仅剩"不另建 `逐字稿/` 子目录"的禁止性表述

## v3.5 (2026-09-14) 全量审查修复
- LLM默认模型 Evolving→2.0-mini
- 盲水印低码率分流（<3Mbps 固定4M+window50）
- 5个旧脚本语速/key/pypinyin 修复
- skill文档降级策略统一
- 新增 skill_config.py 参数中心
- 8产品合规规则更新（260908驳回报表）

## v3.4.1 - 2026-09-10（字幕烧录完整规范）
- [MOD] knowledge/video_parameters/subtitle_burnin.md 重写为完整《字幕烧录规范 subtitle_burn》：9章——烧录组合判定/口播42pt·警示语28pt样式/思源黑体(回退Noto Sans SC实测可用)/产品名品牌色/竖屏1/6布局/ASS模板BGRA逆序/CRF18音频copy/烧后校验/抖音微信平台适配/_burned双版本交付/8条红线
- [MOD] 逐字稿铁律：ASR词时间戳+LLM语义断句(用Doubao-Seed-2.0-mini，Evolving长文本超时)，**禁止本地机械切字**；字幕文本用atomic原文非ASR错字
- [MOD] wf_verification Step5 对齐新规范（42pt/Noto Sans/合并单ASS/_burned命名/双版本保留）；README目录描述更新


## v3.4 - 2026-09-10（补齐资产生成链路：生图/音色/资产管理 + 评审冲突订正）
### 新增
- [NEW] knowledge/video_parameters/image_generation.md — Seedream 生图规范（5.0-lite组图/pro图层分解选型、四视图/场景空镜/首帧、风格锚、按需reuse策略、人物3:4，执行API+Prompt工程）
- [NEW] knowledge/tts_optimization/voice_clone_tts.md — mega_tts 声音复刻（upload训练→S_ speaker_id→/v1/tts合成），区别于视频内generate_audio；发音修复/后期配音/方言资产化
- [NEW] outputs/asset_management.md — 资产管理API（URL↔vendor_asset_id、PixVerse/Gaga/volc/byteplus）+ byteplus真人LivenessFace活体认证流程
- [NEW] 主干状态 **ASSET_PREP**（STORYBOARD与READY之间，按需准备生图/音色/厂商资产ID，默认reuse快速通过）
### 修改
- [MOD] README v3.4 — 模型表加Seedream生图/mega_tts两行；主干流程+依赖图加ASSET_PREP；目录补3新文档
- [MOD] core/state_machine.md — 主干状态表+转移图+三路径图加 ASSET_PREP
- [MOD] templates/{creative_design_template,index,storyboard_template}.md、tts/fallback_strategies.md — 订正残留旧语速"好医保8字/秒、长钱保7字/秒"→7/6（config_matrix单点权威）
- [MOD] entry_brief_only.md — 前贴字数上限改为(目标时长−2s缓冲)×语速，避免填满上限生成超时
### 协调（交叉依赖）
- [X-REF] image_generation（生图）→ character_lock_protocol（逐镜传参）→ wf_storyboard 1d素材就绪门控
- [X-REF] voice_clone_tts ← wf_repair AUDIO_REPAIR升级链（修复失败时训练专属音色）
- [X-REF] asset_management ← ASSET_PREP（真人版权素材/给链接渠道）
### 端到端验证（好医保中老年脚本1，路径A走通）
- ✅ 警示语在SCRIPT_PARSE已剥离，190字打包对象不含警示语→不会截断（字幕层单独挂载）
- ✅ 分段点全在句读边界、内容守恒无半句、每段≤205字
- ✅ 每段prompt都重带完整@VOX卡（工具无状态逐段重传）
- ✅ 同音声调判定用pypinyin实测：保/宝、赔/陪、投/头、腺/线同音同调跳过；替/缇(ti4→ti2)声调错、节/肢异音正确报replace
- [FIX] **混合括号剥离缺陷**：客户原稿`(符合条件可投保）`开半闭全异体配对，旧正则按类型配对剥不干净、警示语残留被TTS念出→改为深度计数法（遇任意开括号+1/闭括号-1，不要求开闭同类型）；entry_direct格式容错已补；verify脚本diff接入pypinyin同音过滤，pip依赖记入config_matrix
- [MOD] wf_verification Step4 补"警示语泄漏检查以该产品atomic正文为基准、禁止跨产品套固定词表"——同句(80%/126种大病/三甲特需部)在少儿53408是口播台词(该念)、在中老年52973是括号警示语(只做字幕)，固定词表会误报；36条成片回查零真泄漏
### 评审冲突订正
- 冲突A单字跳过：wf_verification 已含"同音+声调同→跳过/声调异→replace"，全库无裸"单字跳过"残留（自洽）
- 冲突B语速：config_matrix 为唯一权威，4个模板文件旧值已统一
- 冲突C前贴上限：明确不含2s缓冲

## v3.3.1 - 2026-09-10（README 总纲导航完整性）
- README 升级 v3.3：补 _session/ 状态快照位置（snapshot/repair_log/voice/alignment_map/tts_validation_log）、新增 segmentation_packaging 与 06-Seed-Audio 目录
- 路由阈值统一指向 core/router.md（消除总纲50字 vs entry_mixed 20字的不一致）
- 模型表补分辨率/音频两列；前贴vs成片表补警示语SRT/WARN_MATCH/QC/产物目录4行
- 新增**原则0 合规优先**（FATAL/USER_INPUT_NEEDED 高于生成效率）+ 原则8 知识库版本化
- 新增 workflow 依赖图、品类扩展指引（保险→非保险的可复用/需替换模块）
- TTS规避词验证状态管理（待验证可用→ASR核对→移已验证/升删除级，记录tts_validation_log）
- knowledge 关键文件加版本头 `<!-- v3.3 | 2026-09-10 -->`；订正 pronunciation 残留"字数/8"为按语速
- meta/_skill_revision_context.md：跨文档修订共享标准（内部参考）

## v3.3 - 2026-09-10（全流程 skill 系统性补强，80条建议落地）
### Prompt 工程（prompt_craft_guide）
- 跨镜头一致性：参考图必须**每镜/每段 ImageList 重复传入**（工具无状态，不能只首镜传）
- 运镜补**起幅/落幅**（起始构图+运动时长+终止稳定停留），固定镜头明确"机位不动"
- 多人对话补**景别切换节奏**（说话方近景/听话方反应近景/情绪点双人中景，避免连镜同景同角）
- 光影补**时间段锚定**（时间+太阳高度角+色温+影长）
- 篇幅按镜头类型量化：纯动作120-200/单人台词200-300/多人对话300-400字
- 新增「首生成检查清单与失败兜底」表（变脸/丢台词/僵硬/闪烁/忽快忽慢/加戏/版权/跳切→原因→动作）
### 分段/时长（segmentation_packaging + 各workflow）
- 时长模型四类：A念词+B停顿(逗号0.3/句末0.6-0.8/角色切换1.0-1.3)+C动作(与台词共享不叠加，仅纯动作镜头单独给)+D段末1.5-2s（段首不留）
- extend 台词边界保护（句读处切、不切半句、超长句逗号收束）；首段第0秒即刻开口
- 纯动作镜头预算：establishing 2-3s/反应1.5-2s/转场1.5-3s，标注"动作预算"
### Workflow 全面补强
- **wf_storyboard**：Step1 拆 1a-1e 子步骤；入口路由；多场景冲突分组转场；校验分 P0/P1/P2 优先级+Prompt字数自检；修改三级分类
- **entry_brief**：补目标受众/混合类型；创意确认五要素；前贴字数上限(15s≈105/20s≈140)；产品专属缺失降级；确认三段式展示；多条一致性
- **entry_direct**：脚本格式容错；语速校验二次断句的数字保护回溯；多层命中取最严；利益点关键词清单；脚本编号规则；TTS空格不进字幕；推断场景确认；READY回退分级
- **entry_mixed**：片段覆盖范围判定；用户片段违规处理；补齐风格对齐+来源追溯标记【Brief补齐/险种模板补齐/合规补挂-N/语义推断补齐】；接缝展示；多条片段凑数；已有断句预处理；20字阈值来源
- **wf_creative_design**：意图分层提取；叙事结构时长匹配(15-20/30/60s弧线模板)；角色数量上限(2/3/4)；创意合规自检；确认展示分层；多脚本共用创意；版本管理；风格-弧线互斥校验
- **wf_generation**：纯动作镜头计入总时长；旁白穿插音色锚定；重试占原并发槽+模型不可用降级；extend任务记录task_id数组+费用求和；末帧管理；单镜重做降级判定(1次微调Prompt/2次降分辨率)
- **wf_delivery**：前贴/成片产物分目录；同名覆盖旧版入_历史版本+batch_id；日志跨日去重BATCH START；视频可播放性ffprobe闸门；+2s缓冲来源；SRT UTF-8无BOM/LF；回退分级；清理白名单
- **wf_edit**：混合修改取最深类型；边界模糊判定；KEEP/CHANGE接缝校验；台词改后时长重算；音量归一化(人声-16/BGM-24 LUFS侧链压低)；产物版本识别；未改部分回归校验；edit_reason/before-after_snapshot溯源
- **wf_repair**：参考音频质量(SNR≥15dB/无BGM/单人)；正确文本来源优先级；拼接crossfade+LUFS对齐+采样率声道一致；局部ASR复检；升级时间成本提示；换表达操作流程；error_position累计索引
- **wf_verification**：ASR置信度不达标处理；占位符清单；同音异形拼音判定(声调不同算错)；insert/delete粒度分级；警示语模糊匹配容错；SRT完整格式规范；多SRT时间轴布局；人工审核按风险分级(自动通过/低风险/高风险)
- 全部文档订正过时语速"好医保8字/秒"→统一7字/秒

## v3.2 - 2026-09-10
### 分段打包（核心）
- 新增 `knowledge/video_parameters/segmentation_packaging.md`：**句子流均匀打包算法**——拍平(角色,句子)流、句读边界切、目标190字/硬上限205字(7字/秒)、duration按台词取10/15/20/25/30五秒档、短段给10s不硬撑、消除尾部空洞、场景边界强制切段、extend承接提示
- 废止旧"30s+30s"和"每镜头固定+2.5s动作预算"（实测堆空洞导致忽快忽慢/一顿一顿）；config_matrix 与 prompt_craft_guide 同步改指向新算法
- **时长预算精确化（v3.2.1）**：
  - 停顿按标点/角色类型化，不固定0.5s——逗号0.3s、句末0.6-0.8s、**角色切换1.0-1.3s**（长对白累积）
  - **动作时间与台词时间共享、不叠加**（边做边说不加时）；只有纯动作/无台词镜头才单独给1.5-3s
  - 缓冲只放段末1.5-2s，段首不留
- **Extend 两种承接模式**：同角色承接("接着说") vs 换角色承接("B听完A最后一句立刻回应")；**首段第0秒即刻开口**（否则先2-3秒空镜）
- 新增"防模型自由发挥"：Prompt 禁加戏 + VERIFYING 用 ASR总字数对照期望（字数显著多=插入/重复，重做）
### 多版本 / 方言 / 失败处理
- config_matrix 新增**多版本矩阵**（一脚本×3普通话+四川话+东北话，同台词只改@VOX口音维度）、方言ASR以人工听感为准
- 明确 Seedance `copyright restrictions` 多为**随机撞库误判**，断点续跑+换key/种子重试，勿误判为内容违规
### Prompt / 发音 / 医疗题材
- prompt_craft_guide 新增"医疗题材两模式"：默认禁医生 vs 医生剧情向(只诊断不碰保险)；血氧=指夹探头+SpO₂波形（非心电图ECG）；孩子表现克制
- 发音：CAR-T 整体读"卡替"不逐字母，ICU/CT 才逐字母（pronunciation_rules）
- 语速表订正：好医保系列(中老年/门诊险/少儿)统一7字/秒、长钱保6字/秒
- 归档 `06-Seed-Audio声音工程与音频驱动系统.md`；台词分层明确"声画一体台词随镜头 vs 音频先行才分离"两模式边界；新增六维音色VOX LOCK章节
### 暗水印
- 暗水印编号追踪规范 v1.1：低码率AI片源(<3Mbps)固定CBR 4M+window50（CBR×1.2会压没d1=10水印）；ffprobe路径bug与子进程隔离工程坑

## v3.1 - 2026-09-03
### 修复（深度审查 P0/P1/P2）
- **主干流程图三处不一致** → 统一到 state_machine 为唯一权威（README/router 补 PLANNING 并加权威指向）
- **READY 门**误引用生成后"审核文档" → 改"脚本标注文档"，三处确认清单对齐
- **VERIFYING DIFF 基准**从原始脚本改为原子脚本(期望朗读文本 expected_readback_text)，消除含"(2026版)"产品的无限重生；DIFF 取纠错前 ASR
- **insert/delete** 补 VIDEO_REDO 落点；**repair** 补退出升级链(AUDIO_REPAIR×3→VIDEO_REDO×2→换脚本→FATAL)+retry_counters 跨断点持久
- **合规索引** trigger_conditions/rules.md 接线到 COMPLIANCE_CHECK；**绝对化词**自动替换降为"标记+建议"+官方话术白名单
- **产品文件订正**：45750 主体倒置、52975"蚂蚁数保"→蚂蚁保代理销售（余项压底版本/条款名/保费"起"待甲方）
- **zip** 旧快照封存声明；**家财险**层2空缺补 `险种专项/家财险-合规要求.md` 强制人工复核
- 路径B补SCRIPT_PARSE；路径C/EDIT进状态机；补交付物(原始脚本.csv/_视频日志.csv)生产者；E014对齐error_handler；QC时长口径含+2s缓冲；AUDIO_ANCHOR优先级判定表+重试3次；数字/方言读法规则；fallback策略4改用户确认；暗水印注册WATERMARK_EMBED+编号加产品ID(HYB52973)；index.md重建
### 修正（一致性）
- 异常码计数笔误：v3.0 记"16个"实为15个(E001-E015)
- "四层/三层"术语统一为**三层合规**；README"三种路由"应为四种(A/B/C/EDIT)
- 产物命名归一(voice_{role}.mp3/{序号}_{名称}_fixed.mp4)；_task_ids.jsonl schema 以 task_registry §10 为唯一权威
- config_matrix 历史遗留 Prompt 段(含旧两分支路由)**整段删除**，Prompt 规范统一指向 prompt_craft_guide；旧四层架构 `第四层_产品专属.zip` 已移除、文档删除对其引用（三层合规无第四层）；glossary 补前贴/成片/PLANNING/SKIP/原子化等术语

## v3.0 - 2026-09-02
### 修复（执行链路断链）
- 路径A分镜断链：entry_direct_script 增加分镜步骤，wf_storyboard 支持路径A模式（基于原子脚本列表，不依赖 creative_design.md），state_machine 修正 STORYBOARD 进入条件
- E001 超时策略：从"延迟重试"改为"首次超时切换 extend 模式，extend 仍失败再退避重试"
- 前贴 WARN_MATCH 误触发：state_machine VERIFYING 退出条件区分前贴/成片，wf_verification 增加前贴跳过逻辑
- AUDIO_ANCHOR 接入：wf_generation 新增 Step 3 音色锚定（条件触发，多角色场景，失败不阻断）
- EDIT 路由：新建 wf_edit.md（5级修改类型判定），router 从不存在的 review/post-delivery.md 修正为 wf_edit.md

### 重构（状态机与异常体系）
- state_machine：主干新增 PLANNING 状态（脚本解析/撰写+原子化+合规校验），路径A/B均经过 PLANNING 后进入 STORYBOARD；明确 READY 为固定生成前确认门
- error_handler：异常码从4个补全到15个（E001-E015，新增 E002/E004/E005/E006/E008/E009/E010/E011/E012/E014/E015），覆盖视频生成、ASR、音频修复、ffmpeg、合规、拼接、归档、脚本解析、音色锚定、Key超限、分镜失败

### 修正（文件间不一致）
- router STEP 0：增加脚本完整性判定，完整脚本+简单需求不再误判为路径C
- entry_brief_only：前贴合规从"校验1-3层"统一为"三层全读（禁用表述）"；明确用户确认节点与状态机对齐（PLANNING确认→STORYBOARD确认→READY确认）
- wf_generation：extend 模式补充超60s多段方案；增加 Key 轮转逻辑和动态并发调度策略；硬编码路径加注释
- entry_mixed：从3步概要扩展为完整4步流程，明确引用 entry_direct_script 的原子化/合规/分镜步骤
- task_registry：STORYBOARD 增加异常映射 E015；DELIVERING 新增 BATCH_LOG 任务
- intermediate_artifacts：新增"恢复校验"章节，定义断点恢复时的中间产物有效性检查
- delivery_standard：新增前贴 vs 成片交付物差异表；前贴不生成警示语SRT和脚本标注文档
- entry_direct_script：前贴第三层（产品专属）规则缺失时从"阻断"降级为"警告+记录，不阻断"
- wf_verification："镇度比"笔误修正为"置信度"；补充压底/末尾字幕生成说明

### 更新
- README.md：目录结构新增 wf_edit.md
- README 版本号从 v2.1 同步为 v3.0

## v2.1 - 2026-08-28
### 新增
- workflows/wf_creative_design.md: 创意设计工作流
- workflows/wf_storyboard.md: 分镜规划工作流
- workflows/entry_mixed.md: 混合输入路径C
- core/error_handler.md: 统一异常处理(含SKIP等级)
- knowledge/templates/: 创意/分镜/通知模板库
- outputs/intermediate_artifacts.md: 中间产物规范
### 重构
- 目录结构重组与命名对齐(wf_ 前缀)
- state_machine.md: 升级为四层模型(主干/子/分支/暂停)
- task_registry.md: 增加创意设计/分镜阶段及重试属性
- router.md: 增加混合输入路由
### 更新
- README.md: 目录结构更新
