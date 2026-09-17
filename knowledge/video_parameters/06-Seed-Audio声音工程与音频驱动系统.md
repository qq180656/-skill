<!-- v3.3 | 2026-09-10 -->
# 06-Seed Audio 声音工程与音频驱动系统 (Audio-Driven Engineering)

> 即梦 Seedance 2.5 专属指南 · 六引擎体系 E5(声音工程引擎)+E1(叙事与导演引擎)
> 归档日期：2026-09-09

核心设计理念：
"声音先行，画面跟随"。基于字节跳动 Seed Audio 1.0 音频模型，先生成高质量 24kHz/WAV 音频轨与 100ms 时间轴分镜，再驱动 Seedance 2.5 生成高精度的同步动作与电影分镜。
归属引擎：声音工程引擎 (E5) + 叙事与导演引擎 (E1)（六引擎体系见 references/10）
用户声音资产：用户上传的声音样本按 references/11 锚定为 @CharID_AUDIO_XX（如 @CharID_AUDIO_唐末），与六维音色 + VOX LOCK 结合锁定。

## 一、音频驱动视频生成 6 阶段流水线 (6-Stage Pipeline)

- Stage 1: SD 剧本与声音设计（六维声学建模）
- Stage 2: AE Seed Audio 生成（24kHz/WAV 音频）
- Stage 3: VA 资产强锁定（Identity Board）
- Stage 4: DP 音频驱动分镜蓝图
- Stage 5: KD Seedance 2.5 批次视频生成
- Stage 6: CE 剪辑声画合成（Oscar 80分质检）

## 二、黄金六维音色建模 (6-Dimensional Voice Modeling)

生成配音或音色锁 (@VOX_[名称]) 时，必须包含以下 6 个声学维度：

1. **音域与声部 (Pitch & Register)**：如"低沉干涩男低音"、"清脆高亢少女声"。
2. **语速与节奏 (Speed & Rhythm)**：如"每分钟 120 字，语速缓慢，带有重音微停顿"。
3. **口音与方言 (Accent & Dialect)**：如"带有一丝高原藏区口音的硬朗腔调"。
4. **语气与情绪基调 (Tone & Mood)**：如"克制隐忍、带有一丝疲惫与绝望的潜台词"。
5. **呼吸与微发音 (Breath & Micro-Articulation)**：如"句尾带有明显的吸气声与咽唾沫声"。
6. **录音空间混响 (Room Acoustic Reverb)**：如"石砌封闭地下室的冷酷回声 (Reverb time 1.2s)"。

## 三、五层环境音效架构 (L1–L5 Sound Layers)

- **L1 物理碰撞层 (Physical Impact)**：脚步踩踏碎石声、刀剑交锋撞击声、桌椅倒地破裂声。
- **L2 衣物与质感层 (Friction)**：粗羊毛外套摩擦声、皮革手套握紧声、铠甲金属碰撞声。
- **L3 人体生理音层 (Physiological)**：粗重呼吸声、急促喘息声、心跳声、咽唾沫声。
- **L4 空间环境底噪层 (Room Tone & Atmosphere)**：穿孔风声、暴雨击打窗户声、远处偶发低沉雷鸣。
- **L5 叙事声桥层 (Sound Bridges & Edits)**：J-cut 下一镜音效提前渗入、L-cut 本镜环境音延续至下一镜。

## 四、100ms 时间轴卡点与对白隔离

TIMELINE AUDIO MAP (24kHz WAV Sync) 示例：
```
[00:00.000 - 00:01.200] L4 空间底噪：风吹废墟空旷呼啸声 (-18dB)。
[00:01.200 - 00:01.800] L1 物理音：角色碎石踩踏脚步声 (1.2s 爆点卡点)。
[00:01.800 - 00:03.500] @VOX_罗科 台词："他们已经跨过拱门了。" (带有 0.2s 句前吸气音)。
[00:03.500 - 00:04.000] L3 物理音：下巴咬紧喘息声与碎石散落声。
```

### 无 BGM 铁律 (No Music Rule)

在 Seedance 2.5 生成视频阶段，提示词中绝对禁止包含 BGM 描述。
- 所有音乐统一留在后期剪辑软件（剪映、PR、FCPX）中与画面蒙太奇强卡点铺设。
- 视频 Prompt AUDIO 模块必须统一加入：`Environmental SFX only. No music. No subtitles.`

