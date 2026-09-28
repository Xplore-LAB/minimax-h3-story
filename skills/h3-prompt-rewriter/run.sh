#!/usr/bin/env bash
# h3-prompt-rewriter — 入口脚本
#
# 用法：
#   bash run.sh --input "鲸鱼在深海游泳" [--style cinematic] [--out ./out.json]

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SKILL_DIR"

PY="${PYTHON:-python3}"
exec "$PY" helper.py "$@"