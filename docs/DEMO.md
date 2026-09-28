# DEMO.md — 录屏脚本（用户照着敲即可录）

> 目标：录制一段 **2-3 分钟**的端到端演示视频，从「自然语言指令」到「短视频生成完成」。

## 0. 录屏准备

- 终端：tilix / iTerm2 / Windows Terminal 任一
- 字号调大（≥16pt）便于观看
- 分辨率：1920×1080 起
- 麦克风：可选（不用配解说也行，字幕自加）
- 录屏软件：OBS / SimpleScreenRecorder / 浏览器录屏插件任一

## 1. 开场（30s）

### 1.1 屏幕展示

```bash
# 终端标题：minimax-h3-story — 图生视频端到端演示
cd ~/minimax-h3-story
```

旁白（可选）："这是 NVIDIA DGX Spark Hackathon 的参赛项目 minimax-h3-story，Xplore-LAB 队作品。核心是用 OpenClaw Skill 范式调本机 MultiMax H3 把一张静态图变成带声音的短视频。"

### 1.2 项目结构速览

```bash
ls -la skills/minimax-h3-story/
# SKILL.md  workflow.json  helper.py  run.sh
```

旁白："何老师 workshop 2 的 4 文件 Skill 范式。后端从 FLUX+PuLID 换成本机的 MultiMax H3。"

---

## 2. CLI 演示（60s）

### 2.1 看 SKILL.md 触发词

```bash
cat skills/minimax-h3-story/SKILL.md | head -30
```

旁白："SKILL.md 第一段是 YAML 头，description 写明触发词（'给这张图加一段动画'、'图生视频' 等）。"

### 2.2 跑命令

```bash
# 展示起始图
file assets/h3_frame.png
# 展示 prompt
echo "Prompt: A majestic whale swimming in the deep blue ocean, sunlight rays piercing the water surface, cinematic, stereo sound of ocean waves"

# 跑！
bash skills/minimax-h3-story/run.sh \
  --image assets/h3_frame.png \
  --prompt "A majestic whale swimming in the deep blue ocean, sunlight rays piercing the water surface, cinematic, stereo sound of ocean waves" \
  --prefix demo_cli \
  --outdir ./demo_out \
  --seed 42
```

### 2.3 等结果（约 130s）

旁白（可加快）："helper.py 上传图片、构造 workflow、提交 prompt、轮询、下载。约 130 秒出结果。"

### 2.4 看产物

```bash
ls -lh demo_out/ demo_out/audio/
file demo_out/*.mp4 demo_out/audio/*.flac

# 在 mpv/vlc 里播放
mpv demo_out/demo_cli_00001_.mp4
# 视频里看见鲸鱼 + 听见 ocean waves（立体声）
```

旁白："H.264 mp4 + FLAC 立体声。MiniMax H3 在生成视频的同时输出音频。"

---

## 3. Agent 演示（60s）

### 3.1 看 Skill 在 OpenClaw 里

```bash
openclaw skills info minimax-h3-story
```

旁白："状态 ready。Visible to model: yes，Available as command: yes。"

### 3.2 自然语言触发

```bash
# 强调这是自然语言，不是 CLI 命令
openclaw agent --model stepfun/step-3.7-flash \
  --message "用 minimax-h3-story skill 帮我把 assets/h3_frame.png 变成一段鲸鱼跃水视频"
```

### 3.3 看 Agent 自主执行（约 130s）

旁白（可加快）："Agent 自主识别 Skill、调 helper.py、产出 mp4 + flac。StepFun 推理模型对工具结果会'优化叙述'，以磁盘文件为准。"

### 3.4 看产物

```bash
ls -lh /tmp/h3_agent_demo/ /tmp/h3_agent_demo/audio/
mpv /tmp/h3_agent_demo/whale_v3_final.mp4
```

---

## 4. 平台适配（30s）

### 4.1 展示 GB10 / NVFP4

```bash
nvidia-smi | head -20
# 期望：NVIDIA GB10 ... 130GB
```

```bash
ls -lh /mnt/minimax-h3/models/clip/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors
```

旁白："Qwen3-VL-32B 用 NVFP4 量化。GB10 Blackwell 原生支持 4-bit 浮点，不需要重新量化。"

### 4.2 ComfyUI 容器

```bash
docker ps | grep minimax-h3-comfyui
curl -sS http://127.0.0.1:8188/system_stats | python3 -m json.tool | head -10
```

旁白："ComfyUI 0.30.0 + MiniMax H3 节点已预编译进容器。"

---

## 5. 总结（15s）

旁白："核心贡献是 4 文件 Skill 范式，后端可插拔。我们用本机已部署的 MiniMax H3 填充，零新增下载。Agent 可自然语言调用。完赛保底上上。"

---

## 6. 字幕（可选）

提交 B站时建议加的字幕节点：

```
00:00 - minimax-h3-story 介绍
00:30 - CLI 入口演示
01:30 - Agent 自然语言触发演示
02:30 - GB10 + NVFP4 平台适配
03:00 - 总结
```

---

## 7. 备选演示（如果时间充裕）

### 7.1 不同 prompt 对比

```bash
# 同一张图，不同 prompt
bash run.sh --image assets/h3_frame.png \
  --prompt "A majestic whale swimming slowly in deep ocean, mysterious, slow motion, deep ambient sound" \
  --prefix demo_slow --outdir ./demo_out

bash run.sh --image assets/h3_frame.png \
  --prompt "A dramatic whale breaching the ocean surface, water splashing, sunlight, energetic, dynamic percussion" \
  --prefix demo_dramatic --outdir ./demo_out
```

### 7.2 数据导出（DIFFICULT）

```bash
# 演示多个 Skill 串行（start image → animation → remix）
# 视频暂时略，可作为 README 的 future work
```

---

_最后更新：2026-09-28 07:05_