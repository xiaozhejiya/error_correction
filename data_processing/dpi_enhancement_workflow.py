"""
低DPI图片增强工作流
集成 dpi_enhancement 工具与原有的 preprocess_pipeline
完整处理流程：低DPI检测 -> 上采样 -> 质量优化 -> 倾斜矫正 -> 标准化输出
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dpi_enhancement import DPIEnhancer
from preprocess_pipeline import (
    detect_skew_angle,
    correct_skew,
    SKEW_THRESHOLD
)
from PIL import Image
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ================= 工作流配置 =================
RAW_DIR = "benchmark/raw"           # 原始低DPI图片
ENHANCED_DIR = "benchmark/enhanced/"  # DPI提升后的图片
GT_DIR = "benchmark/ground_truth"    # 最终基准答案（标准化）

TARGET_DPI = 300
# =============================================


class DPIEnhancementWorkflow:
    """
    完整的DPI增强工作流
    
    流程步骤：
    1. 检测原始DPI和图片质量
    2. DPI提升和质量优化（使用 DPIEnhancer）
    3. 倾斜检测和矫正
    4. 最终标准化输出（300 DPI, PNG/JPG格式）
    """
    
    def __init__(self, 
                 target_dpi: int = TARGET_DPI,
                 min_acceptable_dpi: int = 200):
        """初始化工作流"""
        self.target_dpi = target_dpi
        self.min_acceptable_dpi = min_acceptable_dpi
        self.enhancer = DPIEnhancer(
            target_dpi=target_dpi,
            min_acceptable_dpi=min_acceptable_dpi,
            enable_quality_enhancement=True
        )
    
    def process_single_image(self, image_path: str) -> dict:
        """
        处理单张图片的完整工作流
        
        Args:
            image_path: 输入图片路径
            
        Returns:
            处理结果字典
        """
        filename = os.path.basename(image_path)
        logger.info(f"\n{'='*70}")
        logger.info(f"开始处理: {filename}")
        logger.info(f"{'='*70}")
        
        result = {
            "filename": filename,
            "steps": {},
            "success": False,
            "error": None
        }
        
        try:
            # ========== 1. DPI检测与提升 ==========
            logger.info("\n【步骤1】DPI检测与提升...")
            dpi_result = self.enhancer.process(
                image_path,
                output_path=os.path.join(ENHANCED_DIR, f"{Path(filename).stem}_dpi_enhanced.png"),
                output_format="PNG",
                enable_noise_reduction=True,
                enable_auto_contrast=True
            )
            
            result["steps"]["dpi_enhancement"] = dpi_result
            
            if not dpi_result["success"]:
                result["error"] = dpi_result["message"]
                logger.error(f"❌ DPI增强失败: {dpi_result['message']}")
                return result
            
            logger.info(f"✓ DPI增强完成: {dpi_result['message']}")
            
            # ========== 2. 倾斜检测与矫正 ==========
            logger.info("\n【步骤2】倾斜检测与矫正...")
            
            # 加载增强后的图片
            enhanced_image = Image.open(dpi_result["output_path"]).convert('RGB')
            
            # 检测倾斜角度
            angle = detect_skew_angle(enhanced_image)
            logger.info(f"检测到倾斜角度: {angle:.2f}°")
            
            # 矫正倾斜
            corrected_image = correct_skew(enhanced_image, angle)
            
            result["steps"]["skew_correction"] = {
                "angle": angle,
                "corrected": abs(angle) >= SKEW_THRESHOLD
            }
            
            logger.info(f"✓ 倾斜矫正完成")
            
            # ========== 3. 最终标准化输出 ==========
            logger.info("\n【步骤3】最终标准化输出...")
            
            # 确定输出路径
            final_filename = f"{Path(filename).stem}_final"
            output_path = os.path.join(GT_DIR, f"{final_filename}.png")
            
            os.makedirs(GT_DIR, exist_ok=True)
            
            # 保存为标准DPI的PNG格式
            corrected_image.save(
                output_path,
                format="PNG",
                dpi=(self.target_dpi, self.target_dpi),
                compress_level=9
            )
            
            logger.info(f"✓ 已保存至: {output_path}")
            
            result["steps"]["final_output"] = {
                "path": output_path,
                "format": "PNG",
                "dpi": self.target_dpi,
                "size": f"{corrected_image.width}x{corrected_image.height}"
            }
            
            # ========== 4. 生成处理报告 ==========
            result["success"] = True
            summary = f"""
