# Benchmark 数据采集模块

复用本系统的 **PaddleOCR + Agent 分割**流水线，批量处理 `dataset/` 下的考试 PDF（每份取前 2 页），提取所有完整题目按科目分目录保存，用于评测解题智能体准确率。

## 快速开始

```bash
cd backend

# 1. 查看有哪些 PDF（不请求 API）
python -m benchmark.collect --dry-run

# 2. 采集全部科目（4 线程并行）
python -m benchmark.collect

# 3. 只采集某个科目
python -m benchmark.collect --subject 高中数学

# 4. 用文心模型分割
python -m benchmark.collect --provider ernie

# 5. 指定并行数
python -m benchmark.collect --workers 8
```

## 工作流程

```
dataset/{科目}/pdf文档/*.pdf
    │
    ├── 取前 2 页，转 200dpi PNG
    │
    ├── PaddleOCR API 解析（布局+公式+图片识别）
    │
    ├── Agent 智能分割（识别题号、题型、选项、知识点）
    │
    ├── 并行处理多个 PDF（ThreadPoolExecutor）
    │
    ├── 按科目分目录保存 → benchmark/data/target/{科目}/{试卷名}.json
    │
    └── 标注人员填写 answer 字段
            │
            └── python -m benchmark.evaluate  (AI 解答 + 对比正确率)
```

## 输出文件

```
benchmark/data/target/
├── 初中数学/
│   ├── 2023年某市中考数学真题.json
│   └── ...
├── 高中数学/
│   ├── 2023年北京高考数学真题.json
│   └── ...
├── 化学/
│   └── ...
└── ...
```

每个 JSON 文件格式：

```json
[
  {
    "question_id": "2023年北京高考数学真题_1",
    "question_type": "选择题",
    "answer": "",
    "source": { "pdf": "2023年北京高考数学真题", "local_id": "1" },
    "question": {
      "question_id": "2023年北京高考数学真题_1",
      "question_type": "选择题",
      "content_blocks": [{"block_type": "text", "content": "已知集合..."}],
      "options": ["A. ...", "B. ..."],
      "has_formula": true,
      "knowledge_tags": ["集合", "交集"]
    }
  }
]
```

## 标注答案

采集完成后 `answer` 字段为空，标注人员按题型填写：

| 题型 | answer 格式 | 示例 |
|------|-------------|------|
| 选择题 | 选项字母 | `"B"` |
| 判断题 | 正确/错误 | `"正确"` |
| 填空题 | 精确答案 | `"$\\frac{1}{2}$"` |
| 解答题 | 完整解答过程 | `"由题意可知..."` |

标注完成后运行评测：

```bash
python -m benchmark.evaluate                      # 评测全部模型
python -m benchmark.evaluate --provider deepseek   # 只评测 deepseek
python -m benchmark.evaluate --subject 高中数学    # 只评测某科目
```

## 依赖

复用系统已有组件，无额外依赖：

- `src/paddleocr_client.py` — OCR 解析
- `error_correction_agent/tools/split_batch` — Agent 分割
- `pdf2image` + `poppler` — PDF 转图
- 环境变量：`PADDLEOCR_API_URL`、`PADDLEOCR_API_TOKEN`、`DEEPSEEK_API_KEY`
