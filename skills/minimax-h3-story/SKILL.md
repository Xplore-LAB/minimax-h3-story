---
name: minimax-h3-story
description: "把一张起始图变成带立体声的短视频（Multi-Max H3 图生视频）。适用：故事开场、概念演示、动态预览。当用户说「给这张图加一段动画」「图生视频」「加声音的短视频」「story from this picture」「mechanical visual short」时使用。"
user-invocable: true
---

# minimax-h3-story — 图像→带声音短视频

## 触发词

- 「给这张图加一段动画」「图生视频」
- 「加声音的短视频」「给我做个小故事片」
- "story from this picture" / "image to video with audio"
- "mechanical visual short"

## 何时使用

适合 4-8 秒的短视频生成（带立体声环境音或简单音效）。后端是本机 GB10 上的 Multi-Max H3（FL2VA INT8 + Qwen3-VL-32B NVFP4），通过 ComfyUI HTTP API 调度。

**不适合**：
- 真实人物长视频（Multi-Max H3 在人脸上容易崩）
- 超过 96 帧的（默认 96 = 4s @ 24fps）
- 需要电影级运镜 / 复杂运镜的（Multi-Max H3 镜头语言简单）

## 调用规范

```bash
bash skills/minimax-h3-story/run.sh \
  --image /path/to/start.jpg \
  --prompt "A majestic whale swimming in the deep blue ocean, sunlight rays piercing the water surface, cinematic, stereo sound of ocean waves" \
  --outdir ./output
```

参数：
- `--image` 必填：起始图（png/jpg/webp）
- `--prompt` 必填：描述视频内容 + 音频（建议在末尾加 "stereo sound of ..."）
- `--outdir` 选填，默认 `./output`
- `--seed` 选填，默认 42
- `--length` 选填，默认 96（4 秒 @ 24fps）

输出：
- `<outdir>/<prefix>.mp4` — 视频
- `<outdir>/audio/<prefix>.flac` — 立体声音频
- `<outdir>/.prompt_id.json` — ComfyUI prompt_id 与元数据

## 工作流（核心 14 节点）

1. UNETLoader → Multi-Max-H3-FL2VA INT8
2. CLIPLoader → Qwen3-VL-32B NVFP4 (minimax 类型)
3-4. VAELoader × 2（视频 + 音频）
5. EmptyMiniMaxH3LatentAV（608×352×96）
6. MiniMaxH3SigmaShift（video=12.0, audio=3.0）
7. **MiniMaxH3ImageToVideo**（接收 image + prompt）
8. CLIPTextEncode（negative: "blurry, low quality, deformed, camera shake"）
9. KSampler（Euler / simple / cfg=1.0 / steps=20）
10. VAEDecode（视频）
11. VAEDecodeAudio（音频）
12. CreateVideo（fps=24）
13. SaveVideo
14. SaveAudio

## 与何老师 workshop 2 (Build A Claw) 的对应

| 何老师 | 我们 |
|---|---|
| `face_workflow.json`（FLUX+PuLID）| `workflow.json`（Multi-Max H3） |
| `superhero_helper.py` | `helper.py` |
| `run_helper.sh` | `run.sh` |
| 输入：人脸照 | 输入：起始图 |
| 输出：超级英雄照片 | 输出：带声音短视频 |