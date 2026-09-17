<!-- v3.4 | 2026-09-10 -->
<!-- v4.2.1 平台适配声明 2026-09-17 -->
# 资产管理与真人版权素材（vendor_asset_id / LivenessFace）

> **平台适配声明**：本文原始接口为外部 BlueAI 资产管理 API。
> 在小云雀平台环境中，参考图片/视频/音频直接通过沙盒文件路径传入
> `sandbox_generate_video` 的 ImageList/VideoList/AudioList，无需上传换
> vendor_asset_id。PixVerse/Gaga/byteplus 等厂商渠道的资产管理流程仅在
> 外部网关环境下需要。本文的真人版权合规要求（LivenessFace 活体授权、
> 肖像权保护）仍然适用，平台环境同样不得绕过。

> 解决"给图给链接在某些渠道用不了"的问题。
> 多数生成接口收 URL；但 **PixVerse / Gaga / volcengine_visual / byteplus** 等只认**厂商资产 ID**，必须先上传素材换 `vendor_asset_id`，再填进生成接口的 `frame_images`/`input_references`/`provider`。
> 接口：BlueAI 资产管理 API（base `https://bmc-model-openapi.bluemediagroup.cn/api/v1`，Bearer Token）。

## 一、标准流程（AIGC 数字形象）

1. **建素材组** `POST /asset-groups`
   - body：`{"vendor":"volcengine_visual"|"byteplus","name":"...","group_type":"AIGC"}`
   - byteplus 账号首次调用前须在控制台签署授权书
   - 拿 `group_id`
2. **上传素材** `POST /assets`
   - body：`{"vendor":..., "vendor_group_id":group_id, "image_url"|"video_url"|"audio_url":...}`（三选一）
   - 拿 `vendor_asset_id`（PixVerse是整数字符串、Gaga是字符串ID）
3. **等处理完成**：volcengine_visual/byteplus 异步，`status=Processing` 时轮询
   `GET /assets/{vendor_asset_id}` 直到 `Active`（Failed 则换图重试）
4. **生成接口引用** 该 vendor_asset_id
- 查询：`GET /assets?vendor=...`（列表）、`GET /assets/{id}`（详情，url 有时效）
- 删除：`DELETE /assets/{id}`；组 `POST/GET/PATCH/DELETE /asset-groups`（byteplus 组级联删除，仅授权过期/被拒可删）

## 二、真人版权素材（仅 byteplus，LivenessFace 真人肖像）

当用户提供**真人照片/明星/达人肖像**且渠道是 byteplus，不能用 AIGC 组，必须走**真人认证（活体）授权**：

1. `POST /real_human_verification/session`
   - body：`{"callback_url":"<认证完成跳转地址>"}`
   - 返回 `h5_link` + `byted_token`（**30分钟有效**）
2. **终端用户本人**打开 h5_link 完成活体认证；成功跳转 callback_url 并带 `resultCode=10000`
3. `POST /real_human_verification/result`，body `{"byted_token":...}`
   - 返回自动创建的 `vendor_group_id`（LivenessFace 资产组，无手动创建接口）
   - 502=会话不存在/过期/未完成 → 重新发起 session
4. 用该 group_id 调 `POST /assets` 上传真人肖像 → 拿 vendor_asset_id 供生成

合规要点：
- LivenessFace 必须**肖像权人本人完成活体授权**；授权过期/被拒的组才能删除，有效期内受保护
- 无授权不得用真人脸生成；名人/第三方肖像需有合法授权，否则拒绝并告知用户
- 认证是强用户参与步骤（要本人点H5），流程在此 WAITING_USER，不可用 AIGC 组绕过

## 三、决策：URL 还是 vendor_asset_id / AIGC 还是真人

```
用户给图/视频/音频素材
├─ 生成渠道接受 URL（doubao Seedance/Seedream 等）
│   └─ 直接传 URL（必要时先下载转存拿到可访问URL）
└─ 渠道只认资产ID（pixverse/gaga/volcengine_visual/byteplus）
    ├─ AI生成形象/虚拟人/非特定真人 → AIGC组：asset-groups → assets → Active
    └─ 真实人物肖像（用户本人/有授权达人，byteplus）
        └─ LivenessFace：real_human_verification(session→本人H5认证→result) → assets
```

## 四、接线位置
- **STORYBOARD/READY 前的资产准备阶段**：识别分镜需要哪些参考图/参考视频/真人素材 → 缺图先走 `image_generation.md` 生图，真人素材走本文认证 → 全部换好 vendor_asset_id（如渠道需要）再进 GENERATING
- 资产ID与素材绑定关系登记到 `_session/`，避免每次重新上传
- 音色资产（speaker_id S_）走 `voice_clone_tts.md`，不走本资产管理
