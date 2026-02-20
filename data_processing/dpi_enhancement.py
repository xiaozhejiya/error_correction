"""
低DPI图片增强工具
将原生低DPI图片转换为符合PaddleOCR最佳识别的DPI和格式

核心功能：
1. 智能DPI检测和提升（上采样）
2. 图片质量优化（对比度、清晰度）
3. 噪声处理和去模糊
4. 格式转换和压缩优化
"""

import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import logging

# ================= 配置常量 =================
# PaddleOCR 最佳实践参数
TARGET_DPI = 300           # 目标 DPI
MIN_ACCEPTABLE_DPI = 200   # 最低可接受 DPI（低于此值需要提升）
MAX_ACCEPTABLE_DPI = 600   # 最高可接受 DPI（防止过度放大）
DEFAULT_DPI = 72           # 未指定DPI时的默认值

# 图片质量参数
MIN_IMAGE_WIDTH = 400      # 最小宽度（像素）
MIN_IMAGE_HEIGHT = 400     # 最小高度（像素）
MAX_IMAGE_SIZE = 5000      # 最大边长（像素）

# 格式输出参数
OUTPUT_FORMAT = "PNG"      # 输出格式（PNG 保留细节，JPG 节省空间）
PNG_COMPRESSION = 9        # PNG 压缩级别 (0-9)
JPG_QUALITY = 95           # JPG 质量 (1-100)

logger = logging.getLogger(__name__)
# ===============================================


