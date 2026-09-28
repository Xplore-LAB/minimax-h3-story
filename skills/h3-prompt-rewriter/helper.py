#!/usr/bin/env python3
"""h3-prompt-rewriter helper — 调 StepFun API 把中文/模糊描述改写成 MiniMax H3 友好 prompt。

零依赖（urllib stdlib only）。
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

STEPFUN_BASE = os.environ.get("STEPFUN_OPENAI_BASE", "https://api.stepfun.com/step_plan/v1")
STEPFUN_MODEL = os.environ.get("STEPFUN_MODEL", "step-3.7-flash")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "4096"))

SYSTEM_PROMPT = """你是 MultiMax H3 视频生成 prompt 专家。把用户描述改写成 MiniMax H3 友好的英文 prompt。

MiniMax H3 偏好：
- 英文 + 视觉化关键词
- 末尾必须有 "stereo sound of ..." 音频提示（否则不会生成音频）
- 风格词：cinematic / slow motion / dramatic / ambient / documentary / macro
- 镜头词：close-up / wide shot / aerial / tracking shot
- 避免：抽象概念、文字描述、人物特写（容易崩）

输出 JSON（不要 markdown 围栏）：
{
  "prompt": "完整视觉描述（40-80 词）",
  "sound": "环境音/音效描述（10-20 词）",
  "full": "prompt + ', ' + sound（直接喂 MiniMax H3）"
}
"""

USER_TEMPLATE = """用户原始描述：{input}
偏好风格：{style}

请输出 JSON。"""


def load_api_key() -> str:
    key = os.environ.get("STEPFUN_API_KEY", "").strip()
    if key:
        return key
    for p in (
        pathlib.Path.home() / ".openclaw" / "secrets" / "stepfun.key",
        pathlib.Path.home() / ".openclaw" / "secrets" / "stepfun.env",
    ):
        if p.exists():
            text = p.read_text().strip()
            m = re.search(r"STEPFUN_API_KEY=(.+)", text)
            if m:
                return m.group(1).strip()
            if text and "\n" not in text:
                return text
    raise SystemExit("ERROR: 找不到 StepFun API Key（设置 STEPFUN_API_KEY 或写入 ~/.openclaw/secrets/stepfun.key）")


def call_stepfun(api_key: str, user_input: str, style: str) -> dict:
    body = {
        "model": STEPFUN_MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(input=user_input, style=style)},
        ],
    }
    req = urllib.request.Request(
        STEPFUN_BASE + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise SystemExit(f"ERROR: StepFun HTTP {e.code}: {detail}")
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"ERROR: 调用 StepFun 失败: {e}")

    msg = (resp.get("choices") or [{}])[0].get("message") or {}
    content = (msg.get("content") or "").strip()
    if not content:
        raise SystemExit(
            "ERROR: 模型 content 为空（推理模型 token 不足）。"
            f"  finish_reason={(resp.get('choices') or [{}])[0].get('finish_reason')}  "
            f"提高 MAX_TOKENS 后重试（当前 {MAX_TOKENS}）"
        )

    # 抠 JSON
    text = content
    fence = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start >= 0:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start: i + 1])
                    except json.JSONDecodeError:
                        break
    raise SystemExit(f"ERROR: 模型没输出合法 JSON。前 300 字：\n{content[:300]}")


def main() -> int:
    ap = argparse.ArgumentParser(description="中文/模糊描述 → MiniMax H3 prompt")
    ap.add_argument("--input", required=True, help="原始描述")
    ap.add_argument("--style", default="cinematic",
                    choices=["cinematic", "slow motion", "dramatic", "ambient", "documentary", "macro"])
    ap.add_argument("--out", help="输出文件路径（默认 stdout）")
    args = ap.parse_args()

    api_key = load_api_key()
    result = call_stepfun(api_key, args.input, args.style)

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.out).write_text(text)
        print(f"✅ 改写完成 → {args.out}")
        print(f"   full prompt: {result.get('full', '')[:120]}…")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())