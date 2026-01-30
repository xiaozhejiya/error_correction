# 错题本生成系统

基于 PaddleOCR 和 LangChain Agent 的智能错题本生成系统。支持上传 PDF 或图片格式的试卷/习题，通过 OCR 结构化解析和 AI 智能分割，自动提取题目并导出为 Markdown 格式的错题本。

## 项目结构

```
error_correction/
├── error_correction_agent/     # Agent 相关代码
│   ├── prompts.py              # Agent 系统提示词
│   ├── agent.py                # Agent 创建和配置
│   └── tools/                  # Agent 工具集
│       ├── __init__.py
│       ├── question_tools.py   # 题目处理工具
│       └── file_tools.py       # 文件操作工具
│
├── src/                        # 核心功能模块
│   ├── paddleocr_client.py     # PaddleOCR API 客户端
│   ├── workflow.py             # LangGraph 工作流编排
│   └── utils.py                # 通用工具函数
│
├── templates/                  # HTML 模板
│   └── index.html              # Web 界面主页
│
├── static/                     # 静态资源
│   └── css/
│       └── style.css           # 样式表
│
├── uploads/                    # 上传文件临时存储
├── output/                     # 处理输出目录
│   ├── pages/                  # 标准化后的图片（PDF 转 PNG）
│   ├── struct/                 # PaddleOCR 解析结果（JSON）
│   └── assets/                 # 下载的图片资源
│
├── results/                    # 最终结果
│   ├── questions.json          # 分割后的题目
│   ├── preview.html            # 题目预览页面
│   ├── wrongbook.md            # 导出的错题本
│   └── split_issues.jsonl      # Agent 处理问题日志
│
├── web_app.py                  # Flask Web 应用入口
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量模板
├── langgraph.json              # LangGraph 配置
└── WEB_APP_GUIDE.md            # Web 应用使用指南
```

## 工作流程

系统采用 LangGraph 构建 4 步处理流水线，在关键节点设置中断以支持 Web 端分步交互：

```
START → prepare_input → ocr_parse → [中断] → split_questions → [中断] → export → END
```

| 步骤 | 节点 | 类型 | 说明 |
|------|------|------|------|
| 1 | `prepare_input` | 确定性 | 将 PDF/图片转换为标准化 PNG 图片 |
| 2 | `ocr_parse` | 确定性 | 调用 PaddleOCR API 解析文档结构 |
| 3 | `split_questions` | 智能（Agent） | 使用 DeepSeek Agent 智能分割题目 |
| 4 | `export` | 确定性 | 将选中题目导出为 Markdown 错题本 |

### 技术架构

- **步骤 1-2, 4**: 确定性逻辑，不需要 LLM
- **步骤 3**: 核心智能步骤，使用 LangChain Agent
  - 模型: DeepSeek Chat（temperature=0.1）
  - 工具: `save_questions`, `log_issue`, `download_image`, `read_ocr_result`
  - 提示词: 定义在 `error_correction_agent/prompts.py`

## 安装指南

### 环境要求

