# 智卷 — 智能错题本生成系统

基于 PaddleOCR + LangChain Agent 的智能错题本生成系统。上传试卷 PDF 或图片，自动识别文档结构、智能分割题目、OCR 纠错，导出为 Markdown 错题本并存入错题库。支持 AI 解题与教学讲解、笔记整理、独立 AI 对话、错题复习计划与数据统计。

## 功能

- **智能分割**：LLM Agent 自动识别题目边界，支持批次并行处理，跨页去重
- **OCR 纠错**：LLM 对识别结果进行结构化纠错，还原原题格式
- **手写擦除**：EnsExam 模型自动擦除手写字迹，提升 OCR 精度
- **OCR 预览**：识别结果 bbox 框标注叠加在原图上，直观预览
- **错题库**：SQLite 持久化存储，支持按科目、题型、知识点筛选和统计
- **笔记整理**：上传手写笔记图片，OCR + LLM 自动结构化整理为 Markdown
- **AI 解题**：独立解题 Agent，逐步给出解题过程
- **AI 教学**：教学讲解 Agent，绑定错题上下文的一对一辅导
- **AI 对话**：独立多轮对话，支持 SSE 流式输出和深度思考（DeepSeek Reasoner）；会话对外使用 UUID public_id，避免暴露数据库自增主键，并支持 `/app/ai-chat/:sessionId` 直达历史会话
- **复习计划**：间隔复习，追踪错题掌握状态
- **数据统计**：Dashboard 可视化，按科目/题型/时间维度分析
- **导出**：导出为 Markdown 文件，按大题分组

## 项目结构

```
├── backend/                         # Flask 后端（纯 API 服务）
│   ├── core/                        # 核心模块
│   │   ├── config.py                # 集中配置（路径、Settings）
│   │   ├── llm.py                   # LLM 初始化（多 provider 支持）
│   │   ├── state.py                 # 全局会话状态（session_files、锁）
│   │   └── mail.py                  # SMTP 邮件发送
│   ├── web_app.py                   # Flask 应用工厂 + Blueprint 注册
│   ├── routes/                      # 7 个 Blueprint（upload、questions、chat、stats、auth、settings、notes）
│   ├── src/                         # 核心模块（LangGraph workflow、OCR 客户端、工具函数）
│   ├── agents/                      # LangChain Agent
│   │   ├── error_correction/        # 题目分割 + OCR 纠错
│   │   ├── solve/                   # 解题 Agent
│   │   ├── teach/                   # 教学讲解 Agent
│   │   └── note/                    # 笔记整理 Agent
│   ├── db/                          # SQLite + SQLAlchemy ORM
│   │   ├── models.py               # 数据模型（User、Question、Note、Chat 等）
│   │   ├── crud/                    # CRUD 模块化包
│   │   └── migrate.py              # 数据库自动迁移
│   ├── benchmark/                   # 模型评测
│   └── tests/                       # 后端测试
├── frontend/                        # Vue 3 + Vite + Tailwind CSS
│   ├── app.html                     # SPA 入口
│   └── src/
│       ├── views/                   # 页面级组件（HomeView、WorkspaceView）
│       ├── components/              # 55+ 功能组件
│       │   ├── auth/               # 认证（登录、注册、找回密码）
│       │   └── home/               # 首页组件
│       ├── composables/             # 组合式函数（useAuth、useTheme 等）
│       ├── router/                  # Vue Router 路由配置
│       ├── api.js                   # 集中式 API 层
│       ├── utils.js                 # 工具函数（Markdown 渲染、MathJax、DOMPurify）
│       └── __tests__/               # 前端测试（Vitest）
├── example_uploads/                 # 示例测试文件
├── backend/.env.example             # 环境变量模板
└── requirements.txt                 # Python 依赖
```

## 环境部署

### 1. 安装依赖

需要 Python 3.11+、Node.js 18+。

```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend && npm install
```

### 2. 配置环境变量

```bash
# 复制模板到项目根目录
cp backend/.env.example .env
```

编辑 `.env`，必须配置 `SECRET_KEY`。

LLM API Provider（OpenAI / Anthropic / PaddleOCR）配置已迁移到数据库，启动后在系统设置页面管理。

SMTP 邮件配置（注册验证码、找回密码）通过 `.env` 的 `APP_SMTP_*` 变量管理，详见 `backend/.env.example`。

### 3. 启动

**开发模式**（前后端分离，支持热更新）：

```bash
# 终端 1：启动后端
cd backend && python web_app.py

# 终端 2：启动前端开发服务器
cd frontend && npm run dev
```

前端开发服务器会自动将 `/api`、`/images`、`/download`、`/erased`、`/uploads` 请求代理到后端 `localhost:5001`。

访问 **http://localhost:5173** 即可使用。

> **注意**：后端已重构为纯 API 服务器，不提供前端页面。直接访问 `:5001` 只会得到 JSON 404。

## 支持的文件格式

PDF(`.pdf`)、图片(`.jpg` `.jpeg` `.png` `.bmp` `.tiff` `.webp`)，单次上传限制 50 MB。

## 测试

```bash
# 后端测试
cd backend && python -m pytest tests/ -v

# 前端测试
cd frontend && npm test
```

详见 [backend/tests/README.md](backend/tests/README.md) 和 [frontend/src/__tests__/README.md](frontend/src/__tests__/README.md)。

## 许可证

本项目基于 [AGPL-3.0](LICENSE) 开源。任何修改或基于本项目的衍生作品（包括网络服务部署）均须以相同许可证开源。
