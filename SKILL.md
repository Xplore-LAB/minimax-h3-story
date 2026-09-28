# minimax-h3-story (root)

> 这是仓库根目录的 Skill 描述，OpenClaw 会自动扫描到此 `SKILL.md` 并把本仓库作为 Skill 注册。
> 真正的可调用 Skill 在 `skills/minimax-h3-story/`。

## 一句话
把一张起始图变成带立体声的短视频（Multi-Max H3 图生视频）。

## 触发词
- 「给这张图加一段动画」「图生视频」「加声音的短视频」
- "story from this picture" / "image to video with audio"
- "mechanical visual short"

## 详细文档
看 [`skills/minimax-h3-story/SKILL.md`](skills/minimax-h3-story/SKILL.md) 和 [`README.md`](README.md)。

## 调用

CLI：
```bash
bash skills/minimax-h3-story/run.sh \
  --image /path/to/start.jpg \
  --prompt "..." \
  --outdir ./out
```

Agent：
```bash
openclaw agent --model stepfun/step-3.7-flash \
  --message "用 minimax-h3-story skill 帮我把 X.jpg 变成鲸鱼跃水视频"
```