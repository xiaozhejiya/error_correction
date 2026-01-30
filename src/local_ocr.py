"""
PaddleOCR 服务模块
提供图片文字识别功能，支持中英文混合识别
"""
import os
import logging

os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

import warnings
warnings.filterwarnings('ignore')

from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)

# 全局 OCR 实例（避免重复加载模型）
_ocr_instance = None


def get_ocr_instance():
    """获取 PaddleOCR 单例实例"""
    global _ocr_instance
    if _ocr_instance is None:
        logger.info("正在加载 PaddleOCR 模型...")
        _ocr_instance = PaddleOCR(lang='ch')
        logger.info("PaddleOCR 模型加载完成")
    return _ocr_instance


def recognize_image(image_path: str) -> dict:
    """
    对图片进行 OCR 文字识别

    Args:
        image_path: 图片文件路径

    Returns:
        dict: {
            "success": bool,
            "texts": [{"text": str, "confidence": float, "position": list}],
            "full_text": str,
            "error": str or None
        }
    """
    try:
        if not os.path.exists(image_path):
            return {"success": False, "texts": [], "full_text": "", "error": f"文件不存在: {image_path}"}

        ocr = get_ocr_instance()
        result = ocr.predict(image_path)

        texts = []
        for res in result:
            rec_texts = res.get('rec_texts', [])
            rec_scores = res.get('rec_scores', [])
            dt_polys = res.get('dt_polys', [])

            for i, text in enumerate(rec_texts):
                score = rec_scores[i] if i < len(rec_scores) else 0.0
                position = dt_polys[i].tolist() if i < len(dt_polys) else []
                texts.append({
                    "text": text,
                    "confidence": round(float(score), 4),
                    "position": position
                })

        full_text = "\n".join([t["text"] for t in texts])

        return {
            "success": True,
            "texts": texts,
            "full_text": full_text,
            "error": None
        }

    except Exception as e:
        logger.error(f"OCR 识别失败: {str(e)}")
        return {"success": False, "texts": [], "full_text": "", "error": str(e)}
