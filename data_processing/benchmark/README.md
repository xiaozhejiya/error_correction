# 测试数据集 (Benchmark)

## 概述

本目录存放 OCR 的标准测试数据集，用于评估模型的性能和准确率。

---

## 目录结构

```
benchmark/
├── raw/                 # 原始扫描图片（10-20 张标准试卷）
│   ├── img_01.jpg
│   ├── img_02.jpg
│   └── ...
│
└── ground_truth/        # 人工标注的准确文本（Ground Truth）
    ├── img_01_gt.txt
    ├── img_02_gt.txt
    └── ...
```

---

## 1. `raw/` 目录

### 用途
存放原始扫描试卷图片，作为 OCR 模型的输入。

### 要求

- **数量**：10-20 张（足以覆盖主要题型和背景）
- **分辨率**：>= 300 DPI（遵循扫描规范）
- **格式**：JPG 或 PNG
- **多样性**：
  - 不同题型：选择题、填空题、解答题
  - 不同字体：印刷体、手写体混合
  - 不同背景：白纸、草稿纸等
  - 不同新旧程度：新试卷、泛黄试卷
  
### 命名规范

```
img_01.jpg    # 按序号命名
img_02.jpg
img_03.jpg
...
img_20.jpg
```

---

## 2. `ground_truth/` 目录

### 用途
存放每张扫描图对应的**人工标注准确文本**，用于与 OCR 输出进行比对，计算准确率。

### 格式

每张图 `img_XX.jpg` 对应一个 `img_XX_gt.txt` 文件，内容为完整的文本，按原始版面顺序排列。

### 文件示例

**img_01_gt.txt**
```
第一部分：选择题（共 20 分）

1. 下列哪个选项正确？
A. 选项 A
B. 选项 B
C. 选项 C
D. 选项 D

2. 计算 1+1=？
A. 1
B. 2
C. 3
D. 4

...

第二部分：填空题（共 30 分）

11. 计算 2×3=____

12. 求解方程：x+5=10，x=____

...

第三部分：解答题（共 50 分）

21. 求解下列二次方程：
x^2 - 5x + 6 = 0

解：
（学生答案区域）
```

### 标注原则

- **保留版面结构**：题号、题目、选项按原顺序排列
- **特殊符号统一**：遵循 `annotation_standards.md` 中的规范
  - 分数：用 `/` 表示（如 `1/2`）
  - 上下标：用 `^`、`_` 表示（如 `x^2`）
  - 公式：保留原文本或用占位符
- **空白区域**：跳过完全空白部分，不需标注
- **破损字符**：用 `[UNK]` 表示

---

## 3. 数据集质量要求

### 3.1 完整性

- 每张图片 (raw/) 都有对应的 Ground Truth (ground_truth/)
- 图片能完整呈现试卷内容（无缺失、无超界）

### 3.2 多样性

| 维度 | 覆盖范围 | 示例 |
|-----|--------|------|
| **题型** | 选择、填空、解答 | 各覆盖 3-5 张 |
| **字体** | 印刷、手写 | 各覆盖 50% |
| **背景** | 白纸、草稿纸、泛黄 | 各覆盖 30-40% |
| **倾斜** | 正常、轻微倾斜 | 倾斜 <= ±5° |

### 3.3 准确性

- Ground Truth 文本准确无误（逐字逐句检查）
- 符号、公式遵循统一规范
- 充分表示 raw 中的全部内容

---

## 4. 如何使用该数据集

### 4.1 评估 OCR 模型

```python
from evaluate import calculate_accuracy

# 加载 OCR 输出
ocr_output = model.predict('raw/img_01.jpg')

# 加载 Ground Truth
with open('ground_truth/img_01_gt.txt', 'r') as f:
    ground_truth = f.read()

# 计算准确率
accuracy = calculate_accuracy(ocr_output, ground_truth)
print(f"准确率：{accuracy:.2%}")
```

### 4.2 性能基准

基准测试应报告以下指标：

- **字错率 (CER)**：Character Error Rate
- **词错率 (WER)**：Word Error Rate  
- **编辑距离**：Levenshtein Distance
- **整体准确率**：Overall Accuracy

详见 `quality_control/` 目录。

---

## 5. 维护与扩展

### 5.1 定期更新

- 每季度增加 5-10 张新的试卷样本
- 保持数据集的多样性和时效性

### 5.2 版本管理

建议创建版本记录：

```
benchmark_v1.0 (基础集，10 张)
benchmark_v1.1 (扩展集，15 张)
benchmark_v2.0 (覆盖更多题型，20 张)
```

---

## 参考文档

- [试卷扫描规范](../standards/scan_standards.md)
- [数据标注规范](../standards/annotation_standards.md)
- [质量检查脚本](../quality_control/accuracy_test.py)
