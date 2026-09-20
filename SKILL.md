---
name: dynamic-comic-video
description: Turn original stories, scripts, lessons, explainers, or branded narratives into layered motion-video sequences using identity-only character references, narrative beats, fresh shot compositions, master-aligned layers and Remotion MP4 rendering. Manga-style drawing is optional; use for topic-agnostic narrative motion video, not full frame-by-frame animation or lip sync.
---

# Dynamic Comic Video — V0.2

把用户当次提供的原创内容转为可追溯的分镜、逐镜新绘的 master、对齐图层和 Remotion MP4。内容可以是现实故事、历史、科普、教育、产品说明、品牌叙事、幻想或其他用户指定主题。V0.1 的最小闭环是 Agent 编导与图像工具协作，加本地确定性校验和渲染；不是无需图像工具的自动绘制服务。

## 内容边界

Skill 仓库保存能力，不保存用户作品。每次任务先在独立工作目录接收 brief、角色参考和素材；生成的 JSON、提示词、master、图层、预览和 MP4 默认只写入该工作目录。除非用户明确要求发布某个内容项目，否则不把用户故事、角色设定或成片提交到 Skill 仓库，也不把它们混入通用 examples。详见 [内容输入与工作目录](references/content-intake.md)。

## 不可丢失的创作约束

- 视觉语言由用户或 brief 决定：可以是日漫二维手绘，也可以是写实插画、欧美动画、绘本、赛博朋克、历史复原、科普图解、品牌风格或其他指定方向。不要因为技能名称、示例或参考图擅自改变题材、文化、时代、行业、世界观或受众。
- 可选 `style_preset: "paper-collage"` 借鉴纸片拼贴视频的画面语法：可见纸张边缘、轻微错位、纸纤维/印刷颗粒、分层投影、有限调色板和克制的 2.5D 景深。它是画风预设，不改变内容主题；未指定时使用 `custom` 并按 brief 的视觉语言执行。具体规则见 [纸片拼贴画风](references/paper-collage-style.md)。
- 保留原文的地域、时代、人物关系、题材、因果、事实边界与情绪。缺失的关键设定先询问，其余假设写入 brief；不得把教育、商业、历史或现实主题自动改造成校园/日本/幻想故事。
- Character Reference 只锁脸、发型、服装、比例和辨识特征。参考图中的姿势、表情、景别、光线、构图不锁定。每个人物镜头按剧情重新绘制表演；禁止反复粘贴一张固定立绘。
- 先从原文提取 Narrative Beats（信息、行动或情绪的变化），再为每个 beat 设计一个或多个 Shots。不要按相同秒数或句子机械切镜。
- 先完整 master composition，再以该 master 分离/重建图层。统一画布、坐标、透视、尺度与光向；角色移开后背景必须补全。不能独立生成几张互不对齐的图来凑层。
- 每镜以动作与表情变化为核心。V0.2 支持局部部件关键帧（平移、关节旋转、透明度）和对齐姿态图片切换，视差仅为辅助。相机固定后仍应看出表演；有叙事理由的静止镜头须记录停顿目的。详见 [有限动画](references/limited-animation.md)。不包含自动补间、骨骼绑定或嘴型同步。

## 工作流程与交付

1. **Visual / Production Brief**：保存原文、内容保留项、文化时空、视觉语言、情绪和尺寸/帧率/总帧数为 `production_brief.json`。
2. **Character Planning → Reference**：建立 `characters.json`，选择需要保持一致的角色，写 identity 与身份参考提示词。使用可用图像工具生成 reference 并目视核对，再设 `status: ready`。无人物项目允许空列表。不要为了凑人物改写原文。
3. **Narrative Beats → Storyboard Director**：在 `storyboard.json` 先写 beats 的原文摘录与变化，再写 shots；每镜明确目的、人物动作/表情/视线、景别、角度、构图、连续性与拟分层理由。无意义的 foreground/effects 不拆。
4. **Shot Prompt Compiler**：运行 `compile`，得到角色参考与逐镜 master 的结构化提示词。编译只整理已完成的导演决策，不创造新剧情。把 reference 作为身份参考输入图像工具，执行逐镜新绘，保存指定 `master.png`。
5. **Master QC → Layer Planning**：先核对 master 的身份、剧情表演、构图与重复性，再确认该镜实际所需图层。根据 [分层协议](references/layer-protocol.md) 提取人物、补全背景、分离前景/特效，保存透明 PNG 与合成预览。若图像工具无法分层，明确缺少的资产并停在这一阶段；不要悄悄降级为整图推拉。
6. **Motion Director**：使用 motion_plan 0.2，先填写动作意图，安排准备、动作、反应、停顿，再决定所需局部层或新绘姿态。按对白阅读速度和表演分配时长，不把格数当成秒数。编译器输出逐镜 acting 提示词。检查全部关键帧及中间帧的接缝、接触、遮挡、文字和节奏，确认后填写 performance.reviewed。素材生成失败时保存进度并明确缺图，禁止擅自降级为固定立绘推拉。
7. **QC → Remotion → MP4**：运行素材校验、prepare、Remotion 渲染。复查所有切点前后帧和每镜首/中/末帧；报告测试/正式素材状态、时长、尺寸、遗留问题与输出位置。

数据契约见 [契约说明](references/contracts.md) 与 `schemas/*.schema.json`；可执行步骤见 [运行指南](references/runbook.md)。可选画风见 [纸片拼贴画风](references/paper-collage-style.md)。`examples/library/` 只是一个中国南方小城图书馆的原创测试样例，用来示范“视觉语言不改变内容题材”，不是技能的主题限制。

## Repetition QC

自动检查：同一角色相邻出场的 pose_tag 相同；连续三镜的 shot-size、angle 或 composition_tag 相同；人物 PNG 内容完全相同则阻止准备渲染。输出 `qc_report.json`。

标签和文件哈希不能证明视觉多样性。Agent 必须查看逐镜接触表，比较实际肢体轮廓、面部表情、主体占画面比例、机位与视觉重心；改标签不能消除问题。叙事需要的重复在 `repetition_exception` 写具体理由，警告保留供复核。近似重复立绘即使哈希不同也应返工。不要为了多样性破坏空间连续性。

## 工具与隐私

优先使用当前环境可用且已获授权的图像生成/编辑工具；使用时读取其技能说明。此项目不内置任何云端生成 API，也不读取或转发凭据。API Key、Token、密码不得写入 JSON、提示词、浏览器 public、日志或交付包，不得上传网络。若用户粘贴明文密钥，提示风险并指导其改存本地环境变量/加密配置，不用该明文密钥请求网络。配置帮助只询问本地文件路径并提供用户本地执行脚本。需要凭据的外部适配器必须遵守用户密钥仅本地使用的限制；不兼容时明确说明。

## 项目布局

```text
dynamic-comic-video/            技能正式名称；能力面向各种主题
  SKILL.md
  schemas/                 四份严格 JSON Schema (2020-12)
  examples/library/        一个主题样例；测试素材、提示词与 QC 报告
  scripts/                 validate / compile / prepare 与本地 fixture
  references/              契约、分层协议、运行指南
  assets/remotion/         固定依赖版本的渲染模板
  requirements.txt
```

生产项目另存，不覆盖技能示例。按阶段恢复：已确认的 brief/角色身份保持，修改某镜只重做该镜 master、图层与对应 motion/QC；不为局部修改重写全片。完成任务后，除非用户要求保留或发布，清理工作目录中的临时素材。
