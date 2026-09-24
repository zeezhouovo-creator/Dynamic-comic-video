# 简化搞笑条漫画风

这是根据用户参考图提炼的高层视觉语言，不复制参考漫画的角色、台词、分镜格、商标或独特造型。使用时在 `production_brief.json` 设置：

```json
{
  "style_preset": "simple-comic",
  "render_profile": "comic-economy"
}
```

## 画面特征

- 粗而干净的深色线稿，轮廓优先于纹理。
- 平涂色块和少量阴影，颜色明快但控制在有限调色板内。
- 眼睛、嘴型、眉毛和手势清晰，允许夸张表情服务笑点或反应。
- 背景使用简化平面和 2–4 个地点识别物：例如校园树、公告牌、长椅或建筑轮廓；不堆复杂人群、纹理和无关道具。
- 画面保留完整画布和下方约 18–22% 的字幕安全区，人物脸部和关键动作不要压到字幕区。
- 动作线、汗滴、感叹号等漫画符号只在情绪峰值出现，不能每镜都加。

## 文字处理

生图阶段不生成对白气泡、旁白框、漫画字、标题、水印或 Logo。对白、旁白和重点文字统一由视频后期字幕层完成；master 只保留人物表情、手势和足够的留白。若参考图带气泡，只分析其版面节奏，不复制气泡形状和文字。

字幕区要求：

```text
lower 18–22% of the frame kept visually simple and high-contrast;
no faces, hands, props or high-frequency background detail behind subtitles;
do not render any text, speech balloons, captions, logos or watermark in the image.
```

## 连续镜头规则

角色参考锁定脸型、发型、服装、体型和辨识锚点；每个镜头只改变剧情所需的姿势、表情、视线、景别或机位。背景可以简化，但不能改变地点事实。每个镜头先生成完整 master，再从同一 master 拆出人物、背景和必要前景层。

## 负面约束

```text
no speech bubbles, no comic lettering, no generated text, no watermark;
no copied named-comic characters, no copied panel layout or dialogue;
no photorealism, no glossy 3D plastic, no excessive gradients;
no busy background behind the face or subtitle-safe area;
no extra fingers, fused hands, identity drift or missing accessories;
no independent lighting between layers, no transparent holes in the background.
```
