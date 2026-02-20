import os
import json
import sys
import base64
import requests
import math
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image, ImageOps

# 加载环境变量
load_dotenv()

# 添加上层目录到 Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入预处理工具
from dpi_enhancement import DPIEnhancer
from preprocess_pipeline import detect_skew_angle, correct_skew, SKEW_THRESHOLD

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ================= 配置 =================
RAW_DIR = "benchmark/raw"               # 原始图片
COMPARISON_DIR = "benchmark/comparison" # 对比结果目录
REPORT_FILE = "benchmark/comparison_report.json"

TARGET_DPI = 300

# 论文对齐参数 
PATCH_SIZE = 28  
MAX_VISUAL_TOKENS_PARSING = 1280  
MAX_VISUAL_TOKENS_SPOTTING = 2048 
CROP_MARGIN = 15
# =========================================

class OCRComparator:
    """
    PaddleOCR 识别效果对比器
    对比预处理前后的识别结果，并根据 PaddleOCR-VL-1.5 论文量化 Tiling 消耗
    """
    
    def __init__(self):
        """初始化对比器"""
        self.enhancer = DPIEnhancer(
            target_dpi=TARGET_DPI,
            min_acceptable_dpi=200,
            enable_quality_enhancement=True
        )
        self.results = []
    
    def estimate_tiling_tokens(self, width: int, height: int, mode: str = "parsing") -> int:
        """
        根据 PaddleOCR-VL-1.5 论文量化 Token [cite: 253, 261, 412]
        """
        cols = math.ceil(width / PATCH_SIZE)
        rows = math.ceil(height / PATCH_SIZE)
        raw_patches = cols * rows
        
        token_cap = MAX_VISUAL_TOKENS_PARSING if mode == "parsing" else MAX_VISUAL_TOKENS_SPOTTING
        visual_tokens = min(raw_patches, token_cap)
        
        # 基础开销包含 Prompt 和指令识别开销 [cite: 412, 419]
        base_tokens = 128 
        return visual_tokens + base_tokens

    def smart_crop(self, pil_img: Image.Image) -> Image.Image:
        """
        基于内容的智能裁剪：模拟 PP-DocLayoutV3 的局部区域提取逻辑 [cite: 130, 172, 183]
        """
        gray = pil_img.convert('L')
        # 阈值过滤背景噪声
        bw = gray.point(lambda x: 0 if x < 240 else 255, '1')
        inverted = ImageOps.invert(bw.convert('RGB')).convert('L')
        
        bbox = inverted.getbbox()
        if not bbox:
            return pil_img

        left = max(0, bbox[0] - CROP_MARGIN)
        top = max(0, bbox[1] - CROP_MARGIN)
        right = min(pil_img.width, bbox[2] + CROP_MARGIN)
        bottom = min(pil_img.height, bbox[3] + CROP_MARGIN)
        
        return pil_img.crop((left, top, right, bottom))

    def _prepare_raw_image(self, image_path: str) -> str:
        output_dir = os.path.join(COMPARISON_DIR, "raw_prepared")
        os.makedirs(output_dir, exist_ok=True)
        filename = Path(image_path).stem
        output_path = os.path.join(output_dir, f"{filename}_raw.png")
        image = Image.open(image_path).convert('RGB')
        image.save(output_path, 'PNG')
        return output_path
    
    def _prepare_enhanced_image(self, image_path: str) -> Tuple[str, Dict]:
        output_dir = os.path.join(COMPARISON_DIR, "enhanced_prepared")
        os.makedirs(output_dir, exist_ok=True)
        filename = Path(image_path).stem
        output_path = os.path.join(output_dir, f"{filename}_enhanced.png")
        
        metadata = {"dpi_enhancement": None, "skew_correction": None, "cropped": False}
        
        try:
            # 1. DPI 增强与质量提升
            logger.info(f"  [增强] 开始 DPI 增强...")
            dpi_result = self.enhancer.process(
                image_path, output_path=output_path, output_format="PNG",
                enable_noise_reduction=True, enable_auto_contrast=True
            )
            metadata["dpi_enhancement"] = {
                "original_dpi": dpi_result['original_dpi'],
                "target_dpi": TARGET_DPI,
                "success": dpi_result['success']
            }
            
            # 2. 倾斜矫正
            logger.info(f"  [增强] 倾斜检测与智能裁剪中...")
            enhanced_img = Image.open(output_path).convert('RGB')
            angle = detect_skew_angle(enhanced_img)
            
            if abs(angle) >= SKEW_THRESHOLD:
                enhanced_img = correct_skew(enhanced_img, angle)
                metadata["skew_correction"] = {"angle": float(angle), "corrected": True}
            
            # 3. 智能裁剪：显著减少 Tiling 消耗 [cite: 183, 366]
            enhanced_img = self.smart_crop(enhanced_img)
            metadata["cropped"] = True
            
            enhanced_img.save(output_path, format="PNG", dpi=(TARGET_DPI, TARGET_DPI))
            
        except Exception as e:
            logger.error(f"  ✗ 图片预处理失败: {e}")
            image = Image.open(image_path).convert('RGB')
            image.save(output_path, 'PNG')
        
        return output_path, metadata

    def _call_paddle_ocr_api(self, image_path: str) -> List[str]:
        API_URL = "https://i8d1rd37aco4w6md.aistudio-app.com/layout-parsing"
        TOKEN = "f5100e5c057f19a8fc617ac41f30f12d576d01c4"
        text_lines = []
        try:
            with open(image_path, "rb") as file:
                file_data = base64.b64encode(file.read()).decode("ascii")
            headers = {"Authorization": f"token {TOKEN}", "Content-Type": "application/json"}
            payload = {
                "file": file_data, "fileType": 1,
                "useDocOrientationClassify": False, "useDocUnwarping": False
            }
            response = requests.post(API_URL, json=payload, headers=headers, timeout=120)
            if response.status_code == 200:
                res_json = response.json()
                for res in res_json.get("result", {}).get("layoutParsingResults", []):
                    md_text = res.get("markdown", {}).get("text", "")
                    text_lines.extend([line.strip() for line in md_text.split('\n') if line.strip()])
        except Exception as e:
            logger.error(f"  ✗ API 异常: {e}")
        return text_lines

    def _calculate_accuracy(self, text_list: List[str]) -> Dict[str, Any]:
        """保留原有的准确率评估逻辑"""
        if not text_list:
            return {"total_lines": 0, "character_count": 0, "quality_score": 0.0}
        total_lines = len(text_list)
        total_chars = sum(len(line) for line in text_list)
        # 简化版质量计算逻辑
        quality_score = min(100.0, 50.0 + (total_chars / 20.0))
        return {
            "total_lines": total_lines,
            "character_count": total_chars,
            "quality_score": float(quality_score)
        }

    def compare_single_image(self, image_path: str) -> Dict[str, Any]:
        """对比单张图片，包含 Tiling 量化 [cite: 412, 421]"""
        filename = os.path.basename(image_path)
        # 预初始化字典防止 KeyError
        result = {
            "filename": filename,
            "raw": {"tokens_estimated": 0, "metrics": {"quality_score": 0.0}},
            "enhanced": {"tokens_estimated": 0, "metrics": {"quality_score": 0.0}},
            "comparison": {"quality_score_improvement": 0.0, "token_saving_ratio_percent": 0.0}
        }

        try:
            # 1. 原始图处理
            raw_path = self._prepare_raw_image(image_path)
            raw_img = Image.open(raw_path)
            raw_tokens = self.estimate_tiling_tokens(raw_img.width, raw_img.height)
            raw_ocr = self._call_paddle_ocr_api(raw_path)
            raw_metrics = self._calculate_accuracy(raw_ocr)

            # 2. 增强图处理
            enhanced_path, metadata = self._prepare_enhanced_image(image_path)
            enhanced_img = Image.open(enhanced_path)
            enhanced_tokens = self.estimate_tiling_tokens(enhanced_img.width, enhanced_img.height)
            enhanced_ocr = self._call_paddle_ocr_api(enhanced_path)
            enhanced_metrics = self._calculate_accuracy(enhanced_ocr)

            # 3. 量化对比分析
            quality_diff = enhanced_metrics["quality_score"] - raw_metrics["quality_score"]
            token_saved = raw_tokens - enhanced_tokens
            saving_ratio = (token_saved / raw_tokens * 100) if raw_tokens > 0 else 0

            result.update({
                "raw": {"size": f"{raw_img.width}x{raw_img.height}", "tokens_estimated": raw_tokens, "metrics": raw_metrics},
                "enhanced": {"size": f"{enhanced_img.width}x{enhanced_img.height}", "tokens_estimated": enhanced_tokens, "metrics": enhanced_metrics, "metadata": metadata},
                "comparison": {
                    "quality_score_improvement": float(quality_diff),
                    "token_saved_absolute": int(token_saved),
                    "token_saving_ratio_percent": float(saving_ratio),
                    "summary": f"质量提升 {quality_diff:.1f}; Token 节省 {saving_ratio:.1f}%"
                }
            })
            logger.info(f"  ✓ {filename}: 质量提升 {quality_diff:.1f}, Token 节省 {saving_ratio:.1f}%")

        except Exception as e:
            logger.error(f"  ✗ 对比失败: {e}", exc_info=True)
        
        return result

    def batch_compare(self) -> List[Dict]:
        os.makedirs(COMPARISON_DIR, exist_ok=True)
        image_files = [f for f in os.listdir(RAW_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        
        results = []
        for filename in image_files:
            results.append(self.compare_single_image(os.path.join(RAW_DIR, filename)))
        
        self._save_report(results)
        return results
    
    def _save_report(self, results: List[Dict]) -> None:
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            json.dump({"timestamp": datetime.now().isoformat(), "results": results}, f, ensure_ascii=False, indent=2)
        logger.info(f"\n✓ 报告已保存: {REPORT_FILE}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="PaddleOCR 预处理效果对比")
    parser.add_argument('--batch', action='store_true', help='批量处理')
    parser.add_argument('--single', type=str, help='单张处理')
    
    args = parser.parse_args()
    comparator = OCRComparator()
    
    if args.single:
        comparator.compare_single_image(args.single)
    else:
        comparator.batch_compare()

if __name__ == "__main__":
    main()