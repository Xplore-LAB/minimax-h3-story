# minimax-h3-story — Multi-Max H3 图生视频 Skill

> **NVIDIA DGX Spark Hackathon 参赛作品**
> **队伍**：Xplore-LAB · **方向**：复现何老师 Workshop 2（Build A Claw）的 4 文件 Skill 范式，后端用本机已部署的 Multi-Max H3 填充
> **核心问题**：把一张静态起始图 + 一段文字描述，生成 **带立体声的短视频**，整套流程 Agent 可调用、可在本地 GB10 上完全离线完成

---

## 作品特点（Why this is different）

- **后端可插拔**：沿用何老师 workshop 2 的 4 文件 Skill 结构（`SKILL.md` + `workflow.json` + `helper.py` + `run.sh`），后端从 FLUX+PuLID 换成本机已部署的 **Multi-Max H3**（FL2VA + Qwen3-VL 32B NVFP4）。**零新增下载**：模型已在 `/mnt/minimax-h3/models/`，总计 42.5GB。
- **真带音频**：MiniMax H3 在生成视频的同时输出 **立体声 FLAC**（节点 4/11 + 14）。多数开源底图只给视频，MiniMax H3 是少数同时给音频的开源方案。
- **Agent 可调**：Skill 在 OpenClaw 里 `Visible to model: yes`，Agent 收到自然语言指令（"把 X.jpg 变成鲸鱼跃水视频"）后能自主发现并执行 Skill，端到端产 mp4 + flac。
- **GB10 真原生适配**：Multi-Max H3 用了 GB10 Blackwell 架构原生的 **NVFP4 量化**（Qwen3-VL-32B NVFP4 AWQ），不需要重新量化；其它非 Blackwell 显卡需要把 NVFP4 节点换成 FP16/INT8 才能跑。

## 核心亮点（Headline）

1. **零云依赖、零新增下载**：所有模型已在本地磁盘
2. **完全离线**：ComfyUI HTTP API → 本机 MiniMax H3 → 文件落盘，无任何对外网络调用（除 Skill 注册到 OpenClaw）
3. **真声音**：立体声 FLAC（不是后期合成）
4. **复用性强**：4 文件 Skill 结构可换 backbone（FLUX / SDXL / Wan / MiniMax H3 / SVD），helper.py 是 thin wrapper over ComfyUI HTTP API

## 技术方案（How）

```
[用户自然语言] ──► OpenClaw Agent (StepFun step-3.7-flash)
                        │
                        ▼ 自主识别 minimax-h3-story Skill
                  bash run.sh --image X.jpg --prompt "..." --outdir Y
                        │
                        ▼
              helper.py（Python，零依赖 stdlib）
                        │
                        ▼
              ComfyUI HTTP API（端口 8188，本机）
                        │
                        ▼
              Multi-Max H3 工作流（14 节点）
                  ├─ MiniMax-H3-FL2VA INT8  (video backbone)
                  ├─ Qwen3-VL-32B NVFP4     (text encoder, GB10 原生量化)
                  ├─ MiniMax H3 VAE × 2      (video + audio decode)
                  └─ SigmaShift + ImageToVideo + KSampler
                        │
                        ▼
              SaveVideo + SaveAudio
                        │
                        ▼
              mp4 (H.264) + flac (立体声) 落到 outdir
```

### 14 节点 workflow 一览
1. `UNETLoader` — 加载 MiniMax-H3-FL2VA INT8
2. `CLIPLoader` — 加载 Qwen3-VL-32B NVFP4（`type=minimax`）
3. `VAELoader` — 视频 VAE (FP16)
4. `VAELoader` — 音频 VAE (FP32)
5. `EmptyMiniMaxH3LatentAV` — 608×352×96 latent（4s @ 24fps）
6. `MiniMaxH3SigmaShift` — video=12.0, audio=3.0
7. **`MiniMaxH3ImageToVideo`** — 接收起始图 + prompt，输出 positive/latent
8. `CLIPTextEncode` — negative prompt（防抖/防崩）
9. `KSampler` — Euler / simple / cfg=1.0 / steps=20
10. `VAEDecode` — 视频 latent → 帧
11. `VAEDecodeAudio` — 音频 latent → wav
12. `CreateVideo` — fps=24
13. `SaveVideo`
15. `SaveAudio`

## 4 文件 Skill 范式（与何老师 workshop 2 的对应）

何老师 workshop 2 (Build A Claw) 的核心贡献是 4 文件 Skill 范式：

| 何老师 | 本项目 | 改动说明 |
|---|---|---|
| `SKILL.md` | `skills/minimax-h3-story/SKILL.md` | 同构（YAML 头 + 触发词 + 命令规范） |
| `face_workflow.json` (FLUX+PuLID) | `skills/minimax-h3-story/workflow.json` | **核心替换** — 把"人脸→超级英雄照片"换成"起始图→视频+音频" |
| `superhero_helper.py` | `skills/minimax-h3-story/helper.py` | 同构（upload → submit → poll → download） |
| `run_helper.sh` | `skills/minimax-h3-story/run.sh` | 同构 |

