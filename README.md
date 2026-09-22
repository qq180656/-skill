# 保险行业AI视频批量生产规范 v4.4

> 保险行业 AI 视频批量生产的端到端执行规范:路由 → 三层合规 → 创意/分镜 → 生成 → 校验 → 交付。作为 Claude Code skill 使用(入口 `~/.claude/skills/ai-video-production/`,细节按需 Read 本库对应文件)。

## 能力边界(诚实声明)

> 区分「脚本能保证的」与「模型可能翻车的」,不承诺未覆盖的能力。

| ✅ 规范/脚本能保证 | ⚠️ 依赖模型、可能翻车(只能降概率,不能 100% 避免) |
|---|---|
| 流程不跳步(状态门/Pre-flight 强制) | 画面崩坏/崩脸/黑帧(模型随机性) |
| 台词逐字保真(`fidelity_diff.py` 机检) | 生成的文字乱码(英文/中文错字)——故画面不写字、后期烧录 |
| 三层合规逐层 Read(已读证据) | 字幕约束失效(写了"无字幕"仍可能出) |
| 参数/duration 按公式计算 | 版权随机撞库(换 Key+种子重试可解) |
| 参考图逐镜重复传(工具无状态) | 眼睛异常发光/过度风格化 |
| 产物目录/命名/台账确定 | 音频水波纹噪声 |
| 断点快照与会话恢复 | 利益点语速被模型暗自加快(靠 ASR 复检兜) |

- 左列是**工程可控**——出问题=脚本/规范 bug,必须修。
- 右列是**模型固有不确定性**——Prompt 技巧只降概率;这些项一律进 VERIFYING 的 ASR/抽帧复检,不假设一次过。
- 本体系**无代码状态机引擎**,断点/snapshot 靠会话维护到 `_session/`。

## 目录结构

```
core/         路由与状态机
  router.md            路由判定(A完整脚本 / B Brief / C混合 / EDIT)
  state_machine.md     状态主干与不可跳过门
  error_handler.md     异常分级与处理
  task_registry.md     任务 / 进度登记
  platform_adapter.md  平台适配层(Key / 网关 / 端点)
workflows/    各阶段工作流
  entry_*.md           四种入口(direct_script / brief_only / mixed / edit)
  wf_creative_design · storyboard · generation · verification · delivery · repair.md
knowledge/
  compliance/          三层合规(通用规则 / 险种专项 / 产品专属拒审点)
  templates/           创意与分镜模板(prompt_craft_guide / multi_scene_director /
                       broll_skills / 导演分镜工具箱 / 叙事原型 / 视觉风格系统 …)
  tts_optimization/    发音 · TTS · 断句规则
  video_parameters/    模型参数 / 字幕烧录 / ASR / 分段打包
scripts/      可执行工具
  skill_config.py      参数中心(Key 走环境变量)
  atomize_script.py    脚本原子化(去括号/删词/注空格/计时长)→atomic_scripts.json
  gen_character_sheets.py  角色四视图批量生图(配置JSON驱动,16:9,无痣)
  image_to_video.py    生图 → 图生视频 / 多模态参考生视频
  batch_generate.py    批量生成引擎
  fidelity_diff.py     台词保真硬门(分镜/任务台词 vs 原子稿逐字diff)
  storyboard_review.py 分镜LLM语义审查(台词-画面矛盾/伤病锚/时间线/蜡像听者)
  gate_verify.py / pre_compliance_check.py   合规门 / 分镜前预合规校验
  validate_storyboard.py / count_chars.py    分镜验算 / 台词耗时预计算
  blind_watermark_video.py / blind_watermark_util.py  盲水印(视频/图片)
  replace_section.py   分镜md按shot整段替换/删除；auto_repair.py 发音修复(依赖缺失,见已知问题)
meta/         changelog / glossary / 修订上下文
outputs/      交付标准 / 资产管理 / 暗水印编号规范
```

> ⚠️ 密钥不入库:`scripts/skill_config.py` 从环境变量 `BLUEAI_GW_KEYS` / `BLUEAI_LLM_KEYS` 读取(逗号分隔),格式见 `.env.example`;本机用 `setx` 设一次。

## 规范变更后必跑校验

> 任何 .md 文档/文件结构改动后、提交前,跑结构校验(类比单测):

```powershell
python scripts/validate_docs.py --strict
```

四项自动检查:①孤儿文件 ②悬空引用/断链 ③产品三方一致(skill_config↔产品专属↔trigger映射)④硬编码个人路径。**有 ERROR 必须先修**;WARN 需确认是否有意。

## 变更日志 (Changelog)

### [v4.2] - 2026-09-17
**本次更新：完成第三轮深度查缺补漏（P1-1 至 P2-4）**

#### 1. 创意与 Prompt 增强 (P1 系列)
- ✅ **P1-1 台词/旁白语音规则**：在 `prompt_craft_guide.md` 补充了口型驱动句式、台词节奏分档、`count_chars` 耗时预计算、音色锚定引用语法。
- ✅ **P1-2 镜头逻辑自审**：新建 `shot_logic_review.md`，包含场景状态表（12项）与镜头冲突拦截项（13项），支持保险场景特化检查。
- ✅ **P1-3 场景 Prompt 模式库**：新建 `prompt_patterns.md`，提供一致性控制、口播直述、对话剧情、旁白穿插、产品讲解、视频延长、首帧锁定等模版。

#### 2. 生产流程与工具适配 (P2 系列)
- ✅ **P2-1 风格锚定预置图引用**：在 `style_reference.md` 建立平台原生 `creative/anchors/` 预置图映射表，支持直接引用跳过风格图生成。
- ✅ **P2-2 保险视频子品类模版**：新建 `insurance_video_genres.md`，提供产品讲解型、生活场景剧情型、前贴引子型三大细分类别的创意指引与分镜模版。
- ✅ **P2-3 台词耗时预计算工具**：将平台原生 `count_chars.py` 接入技能目录 `scripts/`。
- ✅ **P2-4 分镜验算工具**：将平台原生 `validate_storyboard.py` 接入技能目录 `scripts/`。

---

### [v4.1] - 历史记录
- 完成第一轮查缺补漏（P0/P1/P2 共 10 项），涵盖平台适配层、模型参数、成片合成、创意助手对接、分镜工具加速、Prompt 减法、段数解耦、保留式修改、视频超分/擦字幕、术语转译等。

### [v4.0] - 初始版本
- 初始技能规范构建，建立基础 workflow 框架。
