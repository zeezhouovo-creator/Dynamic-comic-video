---
name: dynamic-comic-video
description: Create fixed-panel sequential comic videos from original stories, lessons or explainers, with identity-consistent fresh panels, local character acting, timed dialogue and captions, simple speech-driven mouth movement and Remotion MP4 rendering. Topic-agnostic; not full frame-by-frame animation or phoneme lip sync.
---

# Dynamic Comic Video — V1.0 candidate

新项目先读取 [V1.0 总控系统](references/v10-control-system.md)，再按 [动态漫画制作向导](references/production-wizard.md) 自动判断项目状态、已有素材和已知信息，只补问当前阶段缺失的内容，再由 Skill 生成或读取分镜、设计表演并输出视频。旧的固定问卷式入口不适用。

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
- 每镜以动作与表情变化为核心。当前 V0.4 使用事件驱动的局部关键帧、对齐姿态图片切换和配音驱动的简单嘴部开合；视差只属于旧兼容路径。相机固定后仍应看出表演；有叙事理由的静止镜头须记录停顿目的。详见 [有限动画](references/limited-animation.md)。不包含自动补间、精确音素口型或骨骼绑定。

## 工作流程与交付

入口与分流统一执行 [动态漫画制作向导](references/production-wizard.md)。已有独立分镜可直接进入分析和动态设计；已有角色设定先建立 Character Reference；无素材时从剧情开始。完整漫画或四格图不作为默认入口，只有用户明确选择时才识别格子并判断是否需要补画。

**分镜生成统一执行 [分镜生成主规则](references/storyboard-director.md)，已替换原来的五项简表和通用分镜建议。**先建立场景空间记录，再独立设计每镜的背景视图、角色表演、倾听反应及切镜因果。跨镜保持空间与角色身份，禁止机械复用背景；镜内固定机位。每镜输出用户指定的17项字段，对白后按叙事需要留反应时间。旧文中的立即切镜和配角静止建议不作为本模式通用规则。

V0.4 制作流程见 [V0.4 制作闭环](references/v04-production.md)：在 V0.3 的固定分镜、对白时间轴和局部表演基础上，统一加入制作向导、角色一致性检查、视听事件、预览前质量闸门和一体化安装。`motion_plan` 仍使用 0.3，保持已有项目兼容；这里的 V0.4 是 Skill 工作流版本，不是新的 JSON 合同版本。V0.4 已通过真实连续镜头样片验收；后续项目仍需按同一验收门复核。

默认视频形式为 [连续分镜式动态漫画](references/sequential-comic.md)，使用 `performance.mode: sequential-comic`。独立漫画分镜、固定构图、人物表演；台词和动作后按剧情保留短暂反应，再硬切下一格。字幕跟随对白时间。复杂动作优先拆为下一张分镜。情绪重点允许漫画式夸张，日常对白保持克制。跨镜锁定角色身份与场景空间，背景构图随机位重新绘制。此模式禁用视差及镜头推拉、平移、旋转、缩放，优先于一般有限动画建议。主题可变，表现形式统一。

人物动作遵循 [人物动作自然度规则](references/motion-naturalness.md)：默认静止，事件触发，准备→动作→停顿/回稳；禁止周期性上下浮动、摇摆、缩放、机械呼吸和固定频率重复动作。

用户要求固定构图或克制微动作时，采用 [固定机位微动作](references/fixed-camera-micro.md)，填写 `performance.mode: fixed-camera-micro`。固定构图来自 Skill 生成的 master composition；参考图只用于保持身份或风格，不直接作为 master。禁止镜头推拉、缩放、平移、旋转和视差。围绕眨眼、说话、视线和事件触发的轻微动作设计表演。

