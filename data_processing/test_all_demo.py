"""
DPI增强工具 - 完整测试脚本
测试所有图片预处理功能

使用方法:
  python test_all_demo.py [选项]

选项:
  test1      运行测试1: 简单DPI增强 (单张)
  test2      运行测试2: 批量DPI增强
  test3      运行测试3: 完整工作流 (单张)
  test4      运行测试4: 完整工作流 (批量)
  all        运行所有测试 (默认)
"""

import os
import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 单个图片测试
text_image = "test2.png"  # 请确保在 benchmark/raw 目录下有这个测试图片

def test_dpi_enhancement_single():
    """测试1: 简单DPI增强 (单张图片)"""
    logger.info("\n" + "="*70)
    logger.info("【测试1】简单DPI增强 - 单张处理")
    logger.info("="*70)
    
    try:
        from dpi_enhancement import enhance_image
        
        current_dir = Path(__file__).parent.resolve()
        input_path = current_dir / "benchmark" / "raw" / f"{text_image}"
        
        if not input_path.exists():
            logger.warning(f"❌ 找不到测试图片: {input_path}")
            logger.info(f"✓ 提示: 请在 benchmark/raw 目录下放置 {text_image}")
            return False
        
        logger.info(f"输入: {input_path}")
        success = enhance_image(str(input_path))
        
        if success:
            output_path = input_path.parent / f"{input_path.stem}_enhanced.png"
            logger.info(f"✓ 处理成功!")
            logger.info(f"输出: {output_path}")
            return True
        else:
            logger.error("❌ 处理失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False


def test_dpi_enhancement_batch():
    """测试2: 批量DPI增强"""
    logger.info("\n" + "="*70)
    logger.info("【测试2】批量DPI增强 - 整个目录")
    logger.info("="*70)
    
    try:
        from dpi_enhancement import batch_enhance
        
        current_dir = Path(__file__).parent.resolve()
        input_dir = current_dir / "benchmark" / "raw"
        output_dir = current_dir / "benchmark" / "enhanced"
        
        # 检查输入目录
        if not input_dir.exists():
            os.makedirs(input_dir, exist_ok=True)
            logger.warning(f"⚠️  输入目录已创建: {input_dir}")
            logger.info("✓ 提示: 请将低DPI图片放入此目录")
            return False
        
        image_files = list(input_dir.glob("*.png")) + list(input_dir.glob("*.jpg")) + \
                     list(input_dir.glob("*.jpeg")) + list(input_dir.glob("*.bmp"))
        
        if not image_files:
            logger.warning(f"⚠️  输入目录为空: {input_dir}")
            logger.info("✓ 提示: 请在 benchmark/raw 目录下放置图片")
            return False
        
        logger.info(f"输入目录: {input_dir}")
        logger.info(f"输出目录: {output_dir}")
        logger.info(f"找到 {len(image_files)} 张图片\n")
        
        success_count = batch_enhance(str(input_dir), str(output_dir))
        
        if success_count > 0:
            logger.info(f"✓ 批处理完成! 成功处理 {success_count} 张图片")
            return True
        else:
            logger.warning("⚠️  没有处理任何图片")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False


def test_dpi_enhancement_workflow_single():
    """测试3: 完整工作流 (单张)"""
    logger.info("\n" + "="*70)
    logger.info("【测试3】完整工作流 - 单张处理")
    logger.info("处理流程: DPI增强 → 倾斜矫正 → 标准化输出")
    logger.info("="*70)
    
    try:
        from dpi_enhancement_workflow import DPIEnhancementWorkflow
        
        current_dir = Path(__file__).parent.resolve()
        input_path = current_dir / "benchmark" / "raw" / f"{text_image}"
        
        if not input_path.exists():
            logger.warning(f"❌ 找不到测试图片: {input_path}")
            logger.info(f"✓ 提示: 请在 benchmark/raw 目录下放置 {text_image}")
            return False
        
        logger.info(f"输入: {input_path}\n")
        
        # 创建工作流
        workflow = DPIEnhancementWorkflow(target_dpi=300)
        result = workflow.process_single_image(str(input_path))
        
        if result["success"]:
            logger.info("\n" + result["summary"])
            logger.info(f"✓ 工作流完成!")
            logger.info(f"最终输出: {result['steps']['final_output']['path']}")
            return True
        else:
            logger.error(f"❌ 工作流失败: {result['error']}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dpi_enhancement_workflow_batch():
    """测试4: 完整工作流 (批量)"""
    logger.info("\n" + "="*70)
    logger.info("【测试4】完整工作流 - 批量处理")
    logger.info("处理流程: DPI增强 → 倾斜矫正 → 标准化输出")
    logger.info("="*70)
    
    try:
        from dpi_enhancement_workflow import DPIEnhancementWorkflow
        
        current_dir = Path(__file__).parent.resolve()
        raw_dir = current_dir / "benchmark" / "raw"
        
        if not raw_dir.exists():
            os.makedirs(raw_dir, exist_ok=True)
            logger.warning(f"⚠️  输入目录已创建: {raw_dir}")
            logger.info("✓ 提示: 请将低DPI图片放入此目录")
            return False
        
        image_files = list(raw_dir.glob("*.png")) + list(raw_dir.glob("*.jpg")) + \
                     list(raw_dir.glob("*.jpeg")) + list(raw_dir.glob("*.bmp"))
        
        if not image_files:
            logger.warning(f"⚠️  输入目录为空: {raw_dir}")
            logger.info("✓ 提示: 请在 benchmark/raw 目录下放置图片")
            return False
        
        logger.info(f"输入目录: {raw_dir}")
        logger.info(f"找到 {len(image_files)} 张图片\n")
        
        # 创建工作流
        workflow = DPIEnhancementWorkflow(
            target_dpi=300,
            min_acceptable_dpi=200
        )
        
        results = workflow.process_batch()
        
        logger.info(f"\n✓ 批处理完成!")
        logger.info(f"总数: {results['total']} 张")
        logger.info(f"成功: {results['success']} 张")
        logger.info(f"失败: {results['failed']} 张")
        
        if results['total'] > 0:
            success_rate = results['success'] / results['total'] * 100
            logger.info(f"成功率: {success_rate:.1f}%")
        
        logger.info(f"\n输出目录: benchmark/ground_truth/")
        
        return results['success'] > 0
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_usage():
    """显示使用说明"""
    usage = """
╔════════════════════════════════════════════════════════════════════════╗
║          DPI增强工具 - 完整测试脚本                                    ║
╚════════════════════════════════════════════════════════════════════════╝

✨ 本脚本会运行以下测试:

  1️⃣  简单DPI增强 (单张)
      └─ 快速增强单张图片: test1.jpg → test1_enhanced.png
      
  2️⃣  批量DPI增强
      └─ 批量增强整个目录中的图片
      
  3️⃣  完整工作流 (单张)
      └─ DPI增强 + 倾斜矫正 + 标准化输出
      └─ 输入: test2.png → 输出: benchmark/ground_truth/
      
  4️⃣  完整工作流 (批量)
      └─ 批量处理所有图片的完整工作流
      └─ 输出: benchmark/ground_truth/

📂 目录结构:

  benchmark/
  ├── raw/              ← 输入目录 (放置原始低DPI图片)
  ├── enhanced/         ← DPI增强的中间产物
  └── ground_truth/     ← 最终标准化图片 (输出)

💡 使用建议:

  1. 确保在 benchmark/raw 目录下有测试图片
  2. 运行此脚本查看预处理效果
  3. 根据结果调整参数
  4. 运行你的OCR处理流程

📌 快速命令:

  # 运行所有测试
  python test_all_demo.py

  # 只运行单个测试
  python test_all_demo.py test1
  python test_all_demo.py test3

  # 批量处理所有图片 (在data_processing目录下)
  python dpi_enhancement_workflow.py --batch

  # 处理单张图片
  python dpi_enhancement_workflow.py --single path/to/image.jpg

════════════════════════════════════════════════════════════════════════
"""
    print(usage)


if __name__ == "__main__":
    
    # 显示使用说明
    show_usage()
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        test_to_run = sys.argv[1].lower()
    else:
        test_to_run = "all"
    
    # 定义测试集合
    tests = {
        "test1": ("测试1: 简单DPI增强 (单张)", test_dpi_enhancement_single),
        "test2": ("测试2: 批量DPI增强", test_dpi_enhancement_batch),
        "test3": ("测试3: 完整工作流 (单张)", test_dpi_enhancement_workflow_single),
        "test4": ("测试4: 完整工作流 (批量)", test_dpi_enhancement_workflow_batch),
    }
    
    # 决定运行哪些测试
    if test_to_run == "all":
        tests_to_execute = tests.items()
    elif test_to_run in tests:
        tests_to_execute = [(test_to_run, tests[test_to_run])]
    else:
        logger.error(f"❌ 未知的测试选项: {test_to_run}")
        logger.info("可用选项: test1, test2, test3, test4, all")
        sys.exit(1)
    
    # 运行测试
    logger.info(f"\n开始运行测试...\n")
    
    results = {}
    for test_key, (test_name, test_func) in tests_to_execute:
        success = test_func()
        results[test_name] = success
    
    # 汇总结果
    logger.info("\n" + "#"*70)
    logger.info("# 测试汇总")
    logger.info("#"*70)
    
    for test_name, success in results.items():
        status = "✓ 通过  " if success else "✗ 跳过/失败"
        logger.info(f"{status} {test_name}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    logger.info("\n" + "="*70)
    logger.info(f"测试完成: {passed}/{total} 个测试通过")
    logger.info("="*70)
    
    if passed == total and total > 0:
        logger.info("✨ 所有测试都通过了! 图片预处理工具已就绪。\n")
    elif passed > 0:
        logger.info(f"⚠️  部分测试未通过,请检查输入目录是否有测试图片。\n")
    else:
        logger.info("❌ 所有测试都未通过,请检查环境配置。\n")
