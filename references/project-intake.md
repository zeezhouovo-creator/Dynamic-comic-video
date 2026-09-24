# 项目启动兼容入口

本文件保留给旧引用。新任务的入口分流、最小提问和已有素材授权以 [动态漫画制作向导](production-wizard.md) 与 [V1.0 总控与恢复规则](v10-control-system.md) 为准；这里不再维护第二套制作流程。

启动时先判断用户提供的是独立分镜、角色参考、剧情/文案、已有项目还是单纯想法。读取对话和目录中已经明确的内容，只询问会改变题材、事实边界、素材用途或阻止下一阶段的缺项。

角色参考只锁身份锚点，不锁姿势、表情、景别和构图。已有独立分镜是否成为最终 master，遵循总控的复用边界：明确授权复用时核对后保留合格素材，仅作参考时按剧情新绘，用途不明且会改变重绘成本时再询问。

当前执行链为：

```text
用户内容 → production_brief.json → characters.json → Narrative Beats / storyboard.json
→ master 与对齐图层 → motion_plan 0.3 → 音频/字幕/动作统一时间轴
→ 质量闸门 → Remotion 预览/MP4 → 用户复核与局部返工
```

新项目默认 `performance.mode: sequential-comic`，固定机位，人物通过局部动作和姿态切换表演。明确要求 `fixed-camera-micro` 或其他兼容模式时才读取对应规则；不使用视差或镜头运动伪造人物动作。

`source_panel` 只记录该 beat/shot 的来源标识（用户授权复用的来源图、或 Skill 生成的 panel/master）；它不是复用授权本身，也不能替代 master、图层和视觉复核。
