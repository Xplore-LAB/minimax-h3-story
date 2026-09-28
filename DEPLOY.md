# DEPLOY.md — 完整部署指南

> 目标：在一台 NVIDIA GB10 (DGX Spark consumer) 上把 **minimax-h3-story** Skill 端到端跑起来。

## 0. 环境需求

| 组件 | 最低 | 推荐 |
|---|---|---|
| GPU | NVIDIA Blackwell 架构（GB10 / GB200）| GB10（DGX Spark）|
| VRAM | 50GB | 100GB+（同时跑 vLLM 时也够）|
| 磁盘 | 60GB | 80GB（模型 + 输出 + docker）|
| OS | Ubuntu 22.04 / 24.04 | Ubuntu 24.04 |
| Docker | 24.0+ | 26+ |
| Python | 3.10+ | 3.12 |
| OpenClaw | ≥2026.9.6 | 最新 |

> **非 Blackwell 显卡**：把 `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` 换成 FP16/BF16 版本（MiniMax H3 官方仓库 release 页有 FP16 clip 备选）。其它节点不用改。

---

## 1. 安装 ComfyUI + MiniMax H3

### 1.1 拉镜像 + 启动容器

```bash
docker run -d \
  --name minimax-h3-comfyui \
  --gpus all \
  --restart unless-stopped \
  -p 0.0.0.0:8188:8188 \
  -v /mnt/minimax-h3/models:/mnt/minimax-h3/models:ro \
  -v /mnt/minimax-h3/output:/mnt/minimax-h3/output \
  -e COMFYUI_PORT=8188 \
  minimax/comfyui:0.30.0-minimax-h3
```

> ⚠️ **绑定 0.0.0.0 才能 LAN 访问**。如果只写 `-p 8188:8188`，Docker 会默认绑 `127.0.0.1`，从其他电脑访问不到。本仓库当前容器已绑 `127.0.0.1`（部署时遗漏），跑完 smoke test 后如需 LAN 访问，按下条命令升级：
> ```bash
> docker stop minimax-h3-comfyui
> docker run -d --name minimax-h3-comfyui --gpus all --restart unless-stopped \
>   -p 0.0.0.0:8188:8188 \
>   -v /mnt/minimax-h3/models:/mnt/minimax-h3/models:ro \
>   -v /mnt/minimax-h3/output:/mnt/minimax-h3/output \
>   minimax/comfyui:0.30.0-minimax-h3
> ```

**验证**：
```bash
curl -sS http://127.0.0.1:8188/system_stats | python3 -m json.tool | head -20
# 期望：含 devices[0].name 含 "GB10" 或 "Blackwell"
```

### 1.2 模型确认

```bash
ls -lh /mnt/minimax-h3/models/checkpoints/ \
       /mnt/minimax-h3/models/clip/ \
       /mnt/minimax-h3/models/vae/
```

期望至少有：
- `minimax_h3_fl2va_pruned_int8_convrot.safetensors`  (~6GB)
- `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`   (~17GB)
- `minimax_h3_video_vae_fp16.safetensors`           (~300MB)
- `minimax_h3_audio_vae_fp32.safetensors`           (~120MB)

> 这些模型合计约 24GB。如未预装，去 MiniMax H3 官方仓库按 `comfy-tensordictionary` 映射章节下载。

### 1.3 Smoke test（2 分钟验证 MiniMax H3 跑通）

```bash
# 用本仓库自带的 workflow + helper.py 跑 4s 视频
bash skills/minimax-h3-story/run.sh \
  --image /mnt/minimax-h3/output/h3_frame.png \
  --prompt "A majestic whale swimming in the deep blue ocean, sunlight rays piercing the water surface, cinematic, stereo sound of ocean waves" \
  --prefix deploy_test \
  --outdir /tmp/deploy_test \
  --seed 42 \
  --timeout 300

# 期望输出：
#   video → /tmp/deploy_test/deploy_test_00001_.mp4
#   audio → /tmp/deploy_test/audio/deploy_test_00001.flac
#   ✅ 完成
ls -lh /tmp/deploy_test/deploy_test_00001_.mp4 /tmp/deploy_test/audio/deploy_test_00001.flac
```

---

## 2. 安装 OpenClaw

### 2.1 装 CLI

