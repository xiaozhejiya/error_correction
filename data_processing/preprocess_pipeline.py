import os
import math
import numpy as np
from PIL import Image, ImageOps  
from deskew import determine_skew
from concurrent.futures import ProcessPoolExecutor

# ================= 配置区 =================
RAW_DIR = "data_processing/benchmark/raw"
GT_DIR = "data_processing/benchmark/ground_truth"

# 建议：若想看到 Token 数量下降，将 DPI 设为 150-200
# 300 DPI 的全页文档几乎百分百触碰 1280 Token 天花板
TARGET_DPI = 150 
MIN_DPI = 150
MAX_DPI = 300

SKEW_THRESHOLD = 0.5 
CROP_MARGIN = 15 

# PaddleOCR-VL-1.5 论文参数 [cite: 253, 261]
PATCH_SIZE = 28  
TOKEN_CAP = 1280 # Parsing 任务视觉 Token 上限
# ==========================================

def estimate_detailed_tokens(width, height):
    """
    量化 Tiling 消耗详情
    返回: (实际消耗 Token, 原始 Patch 总数)
    """
    cols = math.ceil(width / PATCH_SIZE)
    rows = math.ceil(height / PATCH_SIZE)
    raw_patches = cols * rows
    
    # 实际消耗会被模型 Cap 住
    actual_visual_tokens = min(raw_patches, TOKEN_CAP)
    total_tokens = actual_visual_tokens + 128
    
    return total_tokens, raw_patches

def smart_crop(pil_img):
    """加速版智能裁剪"""
    # 缩放 4 倍计算 BBox 以提升速度
    low_res = pil_img.resize((pil_img.width // 4, pil_img.height // 4), Image.NEAREST)
    bw = low_res.convert('L').point(lambda x: 0 if x < 240 else 255, '1')
    inverted = ImageOps.invert(bw.convert('RGB')).convert('L')
    
    bbox_low = inverted.getbbox()
    if not bbox_low: return pil_img

    bbox = (bbox_low[0]*4, bbox_low[1]*4, bbox_low[2]*4, bbox_low[3]*4)
    return pil_img.crop((
        max(0, bbox[0] - CROP_MARGIN),
        max(0, bbox[1] - CROP_MARGIN),
        min(pil_img.width, bbox[2] + CROP_MARGIN),
        min(pil_img.height, bbox[3] + CROP_MARGIN)
    ))

def process_single_image(filename):
    raw_path = os.path.join(RAW_DIR, filename)
    gt_path = os.path.join(GT_DIR, filename)
    
    try:
        with Image.open(raw_path) as img:
            img = img.convert('RGB')
            
            # --- 步骤 1: 旋转 (低负载) ---
            scale = 800.0 / max(img.size)
            check_img = img.resize((int(img.width * scale), int(img.height * scale)), Image.NEAREST)
            angle = determine_skew(np.array(check_img.convert('L'))) or 0.0
            
            if abs(angle) >= SKEW_THRESHOLD:
                img = img.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))
            
            # --- 步骤 2: 裁切 (核心：减少原始 Patch 数) ---
            img = smart_crop(img)
            
            # --- 步骤 3: 检查 DPI 并调整 ---
            # 只有在裁切完文字区域后，再考虑是否需要拉高像素，这样最省资源
            orig_dpi = img.info.get('dpi', (72, 72))[0]
            if not (MIN_DPI <= orig_dpi <= MAX_DPI):
                scale_factor = TARGET_DPI / orig_dpi
                new_w, new_h = int(img.width * scale_factor), int(img.height * scale_factor)
                img = img.resize((new_w, new_h), Image.LANCZOS)
                final_dpi = TARGET_DPI
            else:
                final_dpi = orig_dpi
            
            # --- 步骤 4: 量化 ---
            tokens, patches = estimate_detailed_tokens(img.width, img.height)
            img.save(gt_path, dpi=(final_dpi, final_dpi), quality=95)
            
            status = "已达上限" if patches >= TOKEN_CAP else "优化后"
            return f"✓ {filename:15} | Token: {tokens} ({status}) | 原始 Patches: {patches}"

    except Exception as e:
        return f"✗ {filename:15} | 失败: {str(e)}"

def process_pipeline():
    Image.MAX_IMAGE_PIXELS = None 
    os.makedirs(GT_DIR, exist_ok=True)
    files = [f for f in os.listdir(RAW_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
    
    print(f"🚀 开始并行处理 {len(files)} 张图片...")
    print(f"设定目标 DPI: {TARGET_DPI} | 视觉 Token 上限: {TOKEN_CAP}\n")
    
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(process_single_image, files))
    
    for r in results: print(r)

if __name__ == "__main__":
    process_pipeline()