**参数化方式**：workflow.json 里所有动态参数（`prompt` / `image` / `seed` / `filename_prefix`）都用合法默认值（空字符串 / 0 / `"h3"`），helper.py 在加载 JSON 后用 Python 端覆盖。这样 workflow.json 保持合法 JSON 可直接被 ComfyUI 加载（方便在 ComfyUI UI 里手动运行），同时 helper.py 控制动态参数。

## 平台适配证据（NVIDIA GB10 + vLLM + OpenClaw + MiniMax H3）

| 组件 | 版本/位置 | 适配证据 |
|---|---|---|
| GPU | NVIDIA GB10 (Grace Blackwell) | VRAM 130GB，Multi-Max H3 跑起来占 ~50GB |
| 文本编码器 | Qwen3-VL-32B **NVFP4** AWQ | GB10 Blackwell 架构原生支持 4-bit 浮点量化，无需重新量化 |
| Video backbone | MiniMax-H3-FL2VA INT8 + ConvRot | ComfyUI MiniMax-H3 节点已预编译进容器 |
| ComfyUI | 0.30.0 @ 8188 (docker container `minimax-h3-comfyui`) | `/upload/image` + `/prompt` + `/history/{id}` + `/view` 四接口均验证通 |
| OpenClaw | 2026.9.6 (eb377ac) | Skill 注册到 `~/.openclaw/workspace/skills/minimax-h3-story/`，状态 `✓ ready` |
| Agent LLM | StepFun `step-3.7-flash` (云端推理) | 仅用于 Agent 编排，**不**用于图像/视频生成（保证多模态推理与图像生成解耦） |
| 推理时计算 | 本机 Multi-Max H3 ~127s / 4s 视频 | 包含 KV cache 预热时间，重复任务可降至 ~80s |

### 本地 vs 云端分工

- **本机 GB10** 负责：图像/视频生成（MiniMax H3）、ComfyUI 调度、Skill 注册与执行、文件落盘
- **云端 StepFun** 负责：Agent 编排（仅在 `openclaw agent --model stepfun/...` 调用时）
- **vLLM / 本地 LLM** 角色：GB10 上同时部署了 `vllm-qwen36-prod`（Qwen3.6-35B-A3B NVFP4，tool-call-parser=qwen3_xml）作为本地 LLM 备选；本项目为 MiniMax H3 让出 115GB VRAM 临时停掉 vLLM，但 DEPLOY.md 提供一键重启命令。Agent LLM 可换成 `openclaw agent --model openai-compatible/...` 指向本地 vLLM，完全离线运行。

![Architecture](docs/architecture.png)

### 真实跑通记录
```
$ bash skills/minimax-h3-story/run.sh \
    --image /mnt/minimax-h3/output/h3_frame.png \
    --prompt "A majestic whale swimming in the deep blue ocean, sunlight rays piercing the water surface, cinematic, stereo sound of ocean waves" \
    --prefix h3_demo --outdir ./out --seed 42

── ① 上传起始图：/mnt/minimax-h3/output/h3_frame.png
── ② 构造 workflow（prompt='A majestic whale swimming in the deep blue ocean, sunlight r…'）
── ③ 提交 /prompt
   prompt_id = b70700e1-f548-4c92-9482-3e09e20790b3
── ④ 轮询 /history/b70700e1-f548-4c92-9482-3e09e20790b3  (timeout=300.0s)
  ↳ status=success  elapsed=132s
── ⑤ 拉输出文件
   video → ./out/h3_demo_00001_.mp4
   audio → ./out/audio/h3_demo_00001.flac
✅ 完成
```

### Agent 端到端记录
```
$ openclaw agent --model stepfun/step-3.7-flash \
    --message "用 minimax-h3-story skill 帮我把 /mnt/minimax-h3/output/h3_frame.png 变成一段鲸鱼跃水视频"

→ Agent 自动识别 Skill → 调 helper.py → 调 ComfyUI → 拉回 mp4+flac
→ prompt_id 84257fcb-79d5-44af-b8b5-ce0ed239ff20
→ status=success  (135s)
→ /tmp/h3_agent_demo/whale_v3_final.mp4  (392K, 864×480, 5.17s)
→ /tmp/h3_agent_demo/audio/whale_v3_00001.flac  (166K, 32000Hz stereo)
```
> ⚠️ StepFun 推理模型对工具调用结果的"叙述"会自己优化（如声称"命中之前产物"），**以磁盘上的文件为准**。

## 快速开始

