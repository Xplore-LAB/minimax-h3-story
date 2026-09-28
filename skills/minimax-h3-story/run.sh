#!/usr/bin/env bash
# minimax-h3-story — 入口脚本
#
# 用法：
#   bash run.sh --image start.jpg --prompt "..." [--outdir ./out]
#
# 环境变量：
#   COMFYUI_BASE      ComfyUI HTTP API（默认 http://127.0.0.1:8188）
#   POLL_TIMEOUT      轮询超时秒数（默认 300）
#   POLL_INTERVAL     轮询间隔秒数（默认 3.0）

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SKILL_DIR"

PY="${PYTHON:-python3}"
exec "$PY" helper.py "$@"