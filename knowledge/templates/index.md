# 输出模板库 (Templates Index)

## 模板文件索引（本目录实际文件 + 消费方）

| 模板文件 | 用途 | 消费工作流/状态 |
|---------|------|----------------|
| `creative_design_template.md` | 创意设计文档格式 | wf_creative_design（CREATIVE_DESIGN） |
| `narrative_arc.md` | 故事弧线与节奏（弧线模板+钩子+镜头语言） | wf_creative_design / wf_storyboard |
| `character_lock_protocol.md` | 角色锁定协议（四视图+多角色引用） | wf_creative_design / wf_storyboard（STORYBOARD）→ wf_generation 素材绑定 |
| `storyboard_template.md` | 分镜表格式 | wf_storyboard（STORYBOARD） |
| `prompt_craft_guide.md` | Prompt 编写指南（分层结构+运镜指令表） | wf_storyboard / wf_generation（Prompt构造） |
| `style_reference.md` | 风格速查表（艺术风格+文化美学+情绪参数+日常穿搭风格速查） | wf_creative_design（选风格） |
| `quality_control.md` | 出片自检清单 + KEEP/CHANGE 修改协议 | wf_delivery（QC）/ wf_edit / wf_correction |
| `opening_hooks_library.md` | 开场方式库（40+种，画面描述+写法要点+Prompt示例+避坑） | wf_creative_design（开场选型） |
| `reference_video_analysis.md` | 参考视频拆解案例库（19条优质保险视频逐帧拆解，含6种对话型Hook+3种旁白叙事型模式、5层信息递进、9套创作模板） | wf_creative_design（场景/角色选型）/ wf_storyboard（镜头调度参考） |
| `broll_skills/broll_scene.md` | 空镜6大类型+12种玩法+各体裁空镜配比（通用） | wf_storyboard / wf_generation（按场景加载） |
| `broll_skills/family_daily_broll.md` | 家庭日常空镜（不拍"生病"拍"力不从心"的微动作信号） | wf_storyboard / wf_generation（家庭场景） |
| `broll_skills/hospital_broll.md` | 医院场景空镜（6大可拍区域+合规红线+安全替代） | wf_storyboard / wf_generation（医疗场景） |
| `broll_skills/landmark_scene.md` | 地标/著名景点/航拍/FPV/延时定场空镜 | wf_storyboard / wf_generation（地标场景） |
| `cinematic_narrative_tools.md` | 电影化叙事工具箱（命题先行/道具状态链/信息目标驱动/因果连续/蒙太奇连接/色调对比叙事） | wf_creative_design（命题与叙事设计）/ wf_storyboard（因果与蒙太奇写法）/ wf_generation（色调与旁白写法） |
| `character_asset_pipeline.md` | 角色资产产线（S1验脸→S2面部四视图→S3全身四视图逐级传递出图+自检） | wf_creative_design / wf_generation（角色资产生成） |
| `batch_fission_playbook.md` | 批量裂变操作手册（母版定版→版本矩阵→共享镜头→批量并发生成→按版本交付） | wf_creative_design / wf_generation / wf_delivery（多版本批量场景） |
| `narrative_archetypes.md` | 保险叙事原型库（产品5种角色+四大险种叙事原型+七拍/十拍节拍表+Logline公式+人物弧光+可证伪测试） | wf_creative_design（创意选型/剧本结构） |
| `visual_style_system.md` | 视觉风格系统（风格配方速选+色彩命题+60:30:10配色+四大险种12色方案+五子层光影量化+风格签名串） | wf_creative_design / wf_storyboard（视觉设计/光影配色） |
| `director_shot_toolkit.md` | 导演镜头技法库（6种核心技法+构图关系压力+对方存在证据+动作闭环四拍+多镜切镜+运镜转场词库） | wf_storyboard（镜头设计/分镜规划） |
| `multi_character_layout_spec.md` | 多角色布局控制方案（空间占位符+角色/场景解耦引用，解决多角色镜头中角色融合/变脸问题） | wf_storyboard / wf_generation（多角色镜头布局） |
| `visual_anchor_spec.md` | 视觉锚点描述集（接缝校验执行层：生成前锚点描述注入→生成后描述级比对→不一致时补偿策略矩阵） | wf_edit（KEEP/CHANGE 接缝校验） |
| `prompt_patterns.md` | 常见场景 Prompt 模式库（保险视频常见场景的可套用 Prompt 骨架，prompt_craft_guide.md 配套示例册） | wf_storyboard / wf_generation（Prompt 构造参考） |
| `shot_logic_review.md` | 镜头逻辑自审（场景状态表+单段/多段镜头间连续性自审，检查角色位置/银幕侧/朝向/注视轴/对峙互视轴） | wf_storyboard / wf_verification（镜头逻辑校验） |
| `0902客供批成片问题复盘与分镜规范升级.md` | 成片实测问题复盘（硬切/台词切点/伤病状态丢）→ 切镜铁律+场景切换决策表+跟随/多人/伤病锚规范+LLM语义审查SOP的溯源文档 | 全流程（防复发SOP，新批次必读） |
| `insurance_video_genres.md` | 保险视频子品类创意体裁模板（产品讲解型/场景叙事型/专家背书型三大子品类的创意设计指引和分镜模板） | wf_creative_design（子品类创意选型） |
| `multi_scene_director/` | 多人场景执行引导技能（2+说话角色时强制走多人规范，含街采/对话/群戏场景模板、多人Prompt骨架、人物关系校验门拦） | wf_storyboard / wf_generation（多人场景分镜与生成） |
| `shot_language_guide.md` | 镜头语言速查（9种核心镜头:反打/过肩/主观/鸟瞰/双人/牛仔/全身/反应/插入——使用场景+创作意图+Prompt写法+保险场景组合速查表） | wf_storyboard（镜头选型）/ wf_creative_design（分镜设计参考） |

