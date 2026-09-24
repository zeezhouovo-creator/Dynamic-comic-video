# V1.0 项目状态机

V1.0 使用 `project_state.json` 保存总控层的当前阶段。它只记录流程状态和待处理事项，不复制 brief、角色、分镜或时间轴数据。

## 使用方式

在独立项目目录中运行：

```powershell
python scripts/project_state.py init <project>
python scripts/project_state.py show <project>
python scripts/project_state.py inspect <project>
python scripts/project_state.py transition <project> STORYBOARD --reason "beats 已确认"
python scripts/project_state.py route-feedback "字幕太快"
```

状态只能沿允许的路径流转；用户反馈通常先进入 `REVISION`，再回到实际需要返工的阶段。`route-feedback` 只给出建议，不直接修改项目文件。

`inspect` 是只读检查：根据项目文件给出建议阶段和缺失项。除了检查 brief、角色、分镜、时间轴和质量报告，它还会读取 `asset_report.json` 的缺失项与指纹变更，以及 `visual_review.json` 的图片路径、逐帧 `reviewed` 标记和 `review_status`。素材缺失或指纹仍待核对时回到 `ANIMATION`；视觉清单不完整或未批准时停在 `PREVIEW`。它不会推断 `FINAL`，因为最终确认必须来自用户，而不是文件是否存在。

## 与制作文件的关系

状态机不代替质量闸门，也不代表视觉验收通过。进入 `PREVIEW` 前仍必须运行质量检查；进入 `FINAL` 前仍必须由用户确认预览。状态记录可以提交到独立生产项目，但不应把用户项目文件放回公共 Skill 仓库。
