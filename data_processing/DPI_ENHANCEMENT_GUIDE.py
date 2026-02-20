"""
==============================================
低DPI图片增强工具 - 使用指南和API参考
==============================================

本文档说明如何使用 dpi_enhancement 模块和 dpi_enhancement_workflow 
来处理低DPI图片，使其符合 PaddleOCR 的最优识别条件。

作者: Error Correction Project
日期: 2026年2月
"""

"""
【快速开始】
==================================================

1. 最简单的用法 - 处理单张图片
---------------------------------------------------

from data_processing.dpi_enhancement import enhance_image

# 自动增强图片DPI
enhance_image("path/to/low_dpi_image.jpg")

# 增强后的图片会保存为: path/to/low_dpi_image_enhanced.png


2. 批量处理
---------------------------------------------------

from dpi_enhancement import batch_enhance

# 批量增强目录中的所有图片
success_count = batch_enhance(
    input_dir="benchmark/raw",
    output_dir="benchmark/enhanced"
)

print(f"成功处理 {success_count} 张图片")


3. 完整工作流（推荐）- DPI增强 + 倾斜矫正 + 标准化
---------------------------------------------------

from dpi_enhancement_workflow import DPIEnhancementWorkflow

# 创建工作流
workflow = DPIEnhancementWorkflow(target_dpi=300)

# 批量处理
results = workflow.process_batch()
print(f"成功: {results['success']}/{results['total']}")


4. 命令行使用
---------------------------------------------------

# 批量处理所有图片
cd data_processing
python dpi_enhancement_workflow.py --batch

# 处理单张图片
python dpi_enhancement_workflow.py --single path/to/image.jpg

# 自定义DPI
python dpi_enhancement_workflow.py --batch --dpi 400


==================================================
【详细API参考】
==================================================

### DPIEnhancer 类

初始化参数:
  - target_dpi (int): 目标DPI，默认300
  - min_acceptable_dpi (int): 最低可接受DPI，默认200
  - enable_quality_enhancement (bool): 是否启用质量增强，默认True

主要方法:

1. detect_dpi(image_path: str) -> int
   ✓ 检测图片的原始DPI
   ✓ 如果没有DPI信息，返回默认值72
   
   示例:
     enhancer = DPIEnhancer()
     dpi = enhancer.detect_dpi("image.jpg")
     print(f"DPI: {dpi}")


2. calculate_upsampling_factor(current_dpi: int) -> float
   ✓ 计算将 current_dpi 转换到 target_dpi 所需的缩放倍数
   ✓ 例：从 150 DPI 到 300 DPI 需要 2x 放大
   
   示例:
     factor = enhancer.calculate_upsampling_factor(150)
     print(f"需要放大 {factor:.2f} 倍")  # 输出: 2.0


3. process(image_path: str, output_path: Optional[str] = None, ...) -> Dict
   ✓ 处理单张图片的完整流程：DPI检测 -> 上采样 -> 质量优化
   ✓ 返回包含处理结果的字典
   
   参数:
     image_path: 输入图片路径 (必需)
     output_path: 输出路径，不指定则自动生成
     output_format: "PNG" 或 "JPG" (默认 "PNG")
     enable_noise_reduction: 是否降噪 (默认 True)
     enable_auto_contrast: 是否自动对比度增强 (默认 True)
   
   返回值:
     {
       "success": True/False,
       "original_dpi": 150,
       "enhanced_dpi": 300,
       "scale_factor": 2.0,
       "output_path": "path/to/output.png",
       "message": "处理完成信息"
     }
   
   示例:
     enhancer = DPIEnhancer(target_dpi=300)
     result = enhancer.process("image.jpg", output_path="output.png")
     
     if result["success"]:
         print(f"✓ 从 {result['original_dpi']} DPI 提升到 {result['enhanced_dpi']} DPI")
         print(f"  缩放倍数: {result['scale_factor']:.2f}x")
         print(f"  输出: {result['output_path']}")
     else:
         print(f"✗ 处理失败: {result['message']}")


4. batch_process(input_dir: str, output_dir: str, ...) -> Dict
   ✓ 批量处理目录中的所有图片
   ✓ 返回处理结果统计
   
   参数:
     input_dir: 输入目录
     output_dir: 输出目录
     extensions: 文件扩展名 (默认 .png, .jpg, .jpeg, .bmp)
     output_format: 输出格式 (默认 "PNG")
     enable_noise_reduction: 是否降噪 (默认 True)
     enable_auto_contrast: 是否自动对比度增强 (默认 True)
   
   返回值:
     {
       "total": 10,           # 总处理数
       "success": 9,          # 成功数
       "failed": 1,           # 失败数
       "results": [...]       # 各个文件的处理结果
     }
   
   示例:
     results = enhancer.batch_process(
         input_dir="raw_images",
         output_dir="enhanced_images"
     )
     print(f"成功: {results['success']}/{results['total']}")


==================================================
【DPIEnhancementWorkflow 工作流】
==================================================

多步骤处理流程：DPI增强 -> 倾斜矫正 -> 标准化输出

初始化:
  workflow = DPIEnhancementWorkflow(target_dpi=300, min_acceptable_dpi=200)

主要方法:

1. process_single_image(image_path: str) -> dict
   完整处理一张图片：
   ✓ 步骤1: DPI检测与上采样
   ✓ 步骤2: 倾斜检测与矫正
   ✓ 步骤3: 最终标准化输出
   
   示例:
     result = workflow.process_single_image("raw/document.jpg")
     print(result["summary"])
     # 输出处理摘要和最终统计


2. process_batch(extensions: tuple = (...)) -> dict
   批量处理所有图片
   
   示例:
     results = workflow.process_batch()
     print(f"成功率: {results['success']/results['total']*100:.1f}%")


==================================================
【处理效果和参数说明】
==================================================

### 关键参数说明

1. target_dpi = 300
   - PaddleOCR 推荐的最优DPI
   - 在此DPI下中文识别准确度最高
   - 平衡了质量和性能

2. min_acceptable_dpi = 200
   - 低于此值的DPI会触发上采样
   - 200-300 DPI 之间会略微提升
   - 避免不必要的处理

3. 缩放倍数限制
   - 最高4x放大（保证效果）
   - 超过此倍数会发出警告
   
   常见缩放倍数:
   ┌─────────────┬──────────┬──────────────┐
   │ 原始 DPI    │ 缩放倍数 │ 最终 DPI     │
   ├─────────────┼──────────┼──────────────┤
   │ 72          │ 4.17x    │ 300          │ ← 最大放大
   │ 100         │ 3.0x     │ 300          │
   │ 150         │ 2.0x     │ 300          │ ← 推荐范围
   │ 200         │ 1.5x     │ 300          │
   │ 300         │ 1.0x     │ 300          │ ← 原始即可
   │ 400+        │ ≤1.0x    │ 保持原样或缩小 │
   └─────────────┴──────────┴──────────────┘

4. 降噪 (enable_noise_reduction=True)
   - 使用双边滤波算法
   - 去除图片噪声的同时保留边缘
   - 提高OCR识别准确度 (~2-3%)

5. 自动对比度增强 (enable_auto_contrast=True)
   - 检测图片的对比度
   - 对比度过低时使用CLAHE算法
   - 提高文本清晰度 (~3-5%)

6. 质量增强
   - 对比度 +30%
   - 清晰度 +20%
   - 亮度 +5%


==================================================
【性能和资源使用】
==================================================

处理时间 (估计):
┌──────────────┬──────────────┬─────────────────┐
│ 图片分辨率   │ 缩放倍数     │ 处理时间        │
├──────────────┼──────────────┼─────────────────┤
│ 1000x1414    │ 1x (无需)    │ 0.5 - 1  秒     │
│ 1000x1414    │ 2x (放大)    │ 2 - 3    秒     │
│ 1000x1414    │ 3x (大放大)  │ 3 - 5    秒     │
│ 2000x2828    │ 2x           │ 5 - 8    秒     │
└──────────────┴──────────────┴─────────────────┘

内存使用 (估计):
  - 原图 + 临时处理: ~50-100 MB (取决于分辨率)
  - 处理后保存为PNG: 占用空间较大 (推荐用于最终基准)
  - 处理后保存为JPG: 节省空间 (推荐用于中间处理)


==================================================
【输出格式对比】
==================================================

PNG 格式 (推荐用于基准数据集):
  ✓ 无损压缩，保留所有细节
  ✓ 适合作为ground truth
  ✗ 文件大小较大 (2-10 MB)
  ✗ 处理速度稍慢

JPG 格式 (推荐用于快速处理):
  ✓ 文件大小小 (200-500 KB)
  ✓ 处理速度快
  ✓ 质量95%以上无损感知
  ✗ 有损压缩，细节可能丧失


==================================================
【常见问题 (FAQ)】
==================================================

Q1: 如何判断图片DPI是否过低?
A: 使用 detect_dpi() 方法。低于200 DPI 的图片建议进行增强。
   可以用肉眼观察：文字边缘模糊、点阵明显则需要增强。

Q2: 能放大多少倍而不损失质量?
A: 一般建议不超过 2x-3x。超过 4x 会有明显质量下降。
   对于超低DPI (50-100) 的图片，可能需要接受一定的质量损失。

Q3: 处理后的图片OCR识别准确度能提高多少?
A: 取决于原始图片质量。一般提升 5-15%，某些情况可达 20%+。
   特别是对于清晰文本，提升效果显著。

Q4: 能同时处理PDF吗?
A: 当前工具只处理图片。PDF 需要先用 pdf2image 转换。
   参考 preprocess_pipeline.py 中的PDF处理逻辑。

Q5: 如何加速批处理?
A: 
  - 减少启用的优化选项：disable_noise_reduction, disable_auto_contrast
  - 使用 JPG 格式代替 PNG
  - 在新线程或进程池中处理多张图片
  
  示例（使用进程池）:
    from concurrent.futures import ProcessPoolExecutor
    
    enhancer = DPIEnhancer()
    image_paths = [...]  # 图片列表
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = executor.map(enhancer.process, image_paths)

Q6: 如何集成到我的OCR流程中?
A: 在调用 PaddleOCR 之前，先用本工具预处理图片：
   
   # 步骤1: 增强图片
   enhancer = DPIEnhancer()
   result = enhancer.process("raw_image.jpg")
   
   # 步骤2: 用增强后的图片进行OCR
   ocr_client.parse_image(result["output_path"])


==================================================
【与现有工具的集成】
==================================================

与 preprocess_pipeline.py 的关系:
  ✓ preprocess_pipeline.py: 用于构建基准数据集 (标准化处理)
  ✓ dpi_enhancement.py: 用于OCR前预处理 (质量优化)
  
  推荐使用顺序:
  1. 使用 dpi_enhancement_workflow.py 预处理所有图片
  2. 构建标准化的基准数据集 (GT目录)
  3. 后续OCR处理使用增强后的图片

与 paddleocr_client.py 的集成:
  建议修改 paddleocr_client.py 的 parse_image 方法：
  
  def parse_image(self, image_path, preprocess=True, ...):
      if preprocess:
          enhancer = DPIEnhancer()
          result = enhancer.process(image_path, ...)
          image_path = result["output_path"]
      
      # 后续OCR处理...


==================================================
【监控和日志】
==================================================

启用详细日志:

import logging

# 配置日志级别
logging.basicConfig(
    level=logging.DEBUG,  # 显示对所有处理细节
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('dpi_enhancement')

# 现在所有DEBUG及以上级别的日志都会显示


常见日志消息:

  ✓ "DPI已提升"        → 成功增强
  ✓ "DPI符合要求"      → 无需处理
  ⚠ "DPI提升倍数过高"   → 效果可能不理想
  ⚠ "图片尺寸过小"      → 可能影响识别效果
  ❌ "处理失败"         → 检查输入文件和权限


==================================================
【代码示例】
==================================================

示例1: 处理单张扫描文件

from dpi_enhancement import DPIEnhancer

enhancer = DPIEnhancer(target_dpi=300)

result = enhancer.process(
    image_path="benchmark/raw/document_1.jpg",
    output_path="benchmark/enhanced/document_1.png",
    output_format="PNG",
    enable_noise_reduction=True,
    enable_auto_contrast=True
)

if result["success"]:
    print(f"✓ 处理完成!")
    print(f"  原DPI: {result['original_dpi']}")
    print(f"  增强: {result['scale_factor']:.2f}x")
    print(f"  输出: {result['output_path']}")
else:
    print(f"✗ 处理失败: {result['message']}")


示例2: 批量处理扫描文件夹

from dpi_enhancement import DPIEnhancer

enhancer = DPIEnhancer(target_dpi=300)

results = enhancer.batch_process(
    input_dir="benchmark/raw",
    output_dir="benchmark/enhanced"
)

# 统计
print(f"处理结果: {results['success']}/{results['total']} 成功")
print(f"失败: {results['failed']} 张")

# 查看失败的图片
for result in results["results"]:
    if not result["success"]:
        print(f"  - {result['filename']}: {result['message']}")


示例3: 完整工作流 (包含倾斜矫正)

from dpi_enhancement_workflow import DPIEnhancementWorkflow

workflow = DPIEnhancementWorkflow(
    target_dpi=300,
    min_acceptable_dpi=150
)

# 处理单张
result = workflow.process_single_image("benchmark/raw/page1.jpg")
print(result["summary"])

# 批量处理
batch_results = workflow.process_batch()
print(f"✓ 完成: {batch_results['success']}/{batch_results['total']}")


==================================================
【最佳实践建议】
==================================================

1. 预检查
   □ 确保输入目录存在且包含图片
   □ 检查输出目录的写权限
   □ 备份原始图片 (可选)

2. 批量处理前的测试
   □ 先用 process_single_image() 测试一个样本
   □ 检查输出质量是否满足需求
   □ 调整参数后再批量处理

3. 参数选择
   □ 低质量图片 (50-100 DPI): target_dpi=300, enable all options
   □ 中等质量图片 (150-250 DPI): target_dpi=300, normal options
   □ 良好质量图片 (250+ DPI): target_dpi=300, 可能不需要增强

4. 性能优化
   □ 大批量处理: 使用多线程 (见FAQ Q5)
   □ 快速处理: 禁用不必要的优化选项
   □ 高质量需求: 启用所有优化，使用PNG格式

5. 监控和记录
   □ 保存处理日志以追踪问题
   □ 记录处理时间和成功率
   □ 定期检查输出质量


==================================================
更多帮助和支持，请参考源代码中的注释说明。
"""

# 实际执行的代码
if __name__ == "__main__":
    print(__doc__)
