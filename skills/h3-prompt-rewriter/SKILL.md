---
name: h3-prompt-rewriter
description: "把中文/模糊的视频描述改写为 MultiMax H3 友好的英文 prompt（含 'stereo sound of ...' 音频提示）。当用户说「帮我写个 MiniMax H3 prompt」「中翻英 + 加音频」「给这个想法润色成视频描述」时使用。"
user-invocable: true
---

# h3-prompt-rewriter — 中文/模糊描述 → MiniMax H3 友好英文 prompt

## 触发词

- 「帮我写个 MultiMax H3 prompt」
- 「中翻英 + 加音频」
- 「给这个想法润色成视频描述」
- "rewrite prompt for MiniMax H3"
- "add stereo sound cue"

## 何时使用

用户的中文描述/关键词想直接喂给 `minimax-h3-story` Skill，但：

- **MultiMax H3 prompt 必须是英文**（Qwen3-VL 多模态 encoder 是英文优先）
- **音频需要显式标注**（节点 7 prompt 末尾加 "stereo sound of ..." 才会触发音频生成）
- **风格关键词**（cinematic / slow motion / dramatic / ambient ...）能显著影响视频质感

本 Skill 把上述 3 件事自动化。

## 调用规范

```bash
bash skills/h3-prompt-rewriter/run.sh --input "鲸鱼在深海游泳，水面有阳光"
# → MultiMax H3 友好英文 prompt（含 stereo sound of）
```

参数：
- `--input` 必填：中文/英文/混合描述
- `--style` 选填：默认 `cinematic`（也可 `slow motion` / `dramatic` / `ambient` / `documentary`）
- `--out` 选填：输出到文件（默认 stdout）

输出：
- `MEDIA:/path/to/output.txt` 或 stdout
- JSON 格式：`{"prompt": "...", "sound": "...", "full": "..."}`

## 与 minimax-h3-story 的典型编排

```bash
# Step 1: 改写 prompt
REWRITTEN=$(bash skills/h3-prompt-rewriter/run.sh --input "鲸鱼在深海游泳，水面有阳光")
# Step 2: 喂给 MiniMax H3
bash skills/minimax-h3-story/run.sh \
  --image start.jpg \
  --prompt "$REWRITTEN" \
  --outdir ./out
```

## 4 文件 Skill 范式（同 minimax-h3-story）

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 本文件（YAML 头 + 触发词 + 调用规范）|
| `workflow.json` | LLM 调用模板（prompt 模板 + JSON schema）|
| `helper.py` | 调 StepFun API，零依赖（urllib stdlib）|
| `run.sh` | 入口脚本 |