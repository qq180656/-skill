# 架构变更记录

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
