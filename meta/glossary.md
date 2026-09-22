# 术语表

| 术语 | 定义 |
|------|------|
| 原子任务 | 不可再分的最小操作单元,有唯一ID和标准化I/O |
| 原子脚本 | 按5-8字断句后的单句口播文本,是视频生成的基本单元 |
| 状态快照 | WAITING_USER前保存的当前执行上下文,用于恢复 |
| ASR | 自动语音识别,将视频音频转为带时间戳的逐字稿 |
| 逐字稿 | ASR words **直出**的逐字时间戳数据，**字幕链路唯一源头**。两份同存 `{项目}/{日期}/字幕/`：`{名称}_逐字稿.srt`（每字一条，人看/播放器可加载）+ `{名称}_words.json`（`[{"text":"字","start":0.32,"end":0.36}]`，程序读取）。不经LLM、不做断句/合并/纠错（规范：asr_processing.md 第10.5章） |
| 口播字幕 | `{名称}_口播字幕.srt`，句级（≤13字/行）观众看/烧入用；**由逐字稿派生**（`逐字稿 → LLM语义断句 → 口播字幕`，时间戳取逐字稿词时间戳），**不是**独立再跑一次 ASR 的产物 |
| 发音Diff | 原子脚本(期望朗读文本 expected_readback_text)与ASR识别结果的文本差异分析；基准是原子化后文本，**非原始脚本** |
| REPLACE | 差异类型:同位置文字不同=发音错误 → wf_correction 音频替换(AUDIO_REPAIR)可修复 |
| INSERT | 差异类型:原子脚本有ASR没有=漏念 → VIDEO_REDO 重做镜头 |
| DELETE | 差异类型:ASR有原子脚本没有=多念 → VIDEO_REDO 重做镜头 |
| SKIP(差异) | 差异类型:可接受差异(过滤规则命中)，不修复（大小写与 REPLACE/INSERT/DELETE 等同） |
| TTS克隆 | 使用参考音样本克隆说话人音色重新朗读指定文本 |
| 警示语 | 保险合规要求的强制免责声明,随触发句自动挂载 |
| 三层叠加 | 合规规则分层:通用/险种/产品专属,高优先覆盖低优先 |
| 主干状态 | 状态机中的线性主流程节点(INPUT_PARSE到DONE) |
| 子状态 | 主干状态内部的细分子任务(如GENERATING内的SHOT_1..N) |
| 分支状态 | 任意主干状态均可跳转的修复通道(REPAIRING) |
| 暂停状态 | 任意主干状态均可跳转的用户交互通道(WAITING_USER) |
| FATAL | 致命异常,无法自动恢复,必须终止并通知用户 |
| RECOVERABLE | 可恢复异常,有明确自动修复路径 |
| USER_INPUT_NEEDED | 需用户决策的异常,暂停等待用户响应 |
| 退避策略 | 重试间隔递增策略:立即/10s/30s |
| 质检 | 交付前对产物完整性/命名/格式/对齐的自动检查 |
| 归档 | 质检通过后将产物移至最终路径并清理临时文件 |
| 前贴 | 15-30s引子视频，只引产品名、不讲利益点、不挂警示语 |
| 成片 | 完整口播视频，讲保障/保费/比例，须逐句挂警示语+生成脚本标注文档 |
| PLANNING | 主干状态:脚本解析(SCRIPT_PARSE)+原子化(SCRIPT_ATOMIZE)+合规校验(COMPLIANCE_CHECK) |
| SKIP(异常) | 异常等级之一:任务无意义/用户要求跳过 → 跳过进下一任务 |
| 原子化(SCRIPT_ATOMIZE) | 把脚本拆成TTS友好原子单位:去括号/5-8字断句/空格注入/删除级词删除/数字保护 |
| 期望朗读文本 | 原子化后的文本(atomic_scripts.json 的 spoken 字段)，VERIFYING/DIFF唯一比对基准 |
| 预估时长 | **裸念词时长** = 口播字数(去括号) ÷ 语速。只算台词，不含停顿/动作/缓冲 |
| 修正后总时长 | **完整时长** = 预估时长 + 停顿(逗号/句末/角色切换) + 纯动作镜头时长 + 段末缓冲(1.5-2s)。单段/extend 的判定一律用此值(算法见 `segmentation_packaging.md` Step 6) |
| KEEP/CHANGE | 修改协议:明确哪些镜头保留(KEEP复用)、哪些重做(CHANGE) |
| extend模式 | 单段超模型上限:前段text2video+后段reference2video+ffmpeg拼接 |
| 音色锚定(AUDIO_ANCHOR) | 为多角色/指定音色生成音色样本，作生成/修复参考音 |
| VIDEO_REDO | 单镜头重做:insert/delete或镜头失败时仅重生该镜头 |
| 保留式修改 | 用户对现有画面满意只做有界调整（换BGM/加字幕/删段/超分/擦字幕），不重新生成视频 |

## 面向用户术语转译表

> 与用户交流时，内部技术名词必须转译为用户可理解的表达。自检方法：把发给用户的话里所有技术token（文件名、工具名、内部代号）删掉后，句子仍通顺、信息不缺才允许发出。

| 内部术语（禁止透出） | 对用户说 |
|-------------------|---------|
| creative_design.md | 创意文档 |
| storyboard.md | 分镜规划 |
| atomic_scripts.json / 原子脚本 | 口播文案拆解稿 |
| shot_NN / shot | 第N个分镜（或"第N段"） |
| _task_ids.jsonl | 任务记录 |
| _视频日志.csv | 视频生成日志 |
| snapshot.json | 状态快照 |
| repair_log | 修复记录 |
| AUDIO_REPAIR / AUDIO_ANCHOR | 发音修复 / 音色锚定 |
| VIDEO_REDO | 镜头重做 |
| KEEP/CHANGE | 保留原有画面只改X / 重做X部分 |
| extend模式 | 分段拼接 |
| TaskType=edit/extend/keyframe | 视频编辑/视频延长/首帧锁定 |
| ImageList/VideoList/AudioList | 参考图片/参考视频/参考音频 |
| render_video / sandbox_generate_video 等工具名 | 用动作描述（"合成成片""生成视频"） |
| security_filter_error / code=12002 等错误码 | "该镜头未通过内容审核" |
| LUFS / crossfade / SNR | 音量标准 / 平滑过渡 / 信噪比 |
| ASR | 语音识别 |
| VOX LOCK / 六维音色卡 | 统一配音音色 |
| check_credit_quote | 确认积分够不够 |
| list_capabilities | 查询可用模型 |
| sandbox_process_video | 视频后处理（超分/擦字幕） |