- **Python**: 3.11
- **操作系统**: Windows / macOS / Linux
- **外部服务**（需申请 API Key）:
  - [PaddleOCR API](https://www.paddlepaddle.org.cn/) — 文档 OCR 结构化解析
  - [DeepSeek API](https://platform.deepseek.com/) — LLM 智能题目分割

### 系统依赖

本项目使用 `pdf2image` 将 PDF 转换为图片，该库依赖 **poppler**：

**Windows**:
1. 下载 [poppler for Windows](https://github.com/ossamamehmood/Poppler-Windows/releases)
2. 解压到任意目录（如 `C:\poppler`）
3. 将 `C:\poppler\Library\bin` 添加到系统环境变量 `PATH`

**macOS**:
```bash
brew install poppler
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get install poppler-utils
```

### 步骤 1: 克隆项目

```bash
git clone <仓库地址>
cd error_correction
```

### 步骤 2: 创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 步骤 3: 安装 Python 依赖

```bash
pip install -r requirements.txt
```

`requirements.txt` 包含以下核心依赖：

| 分类 | 包名 | 说明 |
|------|------|------|
| Agent 框架 | `langchain`, `langgraph`, `deepagents` | LangChain 生态 + LangGraph 工作流 |
| 模型适配 | `langchain-deepseek`, `langchain-openai` | DeepSeek / OpenAI 模型接口 |
| 搜索工具 | `tavily`, `langchain-tavily` | Tavily 搜索 API |
| Web 框架 | `flask`, `werkzeug` | HTTP API 和 Web 界面 |
| 图像处理 | `pdf2image`, `Pillow`, `opencv-python` | PDF 转图片、图像操作 |
| 工具库 | `python-dotenv`, `requests`, `pydantic`, `rich` | 环境配置、HTTP、数据验证、CLI 输出 |

### 步骤 4: 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写必需的 API 密钥（详细说明见 `.env.example` 注释）：

| 变量 | 必需 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | 是 | DeepSeek API 密钥，用于 Agent 智能分割 |
| `DEEPSEEK_BASE_URL` | 是 | DeepSeek API 地址 |
| `PADDLEOCR_API_URL` | 是 | PaddleOCR API 地址 |
| `PADDLEOCR_API_TOKEN` | 是 | PaddleOCR API 密钥 |
| `LANGSMITH_API_KEY` | 否 | LangSmith 追踪密钥（调试用） |
| `TAVILY_API_KEY` | 否 | Tavily 搜索 API 密钥 |

### 步骤 5: 验证安装

```bash
# 检查 Python 依赖是否安装成功
python -c "import langchain; import langgraph; import flask; print('依赖安装成功')"

# 启动 Web 应用验证
python web_app.py
```

启动后访问 **http://localhost:5001**，页面顶部的系统状态指示器会显示各项服务是否配置正确。

## 快速开始

### 使用 Web 界面（推荐）

```bash
python web_app.py
```

打开浏览器访问 **http://localhost:5001**，按以下步骤操作：

1. **上传文件** — 拖拽或点击上传 PDF / 图片
2. **自动 OCR 解析** — 系统自动调用 PaddleOCR 进行文档结构化解析
3. **AI 分割题目** — 点击"开始分割题目"，DeepSeek Agent 智能识别并分割题目
4. **预览与导出** — 勾选需要的题目，点击"导出错题本"下载 Markdown 文件

**支持的文件格式**: PDF (`.pdf`)、图片 (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`, `.webp`)

**文件大小限制**: 50MB

详细操作说明请查看 [WEB_APP_GUIDE.md](WEB_APP_GUIDE.md)

## 开发指南

### 修改 Agent 提示词

编辑 `error_correction_agent/prompts.py` 中的 `SYSTEM_PROMPT`

### 添加新工具

1. 在 `error_correction_agent/tools/` 下创建新文件
2. 使用 `@tool` 装饰器定义工具函数
3. 在 `__init__.py` 中导出
4. 在 `agent.py` 中添加到工具列表

### 自定义工作流

修改 `src/workflow.py` 中的 `build_workflow()` 函数，可调整节点和边的定义。

## 输出说明

| 文件 | 路径 | 格式 | 说明 |
|------|------|------|------|
| 标准化图片 | `output/pages/` | PNG | 输入文件转换后的标准化图片 |
| OCR 解析结果 | `output/struct/` | JSON | PaddleOCR 返回的结构化数据 |
| 图片资源 | `output/assets/` | JPG/PNG | OCR 结果中提取的图片 |
| 题目数据 | `results/questions.json` | JSON | Agent 分割后的题目列表 |
| 错题本 | `results/wrongbook.md` | Markdown | 最终导出的错题本 |
| 问题日志 | `results/split_issues.jsonl` | JSONL | Agent 处理中记录的问题 |

## 常见问题

### Q: 安装依赖时 `pdf2image` 报错?

A: `pdf2image` 依赖系统级工具 `poppler`。请参照上方"系统依赖"部分安装对应系统的 poppler。

### Q: Agent 分割效果不好怎么办?

A: 可以调整以下方面:
1. 修改 `error_correction_agent/prompts.py` 中的系统提示词
2. 增加示例题目（few-shot）
3. 调整模型 temperature（在 `agent.py` 中，当前为 0.1）
4. 更换更强大的模型

### Q: 如何查看 Agent 执行日志?

A: 在 `.env` 中设置 `LANGSMITH_TRACING=true` 并填写 `LANGSMITH_API_KEY`，然后访问 [LangSmith 控制台](https://smith.langchain.com) 查看详细的执行轨迹。

### Q: 支持哪些文件格式?

A:
- PDF: `.pdf`
- 图片: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.webp`

## 相关文档

- [Web 应用使用指南](WEB_APP_GUIDE.md) — 详细的 Web 界面操作说明

## 许可证

MIT License
