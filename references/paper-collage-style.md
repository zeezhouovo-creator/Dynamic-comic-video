# Paper Collage 画风预设

这是 `dynamic-comic-video` 的可选画面语言，受到 [cyberlesterr/paper-collage-video](https://github.com/cyberlesterr/paper-collage-video) 公开项目所展示的纸片分层视频思路启发。这里只借鉴抽象的视觉和制作原则，不复制其代码、素材、模板、演示画面或具体故事。

## 画面原则

- 把每个 shot 看成一张被剪开的纸面舞台：background、character、foreground、effects 是有实体厚度的纸片层，而不是透明 PNG 的平面堆叠。
- 保留适量纸张边缘、剪切轮廓、纤维、印刷颗粒和轻微套印错位。瑕疵要统一、克制、服务于手工感，不能损害脸部、文字、手部或关键物件的可读性。
- 采用有限调色板：一个主色、一个强调色、一个深色墨线/阴影色和一个纸张底色。内容需要特定品牌或文化色彩时，以 brief 为准，不套用固定调色板。
- 用接触阴影和窄而柔的投影表达纸片厚度。阴影方向、光色和强度在同一 shot 内保持一致；不要给每层加独立的随机光源。
- 2.5D 运动保持克制：背景慢、人物中等、前景快；移动幅度优先体现空间关系和情绪，不让纸片边缘露出画布，也不把镜头动作变成机械 Ken Burns。
- 允许手绘箭头、胶带、便签、撕边或版面标记，但只有在内容语境需要时才添加；它们不应自动把故事变成课堂、手账或日本题材。

## Prompt 补充

当 `style_preset` 为 `paper-collage`，在每个 master prompt 中加入：

```text
Layered paper collage illustration, tactile cut-paper edges, subtle paper fibers and print grain,
controlled registration offsets, soft contact shadows between layers, limited palette derived from
the production brief, handmade but precise silhouettes, clear readable faces and objects.
Treat every layer as a physical paper cutout; preserve a clean master composition before separation.
```

同时加入负向约束：

```text
No glossy 3D plastic, no photorealistic surface, no random torn edges over faces or text,
no independent lighting per layer, no unrelated scrapbook stickers, no theme or culture substitution.
```

## QC 增补

master 与静态合成预览要检查：纸张纹理是否统一、层间阴影是否重复、边缘是否有白洞、前景是否遮挡叙事重点、套印错位是否超出可读范围。中帧检查视差运动后是否仍像同一张纸片舞台；若错位让角色像漂浮的贴纸，应调整接触阴影、z 顺序或位移，而不是继续增加滤镜。

这个预设不要求所有主题都使用人物。产品、地图、建筑、图表、动物或抽象符号也可以成为纸片层；角色身份锁定规则只在项目实际存在角色时启用。
