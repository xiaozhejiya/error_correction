# 用户使用手册

本手册面向错题本生成系统的终端用户，介绍系统功能、操作流程和常见问题的解决方法。

---

## 目录

- [系统简介](#系统简介)
- [环境准备](#环境准备)
- [启动系统](#启动系统)
- [使用 Web 界面](#使用-web-界面)
  - [步骤 1: 上传文件](#步骤-1-上传文件)
  - [步骤 2: OCR 解析](#步骤-2-ocr-解析)
  - [步骤 3: AI 分割题目](#步骤-3-ai-分割题目)
  - [步骤 4: 预览与导出](#步骤-4-预览与导出)
- [输出文件说明](#输出文件说明)
- [常见问题（FAQ）](#常见问题faq)
- [故障排查](#故障排查)

---

## 系统简介

错题本生成系统是一个基于 AI 的文档处理工具，能够：

- 接收 PDF 或图片格式的试卷/习题
- 通过 PaddleOCR 进行文档结构化解析（识别文字、公式、图片）
- 利用 DeepSeek AI Agent 智能识别和分割题目
- 支持用户选择题目并导出为 Markdown 格式的错题本

**支持的题型**: 选择题、填空题、解答题、判断题

**支持的内容**: 纯文字、数学公式（行内/行间）、图片引用

---

## 环境准备

### 系统要求

| 项目 | 要求 |
|------|------|
| Python | 3.8 或更高版本 |
| 操作系统 | Windows / macOS / Linux |
| 浏览器 | Chrome、Firefox、Edge 等现代浏览器 |
| 网络 | 需要访问 PaddleOCR 和 DeepSeek API |

### 安装步骤

1. **安装系统依赖**

   本系统需要 `poppler` 用于 PDF 转图片：

   - **Windows**: 下载 [poppler for Windows](https://github.com/ossamamehmood/Poppler-Windows/releases)，解压后将 `bin` 目录添加到系统 PATH
   - **macOS**: `brew install poppler`
   - **Linux**: `sudo apt-get install poppler-utils`

2. **安装 Python 依赖**

   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**

   复制 `.env.example` 为 `.env`，并填写以下必需配置：

   ```bash
   cp .env.example .env
   ```

   编辑 `.env` 文件：

   ```bash
   # 必需: DeepSeek API
   DEEPSEEK_API_KEY=your_key
   DEEPSEEK_BASE_URL=https://api.deepseek.com

   # 必需: PaddleOCR API
   PADDLEOCR_API_URL=https://your-paddleocr-api-url
   PADDLEOCR_API_TOKEN=your_token
   ```

---

## 启动系统

在项目根目录执行：

```bash
python web_app.py
```

启动成功后，终端会显示：

```
============================================================
错题本生成系统 - Web应用
============================================================
访问地址: http://localhost:5001
============================================================
```

打开浏览器访问 **http://localhost:5001** 即可使用。

---

## 使用 Web 界面

Web 界面采用 4 步操作流程，页面顶部有步骤指示器显示当前进度。

### 系统状态检查

页面加载后，顶部会显示系统配置状态：

- **PaddleOCR** — OCR 解析服务是否已配置
- **DeepSeek** — AI 模型服务是否已配置
- **LangSmith** — 调试追踪是否已启用（可选）

如果必需服务显示为未配置，请检查 `.env` 文件中的 API 密钥。

### 步骤 1: 上传文件

**操作方式**（二选一）：

- **拖拽上传**: 将文件直接拖拽到上传区域
- **点击选择**: 点击上传区域，在弹出的文件选择框中选择文件

**支持的文件格式**:

| 格式 | 扩展名 |
|------|--------|
| PDF 文档 | `.pdf` |
| 图片 | `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`, `.webp` |

**文件大小限制**: 最大 50MB

**使用建议**:
- PDF 文件会按页自动拆分为图片（DPI 300）
- 图片建议分辨率不低于 300 DPI，清晰的扫描件效果最佳
- 如果试卷有多页，建议使用 PDF 格式一次上传

### 步骤 2: OCR 解析

文件上传后，系统会**自动**执行以下处理：

1. 将 PDF 按页转换为 PNG 图片（如果上传的是 PDF）
2. 将图片标准化为 PNG 格式
3. 调用 PaddleOCR API 对每张图片进行结构化解析

处理完成后，页面会显示：
- 转换后的图片数量
- OCR 解析完成状态

此步骤无需用户操作，等待处理完成即可。

### 步骤 3: AI 分割题目

OCR 解析完成后，点击页面上的 **"开始分割题目"** 按钮。

系统会调用 DeepSeek AI Agent 分析 OCR 结果，自动执行：

- 识别题号和题目边界
- 判断题目类型（选择题、填空题、解答题、判断题）
- 提取题目内容（文字、公式、图片引用）
- 分离选择题的选项

处理完成后，页面会展示所有识别到的题目卡片。

**每张题目卡片包含**:
- 题号（如"题目 1"）
- 题型标签
- 题目内容（文字和公式）
- 选项列表（选择题）
- 选择复选框

### 步骤 4: 预览与导出

1. **预览题目**: 查看 AI 分割出的所有题目，检查内容是否正确
2. **选择题目**: 勾选需要导出到错题本中的题目
   - 点击"全选"可一次选中所有题目
   - 点击"取消全选"可清除所有选择
3. **导出错题本**: 点击 **"导出错题本"** 按钮
4. **下载文件**: 导出完成后，点击下载链接获取 Markdown 文件

---

## 输出文件说明

### 错题本文件 (`results/wrongbook.md`)

导出的错题本为 Markdown 格式，包含以下结构：

```markdown
# 错题本

> 共收录 N 道题目

---

## 1. 题目 X (选择题)

题目内容...

A. 选项一
B. 选项二
C. 选项三
D. 选项四

### 我的答案
_（请在此处填写你的答案）_

### 正确答案
_（请在此处填写正确答案）_

### 解析
_（请在此处填写解题思路和知识点）_

---
```

每道题目包含三个待填写区域，方便你记录学习笔记：
- **我的答案** — 记录自己的作答
- **正确答案** — 记录标准答案
- **解析** — 记录解题思路和涉及的知识点

### 题目数据文件 (`results/questions.json`)

JSON 格式的题目结构化数据，每道题包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `question_id` | string | 题号 |
| `question_type` | string | 题型（选择题/填空题/解答题/判断题） |
| `content_blocks` | array | 题目内容块列表（文字、公式、图片） |
| `options` | array | 选项列表（仅选择题） |
| `has_formula` | boolean | 是否包含公式 |
| `has_image` | boolean | 是否包含图片 |
| `image_refs` | array | 图片引用路径列表 |

### 问题日志 (`results/split_issues.jsonl`)

Agent 在处理过程中遇到的问题记录，每行一条 JSON，常见问题类型：

- `unclear_boundary` — 题目边界不清晰
- `missing_question_number` — 缺少题号
- `complex_structure` — 复杂结构难以解析

---

## 常见问题（FAQ）

### Q1: 上传文件后长时间无响应？

**可能原因**: PaddleOCR API 响应较慢或网络连接问题。

**解决方法**:
1. 检查网络连接是否正常
2. 确认 `.env` 中的 `PADDLEOCR_API_URL` 和 `PADDLEOCR_API_TOKEN` 配置正确
3. 查看终端日志是否有错误输出
4. 尝试上传较小的文件测试

### Q2: AI 分割结果不准确？

**可能原因**: OCR 识别质量不佳或 Agent 提示词需要优化。

**解决方法**:
1. 确保上传的文件清晰度足够（建议 300 DPI 以上）
2. 检查 `output/struct/` 目录下的 OCR 结果是否正确识别了文字
3. 如果是特定题型分割不佳，可联系开发人员调整 Agent 提示词
4. 查看 `results/split_issues.jsonl` 了解 Agent 记录的问题

### Q3: 导出的错题本公式显示异常？

**可能原因**: Markdown 编辑器不支持 LaTeX 公式渲染。

**解决方法**:
- 使用支持 LaTeX 的 Markdown 编辑器查看（如 Typora、VS Code + Markdown Preview Enhanced 插件）
- 错题本中行间公式使用 `$$...$$` 格式，行内公式使用 `$...$` 格式

### Q4: 导出的错题本图片无法显示？

**可能原因**: 图片路径使用的是相对路径。

**解决方法**:
- 确保 `output/struct/` 和 `output/assets/` 目录中的图片文件存在
- 在 `results/` 目录下查看错题本时，图片路径是相对于该目录的

### Q5: 如何只处理试卷中的某几页？

目前系统会处理整个文件的所有页面。如果只需要部分页面：
- 对于 PDF，可先用 PDF 工具提取需要的页面再上传
- 对于图片，直接上传需要处理的那张图片
- 在步骤 4 中，通过勾选机制只导出需要的题目

---

## 故障排查

### 检查系统日志

启动 Web 应用后，终端会输出所有请求日志：

```
127.0.0.1 - - [27/Jan/2026 10:30:15] "POST /api/upload HTTP/1.1" 200 -
127.0.0.1 - - [27/Jan/2026 10:30:45] "POST /api/split HTTP/1.1" 200 -
```

如果请求返回 500 错误，终端会打印详细的异常堆栈信息。

### 检查中间输出

| 检查内容 | 文件位置 | 说明 |
|----------|----------|------|
| PDF 转换结果 | `output/pages/` | 查看 PNG 图片是否正确生成 |
| OCR 解析结果 | `output/struct/` | 查看 JSON 文件中的文字识别是否准确 |
| 题目分割结果 | `results/questions.json` | 查看 Agent 分割的题目数据 |
| 处理问题日志 | `results/split_issues.jsonl` | 查看 Agent 记录的异常情况 |

### 启用 LangSmith 追踪

如果需要深入调试 AI Agent 的行为，可以启用 LangSmith：

1. 在 `.env` 中配置：
   ```bash
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=your_langsmith_api_key
   LANGSMITH_PROJECT=error-correction
   ```

2. 重启 Web 应用
3. 访问 [LangSmith 控制台](https://smith.langchain.com) 查看 Agent 的完整执行轨迹，包括：
   - LLM 的输入和输出
   - 工具调用记录
   - 每一步的处理耗时

### 浏览器端调试

按 `F12` 打开浏览器开发者工具：

- **Console 标签**: 查看 JavaScript 错误
- **Network 标签**: 查看 API 请求和响应详情，确认请求是否成功

---

*文档版本: v1.0.0*
