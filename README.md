# Dynamic-comic-video

将各种原创内容转为可追溯的分层动态视频。内容可以是故事、教育、科普、历史、产品说明、品牌叙事、幻想或用户指定的其他主题。项目把角色身份、叙事节拍、镜头设计、母版画面、图层和 Remotion 渲染拆成可检查的本地文件，避免把固定角色立绘反复用作镜头表演。

日漫二维手绘只是可选视觉语言，不能决定内容主题。用户可以指定写实插画、绘本、欧美动画、历史复原、科普图解、赛博朋克或品牌风格；技能必须保留用户原本的地域、时代、题材、事实边界和叙事目的。角色参考图只约束脸、发型、服装、比例等身份；每个镜头仍根据内容产生新的动作、表情、景别和构图。

项目也提供可选的 `paper-collage` 画风预设，借鉴纸片分层视频的视觉语法：纸张边缘、轻微套印错位、纸纤维与印刷颗粒、分层投影、有限调色板和克制的 2.5D 景深。这个预设只改变表现形式，不改变内容主题；未选择时不会自动套用。

这是一个生成技能仓库，不是用户内容仓库。每次用户提供的故事、角色、参考图、master、图层和成片都应在独立的本地工作目录中生成；`projects/` 已被 Git 忽略，不会自动提交或上传。仓库只保存通用流程、Schema、提示词规则、渲染模板和无关具体用户故事的测试夹具。

## V0.3 候选版

默认制作固定构图的连续分镜式动态漫画。新增本地 WAV 配音、同步字幕、音量驱动的简单嘴部开合、局部表情替换、素材缺项/变化报告和指定镜头编译、渲染。完整用法和真实样片验收标准见 [V0.3 制作闭环](references/v03-production.md)。不是精确音素口型、自动抠图或无人审核的全自动成片；正式版本标签须通过真实3—5镜样片验收后发布。

分镜生成统一使用 [分镜生成主规则](references/storyboard-director.md)：同一空间连续、背景构图按独立机位变化、角色身份连续、说话与倾听均有表演、切镜有因果，并输出17项逐镜审阅稿。旧五项简表已替换。

已有能力：

- `production_brief.json`、`characters.json`、`storyboard.json`、`motion_plan.json` 的严格 Schema 与跨文件检查。
- Narrative Beats 先于 Shots 的分镜工作流。
- “完整 master → 对齐提取/重建图层”的图层协议，包含背景补全要求。
- pose、景别、角度、构图标签的重复预警，以及重复人物 PNG 的阻断检查。
- Remotion 局部部件平移、关节旋转、透明度关键帧，以及对齐姿态图片切换；硬切和视差作为辅助。
- 动作意图与静止理由校验，阻止纯推拉冒充角色表演。真实动作质量仍须目视复核。
- 不含口型、配音、音乐、骨骼绑定或完整逐帧动画。

新制作使用 motion_plan 0.2，其他合同保持 0.1。见 [有限动画协议](references/limited-animation.md)。旧 library 示例保留为视差回归测试；运行 `python scripts/make_acting_fixture.py ../acting-fixture` 生成固定相机下的通用抬臂/眨眼测试，再用 prepare 与 Remotion 渲染。它验证执行能力，不代表正式美术质量。

## 快速验证

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts\test_pipeline.py
.\.venv\Scripts\python scripts\pipeline.py compile examples\library
.\.venv\Scripts\python scripts\make_fixture.py examples\library
.\.venv\Scripts\python scripts\pipeline.py prepare examples\library --renderer ..\manga-renderer
```

随后在 `../manga-renderer` 中运行：

```powershell
npm ci
npm run render
```

示例使用本地几何测试素材，验证数据、透明层、视差和 MP4 管线；它不是某种主题的成片。正式项目需要按 `SKILL.md`、`references/content-intake.md` 与 `references/layer-protocol.md` 在独立工作目录中生成并检查真实 master 和分层素材。

## 目录

```text
schemas/                 JSON Schema
examples/library/        一个可执行的三镜主题样例与测试素材
scripts/                 校验、提示词编译、渲染准备、测试
assets/remotion/         固定版本的 Remotion 模板
references/              数据契约、图层协议、运行和验证说明
SKILL.md                 Agent Skill 正式工作协议
```

## 长期维护方向

近期版本将优先补齐真实图像生成/编辑适配层、可视化接触表、镜头审核界面与生产项目脚手架。任何扩展都应保持：用户原文不被改题材、角色参考不锁镜头姿势、master 是图层对齐的唯一视觉基准。

开发规范、运行细节和已验证边界见 [SKILL.md](SKILL.md) 与 [验证记录](references/validation.md)。
