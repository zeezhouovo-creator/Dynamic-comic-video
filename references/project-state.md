# V1.0 项目状态机

V1.0 使用 `project_state.json` 保存总控层的当前阶段。它只记录流程状态和待处理事项，不复制 brief、角色、分镜或时间轴数据。

## 使用方式

在独立项目目录中运行：

```powershell
python scripts/project_state.py init <project>
python scripts/project_state.py show <project>
python scripts/project_state.py inspect <project>
python scripts/project_state.py review <project> --approve --reviewer "name"
python scripts/project_state.py review <project> --reject --note "shot_002 接缝明显"
python scripts/project_state.py revision add <project> --text "字幕太快" --shot shot_002
python scripts/project_state.py revision update <project> rev_001 --status resolved --note "已重新预览"
python scripts/project_state.py transition <project> STORYBOARD --reason "beats 已确认"
python scripts/project_state.py route-feedback "字幕太快"
python scripts/deliver.py <project>
```

状态只能沿允许的路径流转；用户反馈通常先进入 `REVISION`，再回到实际需要返工的阶段。`route-feedback` 只给出建议，不直接修改项目文件。

`inspect` 是只读检查：根据项目文件给出建议阶段和缺失项。它会先用 `schemas/*.schema.json` 检查 brief、角色、分镜和时间轴，并在结果中给出 `schema_errors` 的具体 JSON 路径；随后检查素材报告的缺失项与指纹变更、返工台账和视觉复核清单。素材缺失或指纹仍待核对时回到 `ANIMATION`；存在未解决返工时进入 `REVISION`；视觉清单不完整或未批准时停在 `PREVIEW`。它不会推断 `FINAL`，因为最终确认必须来自用户，而不是文件是否存在。

打开首、中、末帧并确认当前预览后，使用 `review --approve` 写入批准状态；发现问题则使用 `review --reject --note`，下一次 `inspect` 会路由到 `REVISION`。批准记录绑定 brief、角色、分镜、时间轴、素材报告、质量报告、MP4 和复核图片的 SHA-256 指纹。任一输入被修改后，旧批准会自动失效，必须重新渲染并复核。

反馈可以通过 `revision add` 写入 `revision_log.json`，它会沿用 `route-feedback` 的模块路由，并记录镜头、源指纹和状态。处理完成后使用 `revision update ... --status resolved` 关闭；有未关闭记录时，`inspect` 不会把项目误判为可交付。

## 与制作文件的关系

状态机不代替质量闸门，也不代表视觉验收通过。进入 `PREVIEW` 前仍必须运行质量检查；进入 `FINAL` 前仍必须由用户确认预览。状态记录可以提交到独立生产项目，但不应把用户项目文件放回公共 Skill 仓库。

`deliver.py` 是交付前的机器闸门，不会替用户做视觉判断。它要求质量报告通过、`visual_review.json` 已批准且指纹新鲜、返工台账没有 `open`/`in_progress` 项，并用 `ffprobe` 检查复核所指向的 MP4。结果保存为 `delivery_report.json`；只有 `status: "PASS"` 才能进入最终交付说明。
