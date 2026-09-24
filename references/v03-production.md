# motion_plan 0.3 兼容说明

`motion_plan.version` 使用 `"0.3"`，另外三份 JSON 保持 `"0.1"` 并向后兼容新增字段。默认 `sequential-comic`，只允许固定漫画构图模式。此文件描述数据合同兼容细节，不是 V1.0 的另一套工作流。不得用测试夹具冒充真实内容验收。

## 对白、字幕和简单嘴部开合同一时间轴

storyboard 每条 dialogue 增加 `audio: "audio/line_01.wav"` 和 `timing_source: "audio"`。输入为本地未压缩16位PCM WAV；开始/结束帧相对当前分镜，结束不含。字幕区间长度必须和实际音频长度一致（最多1帧舍入差）。有对白的正式素材准备阶段拒绝估计时间或缺少配音。无声预演可使用 fixture，必须明确标注。

嘴部层的 acting 增加：

```json
{"speech":{"speaker":"char_01","closed_asset":"shots/shot_001/mouth_closed.png","open_asset":"shots/shot_001/mouth_open.png"}}
```

还需原有 part="mouth"、pivot、keys，speaker 必须在当前镜头有对白且可见。prepare 从本地音频计算每帧音量，静默时闭嘴，有声时驱动简单开合；Remotion 同步播放音频和字幕。不是语音识别、强制对齐或精确音素口型。先试听，判断开合频率是否自然，再做视觉确认。声音可来自用户录音或已授权的本地语音工具，不内置密钥或偷偷调用云服务。

## 素材路线

1. 有肢体移动：沿用 master → 提取人物/部件 → 补全遮挡背景 → 局部关键帧/姿态序列。逐镜新素材不复用参考立绘。
2. 只有眨眼、嘴部、局部表情：允许固定 `panel_base`（原始 master 完整保留）加局部不透明替换片。motion 层 `region: [x,y,width,height]` 为0—1归一化坐标，素材仍与 master 同尺寸；渲染器只显示该区域，不改图片其他位置。panel_base 必须是原始 master，不动、不裁、不加 acting。替换区域仅切图，不允许平移、旋转、透明度动画；手、头或身体要移动时改用路线1并补全遮挡，不能拖动矩形皮肤块。

局部编辑必须调用图像工具，锁定原图坐标、肤色、线宽、五官位置。分别检查睁眼闭嘴、闭眼闭嘴、睁眼张嘴、闭眼张嘴四种组合，确认无双嘴、接缝、眉毛变化或肤色闪烁。region 是确定性合成边界，不是自动抠图或自动修复承诺。

## 检查、报告和逐镜重做

```text
python scripts/pipeline.py report <本地项目>
python scripts/pipeline.py compile <本地项目> --shot shot_002
python scripts/pipeline.py prepare <本地项目> --shot shot_002 --renderer <独立单镜渲染目录>
```

asset_report.json 列出 master、身份参考、姿态、嘴部和音频文件缺项及内容指纹。changed 表示相对上一次报告的变化，不代表相对最近成片；修改单镜不会改其他镜的指纹，修改全片 brief 会使所有镜头重新待查。compile --shot 仅重写指定镜头的提示词，完整审阅稿仍更新；prepare --shot 只复制指定镜的素材，并将时间轴归零，不要求其他镜素材齐全。全片交付必须再次不带 --shot 验证和渲染。

报告不会调用生成工具、覆盖用户素材或自动宣称视觉合格。制作时按 missing 补图；数据字段合法不代表表演自然。真实素材初次渲染使用 asset_mode="preview"，与几何 fixture 区分；此时保留未通过的视觉复核标记。只有复核通过后才改为 production。所有输入和报告都留在项目目录，禁止提交用户内容到 Skill 仓库。

## 正式版本验收

至少一段真实本地内容包含3—5个独立分镜，角色身份一致、实际说话/眨眼或动作、固定背景、按对白切镜、字幕同步、无明显接缝形变。保存本地 acceptance.md，记录成片、逐镜首/中/末和关键帧、音频试听结果及已知局限。若视觉或声音尚未达标，交付候选版与具体问题，不发布正式版本标签。几何夹具仅验证工程机制。