> ⚠️ 下方 `script_template` / `asr_report_template` / `user_notify_template` 为**内联输出模板**（本文件内嵌，非独立 .md 文件），分别供 SCRIPT_PARSE 结构化输出 / VERIFYING 校验报告 / 用户交互通知 使用。


## script_template.md
# 脚本解析标准化输出模板

## 输出格式
脚本解析完成后必须输出以下结构化对象:

```json
{
  "project_name": "好医保中老年长期医疗2026",
  "video_type": "前贴或成片",
  "total_scripts": 3,
  "scripts": [
    {
      "script_id": "001",
      "scene_desc": "场景描述",
      "speaker_count": 1,
      "segments": [
        {"text": "口播正文", "warning": null},
        {"text": "涉及0免赔", "warning": "本产品为0免赔额..."}
      ]
    }
  ]
}
```

### 字段说明
| 字段 | 类型 | 说明 |
|------|------|------|
| project_name | string | 项目全称，与产品专属文件名一致 |
| video_type | string | "前贴"或"成片" |
| total_scripts | number | 脚本总条数 |
| script_id | string | 脚本编号，三位数字（001/002...） |
| scene_desc | string | 场景简要描述 |
| speaker_count | number | 说话人数 |
| segments | array | 原子句列表，每句包含text和warning |
| segments[].text | string | 口播正文（已TTS优化，问题词加空格） |
| segments[].warning | string/null | 该句触发的警示语，无则null |


## asr_report_template.md
# ASR校验报告模板

## 报告结构

### 1. 基本信息
| 字段 | 值 |
|------|-----|
| 项目名 | {产品全称} |
| 视频ID/序号 | {序号}_{名称} |
| 视频时长 | {N}秒 |
| ASR识别耗时 | {N}秒 |
| 识别模型 | {模型名称} |

### 2. 发音差异列表
| 序号 | 原文 | ASR识别 | 差异类型 | 时间轴 | 状态 |
|------|------|---------|----------|--------|------|
| 1 | 免赔额 | 领口 | REPLACE | 00:03-00:05 | 待修复 |
| 2 | 符合条件 | 个头条件 | REPLACE | 00:08-00:10 | 待修复 |

> 差异类型：REPLACE（念错词）/ INSERT（多念）/ DELETE（漏念）/ SKIP（可接受差异）

### 3. 警示语挂载状态
| 触发句 | 警示语 | 挂载时间轴 | 状态 |
|--------|--------|------------|------|
| 0免赔额 | （一般医疗2万免赔额...） | 00:05-00:08 | ✅ 已挂载 |
| 100%报销 | （责任内最高100%比例报销） | 00:12-00:15 | ❌ 缺失 |

### 4. 整体评估
| 指标 | 值 |
|------|-----|
| 发音准确率 | {N}%（正确字数/总字数） |
| 警示语完整率 | {N}/{N}（已挂载/应挂载） |
| 需修复发音问题 | {N}处 |
| 建议 | {修复建议或确认可交付} |


## user_notify_template.md
# 用户交互通知模板

## 确认类通知

### 脚本确认
```
脚本已生成完成，共 {N} 条。

【脚本内容摘要】
- 项目：{产品名}
- 类型：{前贴/成片}
- 总时长：约 {N} 秒
- 语速：{好医保系列7字/秒 | 长钱保6字/秒}

【合规校验结果】
- 通用合规：✅ 通过 / ❌ {问题数}处
- 险种专项：✅ 通过 / ❌ {问题数}处
- 产品专属：✅ 通过 / ❌ {问题数}处
- 警示语挂载：{N}条已挂载

请确认后开始生成视频，或告诉我需要修改的地方。
```

### 交付确认
```
视频已生成完成，请确认以下产物：

【交付文件清单】
- 裸视频：{N} 条（{总时长}秒）
- 口播字幕SRT：{N} 条
- 警示语SRT：{N} 条（成片）
- 审核文档：{N} 份
- 批量日志：1份

【质检结果】
- 文件完整性：✅
- 字幕对齐：✅
- 发音准确率：{N}%
- 合规校验：✅ 通过

请确认完成交付，或告诉我需要调整的地方。
```

## 异常通知

### 合规异常
```
脚本中检测到以下合规问题：

【问题列表】
1. {问题描述}（{层级}：{具体规则}）
   - 建议替换：{替换方案}
2. ...

请确认替换方案，或自行修改后回复。
```

### 生成失败
```
第 {N} 个镜头生成失败，已重试 {N} 次。

【失败原因】
{错误信息}

【已完成镜头】
- 已完成：{N}/{N} 条
- 失败：{序号列表}

建议：修改该镜头脚本 / 更换参数 / 跳过该镜头。
请告知处理方式。
```

### 发音修复失败
```
第 {N} 个镜头发音修复已尝试 {N} 次仍未通过。

【问题词】
- {问题词}：ASR识别为"{错误发音}"（应为"{正确发音}"）

【已尝试策略】
1. {策略1}
2. {策略2}
3. {策略3}

建议：修改脚本表达（替换为同义词）/ 接受当前发音 / 重新生成该镜头。
请告知处理方式。
```