class DPIEnhancer:
    """低DPI图片增强器"""
    
    def __init__(self, 
                 target_dpi: int = TARGET_DPI,
                 min_acceptable_dpi: int = MIN_ACCEPTABLE_DPI,
                 enable_quality_enhancement: bool = True):
        """
        初始化增强器
        
        Args:
            target_dpi: 目标 DPI（默认300）
            min_acceptable_dpi: 最低可接受 DPI（低于此值会触发提升）
            enable_quality_enhancement: 是否启用质量增强（对比度、清晰度）
        """
        self.target_dpi = target_dpi
        self.min_acceptable_dpi = min_acceptable_dpi
        self.enable_quality_enhancement = enable_quality_enhancement
    
    def detect_dpi(self, image_path: str) -> int:
        """
        检测图片的DPI
        
        Args:
            image_path: 图片路径
            
        Returns:
            检测到的DPI值
        """
        try:
            with Image.open(image_path) as img:
                # 尝试获取图片元数据中的DPI
                dpi_info = img.info.get('dpi')
                if dpi_info:
                    return int(dpi_info[0])
                
                # 如果图片没有DPI信息，检查图片大小来推测
                # 通常DPI信息在元数据中
                logger.warning(f"图片 {image_path} 未包含DPI信息，使用默认值 {DEFAULT_DPI}")
                return DEFAULT_DPI
        except Exception as e:
            logger.error(f"检测DPI失败: {e}")
            return DEFAULT_DPI
    
    def calculate_upsampling_factor(self, current_dpi: int) -> float:
        """
        计算上采样因子
        
        将 current_dpi 转换为 target_dpi 所需的缩放倍数
        
        Args:
            current_dpi: 当前DPI
            
        Returns:
            缩放倍数（>1 表示放大）
        """
        if current_dpi <= 0:
            current_dpi = DEFAULT_DPI
        
        factor = self.target_dpi / current_dpi
        
        # 限制缩放因子，防止过度放大
        if factor > 4.0:  # 超过4倍放大需要警告
            logger.warning(
                f"DPI提升倍数过高 ({factor:.2f}x)，可能导致效果不佳。"
                f"建议检查原始图片质量。"
            )
            factor = min(factor, 4.0)
        
        return factor
    
    def upsample_image(self, 
                       image: Image.Image, 
                       scale_factor: float,
                       method: str = "lanczos") -> Image.Image:
        """
        高质量上采样
        
        使用多种插值算法进行上采样，保留图片细节
        
        Args:
            image: PIL Image 对象
            scale_factor: 缩放倍数
            method: 插值方法 ("lanczos", "bicubic", "super_resolution")
            
        Returns:
            上采样后的 PIL Image 对象
        """
        if scale_factor <= 1.0:
            return image
        
        new_width = int(image.width * scale_factor)
        new_height = int(image.height * scale_factor)
        
        # 限制最大尺寸
        if new_width > MAX_IMAGE_SIZE or new_height > MAX_IMAGE_SIZE:
            ratio = MAX_IMAGE_SIZE / max(new_width, new_height)
            new_width = int(new_width * ratio)
            new_height = int(new_height * ratio)
            logger.warning(f"图片尺寸超过限制，已缩放至 {new_width}x{new_height}")
        
        logger.info(f"上采样: {image.width}x{image.height} -> {new_width}x{new_height} "
                   f"(factor: {scale_factor:.2f}x)")
        
        if method == "lanczos":
            # Lanczos 是最高质量的插值方法，适合放大10倍以内
            upsampled = image.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )
        elif method == "bicubic":
            # Bicubic 适合中等放大倍数
            upsampled = image.resize(
                (new_width, new_height),
                Image.Resampling.BICUBIC
            )
        else:
            # 默认使用 LANCZOS
            upsampled = image.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )
        
        return upsampled
    
    def enhance_quality(self, image: Image.Image) -> Image.Image:
        """
        增强图片质量
        
        包括：
        - 对比度增强（使文本更清晰）
        - 清晰度增强（防止模糊）
        - 亮度自适应调整
        
        Args:
            image: PIL Image 对象
            
        Returns:
            增强后的 PIL Image 对象
        """
        if not self.enable_quality_enhancement:
            return image
        
        logger.info("开始质量增强处理...")
        
        # 1. 对比度增强
        contrast_enhancer = ImageEnhance.Contrast(image)
        image = contrast_enhancer.enhance(1.3)  # 提升30%对比度
        logger.debug("✓ 对比度增强 (+30%)")
        
        # 2. 清晰度增强
        sharpness_enhancer = ImageEnhance.Sharpness(image)
        image = sharpness_enhancer.enhance(1.2)  # 提升20%清晰度
        logger.debug("✓ 清晰度增强 (+20%)")
        
        # 3. 亮度调整（防止过暗）
        brightness_enhancer = ImageEnhance.Brightness(image)
        image = brightness_enhancer.enhance(1.05)  # 轻微提升亮度
        logger.debug("✓ 亮度微调 (+5%)")
        
        return image
    
    def reduce_noise(self, image: Image.Image) -> Image.Image:
        """
        降噪处理
        
        使用多种算法减少图片噪声，同时保留细节
        
        Args:
            image: PIL Image 对象
            
        Returns:
            降噪后的 PIL Image 对象
        """
        logger.info("开始降噪处理...")
        
        # 转换为 OpenCV 格式
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # 使用双边滤波（Bilateral Filter）
        # 边保留滤波，很好地保留边缘同时去除噪声
        denoised = cv2.bilateralFilter(cv_image, 9, 75, 75)
        logger.debug("✓ 双边滤波降噪")
        
        # 转换回 PIL 格式
        result = Image.fromarray(cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB))
        
        return result
    
    def auto_contrast(self, image: Image.Image) -> Image.Image:
        """
        自动对比度调整
        
        自动检测和调整对比度，提高文本识别率
        
        Args:
            image: PIL Image 对象
            
        Returns:
            调整后的 PIL Image 对象
        """
        # 转换为灰度图分析
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        
        # 计算对比度（标准差）
        contrast = np.std(gray)
        
        # 如果对比度偏低，进行 CLAHE（对比度自适应直方图均衡化）
        if contrast < 30:
            logger.info(f"检测到低对比度 (σ={contrast:.1f})，进行CLAHE处理...")
            
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced_gray = clahe.apply(gray)
            
            # 转换回彩色
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            b, g, r = cv2.split(cv_image)
            
            b = clahe.apply(b)
            g = clahe.apply(g)
            r = clahe.apply(r)
            
            enhanced_cv = cv2.merge([b, g, r])
            result = Image.fromarray(cv2.cvtColor(enhanced_cv, cv2.COLOR_BGR2RGB))
            
            logger.debug("✓ CLAHE 对比度增强")
            return result
        
        return image
    
    def process(self,
                image_path: str,
                output_path: Optional[str] = None,
                output_format: str = OUTPUT_FORMAT,
                enable_noise_reduction: bool = True,
                enable_auto_contrast: bool = True) -> Dict[str, Any]:
        """
        处理单张图片的完整流程
        
        Args:
            image_path: 输入图片路径
            output_path: 输出路径（如果为None，在原路径添加后缀）
            output_format: 输出格式 ("PNG" 或 "JPG")
            enable_noise_reduction: 是否启用降噪
            enable_auto_contrast: 是否启用自动对比度
            
        Returns:
            处理结果字典，包含：
            - success: 是否成功
            - original_dpi: 原始DPI
            - enhanced_dpi: 增强后的DPI
            - scale_factor: 缩放倍数
            - output_path: 输出路径
            - message: 处理信息
        """
        result = {
            "success": False,
            "original_dpi": 0,
            "enhanced_dpi": self.target_dpi,
            "scale_factor": 1.0,
            "output_path": None,
            "message": ""
        }
        
        try:
            # 1. 检测原始 DPI
            original_dpi = self.detect_dpi(image_path)
            result["original_dpi"] = original_dpi
            
            # 2. 打开图片
            logger.info(f"处理图片: {image_path}")
            image = Image.open(image_path).convert('RGB')
            logger.info(f"原始尺寸: {image.width}x{image.height}, 原始DPI: {original_dpi}")
            
            # 检查最小尺寸
            if image.width < MIN_IMAGE_WIDTH or image.height < MIN_IMAGE_HEIGHT:
                logger.warning(
                    f"图片尺寸过小 ({image.width}x{image.height})，"
                    f"推荐最小 {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT}"
                )
            
            # 3. 判断是否需要 DPI 提升
            needs_upsampling = original_dpi < self.min_acceptable_dpi
            
            if needs_upsampling:
                scale_factor = self.calculate_upsampling_factor(original_dpi)
                result["scale_factor"] = scale_factor
                image = self.upsample_image(image, scale_factor)
                logger.info(f"✓ DPI提升完成: {original_dpi} -> {self.target_dpi}")
            else:
                logger.info(f"✓ DPI {original_dpi} 已满足要求，无需提升")
            
            # 4. 降噪处理
            if enable_noise_reduction:
                image = self.reduce_noise(image)
            
            # 5. 自动对比度增强
            if enable_auto_contrast:
                image = self.auto_contrast(image)
            
            # 6. 质量增强
            image = self.enhance_quality(image)
            
            # 7. 确定输出路径
            if output_path is None:
                base_path = Path(image_path)
                output_path = str(base_path.parent / f"{base_path.stem}_enhanced.{output_format.lower()}")
            
            result["output_path"] = output_path
            
            # 8. 保存输出
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            
            if output_format.upper() == "PNG":
                image.save(
                    output_path,
                    format="PNG",
                    dpi=(self.target_dpi, self.target_dpi),
                    compress_level=PNG_COMPRESSION
                )
                logger.info(f"✓ 已保存为PNG格式 (DPI: {self.target_dpi})")
            else:  # JPG
                image.save(
                    output_path,
                    format="JPEG",
                    dpi=(self.target_dpi, self.target_dpi),
                    quality=JPG_QUALITY,
                    optimize=True
                )
                logger.info(f"✓ 已保存为JPG格式 (DPI: {self.target_dpi}, 质量: {JPG_QUALITY})")
            
            # 9. 获取输出文件大小
            output_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            
            result["success"] = True
            result["message"] = (
                f"成功处理: {original_dpi}DPI -> {self.target_dpi}DPI "
                f"({scale_factor:.2f}x) | 输出: {output_size_mb:.2f}MB"
            )
            logger.info(f"✓ {result['message']}")
            
            return result
            
        except Exception as e:
            error_msg = f"处理失败: {str(e)}"
            result["message"] = error_msg
            logger.error(error_msg, exc_info=True)
            return result
    
    def batch_process(self,
                      input_dir: str,
                      output_dir: str,
                      extensions: Tuple[str, ...] = ('.png', '.jpg', '.jpeg', '.bmp'),
                      output_format: str = OUTPUT_FORMAT,
                      enable_noise_reduction: bool = True,
                      enable_auto_contrast: bool = True) -> Dict[str, Any]:
        """
        批量处理目录中的所有图片
        
        Args:
            input_dir: 输入目录
            output_dir: 输出目录
            extensions: 要处理的文件扩展名
            output_format: 输出格式
            enable_noise_reduction: 是否启用降噪
            enable_auto_contrast: 是否启用自动对比度
            
        Returns:
            批处理结果统计
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 收集所有待处理图片
        image_files = [
            f for f in os.listdir(input_dir)
            if f.lower().endswith(extensions)
        ]
        
        if not image_files:
            logger.warning(f"目录 {input_dir} 中没有找到图片文件")
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "results": []
            }
        
        logger.info(f"开始批量处理，共 {len(image_files)} 张图片...")
        
        results = {
            "total": len(image_files),
            "success": 0,
            "failed": 0,
            "results": []
        }
        
        for idx, filename in enumerate(image_files, 1):
            input_path = os.path.join(input_dir, filename)
            
            # 保持原文件名，改变扩展名
            output_filename = f"{Path(filename).stem}_enhanced.{output_format.lower()}"
            output_path = os.path.join(output_dir, output_filename)
            
            logger.info(f"[{idx}/{len(image_files)}] 处理: {filename}")
            
            result = self.process(
                input_path,
                output_path,
                output_format,
                enable_noise_reduction,
                enable_auto_contrast
            )
            
            results["results"].append({
                "filename": filename,
                "status": "✓" if result["success"] else "✗",
                **result
            })
            
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
        
        # 打印汇总统计
        logger.info("=" * 60)
        logger.info(f"批处理完成: 成功 {results['success']}/{results['total']}, "
                   f"失败 {results['failed']}/{results['total']}")
        logger.info("=" * 60)
        
        return results


# ===============================================
# 便捷函数（直接调用）

def enhance_image(image_path: str, output_path: Optional[str] = None) -> bool:
    """
    快速增强单张图片
    
    Args:
        image_path: 输入图片路径
        output_path: 输出路径（可选）
        
    Returns:
        是否成功
    """
    enhancer = DPIEnhancer()
    result = enhancer.process(image_path, output_path)
    return result["success"]


def batch_enhance(input_dir: str, output_dir: str) -> int:
    """
    快速批量增强图片
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        
    Returns:
        成功数
    """
    enhancer = DPIEnhancer()
    results = enhancer.batch_process(input_dir, output_dir)
    return results["success"]


# ===============================================
# 命令行使用示例

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 示例1: 处理单张图片
    print("\n[示例1] 处理单张低DPI图片:")
    print("-" * 60)
    enhancer = DPIEnhancer(target_dpi=300)
    
    # 如果有测试图片，可以这样调用：
    # result = enhancer.process("path/to/low_dpi_image.jpg")
    # print(result)
    
    # 示例2: 批量处理
    print("\n[示例2] 批量处理图片:")
    print("-" * 60)
    results = enhancer.batch_process(
        input_dir="data_processing/benchmark/raw",
        output_dir="data_processing/benchmark/enhanced",
        output_format="PNG"
    )
    print(f"处理完成: {results['success']}/{results['total']} 成功")
