# 高调通透画风调色板（High-Key Style Palette）

<!-- v1.0 | 2026-09-14 -->

> 用途：保险口播/剧情短视频统一「高调通透」基底，同时按**场景**切换不同的通透亚型，避免全片一个调子。
> 设计原则：**统一基底 + 差异化变量**。6 个亚型共享同一套高调约束，只靠色温和质感区分，观众感到"场景变了氛围也变了"，而不是"换了个滤镜"。
> 适配性：本调色板全部是**静态光线/静态质感**描述，正是 Seedance 2.5 稳定可执行的范围；不涉及 rack focus、人物移动中动态光影等实验性手法。

---

## 一、统一基底（所有亚型共享，锁死不变）

| 维度 | 约束 | Prompt 关键词 |
|------|------|---------------|
| 对比度 | 一律低，高光不刺眼、暗部不死黑、过渡柔和 | low contrast, soft tonal roll-off |
| 肤色 | 一律保护，不偏黄/偏绿/偏红 | natural skin tones preserved |
| 饱和度 | 整体压低，不浓艳 | low/muted saturation |
| 阴影 | 一律提亮，画面底部不发沉 | lifted shadows |

**这 4 条保证"都是高调通透"。** 任何亚型都必须带这 4 个基底关键词，亚型只追加自己的色温/质感变量。

---

## 二、4 个可调变量轴

| 变量 | 选项 | 决定的画面属性 |
|------|------|----------------|
| 色温方向 | 冷青 / 中性 / 暖琥珀 | 情绪：清冷 / 干净 / 温暖 |
| 饱和度策略 | 极低 / 适中 / 单色锚定 | 性格：极简 / 自然 / 有焦点色 |
| 质感处理 | 无颗粒 / 轻胶片颗粒 / 柔焦雾感 | 气质：数码锐利 / 胶片温度 / 梦幻朦胧 |
| 光线硬度 | 均匀柔光 / 方向性柔光 / 侧逆光勾边 | 立体感：平面 / 自然层次 / 轮廓发光 |

---

## 三、6 种高调通透亚型

### 1. 清透冷白 Clean White
- **色温**：冷（约 5000K 偏蓝）｜**饱和**：极低近乎去色｜**质感**：无颗粒、数码锐利｜**光线**：顶棚均匀柔光无方向性
- **情绪**：专业、干净、可信赖
- **适用**：诊室、保险公司办公室、产品讲解（口播主讲段）
- **关键词**：`clean high-key, cold white tones, minimal saturation, even soft overhead lighting, clinical clarity, no grain, lifted shadows, natural skin tones`

### 2. 日系空气感 Airy Japanese
- **色温**：冷青（高光偏青蓝）｜**饱和**：低、绿植偏青不偏黄｜**质感**：轻胶片颗粒 + 高光柔化过曝｜**光线**：窗户自然光侧射，允许轻微过曝
- **情绪**：治愈、安静、日常
- **适用**：家庭客厅、儿童房、阳台、居家日常对话
- **关键词**：`airy Japanese pastel tone, soft overexposed highlights, slight film grain, low contrast, cool cyan highlights, clean and breathable, natural skin tones`

### 3. 暖通透 Warm Luminous
- **色温**：暖（约 3500K 琥珀）｜**饱和**：适中偏低、暖色不腻｜**质感**：无颗粒、光感圆润｜**光线**：落地窗暖光侧射、金色光晕
- **情绪**：温情、安心、亲情
- **适用**：家庭餐桌对话、睡前场景、黄昏接送
- **关键词**：`warm luminous high-key, amber golden light, soft glow, low contrast, natural skin tones preserved, creamy highlight roll-off, lifted shadows`

### 4. 柔粉通透 Soft Pastel Glow
- **色温**：中性偏微暖｜**饱和**：低、粉彩色（淡粉/淡蓝/雾绿）｜**质感**：柔焦雾感、高光弥漫｜**光线**：散射光、无硬阴影
- **情绪**：温柔、关怀
- **适用**：新生儿/儿童场景、母子互动
- **关键词**：`soft pastel high-key, dreamy diffused light, misty glow, muted pink and baby blue palette, gentle and caring mood, natural skin tones`

### 5. 明亮通透 + 冷蓝底 Bright Cool Background
- **色温**：人物暖肤色 + 背景冷蓝｜**饱和**：肤色保护、背景去饱和偏青｜**质感**：无颗粒｜**光线**：人物正面柔光、背景冷调
- **情绪**：人物突出、专业但不冷
- **适用**：医院走廊、ICU 门口、办公大堂
- **关键词**：`bright high-key, warm natural skin tones against cool blue desaturated background, subject-background color separation, clean and professional, lifted shadows`

### 6. 清晨通透 Morning Fresh
- **色温**：中性偏冷微暖（晨光）｜**饱和**：适中、干净不浓｜**质感**：无颗粒、空气清透｜**光线**：清晨侧光、长投影、空气透明感
- **情绪**：新的一天、希望、重新开始
- **适用**：出院、早晨送孩子、新生活开始（叙事收尾段）
- **关键词**：`fresh morning light, clean high-key, transparent airy atmosphere, soft directional sunlight, cool shadows with warm highlights, hopeful mood, natural skin tones`

