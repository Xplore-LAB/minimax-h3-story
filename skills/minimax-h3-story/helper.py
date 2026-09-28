#!/usr/bin/env python3
"""minimax-h3-story helper — 调 ComfyUI HTTP API 把一张起始图变成带声音短视频。

零第三方依赖（stdlib only）：urllib + json + argparse + pathlib。

用法：
  python3 helper.py --image start.jpg --prompt "..." --outdir ./out

工作流：
  1. POST /upload/image  把起始图上传到 ComfyUI
  2. 替换 workflow.json 里的占位符
  3. POST /prompt           提交工作流
  4. 轮询 GET /history/{id}  等 status_str == success
  5. 从 outputs 拉 mp4/flac 到本地

———
这个 helper 与何老师 workshop 2 的 superhero_helper.py 完全同构：
只是把"调 FLUX+PuLID"换成"调 Multi-Max H3"，把"生成超级英雄照片"换成"生成短视频"。
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

COMFYUI_BASE = os.environ.get("COMFYUI_BASE", "http://127.0.0.1:8188")
WORKFLOW_PATH = pathlib.Path(__file__).parent / "workflow.json"

DEFAULT_NEG = "blurry, low quality, deformed, camera shake, static image"
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "3.0"))
POLL_TIMEOUT = float(os.environ.get("POLL_TIMEOUT", "300.0"))


def http_post(path: str, payload: dict, timeout: float = 30.0) -> dict:
    """POST JSON 到 ComfyUI，返回解析后的 JSON 响应。"""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        COMFYUI_BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise SystemExit(f"ERROR: ComfyUI HTTP {e.code} {path}: {detail}")
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"ERROR: 调用 ComfyUI 失败 {path}: {e}")


def upload_image(image_path: pathlib.Path) -> str:
    """上传起始图到 ComfyUI，返回 server-side filename。"""
    if not image_path.exists():
        raise SystemExit(f"ERROR: 图片不存在: {image_path}")
    boundary = "----minimax-h3-story-boundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{image_path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + image_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        COMFYUI_BASE + "/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.load(r)
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"ERROR: 上传图片失败: {e}")

    name = resp.get("name")
    if not name:
        raise SystemExit(f"ERROR: /upload/image 没返回 name：{resp}")
    return name


def build_workflow(prompt: str, image_filename: str, seed: int, prefix: str) -> dict:
    """读 workflow.json + 替换占位符。"""
    raw = WORKFLOW_PATH.read_text()
    wf = json.loads(raw)
    wf["7"]["inputs"]["prompt"] = prompt
    wf["7"]["inputs"]["image"] = image_filename
    wf["9"]["inputs"]["seed"] = int(seed)
    wf["13"]["inputs"]["filename_prefix"] = prefix
    wf["14"]["inputs"]["filename_prefix"] = f"audio/{prefix}"
    return wf


def submit(wf: dict, client_id: str) -> str:
    """POST /prompt，返回 prompt_id。"""
    resp = http_post("/prompt", {"prompt": wf, "client_id": client_id}, timeout=30.0)
    pid = resp.get("prompt_id")
    if not pid:
        raise SystemExit(f"ERROR: /prompt 没返回 prompt_id：{resp}")
    return pid


def poll(prompt_id: str, timeout: float) -> dict:
    """轮询 /history/{prompt_id}，等到 status_str == success 或失败。"""
    deadline = time.time() + timeout
    last_state = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                COMFYUI_BASE + f"/history/{prompt_id}", timeout=15
            ) as r:
                hist = json.load(r)
        except Exception:  # noqa: BLE001
            hist = {}
        entry = hist.get(prompt_id) or {}
        status = (entry.get("status") or {}).get("status_str")
        if status != last_state:
            print(f"  ↳ status={status}  elapsed={int(time.time() - (deadline - timeout))}s")
            last_state = status
        if status == "success":
            return entry
        if status in ("error", "failed"):
            raise SystemExit(f"ERROR: 工作流失败 status={status}：{entry.get('status')}")
        time.sleep(POLL_INTERVAL)
    raise SystemExit(f"ERROR: 轮询超时（>{timeout}s）")


def fetch_outputs(entry: dict, outdir: pathlib.Path) -> dict:
    """从 /history entry.outputs 里下载 mp4 / flac 到 outdir。"""
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "audio").mkdir(parents=True, exist_ok=True)
    outputs = entry.get("outputs") or {}
    files = {"video": None, "audio": None}
    for node_id, node_out in outputs.items():
        # 不同节点 outputs 走不同 key（SaveVideo→images, SaveAudio→audio, 其它→files）
        for f in node_out.get("images", []) + node_out.get("files", []) + node_out.get("audio", []):
            fn = f.get("filename")
            sub = f.get("subfolder") or ""
            ftype = f.get("type") or "output"
            if not fn:
                continue
            url = f"{COMFYUI_BASE}/view?filename={fn}&type={ftype}"
            if sub:
                url += f"&subfolder={sub}"
            local = outdir / (sub if sub else "") / fn
            local.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url, timeout=60) as r, open(local, "wb") as out:
                out.write(r.read())
            if fn.endswith(".mp4"):
                files["video"] = str(local)
            elif fn.endswith((".flac", ".wav", ".mp3")):
                files["audio"] = str(local)
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description="Multi-Max H3 图像→短视频（带声音）")
    ap.add_argument("--image", required=True, help="起始图路径")
    ap.add_argument("--prompt", required=True, help="视频 + 音频描述（建议末尾加 'stereo sound of ...'）")
    ap.add_argument("--outdir", default="./output", help="输出目录")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--prefix", default="h3", help="输出文件名前缀")
    ap.add_argument("--client-id", default="minimax-h3-story")
    ap.add_argument("--timeout", type=float, default=POLL_TIMEOUT, help="轮询超时（秒）")
    ap.add_argument("--negative", default=DEFAULT_NEG)
    args = ap.parse_args()

    image_path = pathlib.Path(args.image).resolve()
    outdir = pathlib.Path(args.outdir).resolve()
    print(f"── ① 上传起始图：{image_path}")
    img_name = upload_image(image_path)
    print(f"   → {img_name}")

    print(f"── ② 构造 workflow（prompt='{args.prompt[:60]}…'）")
    wf = build_workflow(args.prompt, img_name, args.seed, args.prefix)
    # negative prompt 走 nodes[8]，运行时也允许覆盖
    wf["8"]["inputs"]["text"] = args.negative

    print("── ③ 提交 /prompt")
    pid = submit(wf, args.client_id)
    print(f"   prompt_id = {pid}")

    print(f"── ④ 轮询 /history/{pid}  (timeout={args.timeout}s)")
    entry = poll(pid, args.timeout)

    print("── ⑤ 拉输出文件")
    files = fetch_outputs(entry, outdir)
    print(f"   video → {files['video']}")
    print(f"   audio → {files['audio']}")

    meta = {
        "prompt_id": pid,
        "prompt": args.prompt,
        "image": str(image_path),
        "seed": args.seed,
        "outputs": files,
        "usage": entry.get("usage"),
    }
    meta_out = outdir / ".prompt_id.json"
    meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"   meta  → {meta_out}")
    print("✅ 完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())