# 数据质量检查 (Quality Control)

## 概述

本模块用于评估 OCR 识别结果的准确率，通过**编辑距离 (Levenshtein Distance)**、**字错率 (CER)**、**词错率 (WER)**等核心指标来量化 OCR 性能。

---

## 核心概念

### 1. 编辑距离 (Levenshtein Distance)

定义：从一个字符串转换为另一个字符串所需的**最少操作次数**。

允许的操作：
- **插入**：添加一个字符
- **删除**：移除一个字符
- **替换**：将一个字符替换为另一个字符

#### 示例

```
Ground Truth: "你好世界"
OCR Output:   "你好市界"  (世 -> 市)
编辑距离 = 1
```

```
Ground Truth: "Hello"
OCR Output:   "Helo"   (删除一个 l)
编辑距离 = 1
```

---

### 2. 字错率 (Character Error Rate, CER)

**公式**：
$$\text{CER} = \frac{S + D + I}{N}$$

其中：
- $S$：替换 (Substitution) 错误数
- $D$：删除 (Deletion) 错误数
- $I$：插入 (Insertion) 错误数
- $N$：Ground Truth 中的总字符数

#### 范围
- **0** = 完全正确
- **1** = 完全错误
- \> **1** = 插入过多（罕见）

#### 示例

```
Ground Truth: "1+1=2"     (5 个字符)
OCR Output:   "1+1=3"     (1 个替换错误)
CER = 1/5 = 0.2 = 20%
```

---

### 3. 词错率 (Word Error Rate, WER)

**公式**：
$$\text{WER} = \frac{S + D + I}{N_{\text{words}}}$$

其中 $N_{\text{words}}$ 是 Ground Truth 中的总词数。

#### 特点
- 比 CER 更关注词级别的错误
- 适合评估中文文本时可结合分词工具
- 对空格、标点符号的处理有影响

---

### 4. 准确率 (Accuracy)

**公式**：
$$\text{Accuracy} = 1 - \text{CER} = \frac{\text{匹配字符数}}{N}$$

#### 直观理解
- **95% 准确率** = 字错率 5%，平均每 20 个字有 1 个错误

---

## 使用指南

### 快速开始

#### 方法 1：计算单个样本

```python
from accuracy_test import calculate_metrics

ocr_output = "第1题：1+1=2"
ground_truth = "第1题：1+1=2"

metrics = calculate_metrics(ocr_output, ground_truth)
print(f"字错率 (CER)：{metrics['cer']:.4f}")
print(f"准确率：{metrics['accuracy']:.4%}")
print(f"编辑距离：{metrics['edit_distance']}")
```

#### 方法 2：批量评估 Benchmark

```python
from accuracy_test import BenchmarkEvaluator

evaluator = BenchmarkEvaluator('benchmark/')

# 假设已有 OCR 输出结果
ocr_results = {
    'img_01': 'OCR 识别出的文本',
    'img_02': 'OCR 识别出的文本',
    ...
}

results = evaluator.evaluate(ocr_results)
report = evaluator.generate_report(results)
print(report)
```

### 脚本说明

#### 主要类

| 类名 | 功能 |
|------|-----|
| `LevenshteinDistance` | 计算编辑距离 |
| `OCRQualityMetrics` | 计算 CER、WER、准确率 |
| `BenchmarkEvaluator` | 批量评估 benchmark 数据集 |

#### 主要方法

| 方法 | 功能 | 返回值 |
|------|-----|--------|
| `LevenshteinDistance.calculate(s1, s2)` | 编辑距离 | int |
| `OCRQualityMetrics.character_error_rate(pred, gt)` | 字错率 | float (0-1) |
| `OCRQualityMetrics.word_error_rate(pred, gt)` | 词错率 | float (0-1) |
| `OCRQualityMetrics.accuracy(pred, gt)` | 准确率 | float (0-1) |
| `BenchmarkEvaluator.evaluate(ocr_results)` | 批量评估 | Dict |
| `BenchmarkEvaluator.generate_report(results)` | 生成报告 | str |

---

## 评估报告示例

```
============================================================
OCR 质量评估报告 (Benchmark Results)
============================================================

【汇总指标】
样本总数：20
平均字错率 (CER)：0.0532
平均词错率 (WER)：0.0812
平均准确率 (Accuracy)：94.68%

【各样本详细指标】
------------------------------------------------------------
文件：img_01
  字错率 (CER)：0.0200
  词错率 (WER)：0.0500
  准确率 (Accuracy)：98.00%
  编辑距离：5
  GT 长度：250 | 预测长度：248

文件：img_02
  字错率 (CER)：0.0800
  词错率 (WER)：0.1200
  准确率 (Accuracy)：92.00%
  编辑距离：24
  GT 长度：300 | 预测长度：295

...

============================================================
```

---

## 性能基准参考

| 应用场景 | 推荐准确率 | 备注 |
|---------|---------|-----|
| 印刷卷子（高质量） | > 95% | CER < 5% |
| 印刷卷子（一般质量） | 90-95% | CER 5-10% |
| 手写卷子（规范书写） | 85-90% | CER 10-15% |
| 手写卷子（草体） | 70-85% | CER 15-30% |
| 破损 / 变形试卷 | < 70% | 需人工审核 |

---

## 常见问题

### Q1：CER 的理想范围是多少？

**A**：取决于应用场景：
- **高精度应用**：CER < 2%（即准确率 > 98%）
- **一般应用**：CER 3-8%（准确率 92-97%）
- **容错应用**：CER 10-15%（准确率 85-90%）

### Q2：为什么 CER 有时 > 100%？

**A**：如果 OCR 输出远长于 Ground Truth（插入过多），CER 可能 > 1.0，这表示模型输出的字符数远超预期。

### Q3：如何处理特殊符号（公式、表格等）？

**A**：
- 遵循 `annotation_standards.md` 中的符号标准化规范
- 确保 Ground Truth 和 OCR 输出都采用相同的编码
- 可自定义字符权重（某些符号错误权重更高）

### Q4：中文和英文混合文本如何评估？

**A**：
- CER 和 WER 都能处理混合文本
- 建议同时查看两个指标，做**加权评估**

---

## 集成到项目

### 与 Backend 集成

```python
# 在 backend/error_correction_agent/tools/question_tools.py 中
from data_processing.quality_control.accuracy_test import calculate_metrics

def quality_check(ocr_output, ground_truth):
    """质量检查工具"""
    metrics = calculate_metrics(ocr_output, ground_truth)
    return metrics
```

### 与 Frontend 集成

前端可调用后端 API 获取质量指标：

```javascript
// frontend/src/api.js
async function evaluateOCRQuality(ocrOutput, groundTruth) {
  const response = await fetch('/api/quality-check', {
    method: 'POST',
    body: JSON.stringify({
      ocr_output: ocrOutput,
      ground_truth: groundTruth,
    }),
  });
  return response.json();
}
```

---

## 参考资源

- [Levenshtein Distance - Wikipedia](https://en.wikipedia.org/wiki/Levenshtein_distance)
- [PaddleOCR 性能评估](https://paddleocr.readthedocs.io/zh_CN/latest/)
- [精确率、召回率、F1-Score 等指标][https://scikit-learn.org/stable/modules/model_evaluation.html]
