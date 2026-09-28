#!/usr/bin/env python3
"""画 minimax-h3-story 架构图。

输出：docs/architecture.png

依赖：matplotlib（项目本身零依赖；本脚本是 docs 生成工具）。
"""
from __future__ import annotations
import pathlib
import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# CJK 字体：NotoSansCJK-Light.ttc
_CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Light.ttc"
if pathlib.Path(_CJK).exists():
    fm.fontManager.addfont(_CJK)
    plt.rcParams["font.family"] = ["Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = pathlib.Path(__file__).parent / "architecture.png"

# 颜色（dark theme safe：浅色背景 + 深色字）
C_USER = "#E8F4FD"
C_AGENT = "#FFF4E1"
C_HELPER = "#E5F8E1"
C_COMFY = "#F4E5FA"
C_MODEL = "#FDE2E2"
C_OUTPUT = "#E8E8E8"
C_BORDER = "#222222"

fig, ax = plt.subplots(figsize=(13, 9), dpi=110)
ax.set_xlim(0, 13)
ax.set_ylim(0, 9)
ax.set_axis_off()


def box(x, y, w, h, label, sub, color, fontsize=10, sub_size=7.5):
    p = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.06,rounding_size=0.12",
        fc=color, ec=C_BORDER, lw=1.2,
    )
    ax.add_patch(p)
    ax.text(x + w / 2, y + h * 0.62, label, ha="center", va="center",
            fontsize=fontsize, fontweight="bold", color="#111")
    ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center",
            fontsize=sub_size, color="#333")


def arrow(x1, y1, x2, y2, label="", color="#444", offset=0.2):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14,
                        lw=1.3, color=color)
    ax.add_patch(a)
    if label:
        ax.text((x1 + x2) / 2 + offset, (y1 + y2) / 2, label,
                fontsize=8, color=color, ha="left",
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85))


# Layer 1: User
box(0.3, 7.7, 2.6, 0.9, "User", "自然语言指令\n「把 X.jpg 变成鲸鱼跃水视频」", C_USER)

# Layer 2: OpenClaw Agent
box(4.0, 7.7, 4.8, 0.9, "OpenClaw Agent",
    "StepFun step-3.7-flash (云端推理)\n+ minimax-h3-story Skill (本地 discovered)", C_AGENT)

# arrow user -> agent
arrow(2.9, 8.15, 4.0, 8.15, "message", color="#0a6ec5")

# Layer 3: 4-file Skill (helper.py + run.sh + workflow.json + SKILL.md)
box(0.3, 5.6, 12.4, 1.7, "minimax-h3-story Skill (4-file)",
    "", C_HELPER, fontsize=11)
# 子 box
box(0.6, 5.85, 2.8, 1.2, "SKILL.md", "YAML 头 + 触发词\ndescription = intent", "#F0FBF0", 9, 7)
box(3.7, 5.85, 2.8, 1.2, "workflow.json", "14 节点 MiniMax H3 graph\n参数化占位符", "#F0FBF0", 9, 7)
box(6.8, 5.85, 2.8, 1.2, "helper.py", "ComfyUI HTTP API client\nupload → /prompt → /history", "#F0FBF0", 9, 7)
box(9.9, 5.85, 2.6, 1.2, "run.sh", "CLI 入口\n转发到 helper.py", "#F0FBF0", 9, 7)

# arrow agent -> skill
arrow(6.4, 7.7, 6.4, 7.4, "bash run.sh --image X.jpg --prompt ...", color="#0a6ec5", offset=0.5)

# Layer 4: ComfyUI HTTP API
box(4.0, 3.7, 4.8, 0.9, "ComfyUI HTTP API",
    "POST /upload/image · POST /prompt · GET /history/{id} · GET /view", C_COMFY)

# arrow helper -> comfy
arrow(6.4, 5.85, 6.4, 4.6, "urllib stdlib only", color="#0a6ec5", offset=0.5)

# Layer 5: MiniMax H3 (14 nodes inside)
box(0.3, 1.0, 12.4, 2.4, "MultiMax H3 (14 节点 workflow) · GB10 + NVFP4",
    "", C_MODEL, fontsize=11)
# nodes laid out
nodes = [
    (0.6, 1.4, "UNETLoader", "MiniMax-H3-FL2VA\nINT8"),
    (3.4, 1.4, "CLIPLoader", "Qwen3-VL-32B\nNVFP4 (Blackwell)"),
    (6.2, 1.4, "VAE ×2", "video FP16\n+ audio FP32"),
    (9.0, 1.4, "EmptyMiniMax\nH3LatentAV", "608×352×96\n(4s@24fps)"),
    (0.6, 2.6, "SigmaShift", "v=12.0 a=3.0"),
    (3.4, 2.6, "ImageToVideo", "image + prompt"),
    (6.2, 2.6, "KSampler", "Euler cfg=1\nsteps=20"),
    (9.0, 2.6, "VAEDecode ×2", "video + audio"),
]
for x, y, name, sub in nodes:
    box(x, y, 2.6, 0.7, name, sub, "#FFF5F5", 8.5, 6.5)

# arrow comfy -> nodes
arrow(6.4, 3.7, 6.4, 3.4, "execute", color="#0a6ec5", offset=0.4)

# Layer 6: Output
box(4.0, 0.0, 4.8, 0.7, "Outputs",
    "MP4 (H.264 视频) + FLAC (立体声)", C_OUTPUT)

# arrow nodes -> output
arrow(6.4, 1.0, 6.4, 0.7, "SaveVideo + SaveAudio", color="#0a6ec5", offset=0.5)

# Layer labels
ax.text(0.05, 8.5, "L1", fontsize=8, color="#666")
ax.text(0.05, 6.4, "L2", fontsize=8, color="#666")
ax.text(0.05, 4.1, "L3", fontsize=8, color="#666")
ax.text(0.05, 2.2, "L4", fontsize=8, color="#666")
ax.text(0.05, 0.35, "L5", fontsize=8, color="#666")

# Title
ax.text(6.5, 8.85, "minimax-h3-story 架构图 — 从自然语言到带声音短视频",
        ha="center", fontsize=13, fontweight="bold", color="#111")

fig.tight_layout()
fig.savefig(OUT, dpi=110, bbox_inches="tight", facecolor="white")
print(f"✅ {OUT}  ({OUT.stat().st_size // 1024} KB)")