```bash
# 见官方最新安装文档（https://docs.openclaw.ai）
curl -fsSL https://openclaw.ai/install.sh | bash

# 验证
openclaw --version
# 期望：OpenClaw 2026.9.6 (eb377ac) 或更新
```

### 2.2 注册本 Skill

```bash
# 把本仓库 skills/minimax-h3-story/ 复制到 OpenClaw workspace
cp -r skills/minimax-h3-story ~/.openclaw/workspace/skills/

# 验证
openclaw skills list | grep minimax-h3-story
# 期望：│ ✓ ready │ minimax-h3-story │ ...
```

### 2.3 配 StepFun（Agent LLM）

```bash
mkdir -p ~/.openclaw/secrets
# 把 <your-stepfun-api-key> 换成你自己从 https://platform.stepfun.com 拿到的 key
echo "<your-stepfun-api-key>" > ~/.openclaw/secrets/stepfun.key
chmod 600 ~/.openclaw/secrets/stepfun.key

# 配 OpenClaw provider + key_file
openclaw providers add stepfun \
  --base-url https://api.stepfun.com/step_plan/v1 \
  --key-file ~/.openclaw/secrets/stepfun.key

# 验证
openclaw providers list | grep stepfun
```

> StepFun API key 仅用于 Agent 编排，**不**用于图像/视频生成。如果不想用云端 Agent，可以换成 vLLM 本地部署的 Qwen3.6：
> ```bash
> docker run -d --name vllm-qwen36 --gpus all -p 8000:8000 \
>   -v /mnt/qwen36/model:/model:ro \
>   vllm/vllm-openai:latest \
>   --model /model --served-model-name qwen3.6-35b-a3b \
>   --moe-backend flashinfer_cutlass --tool-call-parser qwen3_xml \
>   --reasoning-parser qwen3
> ```

---

## 3. 端到端测试

### 3.1 CLI 入口（产物输出）

```bash
bash skills/minimax-h3-story/run.sh \
  --image assets/h3_frame.png \
  --prompt "..." \
  --outdir ./out
```

### 3.2 Agent 入口（自然语言）

```bash
openclaw agent --model stepfun/step-3.7-flash \
  --message "用 minimax-h3-story skill 帮我把 assets/h3_frame.png 变成鲸鱼跃水视频"
```

期望：
- Agent 自动识别 Skill
- 调 helper.py → 调 ComfyUI
- 收到 mp4 + flac 落到 outdir
- Agent 在回复里附上文件路径

### 3.3 排错

| 现象 | 排查 |
|---|---|
| ComfyUI `connection refused` | `docker ps \| grep minimax` 看容器在不在；`docker logs minimax-h3-comfyui` 看启动日志 |
| MiniMax H3 出 CUBLAS error | `docker restart minimax-h3-comfyui` 后重试 |
| Agent 看不到 Skill | `openclaw skills list \| grep h3`；状态应是 `ready` 且 `Visible to model: yes` |
| Agent 汇报与产物对不上 | **以磁盘文件为准**，StepFun 推理模型对工具结果会"优化描述" |
| mp4 出来了 flac 没出来 | 检查 helper.py 是否用最新版（`outputs[].audio` 字段已收集）|

---

## 4. 性能参考

| 模式 | 4s 视频 + 立体声 | 备注 |
|---|---|---|
| 首次（KV cache 冷启）| ~127s | smoke test 实测 |
| 重复任务 | ~80-100s | KV cache 复用 |
| 排队中（多 Skill 同时跑）| 200s+ | MiniMax H3 单卡只能串行 |
| VRAM 占用 | ~50GB | 跑完自动释放 |

> ⚠️ MiniMax H3 同时只能跑一个任务，多 Skill 并发需要排队。

---

## 5. 升级

```bash
# 升级 ComfyUI 容器（保留模型 + 输出）
docker pull minimax/comfyui:0.30.0-minimax-h3
docker stop minimax-h3-comfyui && docker rm minimax-h3-comfyui
docker run -d --name minimax-h3-comfyui --gpus all -p 8188:8188 \
  -v /mnt/minimax-h3/models:/mnt/minimax-h3/models:ro \
  -v /mnt/minimax-h3/output:/mnt/minimax-h3/output \
  minimax/comfyui:0.30.0-minimax-h3

# 升级 OpenClaw
curl -fsSL https://openclaw.ai/install.sh | bash
```

---

_最后更新：2026-09-28 07:05_