✅ 图片处理完成! ({filename})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 处理摘要:
  • 原始DPI:      {dpi_result['original_dpi']} DPI
  • 增强因子:     {dpi_result['scale_factor']:.2f}x
  • 目标DPI:      {self.target_dpi} DPI
  • 倾斜角度:     {angle:.2f}°
  • 倾斜已矫正:   {'是' if abs(angle) >= SKEW_THRESHOLD else '否'}
  • 最终尺寸:     {corrected_image.width}x{corrected_image.height}
  • 输出格式:     PNG (无损)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            logger.info(summary)
            result["summary"] = summary
            
            return result
            
        except Exception as e:
            error_msg = f"处理失败: {str(e)}"
            result["error"] = error_msg
            logger.error(error_msg, exc_info=True)
            return result
    
    def process_batch(self, extensions=('.png', '.jpg', '.jpeg', '.bmp')):
        """
        批量处理目录中的所有图片
        
        Args:
            extensions: 要处理的文件扩展名
            
        Returns:
            批处理结果统计
        """
        # 创建必要的目录
        os.makedirs(RAW_DIR, exist_ok=True)
        os.makedirs(ENHANCED_DIR, exist_ok=True)
        os.makedirs(GT_DIR, exist_ok=True)
        
        # 收集图片文件
        image_files = [
            f for f in os.listdir(RAW_DIR)
            if f.lower().endswith(extensions)
        ]
        
        if not image_files:
            logger.warning(f"目录 {RAW_DIR} 中没有找到图片文件")
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "results": []
            }
        
        logger.info(f"\n{'#'*70}")
        logger.info(f"# 开始批量处理，共 {len(image_files)} 张图片")
        logger.info(f"{'#'*70}")
        
        results = {
            "total": len(image_files),
            "success": 0,
            "failed": 0,
            "results": []
        }
        
        for idx, filename in enumerate(image_files, 1):
            input_path = os.path.join(RAW_DIR, filename)
            
            try:
                result = self.process_single_image(input_path)
                results["results"].append(result)
                
                if result["success"]:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                logger.error(f"处理 {filename} 时出错: {e}")
                results["failed"] += 1
                results["results"].append({
                    "filename": filename,
                    "success": False,
                    "error": str(e)
                })
        
        # 输出最终统计
        logger.info(f"\n{'#'*70}")
        logger.info(f"# 批处理完成统计")
        logger.info(f"{'#'*70}")
        logger.info(f"总数:     {results['total']} 张")
        logger.info(f"成功:     {results['success']} 张 ✓")
        logger.info(f"失败:     {results['failed']} 张 ✗")
        logger.info(f"成功率:   {results['success']/results['total']*100:.1f}%")
        logger.info(f"\n✓ 标准化图片已保存至: {GT_DIR}")
        
        return results


# ===============================================
# 便捷函数

def enhance_and_standardize(image_path: str) -> bool:
    """
    快速处理单张图片：DPI增强 + 倾斜矫正 + 标准化
    
    Args:
        image_path: 输入图片路径
        
    Returns:
        是否成功
    """
    workflow = DPIEnhancementWorkflow()
    result = workflow.process_single_image(image_path)
    return result["success"]


def batch_enhance_and_standardize() -> int:
    """
    批量处理：DPI增强 + 倾斜矫正 + 标准化
    
    Returns:
        成功处理的图片数
    """
    workflow = DPIEnhancementWorkflow()
    results = workflow.process_batch()
    return results["success"]


# ===============================================
# 命令行入口

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="低DPI图片增强与标准化工作流",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 批量处理所有图片
  python dpi_enhancement_workflow.py --batch
  
  # 处理单张图片
  python dpi_enhancement_workflow.py --single path/to/image.jpg
  
  # 自定义目标DPI
  python dpi_enhancement_workflow.py --batch --dpi 300
        """
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理 RAW_DIR 中的所有图片"
    )
    
    parser.add_argument(
        "--single",
        type=str,
        help="处理单张图片，指定图片路径"
    )
    
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="目标DPI（默认: 300）"
    )
    
    parser.add_argument(
        "--min-dpi",
        type=int,
        default=200,
        help="最低可接受DPI，低于此值会触发增强（默认: 200）"
    )
    
    parser.add_argument(
        "--raw-dir",
        type=str,
        default=RAW_DIR,
        help="原始图片目录"
    )
    
    args = parser.parse_args()
    
    # 创建工作流实例
    workflow = DPIEnhancementWorkflow(
        target_dpi=args.dpi,
        min_acceptable_dpi=args.min_dpi
    )
    
    if args.batch:
        # 批量处理
        results = workflow.process_batch()
        sys.exit(0 if results["success"] > 0 else 1)
    
    elif args.single:
        # 单张处理
        if not os.path.exists(args.single):
            logger.error(f"文件不存在: {args.single}")
            sys.exit(1)
        
        result = workflow.process_single_image(args.single)
        sys.exit(0 if result["success"] else 1)
    
    else:
        parser.print_help()
        sys.exit(0)
