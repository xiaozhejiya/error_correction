"""
文字擦除推理测试脚本
运行方式：cd backend/models && python test_erase.py <图片路径>
示例：python test_erase.py E:/code/python/error_correction/dataset/初中数学/图片/xxx.jpg
"""
import sys
import os
# backend/models/ → backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
torch.backends.cudnn.enabled = False   # cuDNN v8 frontend 与 A30+PyTorch2.1 不兼容
from pathlib import Path
from PIL import Image
import numpy as np

# ── 命令行参数 ────────────────────────────────────────
if len(sys.argv) < 2:
    print("用法: python test_erase.py <图片路径>")
    print("示例: python test_erase.py E:/xxx/photo.jpg")
    sys.exit(1)

test_img_path = Path(sys.argv[1])
if not test_img_path.exists():
    print(f"错误: 图片不存在 -> {test_img_path}")
    sys.exit(1)

# ── 路径配置 ──────────────────────────────────────────
MODEL_PATH = Path(__file__).parent / "weight" / "best.pth"
OUTPUT_DIR = Path(__file__).parent.parent / "runtime_data" / "erased"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── GPU 信息 ──────────────────────────────────────────
print("=" * 50)
print(f"PyTorch   : {torch.__version__}")
print(f"CUDA 可用 : {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU       : {torch.cuda.get_device_name(0)}")
    print(f"VRAM      : {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
print("=" * 50)

# ── 加载模型 ──────────────────────────────────────────
print(f"\n[1] 加载权重: {MODEL_PATH}")
assert MODEL_PATH.exists(), f"找不到权重文件: {MODEL_PATH}"

from models.model import Generator
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
G = Generator().to(device)
ckpt = torch.load(MODEL_PATH, map_location=device, weights_only=False)
state_dict = ckpt.get("G_state_dict") or ckpt.get("generator_state_dict") or ckpt
G.load_state_dict(state_dict)
G.eval()
print(f"    权重加载成功，运行设备: {device}")

# ── 推理 ──────────────────────────────────────────────
PATCH = 512
OVERLAP = 32

def preprocess(pil_img):
    img = pil_img.convert("RGB")
    w, h = img.size
    pw = (PATCH - w % PATCH) % PATCH
    ph = (PATCH - h % PATCH) % PATCH
    if pw or ph:
        canvas = Image.new("RGB", (w + pw, h + ph), (255, 255, 255))
        canvas.paste(img, (0, 0))
        img = canvas
    arr = np.array(img, dtype=np.float32) / 127.5 - 1.0
    return arr, w, h

def to_tensor(arr):
    return torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(device)

def to_numpy(t):
    arr = t.squeeze(0).permute(1, 2, 0).cpu().numpy()
    return np.clip((arr + 1.0) * 127.5, 0, 255).astype(np.uint8)

def infer(arr):
    h, w, _ = arr.shape
    stride = PATCH - OVERLAP
    result = np.zeros((h, w, 3), dtype=np.float64)
    weight = np.zeros((h, w, 1), dtype=np.float64)

    def ticks(total):
        pts = list(range(0, total - PATCH + 1, stride))
        if not pts or pts[-1] + PATCH < total:
            pts.append(total - PATCH)
        return pts

    ys, xs = ticks(h), ticks(w)
    total = len(ys) * len(xs)
    done = 0
    with torch.no_grad():
        for y in ys:
            for x in xs:
                patch = to_tensor(arr[y:y+PATCH, x:x+PATCH])
                *_, Icomp = G(patch)
                out = to_numpy(Icomp).astype(np.float64)
                result[y:y+PATCH, x:x+PATCH] += out
                weight[y:y+PATCH, x:x+PATCH] += 1.0
                done += 1
                print(f"    patch {done}/{total}", end="\r")

    print()
    return np.clip(result / weight, 0, 255).astype(np.uint8)

print(f"\n[2] 测试图片: {test_img_path.name}")
pil_orig = Image.open(test_img_path)
print(f"    原图尺寸: {pil_orig.size[0]}x{pil_orig.size[1]}")
arr, orig_w, orig_h = preprocess(pil_orig)
print(f"    Padding 后: {arr.shape[1]}x{arr.shape[0]}")

print("\n[3] 开始推理...")
result_arr = infer(arr)
result_arr = result_arr[:orig_h, :orig_w]
result_img = Image.fromarray(result_arr)

# ── 保存结果 ──────────────────────────────────────────
out_name = "erased_" + test_img_path.stem + ".png"
out_path = OUTPUT_DIR / out_name
result_img.save(out_path)
print(f"\n[4] 结果已保存: {out_path}")
print("    完成！")