```bash
# 1. 假设 ComfyUI + MiniMax H3 容器已在跑（端口 8188）
# 2. 假设 OpenClaw 已装（≥2026.9.6）

# CLI 直接调
bash skills/minimax-h3-story/run.sh \
  --image /path/to/start.jpg \
  --prompt "..." \
  --outdir ./out

# 让 Agent 调（自然语言）
openclaw agent --model stepfun/step-3.7-flash \
  --message "用 minimax-h3-story skill 帮我把 /path/to/start.jpg 变成鲸鱼跃水视频"
```

详见 [DEPLOY.md](DEPLOY.md) 和 [docs/DEMO.md](docs/DEMO.md)。

## 多 Skill 编排

本仓库内含 **2 个 Skill**，可串行编排形成完整 pipeline：

```
[中文描述] ─► h3-prompt-rewriter ─► [MiniMax H3 友好英文 prompt]
                                          │
                                          ▼
                  minimax-h3-story ─► [mp4 + flac]
```

### 端到端 bash 编排示例（已验证）

```bash
# Step 1: 中文 prompt → 英文 prompt + stereo sound 标记
REWRITTEN=$(bash skills/h3-prompt-rewriter/run.sh \
  --input "鲸鱼在深海游泳，水面阳光，水母在远处发光" \
  --style cinematic | python3 -c "import json,sys; print(json.load(sys.stdin)['full'])")

# Step 2: 喂给 MiniMax H3
bash skills/minimax-h3-story/run.sh \
  --image assets/h3_frame.png \
  --prompt "$REWRITTEN" \
  --prefix multi_skill_demo --outdir /tmp/out --seed 42
```

**实测产物**（prompt_id `d7859fb3-a0b9-4598-ba42-73c1a44965fd`，135s）：
- `multi_skill_demo_00001_.mp4`（视频）
- `audio/multi_skill_demo_00001.flac`（立体声）

### 为什么拆成两个 Skill

- **职责单一**：`h3-prompt-rewriter` 只负责 prompt 工程，`minimax-h3-story` 只负责生成
- **可独立测试**：每个 Skill 有自己的 4 文件范式（SKILL.md + workflow.json + helper.py + run.sh）
- **可复用**：未来换 backbone（如 Wan / SVD），只改 `minimax-h3-story`，prompt rewriter 不动

## 技术栈

| 层 | 选型 | 理由 |
|---|---|---|
| 图像/视频生成 | MultiMax H3 (FL2VA + Qwen3-VL NVFP4) | GB10 原生量化 + 同步出音频 |
| 调度 | ComfyUI 0.30.0 | 工作流可视化 + HTTP API 暴露 |
| Skill 框架 | OpenClaw 2026.9.6 | 本比赛官方推荐 |
| Agent LLM | StepFun step-3.7-flash | 多模态理解 + 工具调用 + 中文指令 |
| 工作流定义 | JSON (14 节点) | 与 ComfyUI UI 完全兼容 |
| 语言 | Python 3.12 stdlib only（无第三方依赖） | 部署零摩擦 |

## 仓库结构

```
minimax-h3-story/
├── README.md                              # 本文件
├── SKILL.md                               # 根目录 Skill 描述（OpenClaw 自动发现）
├── DEPLOY.md                              # 部署说明（GB10 + Docker + ComfyUI + OpenClaw）
├── LICENSE                                # MIT
├── docs/
│   ├── DEMO.md                            # 录屏脚本
│   ├── architecture.png                   # 架构图（matplotlib 生成）
│   └── gen_architecture.py                # 架构图生成脚本
├── skills/
│   ├── minimax-h3-story/                  # Skill 1：图像→视频+音频
│   │   ├── SKILL.md                       # YAML 头 + 触发词
│   │   ├── workflow.json                  # 14 节点 MiniMax H3 workflow（参数化）
│   │   ├── helper.py                      # ComfyUI HTTP API client（零依赖）
│   │   └── run.sh                         # 入口脚本
│   └── h3-prompt-rewriter/                # Skill 2：中文→英文 MiniMax H3 prompt
│       ├── SKILL.md                       # YAML 头 + 触发词
│       ├── workflow.json                  # LLM prompt 模板 + JSON schema
│       ├── helper.py                      # StepFun API client（零依赖）
│       └── run.sh                         # 入口脚本
└── assets/
    └── h3_frame.png                       # 演示用起始图（鲸鱼跃水场景）
```

## 团队

**Xplore-LAB** — NVIDIA DGX Spark Hackathon 参赛队伍

参赛成员：[填入]

## 致谢

- **何老师** workshop 2 (Build A Claw) — 4 文件 Skill 范式
- **NVIDIA** DGX Spark + Multi-Max H3 模型 + OpenClaw 框架
- **StepFun** step-3.7-flash（Agent 推理用）

## License

MIT

---

_最后更新：2026-09-28 07:18（v2 — 加 h3-prompt-rewriter + 真实架构图 + DEPLOY LAN 提示 + 多 Skill 编排段）_