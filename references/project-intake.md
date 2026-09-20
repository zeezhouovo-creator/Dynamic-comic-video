# 新项目启动引导

新项目开始时先询问用户的主题或故事，不先要求上传漫画图片。随后依次确认受众、视觉语言和最终比例（9:16、16:9、4:3、1:1 或自定义），一次只询问当前必要的信息。

图片可以作为可选的角色身份参考或画风参考。Skill 只分析脸、发型、服装、比例、线条、上色、光影和背景复杂度，然后重新生成角色参考和所有正式漫画分镜；完整漫画、四格图或单张分镜不得直接成为最终 master 或视频镜头。

正式流程固定为：用户原创内容 → Visual/Production Brief → Character Planning 与 Character Reference → 用户确认角色身份 → Narrative Beats → Storyboard Director → Shot Prompt Compiler → Skill 生成 Master Shot → Layer Planning → 分离/重建 background、character、foreground、effects → 基础 Motion Director/Parallax → 配音/字幕/音效 → Remotion 输出 MP4。角色身份确认前不批量生成正式分镜。

每镜写 `source_panel` 时，它表示 Skill 生成的 panel/master 标识，不表示用户上传的漫画图片。
