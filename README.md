# Dynamic-comic-video

将各种原创内容转为可追溯的分层动态视频。内容可以是故事、教育、科普、历史、产品说明、品牌叙事、幻想或用户指定的其他主题。项目把角色身份、叙事节拍、镜头设计、母版画面、图层和 Remotion 渲染拆成可检查的本地文件，避免把固定角色立绘反复用作镜头表演。

日漫二维手绘只是可选视觉语言，不能决定内容主题。用户可以指定写实插画、绘本、欧美动画、历史复原、科普图解、赛博朋克或品牌风格；技能必须保留用户原本的地域、时代、题材、事实边界和叙事目的。角色参考图只约束脸、发型、服装、比例等身份；每个镜头仍根据内容产生新的动作、表情、景别和构图。

## V0.1 已实现

- `production_brief.json`、`characters.json`、`storyboard.json`、`motion_plan.json` 的严格 Schema 与跨文件检查。
- Narrative Beats 先于 Shots 的分镜工作流。
- “完整 master → 对齐提取/重建图层”的图层协议，包含背景补全要求。
- pose、景别、角度、构图标签的重复预警，以及重复人物 PNG 的阻断检查。
- Remotion 的基础硬切、推拉与 2.5D 视差输出。
- 不含口型、配音、音乐、骨骼绑定或完整逐帧动画。

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

示例使用本地几何测试素材，验证数据、透明层、视差和 MP4 管线；它不是某种主题的成片。正式项目需要按 `SKILL.md` 与 `references/layer-protocol.md` 生成并检查真实 master 和分层素材。

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
