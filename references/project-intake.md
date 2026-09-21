# 新项目启动引导

新项目开始时先读取 [动态漫画制作向导](production-wizard.md)，先判断用户是否已有独立分镜、角色设定或剧情，再只询问当前必要的信息。

独立分镜可以作为已有镜头进入动态设计；角色立绘、三视图和设定图用于建立身份参考；画风参考用于分析视觉语言。完整漫画或四格图不是默认入口，只有用户明确选择时才识别真实格子边界并逐格评估，不能机械切割后直接当作正式动态镜头。

正式流程固定为：用户原创内容 → Visual/Production Brief → Character Planning 与 Character Reference → 用户确认角色身份 → Narrative Beats → Storyboard Director → Shot Prompt Compiler → Skill 生成 Master Shot → Layer Planning → 分离/重建 background、character、foreground、effects → 基础 Motion Director/Parallax → 配音/字幕/音效 → Remotion 输出 MP4。角色身份确认前不批量生成正式分镜。

每镜写 `source_panel` 时，它表示 Skill 生成的 panel/master 标识，不表示用户上传的漫画图片。
