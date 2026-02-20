# PaddleOCR 识别效果对比指南

## 概述

这个脚本用于**对比预处理前后的 PaddleOCR 识别效果**，直观展示本地图片预处理的必要性。

## 文件说明

- **`ocr_comparison.py`** - 主要对比脚本
  - 支持批量对比和单张图片对比
  - 自动调用 DPI 增强、倾斜矫正等预处理流程
  - 生成详细的对比报告（JSON 格式）
  - 计算识别准确率提升幅度

## 使用方法

### 前置条件

1. **配置 PaddleOCR API**
   在项目根目录的 `.env` 文件中确保已配置：
   ```env
   PADDLEOCR_API_URL=https://your-paddleocr-api-url.com/layout-parsing
   PADDLEOCR_API_TOKEN=your_actual_token
   ```

2. **安装依赖**
   ```bash
   pip install opencv-python-headless deskew pillow scikit-image
   ```

### 方法 1: 批量对比所有图片

```bash
cd data_processing
python ocr_comparison.py --batch
```

**流程**：
1. 扫描 `benchmark/raw` 目录中的所有 PNG/JPG 图片
2. 对每张图片分别进行：
   - **原始处理**：仅转换为 PNG（模拟现在的 utils.py）
   - **完整预处理**：DPI 增强 + 倾斜矫正 + 质量优化
3. 分别调用真实 PaddleOCR API 识别两个版本
4. 提取并对比识别结果
5. 生成详细对比报告

### 方法 2: 对比单张图片

```bash
python ocr_comparison.py --single path/to/image.jpg
```

## 目录结构

```
benchmark/
├── raw/                        # 【输入】原始测试图片
├── comparison/                 # 【输出】对比结果
│   ├── raw_prepared/          # 原始处理后的图片
│   ├── enhanced_prepared/     # 增强处理后的图片
│   └── comparison_report.json # 详细对比报告
└── comparison_report.json     # 汇总报告（自动生成）
```

## 对比报告说明

## 对比报告说明

### 报告格式 (JSON)

```json
{
  "filename": "test_page.png",
  "raw": {
    "dpi": 72,
    "size": "1024x1536",
    "ocr_result": ["识别的文本行1", "识别的文本行2", ...],
    "ocr_accuracy": {
      "total_lines": 7,
      "character_count": 145,
      "quality_score": 65.3,   // 质量分（0-100）
      "empty_rate": 5.2,       // 空行比例
      "completeness": "部分缺失"
    }
  },
  "enhanced": {
    "dpi": 300,
    "size": "4096x6144",
    "metadata": {
      "dpi_enhancement": {
        "original_dpi": 72,
        "target_dpi": 300,
        "scale_factor": 4.17
      },
      "skew_correction": {
        "detected_angle": 2.3,
        "corrected": true
      }
    },
    "ocr_result": ["识别的文本行1", "识别的文本行2", ...],
    "ocr_accuracy": {
      "total_lines": 9,
      "character_count": 175,
      "quality_score": 96.8,   // 质量分提升
      "empty_rate": 0.0,
      "completeness": "较完整"
    }
  },
  "comparison": {
    "raw_quality_score": 65.3,
    "enhanced_quality_score": 96.8,
    "improvement": 31.5,        // 质量分上升值
    "improvement_ratio": 48.2,  // 相对提升百分比
    "summary": "增强后质量分提升 31.5% (相对提升: 48.2%)"
  }
}
```

## 关键指标解读

| 指标 | 含义 | 期望值 |
|------|------|--------|
| `total_lines` | 识别的文本行数 | 越多越好（完整识别） |
| `character_count` | 识别的字符总数 | 越多越好（识别更完整） |
| `quality_score` | 文本质量分 | 0-100，越高越好 |
| `empty_rate` | 空行比例（%） | 越低越好（识别完整） |
| `improvement` | 质量分绝对提升值 | 20-30 |
| `improvement_ratio` | 相对提升百分比 | 30-50% |

## 预期结果

### 针对低 DPI 图片 (< 150 DPI)
```
原始识别:     58 行，892 字符，质量分: 58.2
增强后识别:   72 行，1145 字符，质量分: 94.6
质量分提升:   36.4 ⬆️ (相对提升: 62.5%)
```

### 针对倾斜图片
```
原始识别:     45 行，680 字符，质量分: 62.5  (倾斜导致文字行被切断)
增强后识别:   52 行，751 字符，质量分: 98.1  (倾斜已矫正)
质量分提升:   35.6 ⬆️ (相对提升: 56.8%)
```