1. **Visual / Production Brief**：保存原文、内容保留项、文化时空、视觉语言、情绪和尺寸/帧率/总帧数为 `production_brief.json`。
2. **Character Planning → Reference**：建立 `characters.json`，选择需要保持一致的角色，写 identity、3–5 个视觉识别锚点与身份参考提示词。使用可用图像工具生成 reference 并目视核对，再设 `status: ready`。无人物项目允许空列表。不要为了凑人物改写原文。详细身份锁定与表演前检查见 [角色一致性与自然表演](references/character-consistency.md)。
3. **Narrative Beats → Storyboard Director**：先写 scenes 空间锚点与 beats 的原文摘录/变化，再按主规则写独立 shots 和 direction。角色身份一致、场景空间连续、背景构图随机位自然变化；明确说话与倾听表演、台词时间、微动态、音效、切镜原因与下一镜衔接。编译输出17项逐镜审阅稿。无意义的 foreground/effects 不拆。只有用户提出需要时，才把知识卡、总结卡或 CTA 作为可选独立收束镜头加入；规则见 [可选收束卡](references/outro-card.md)。
4. **Shot Prompt Compiler**：运行 `compile`，得到角色参考与逐镜 master 的结构化提示词。编译只整理已完成的导演决策，不创造新剧情。把 reference 作为身份参考输入图像工具，执行逐镜新绘，保存指定 `master.png`。
5. **Master QC → Layer Planning**：先核对 master 的身份、剧情表演、构图与重复性，再确认该镜实际所需图层。根据 [分层协议](references/layer-protocol.md) 提取人物、补全背景、分离前景/特效，保存透明 PNG 与合成预览。若图像工具无法分层，明确缺少的资产并停在这一阶段；不要悄悄降级为整图推拉。
6. **Motion Director**：新项目使用 motion_plan 0.3，先依据 [角色一致性与自然表演](references/character-consistency.md) 和 [音频驱动时间轴](references/audio-timeline.md) 建立每镜统一 `timeline`。先取得实际配音时间，再填写字幕单元、speech intervals、关键词动作触发原因、主要动作、静止时间、眨眼时间、反应停顿和 CUT，再安排准备、动作、反应、停顿。按实际对白音频和表演分配时长，不把格数当成秒数。需要重点字幕、漫画符号、音效、环境音或音乐变化时，遵循 [漫画演出与视听反馈](references/comic-performance.md)，并把事件写入同一 `timeline`。编译器输出逐镜 acting 提示词。先用 preview 渲染，检查全部关键帧及中间帧的接缝、接触、遮挡、文字和节奏，确认后填写 performance.reviewed，再设 production。素材生成失败时保存进度并明确缺图，禁止擅自降级为固定立绘推拉。
7. **质量闸门 → QC → Remotion → MP4**：预览前运行 [动态漫画质量闸门](references/quality-gate.md) 和 `scripts/quality_gate.py`，先修复 Critical/Major 问题，再运行素材校验、prepare、Remotion 渲染。复查所有切点前后帧和每镜首/中/末帧；报告测试/正式素材状态、时长、尺寸、遗留问题与输出位置。质量闸门只能自动修复安全的时间轴元数据，不能用标签或自动修正掩盖角色、场景和表演问题。

正式项目可以用 `scripts/preview.py <project> --renderer <external-renderer>` 串联校验、质量闸门、提示词编译、prepare 和 Remotion 预览；它把 MP4 复制回项目目录的 `preview.mp4`，不上传用户内容。渲染器必须位于项目目录之外。

数据契约见 [契约说明](references/contracts.md) 与 `schemas/*.schema.json`；可执行步骤见 [运行指南](references/runbook.md)。可选画风见 [纸片拼贴画风](references/paper-collage-style.md)。`examples/library/` 只是一个中国南方小城图书馆的原创测试样例，用来示范“视觉语言不改变内容题材”，不是技能的主题限制。

## V0.4 质量与兼容边界

V0.4 将“向导 → 分镜 → 表演 → 音频时间轴 → 视听反馈 → 质量闸门 → Remotion”作为一条可追踪流程。质量闸门先修复 Critical/Major 问题，再允许生成预览；局部问题只回到对应模块处理。版本升级不改变用户主题，也不把参考图直接当成最终镜头。

V0.4 仍然不承诺精确音素口型、骨骼绑定、完整逐帧动画、自动抠图或无人审核的全自动成片。`motion_plan.version: "0.3"`、其他 JSON 合同的 `0.1` 版本和旧的 0.2 迁移入口继续可读；只有在合同真的发生不兼容变化时才另开 schema 版本。

下一阶段的优化边界见 [V0.5 优化路线](references/v05-roadmap.md)：优先增加可检查的头部、手部、道具和界面局部表演，改善配音与停顿，再扩展到完整短话；不以持续运动或镜头推拉替代角色表演。

## V1.0 总控层

V1.0 在 V0.4 执行层之上增加项目状态机（INIT、CHARACTER、STORY、STORYBOARD、ANIMATION、AUDIO、PERFORMANCE、COMPOSITION、QUALITY_CHECK、PREVIEW、REVISION、FINAL）、入口分流、最小提问、用户反馈路由和最小修改原则。需要恢复或交接项目时使用 [V1.0 项目状态机](references/project-state.md) 与 `scripts/project_state.py`。完整规则见 [V1.0 总控系统](references/v10-control-system.md)。V1.0 当前为候选版，不改变 V0.4 的 JSON 合同、固定镜头和本地素材边界。

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
