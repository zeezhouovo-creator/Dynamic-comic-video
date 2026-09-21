# Dynamic-comic-video

这是一个关于制作动态漫画视频的 Agent Skill 尝试。它用于探索如何把故事、角色、漫画分镜、局部人物动作、配音字幕和 Remotion 输出组织成连续分镜式动态漫画视频。

项目目前处于持续试验和迭代阶段，欢迎项目组成员通过 GitHub 共同完善。真实故事、角色图和成片留在各自本地。

## 团队安装

### 只安装 Skill

如果成员使用 Codex，只需要把公开 GitHub 仓库安装到自己的 Skill 目录。安装脚本会把它放到 `~/.codex/skills/dynamic-comic-video`，下一轮对话即可使用：

```powershell
python "$env:USERPROFILE\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py" `
  --repo zeezhouovo-creator/Dynamic-comic-video `
  --path . `
  --name dynamic-comic-video
```

更新版本时重新执行安装，或进入已安装目录执行 `git pull`。如果团队成员使用其他 Agent 宿主，只需将仓库根目录作为 Agent Skill 导入，并确保 `SKILL.md` 位于根目录。

### 需要输出 MP4

Skill 规则本身不需要 npm。只有执行 Remotion 视频渲染时才需要 Node.js 和 npm：

```powershell
git clone https://github.com/zeezhouovo-creator/Dynamic-comic-video.git
Set-Location Dynamic-comic-video
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
python scripts\pipeline.py validate examples\library
python scripts\quality_gate.py examples\library
python scripts\pipeline.py prepare examples\library --renderer ..\manga-renderer
Set-Location ..\manga-renderer
npm ci
npm run render
```

真实项目要在仓库外建立独立工作目录；用户故事、角色图片、配音和成片不提交到这个公共仓库。npm 只负责安装和运行 Remotion 渲染器，Python 负责 Skill 的校验、编译和质量闸门。

### 一体化安装

如果希望一次准备好 Skill、Python 校验环境和 Remotion 渲染依赖，可以在仓库根目录运行安装脚本：

```powershell
.\scripts\setup.ps1
```

脚本会把完整 Skill 安装到 `$env:USERPROFILE\.codex\skills\dynamic-comic-video`，在该目录创建本地 Python 虚拟环境，并在 `assets/remotion` 中执行 `npm ci`。macOS/Linux 使用：

```bash
bash scripts/setup.sh
```

安装后仍然把每个故事项目放在仓库之外；Skill 和渲染器是一套安装，用户内容和成片是另一套本地项目。不要把 `node_modules`、`.venv`、API Key 或用户内容提交到 GitHub。

### 从 GitHub 手动复制

```powershell
git clone https://github.com/zeezhouovo-creator/Dynamic-comic-video.git
Copy-Item -Recurse .\Dynamic-comic-video "$env:USERPROFILE\.codex\skills\dynamic-comic-video"
```

如果已有旧版本，使用 `git pull` 更新。每位成员都应在自己的本地环境中配置依赖和渲染器；不要把 API Key 写入仓库。

## 协作方式

日常修改请从 `main` 创建分支并提交 Pull Request。提交前运行 [贡献指南](CONTRIBUTING.md) 中的测试。版本变化记录在 [CHANGELOG.md](CHANGELOG.md)，稳定版本使用 Git tag 标记。

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