---

## 四、场景 → 画风映射（生成时自动选亚型）

| 场景类型 | 亚型 | 理由 |
|----------|------|------|
| 医院诊室 / 办公室 / 产品讲解口播 | 清透冷白 | 医疗/专业场景冷白最可信 |
| ICU / 走廊 | 明亮通透+冷蓝底 | 背景冷蓝符合医院环境认知，人物暖肤突出 |
| 家庭客厅 | 日系空气感 | 居家日常用空气感最自然 |
| 家庭餐桌 / 傍晚 | 暖通透 | 亲情场景暖调传温度 |
| 儿童房 / 母子互动 | 柔粉通透 | 婴幼儿/温柔场景 |
| 出院 / 新生活收尾 | 清晨通透 | 叙事上代表"事情解决了" |

> **门诊险 260901 批次对照**：候诊区/缴费大厅 = 清透冷白 或 冷蓝底；夫妻客厅 = 日系空气感（日常）/暖通透（温情）；咨询角独白 = 清透冷白。
> **少儿长期医疗对照**：儿童病房 = 柔粉通透或冷白；ICU 门口 = 冷蓝底；居家 = 日系/暖通透。

---

## 五、使用规则（防风格漂移）

1. **一个场景一个亚型**：同一场景（如全片候诊区）内锁定同一亚型，跨场景才切换（呼应 v3.7「光源同场景锁死、只跨场景换光」）。
2. **关键词每镜重带**：Seedance 无状态，亚型关键词要在每个镜头/每段 prompt 的 STYLE 段重复，不能只声明一次。
3. **基底不可省**：4 条统一基底关键词每条 prompt 必带，亚型变量只增不改基底。
4. **切换要在段边界**：亚型切换（如冷白诊室 → 暖通透家中）必须落在 reference2video 的段边界，并在新段写明新光源，不在单段内换调。
5. **多版本一致性**：同一脚本的多个视觉版本（V1/V2/…）若用不同亚型，各自全程锁定；不要在一个版本内混用。
6. **禁动态光影**：本调色板只描述静态光。人物从亮区走入暗区的连续光变、rack focus 等仍按 prompt_craft_guide v3.7 归为实验性，不入正式批次。

---

## 六、结构化定义（供生成器读取）

每个画风的机器可读结构，生成器按场景 key 取 STYLE：

```json
{
  "clean_white": {
    "name_zh": "清透冷白", "kelvin": 5000,
    "saturation": "极低", "texture": "无颗粒数码锐利", "light": "顶棚均匀柔光",
    "scenes": ["诊室", "办公室", "产品讲解", "候诊区", "咨询角"],
    "prompt_en": "clean high-key, cold white tones, minimal saturation, even soft overhead lighting, clinical clarity, no grain"
  },
  "airy_japanese": {
    "name_zh": "日系空气感", "kelvin": "冷青",
    "saturation": "低", "texture": "轻胶片颗粒+高光柔化", "light": "窗光侧射轻微过曝",
    "scenes": ["家庭客厅", "儿童房", "阳台", "居家日常"],
    "prompt_en": "airy Japanese pastel tone, soft overexposed highlights, slight film grain, low contrast, cool cyan highlights, clean and breathable"
  },
  "warm_luminous": {
    "name_zh": "暖通透", "kelvin": 3500,
    "saturation": "适中偏低", "texture": "无颗粒光感圆润", "light": "落地窗暖光金色光晕",
    "scenes": ["家庭餐桌", "睡前", "黄昏", "温情夫妻"],
    "prompt_en": "warm luminous high-key, amber golden light, soft glow, low contrast, creamy highlight roll-off"
  },
  "soft_pastel": {
    "name_zh": "柔粉通透", "kelvin": "中性微暖",
    "saturation": "低粉彩", "texture": "柔焦雾感", "light": "散射光无硬影",
    "scenes": ["新生儿", "儿童", "母子互动"],
    "prompt_en": "soft pastel high-key, dreamy diffused light, misty glow, muted pink and baby blue palette, gentle mood"
  },
  "bright_cool_bg": {
    "name_zh": "明亮通透冷蓝底", "kelvin": "人暖/景冷",
    "saturation": "肤色保护背景去饱和", "texture": "无颗粒", "light": "人物正面柔光背景冷调",
    "scenes": ["医院走廊", "ICU门口", "缴费大厅", "办公大堂"],
    "prompt_en": "bright high-key, warm natural skin tones against cool blue desaturated background, subject-background color separation"
  },
  "morning_fresh": {
    "name_zh": "清晨通透", "kelvin": "中性偏冷暖",
    "saturation": "适中干净", "texture": "无颗粒空气清透", "light": "清晨侧光长投影",
    "scenes": ["出院", "早晨", "新生活", "收尾"],
    "prompt_en": "fresh morning light, clean high-key, transparent airy atmosphere, soft directional sunlight, cool shadows with warm highlights"
  }
}
```

> 所有亚型追加统一基底后缀：`, low contrast, lifted shadows, natural skin tones, low saturation`。
