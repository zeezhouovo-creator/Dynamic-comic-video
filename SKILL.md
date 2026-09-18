---
name: manga-motion-video
description: Turn original stories or scripts into 2D hand-drawn manga motion videos using identity-only character references, narrative beats, fresh shot compositions, master-aligned layers and Remotion MP4 rendering. Use for narrative motion comics and layered parallax, not full frame-by-frame animation or lip sync.
---

# Manga Motion Video — V0.1

把用户原创内容转为可追溯的分镜、逐镜新绘的 master、对齐图层和 Remotion MP4。V0.1 的最小闭环是 Agent 编导与图像工具协作，加本地确定性校验和渲染；不是无需图像工具的自动绘制服务。

## 不可丢失的创作约束

- 日漫二维手绘仅是视觉语言。保留原文的国家、时代、人物关系、题材、因果与情绪，不擅自加入日本街景、校服、神社或日文。缺失的关键设定先询问，其余假设写入 brief。
- Character Reference 只锁脸、发型、服装、比例和辨识特征。参考图中的姿势、表情、景别、光线、构图不锁定。每个人物镜头按剧情重新绘制表演；禁止反复粘贴一张固定立绘。
- 先从原文提取 Narrative Beats（信息、行动或情绪的变化），再为每个 beat 设计一个或多个 Shots。不要按相同秒数或句子机械切镜。
- 先完整 master composition，再以该 master 分离/重建图层。统一画布、坐标、透视、尺度与光向；角色移开后背景必须补全。不能独立生成几张互不对齐的图来凑层。
- 视差只是演出补充，不能代替逐镜新动作。V0.1 支持硬切、缓慢平移/推拉、背景/人物/前景不同速度；不实现嘴型、骨骼绑定、完整逐帧动画或自动姿态迁移。

## 工作流程与交付

1. **Visual / Production Brief**：保存原文、内容保留项、文化时空、视觉语言、情绪和尺寸/帧率/总帧数为 `production_brief.json`。
2. **Character Planning → Reference**：建立 `characters.json`，选择需要保持一致的角色，写 identity 与身份参考提示词。使用可用图像工具生成 reference 并目视核对，再设 `status: ready`。无人物项目允许空列表。不要为了凑人物改写原文。
3. **Narrative Beats → Storyboard Director**：在 `storyboard.json` 先写 beats 的原文摘录与变化，再写 shots；每镜明确目的、人物动作/表情/视线、景别、角度、构图、连续性与拟分层理由。无意义的 foreground/effects 不拆。
4. **Shot Prompt Compiler**：运行 `compile`，得到角色参考与逐镜 master 的结构化提示词。编译只整理已完成的导演决策，不创造新剧情。把 reference 作为身份参考输入图像工具，执行逐镜新绘，保存指定 `master.png`。
5. **Master QC → Layer Planning**：先核对 master 的身份、剧情表演、构图与重复性，再确认该镜实际所需图层。根据 [分层协议](references/layer-protocol.md) 提取人物、补全背景、分离前景/特效，保存透明 PNG 与合成预览。若图像工具无法分层，明确缺少的资产并停在这一阶段；不要悄悄降级为整图推拉。
6. **Motion Director**：根据叙事情绪填写 `motion_plan.json`，采用镜头内帧数与明确起止变换。先小幅视差；检查首/中/末帧、遮挡关系、边缘和补洞区域。通过目视复核后更新 review 字段。正式素材必须 `asset_mode: production`。
7. **QC → Remotion → MP4**：运行素材校验、prepare、Remotion 渲染。复查所有切点前后帧和每镜首/中/末帧；报告测试/正式素材状态、时长、尺寸、遗留问题与输出位置。

数据契约见 [契约说明](references/contracts.md) 与 `schemas/*.schema.json`；可执行步骤见 [运行指南](references/runbook.md)。`examples/library/` 是中国南方小城图书馆的原创测试故事，示范“视觉语言不改变文化题材”。

## Repetition QC

自动检查：同一角色相邻出场的 pose_tag 相同；连续三镜的 shot-size、angle 或 composition_tag 相同；人物 PNG 内容完全相同则阻止准备渲染。输出 `qc_report.json`。

标签和文件哈希不能证明视觉多样性。Agent 必须查看逐镜接触表，比较实际肢体轮廓、面部表情、主体占画面比例、机位与视觉重心；改标签不能消除问题。叙事需要的重复在 `repetition_exception` 写具体理由，警告保留供复核。近似重复立绘即使哈希不同也应返工。不要为了多样性破坏空间连续性。

## 工具与隐私

优先使用当前环境可用且已获授权的图像生成/编辑工具；使用时读取其技能说明。此项目不内置任何云端生成 API，也不读取或转发凭据。API Key、Token、密码不得写入 JSON、提示词、浏览器 public、日志或交付包，不得上传网络。若用户粘贴明文密钥，提示风险并指导其改存本地环境变量/加密配置，不用该明文密钥请求网络。配置帮助只询问本地文件路径并提供用户本地执行脚本。需要凭据的外部适配器必须遵守用户密钥仅本地使用的限制；不兼容时明确说明。

## 项目布局

```text
manga-motion-video/
  SKILL.md
  schemas/                 四份严格 JSON Schema (2020-12)
  examples/library/        四份示例输入；测试素材、提示词与 QC 报告
  scripts/                 validate / compile / prepare 与本地 fixture
  references/              契约、分层协议、运行指南
  assets/remotion/         固定依赖版本的渲染模板
  requirements.txt
```

生产项目另存，不覆盖技能示例。按阶段恢复：已确认的 brief/角色身份保持，修改某镜只重做该镜 master、图层与对应 motion/QC；不为局部修改重写全片。
