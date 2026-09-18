# V0.1 数据契约

所有文件 `version: "0.1"`，同一 `project_id`，UTF-8。Schema 不允许未声明字段。JSON Schema 负责结构；`pipeline.py` 负责跨文件引用和时间/素材一致性。

| 文件 | 所有者与主要字段 | 消费方 |
|---|---|---|
| production_brief.json | 原文、保留项、setting、visual_language、tone、format、assumptions | 所有阶段 |
| characters.json | identity 五类稳定特征；reference 路径、提示词、状态与 identity_only | 提示词编译、master QC |
| storyboard.json | beats 原文摘录/变化/情绪；shots 动作、表情、机位、构图、连续性、master、layers | 编译器、分层、QC |
| motion_plan.json | asset_mode、逐镜起始帧/时长、逐层变换/z、review | 素材 QC、Remotion |

Schema 文件位于 `../schemas/`，完整实例位于 `../examples/library/`。Narrative Beats 内嵌于 storyboard，V0.1 不另增第五个必须文件。Visual Brief 内嵌于 production brief，保持风格与内容设定分离。

## 单位与路径

- 宽高为像素，H.264 要求偶数。时间全部为整数帧，区间 `[start_frame, start_frame + duration_frames)`；每镜至少两帧，无空隙无重叠，顺序与 storyboard 一致。
- asset/master/reference 路径相对生产项目根；只能本地相对路径，不能 URL、绝对路径、`..` 或反斜杠。准备渲染时仅复制使用的层到 renderer/public。
- 全图层与 master 同尺寸；人物 PNG 保留全画布透明区域，不使用紧裁 bbox。中心为变换原点，x/y 为输出画布像素，scale 为统一缩放倍率。from 是镜头首帧，to 是末帧。
- z 越大越靠前且不得相同。background 必須唯一且最底层，其他层按实际遮挡排列。人物持有的纸条等刚性随身物可归到人物层；独立运动时才另拆。
- V0.1 采用线性变换与硬切。scale 范围 1–1.3；脚本检查两端画布覆盖，线性插值因此不会在中间超出这个边界，但仍须目视检查实际绘制范围和遮挡孔洞。

## 状态与检查边界

`reference.status: planned` 可用于早期编译；正式素材准备必须 `ready` 且文件存在。`motion_plan.asset_mode: fixture` 明确允许测试图片，视频会有测试标记；切换 production 不能替代实质绘制和复核。

review 三个布尔值分别表示人工/Agent 已核对 master 对齐、遮挡背景补全、完整运动范围。程序只检查申报，不自动证明艺术质量。每镜 `notes` 写复核观察。自动 QC 不具备姿态识别或图像分割能力；精确重复哈希是底线检查。

外部图像生成不是本地脚本的一部分。Agent 负责读取 prompts/*.json、将 reference 或 master 作为图像输入、调用可用工具、保存回对应位置。没有工具时交付已编译的提示词和明确缺图清单，不能声称成片完成。