### 针对低对比度图片
```
原始识别:     42 行，635 字符，质量分: 55.3  (灰蒙蒙的纸质照片)
增强后识别:   60 行，912 字符，质量分: 91.2  (对比度优化)
质量分提升:   35.9 ⬆️ (相对提升: 64.9%)
```

## 实际部署说明

**当前版本**：使用真实的 PaddleOCR API 进行对比

**配置要求**：
1. 在 `.env` 文件中正确配置以下环境变量：
   ```
   PADDLEOCR_API_URL=https://your-paddleocr-api-url.com/layout-parsing
   PADDLEOCR_API_TOKEN=your_actual_token
   ```

2. 确保后端代码路径可访问（脚本会自动加载 `src/paddleocr_client.py`）

**工作流程**：
1. 加载图片，检测 DPI
2. 创建两个版本：
   - **原始版本**：仅做最小化处理（模拟现在的 utils.py）
   - **增强版本**：完整预处理（DPI提升、倾斜矫正、质量优化）
3. 分别调用真实 PaddleOCR API 识别两个版本
4. 提取识别结果中的文本行
5. 计算质量分并对比结果

## 输出日志示例

```
==============================================================================
开始对比: test_page.png
==============================================================================

【处理原始图片】
✓ 原始图片已准备: benchmark/comparison/raw_prepared/test_page_raw.png
  调用 PaddleOCR 识别原始图片...
  ✓ 识别完成，共 58 行
  ✓ 原始图片识别完成 (质量分: 58.2/100)

【处理增强图片】
  → DPI增强中...
  ✓ DPI增强完成 (72 → 300 DPI)
  → 倾斜检测中...
  → 倾斜矫正中 (角度: 2.34°)...
  ✓ 倾斜矫正完成
✓ 增强图片已准备: benchmark/comparison/enhanced_prepared/test_page_enhanced.png
  调用 PaddleOCR 识别增强后的图片...
  ✓ 识别完成，共 72 行
  ✓ 增强图片识别完成 (质量分: 94.6/100)

【对比分析】
  原始质量分:   58.2/100 (58 行，892 字符)
  增强后质量分: 94.6/100 (72 行，1145 字符)
  质量分提升:   36.4% ⬆️
  DPI 提升:      72 → 300 DPI (4.17x)
  倾斜矫正:      2.34° ✓

##############################################################################
# 对比完成统计
##############################################################################
总数: 1 张
成功: 1 张 ✓
平均质量分提升: 36.4%

✓ 对比报告已保存: benchmark/comparison_report.json
```

## 故障排查

### 问题 1: 导入错误 (ImportError)
```
ModuleNotFoundError: No module named 'dpi_enhancement'
```

**解决方案**：确保在 `data_processing` 目录运行脚本
```bash
cd data_processing
python ocr_comparison.py --batch
```

### 问题 2: 找不到输入图片
```
目录 benchmark/raw 中没有找到图片文件
```

**解决方案**：放置测试图片到 `benchmark/raw` 目录
```bash
cp your_test_images/*.png data_processing/benchmark/raw/
```

### 问题 3: DPI 增强失败

**解决方案**：检查 PIL/Pillow 和相关依赖是否安装
```bash
pip install pillow opencv-python-headless deskew numpy scikit-image
```

## 推荐测试场景

为了最佳演示效果，建议准备以下类型的图片：

1. **低 DPI 扫描件** (72-96 DPI)
   - 特点：模糊不清
   - 预期改善：最显著（40-50%）

2. **手机照片**
   - 特点：低DPI + 可能倾斜
   - 预期改善：很显著（35-45%）

3. **纸质教材照片**
   - 特点：对比度低、灰蒙蒙
   - 预期改善：显著（30-40%）

4. **倾斜的试卷**
   - 特点：角度明显歪斜
   - 预期改善：显著（30-35%）

5. **已经很清晰的高 DPI 图片** (300+ DPI)
   - 预期改善：较小（5-10%）作为对照

## 下一步

### 集成到生产环境

如果对比结果满意，可以将预处理逻辑集成到 `backend/src/utils.py` 的 `prepare_input()` 函数中：

```python
def prepare_input(file_path: str, enable_local_preprocessing: bool = True):
    # ... 现有代码 ...
    
    # 新增质量检测和预处理
    if enable_local_preprocessing:
        from data_processing.dpi_enhancement_workflow import DPIEnhancementWorkflow
        workflow = DPIEnhancementWorkflow()
        # 对低质图片进行预处理
```

### 性能评估

使用对比报告的数据写出性能优化总结：
- 识别准确率提升幅度
- API 成本减少比例（减少重试）
- 处理时间改善

这将直观展示给项目负责人。