## 五、声音锁定与压测 (Voice Lock & Stress Test)

吸收自 Hell Grind 制作简报 (The voice is not an asset)。

- **声音不是资产**：Seedance 在每个角色的同一种语调内持有 3-4 种声音——足够一部长片，但前提是你管理声音。
- **前期锁定 (Lock in Pre-Production)**：在对话开始前锁定每个主角的声音——音域、语速、口音、举止。声音提示词逐字粘贴进音频栏，每次该角色开口都用，永不修改。
- **VOX LOCK 跨镜一致性锁定（六维音色 + 用户声音资产双轨）**：
  - `VOX LOCK: [角色名] 声音 = "低沉干涩"（六维音色描述）`
  - 同一角色在 [争吵/突变] 场景下：语气词变化 + 声调升高，但音色指纹不变
  - 用户声音样本：@CharID_AUDIO_XX 逐字锚定，全项目不漂移
- **声音压测 (Voice Stress Test)**：与外貌压测同样方式测试声音跨代保持——10 次生成声音是否可辨；若漂移，回头把措辞锁得更死。

**Voice Prompt 公式（1-2 句，引号内）：**
> "A [age]-year-old [origin / accent descriptor]. [Timbre and register]; [pace and delivery manner]; [emotional character — and how it shifts under pressure]."

例："A 60-year-old ex-boxer and night-cab driver, working-class city accent. Low, hoarse, unhurried baritone; short flat economical sentences with long comfortable pauses; calm and faintly amused, going quieter — never louder — as things get serious."

## 五·五、同期声锁 (Diegetic-Sound Lock — 图生视频默认)

图生视频/视频生成提示词中，音频块默认只生成同期声（台词/音效/声音特效），不生成音乐。除非用户显式要求配乐。

- **锁句（写入 AUDIO 块）**：`SFX only. No music. No BGM. Environmental SFX and dialogue only.`
- 原因：① 模型自生成音乐会与后期配乐冲突；② 音乐铺底会掩盖对白清晰度与音效卡点；③ 用户需求明确"图生视频提示词里设定不要生成音乐，只生成同期声"。
- **例外**：用户显式要求"本片需要配乐/背景音乐"时，才允许在提示词中描述音乐，且仍建议后期铺设。
- **静音生成**：若需后期自行配音，使用负向词"禁止生成任何背景音乐，静音生成"。

## 六、对白构建四要素与混音规则 (Dialogue Construction & Mixing)

- **对白四要素公式**：声音+情绪 → 引号台词 → 物理动作 → 面部反应。台词只住在 AUDIO 区块，动作与台词永不混写（详见 references/04 §五）。
- **台词唯一铁律 (Only-the-Line Rule)**：everyone speaks ONLY the line in quotes; whoever has no line stays completely silent; a "half-laugh" written in the action is a facial expression, with no sound.
- **混音规则 (The Mix)**：人声干净近麦、环境音垫底、说话时环境音自动压低 (ambience ducks under dialogue)。
- **罕见人名附音标转写**：否则模型会读破名字。

### 剪辑缝技巧 (Seam Tricks)

- 对白宽镜中，把上一镜台词尾音喂入提示词——帮助唇形与节奏。
- 每个新生成用上一镜收尾那句开头——情绪随文本一起跨过接缝。
- **前后静默**：干净对白需要每句台词前后 ≥1 秒环境静默；若需立即开口，`line begins within the first 0.3 seconds`。
- **先前音频上下文**：只需情绪连续性时写 `Prior audio context only, not visual content: "line."`——不要把先前音频中的人/物可视化为本镜内容（除非本镜激活）。

## 七、后期声画处理 (Post-Production Audio)

- **不重录音**：Seedance 唇形同步台词直接从生成结果中清理——降噪、拉平片段间音色、把声音放进空间里；只有片段完全无可用人声时才进棚补录。
- **连续环境底噪 (Continuous Ambience)**：后期用一条共享的氛围底噪把生成的镜头粘合成同一空间——画面轻微漂移时，声音仍能兜住整体感。
- **声音设计在后期铺**：音乐与精细声音设计全部在剪辑/混音阶段叠加到连续氛围之上。
