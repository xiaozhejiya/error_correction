# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 常用命令

### 开发模式（前后端分离，热更新）

```bash
# 终端 1：后端
cd backend && python web_app.py          # Flask on localhost:5001

# 终端 2：前端
cd frontend && npm run dev               # Vite dev server, proxy /api → :5001
```

### 生产构建

```bash
cd frontend && npm run build             # 构建前端产物（目前仅用于部署，Flask 不再托管）
cd backend && python web_app.py          # 启动纯 API 服务，仅监听 :5001
```

> **注意**：`web_app.py` 已重构为纯 API 服务器，不提供前端页面。前端必须通过 Vite dev server（`:5173`）或独立部署访问，直接访问 `:5001` 只会得到 JSON 404。

### 测试

```bash
# 后端（工作目录必须是 backend/）
cd backend
C:/ProgramData/miniconda3/envs/da/python.exe -m pytest tests/ -v          # 全量
C:/ProgramData/miniconda3/envs/da/python.exe -m pytest tests/test_utils.py -v  # 单个模块
C:/ProgramData/miniconda3/envs/da/python.exe -m pytest tests/test_utils.py::test_name -v  # 单个用例

# 前端（工作目录必须是 frontend/）
cd frontend
npm test                                 # vitest run（单次）
npm run test:watch                       # vitest watch 模式
```

### 依赖安装

```bash
pip install -r requirements.txt          # 后端（Python 3.11+）
cd frontend && npm install               # 前端（Node 18+）
```

### 环境配置

复制 `backend/.env.example` → 项目根目录 `.env`，必须配置 `SECRET_KEY`。`core/config.py` 从项目根目录读取 `.env`。LLM API Provider 配置（OpenAI / Anthropic / PaddleOCR）已迁移到数据库，用户在系统设置页面管理。SMTP 邮件配置（注册验证码、找回密码）通过 `.env` 的 `APP_SMTP_*` 变量管理。

---

## 系统架构

**错题本生成系统**：上传试卷 PDF/图片 → OCR 结构化识别 → LLM Agent 智能分割题目 → 纠错 → 导出 Markdown / 存入错题库。

### 核心数据流

```
用户上传文件
  → prepare_input（PDF 转图片）
  → [可选] EnsExam 擦除手写字迹（/api/erase，独立预处理步骤）
  → PaddleOCR API（/api/ocr，异步并行，返回 bbox 预览）
  → simplify_ocr_results()（block_label 归一化，唯一转换点）
  → split_batch（2 页/批滑动窗口，ThreadPoolExecutor 并行，上限 3）
  → LLM Agent 分割题目（invoke_split）
  → _dedup_questions()（跨批次去重）
  → _normalize_image_paths()（修复 LLM 篡改的图片路径）
  → LLM Agent 纠错（invoke_correction）
  → 导出 / 保存数据库
```

### 关键模块关系

- **`backend/src/workflow.py`** — LangGraph StateGraph 主工作流，串联所有处理步骤
- **`backend/agents/error_correction/`** — 题目分割 + OCR 纠错 Agent（`create_inner_split_agent` / `create_inner_correct_agent`）
- **`backend/agents/solve/`** — 独立的解题 Agent（`invoke_solve`）
- **`backend/agents/teach/`** — 教学讲解 Agent，流式多轮对话（`stream_teach`）
- **`backend/agents/note/`** — 笔记整理 Agent，OCR → LLM 结构化（`invoke_note_organize`）
- **`backend/web_app.py`** — Flask 应用工厂，注册 7 个 Blueprint，全局 session 状态在 `state.py`
- **`backend/routes/`** — 7 个 Blueprint 模块（upload、questions、chat、stats、auth、settings、notes）
- **`backend/core/state.py`** — 全局会话状态（`session_files`、`session_lock`）
- **`backend/core/mail.py`** — SMTP 邮件发送（注册验证码、找回密码）
- **`backend/core/config.py`** — 所有运行时路径 + LLM provider 注册集中管理，`ensure_dirs()` 显式初始化
- **`backend/core/llm.py`** — `init_model()` 统一 LLM 初始化，支持多 provider
- **`backend/db/`** — SQLite + SQLAlchemy ORM，错题库持久化；`db/crud/providers.py` 管理用户存储的 API key

### Flask 路由

路由实现在 `backend/routes/` 的 7 个 Blueprint 模块中，`web_app.py` 仅做注册：

- `POST /api/upload` / `/api/erase` / `/api/ocr` / `/api/split` / `/api/export` / `/api/cancel_file` — 核心工作流 API（upload.py）
- `GET /api/image/<filename>` — 图片资源访问（upload.py）
- `GET /api/status` — 系统状态（OCR 配置、可用模型列表）（upload.py）
- `GET /api/split-records` — 分割历史记录（upload.py）
- `/api/error-bank` / `/api/subjects` / `/api/question-types` — 错题库 CRUD（questions.py）
- `/api/stats` — 统计数据（stats.py）
- `/api/chat` / `/api/chat/<id>/messages` / `/api/chat/<id>/stream` — AI 对话（SSE 流式）（chat.py）
- `/api/ai-analysis` — AI 分析（teach_agent）（chat.py）
- `/api/auth` / `/api/auth/send-code` / `/api/auth/reset-password` — 认证 + 邮箱验证码（auth.py）
- `/api/settings` — LLM provider 配置（settings.py）
- `/api/notes` — 笔记 CRUD（notes.py）

---

## 本地 LangChain 文档

本项目包含 LangChain（Python）本地文档快照，入口为 `docs/INDEX.md`。

**使用原则**：按需检索、最小读取。先读 `docs/INDEX.md` 定位章节，再只打开 1–3 个相关片段（禁止整库加载）。

覆盖主题：Core components（Agents, Models, Messages, Tools, Streaming, Structured output）、Middleware、Advanced usage（Guardrails, MCP, Multi-agent, Retrieval）、Agent development、Deploy with LangSmith。超出覆盖范围的问题必须明确说明。

---

## 前端开发规范

### 技术栈

- Vue 3 + `<script setup>`（Composition API，不使用 Options API）
- Vite 单页应用，入口 `app.html`，Vue Router 4 客户端路由
- Tailwind CSS 3（utility-first，class-based dark mode）+ `@tailwindcss/typography`
- HeadlessUI Vue 用于可访问交互组件（Listbox、Dialog 等）
- DOMPurify 用于 HTML 净化（白名单在 `utils.js` 的 `ALLOWED_HTML_TAGS`）
- 纯 JavaScript（不使用 TypeScript），原生 fetch（不使用 axios），文件上传用 XHR
- CDN 外部依赖（非 npm）：Font Awesome 6.5、MathJax 3、SortableJS 1.15、Chart.js 4、marked 15

### 目录结构

```
frontend/src/
├── components/           # 可复用组件（55+）
│   ├── auth/            # 认证：AuthLayout、LoginView、RegisterView、ForgotPasswordModal
│   └── home/            # 首页：HomeNav、HomeHero、HomeFeatures 等
├── composables/          # Vue 3 组合式函数（12 个）
│   ├── useAuth.js       # 认证状态（currentUser、authChecked）
│   ├── useTheme.js      # 主题切换（isDark、toggleTheme + View Transition 动画）
│   ├── usePageTransition.js  # 全局页面过渡遮罩
│   ├── useClickOutside.js    # 点击外部关闭
│   ├── useImageModal.js      # 图片预览弹窗
│   ├── useWorkspaceToast.js  # Toast 通知
│   ├── useSystemStatus.js    # 系统状态（OCR/模型配置）
│   ├── useSidebarIndicator.js # 侧边栏 active 指示器动画
│   ├── useAiChatSessions.js  # AI 对话会话管理
│   ├── useFileUpload.js      # 文件上传状态
│   ├── useSplitPipeline.js   # 分割流水线（擦除→OCR→分割）
│   └── useQuestionList.js    # 题目列表状态
├── router/index.js       # 路由配置
├── views/                # 页面级组件
│   ├── HomeView.vue     # 首页（强制暗色主题）
│   └── WorkspaceView.vue # 工作台主容器（侧边栏 + 内容区）
├── api.js                # 集中式 API 层（50+ 函数）
├── utils.js              # 工具函数（sanitizeHtml、renderMarkdown、typesetMath）
├── style.css             # 全局样式 + Tailwind 自定义类
├── App.vue               # 根组件
└── main.js               # Vue 应用入口
```

### 路由

| 路径 | 组件 | 说明 |
|------|------|------|
| `/` | HomeView | 首页 |
| `/auth/login` | LoginView | 登录 |
| `/auth/register` | RegisterView | 注册 |
| `/app/workspace` | WorkspaceView | 录入工作台 |
| `/app/dashboard` | Dashboard | 数据统计 |
| `/app/error-bank` | ErrorBank | 错题库 |
| `/app/notes` | NoteView | 笔记整理 |
| `/app/ai-chat` | ChatPage | AI 对话 |
| `/app/review` | ReviewView | 复习计划 |
| `/app/settings` | SettingsView | 系统设置 |
| `/app/split-history` | SplitHistory | 分割历史 |
| `/app/chat` | ChatView | 独立对话 |

路由 meta 字段：`layout`（`'home'` / `'auth'` / `'app'`）、`requiresAuth`（boolean）

### 布局

- **PC 端**：左侧固定侧边栏（`aside w-64`）+ 右侧主内容区，导航分组可折叠
- **移动端**：底部 Tab 导航栏（`fixed bottom-0`）+ 全宽内容区
- `currentView` ref 控制视图切换，路由参数 `/app/:view?/:subview?`

### 设计风格

**Glass Morphism + Linear 风格**，以暗色为主、亮色兼容。

**配色 Token：**

| 语义 | 暗色 | 亮色 |
|------|------|------|
| 页面背景 | `[#0A0A0F]` / `slate-950` | `white` / `slate-50` |
| 卡片 / 面板 | `white/[0.02]` ~ `white/[0.05]` + `backdrop-blur-xl` | `white/70` + `backdrop-blur-xl` |
| 边框 | `white/[0.06]` ~ `white/[0.10]` | `slate-200/60` |
| 品牌色 | `rgb(129,115,223)` ~ `rgb(145,132,235)` | `indigo-600` / `blue-600` |
| 成功 | `emerald-400` | `emerald-600` |
| 错误 | `rose-400` | `rose-600` |
| 主要文字 | `white` / `[#d0d6e0]` | `slate-900` |
| 次要文字 | `[#8a8f98]` / `slate-400` | `slate-500` / `slate-700` |
| 占位文字 | `[#62666d]` | `slate-400` |

**Glass 卡片标准写法：**
```
bg-white/[0.02] border border-white/[0.06] rounded-xl
border-t-white/[0.15] border-b-white/[0.03]
hover:bg-white/[0.04] transition-all
```

**圆角：**

| 元素 | 值 |
|------|-----|
| 大卡片、Modal | `rounded-2xl` / `rounded-3xl` |
| 按钮、输入框、小卡片 | `rounded-xl` |
| 标签、Badge、Pill | `rounded-full` |
| 图标容器、小元素 | `rounded-lg` |

**阴影（只允许 2 层）：**

| 状态 | 值 |
|------|-----|
| 默认 | `shadow-sm` |
| Hover / 激活 | `shadow-md` 或品牌色光晕 `shadow-blue-500/20` |

### 按钮

| 类型 | 样式 |
|------|------|
| 品牌按钮 | `brand-btn`（style.css 中定义，frosted glass 风格） |
| 主按钮 | `btn-primary`（蓝→靛渐变，shadow-blue-500/20） |
| 成功按钮 | `btn-success`（翠绿渐变） |
| 次按钮 | `btn-secondary`（边框 + 透明底） |
| 通用属性 | `inline-flex items-center justify-center gap-2 transition-all h-10 rounded-xl text-sm font-bold` |
| 禁用 | `disabled:cursor-not-allowed disabled:opacity-50` |

按钮高度统一 `h-10`（40px），图标尺寸 `size-4`（16px）或 `size-5`（20px）。

### 筛选器

使用 `filter-pill` / `filter-pill--active` 类（style.css），激活态为品牌紫色 `rgb(145,132,235)`。

### 排版

字号只允许以下 7 档：

| 层级 | Tailwind | 用途 |
|------|----------|------|
| 超大标题 | `text-4xl` | 落地页 Hero |
| 大标题 | `text-3xl` | 页面主标题 |
| 标题 | `text-2xl` | 区块标题、Modal 标题 |
| 副标题 | `text-xl` | 卡片标题 |
| 正文 | `text-base` | 题目内容 |
| 辅助 | `text-sm` | 标签、次要信息 |
| 标注 | `text-xs` | 元数据、时间戳 |

禁止 `text-[13px]`、`text-[11px]` 等任意值。

### 间距（8pt Grid）

只允许 4 的倍数：`p-1` `p-2` `p-3` `p-4` `p-6` `p-8` `p-10` `p-12`。禁止 `p-5` `p-7` `p-9` 和 `px-[17px]` 等魔法数字。

### 主题系统

- `useTheme` composable 管理暗色/亮色切换
- `document.documentElement.classList.toggle('dark')` + `localStorage.theme`
- 切换动画：View Transition API 圆形扩散（`clip-path` 圆形展开）
- `app.html` 内有防白闪脚本（DOM 渲染前读取 localStorage 设置 `dark` 类）
- **所有新增元素必须包含 `dark:` 变体**
- 首页强制暗色主题，离开时恢复用户原主题

### 状态管理

- 无 Vuex/Pinia，轻量 ref 方案
- 全局认证状态：`useAuth` composable（`currentUser`、`authChecked`）
- 页面级状态：集中在 `WorkspaceView.vue`（ref/reactive/computed/watch）
- 父子通信：props 向下，emits 向上
- 跨组件共享通过 composable 单例 ref

### API 调用

- 集中在 `api.js`，所有函数导出供组件调用
- 统一错误处理：检查 `resp.ok` + `data.success`，throw 描述性错误
- 模型请求用 `_buildModelBody(modelProvider, modelName, extra)` 构建
- SSE 流式：`streamChat()` 支持 abort signal
- 文件上传用 XHR（支持 progress 回调）

### 内容渲染

- `renderMarkdown(text)` — marked.js 解析 + DOMPurify 净化
- `sanitizeHtml(html)` — 白名单标签净化（table、img 等）
- `typesetMath(el)` — MathJax 公式渲染（行内 `$...$`、独占行 `$$...$$`）
- 渲染后必须调用 `typesetMath` 触发公式排版

### 图标

- 主要：Font Awesome `<i class="fas fa-icon-name"></i>`
- 备用：lucide-vue-next（按需导入）
- 加载中：`fa-spinner fa-spin`

### 组件开发规范

```vue
<script setup>
import { ref, computed, watch, onMounted } from 'vue'

const props = defineProps({ ... })
const emit = defineEmits(['event-name'])

// 状态、计算属性、生命周期...
</script>

<template>
  <!-- 模板 -->
</template>

<style scoped>
/* 仅组件私有样式，全局样式放 style.css */
</style>
```

- UI 文案使用中文，API 路径前缀 `/api/`
- 新功能提取为独立 `.vue` 组件放 `src/components/`
- 认证组件放 `components/auth/`，首页组件放 `components/home/`
- 关键 DOM 元素添加语义类名或 `data-testid`
- Modal/Dropdown 使用 `useClickOutside` 处理外部点击关闭

### Vite 配置

- API 代理：`/api`、`/images`、`/download`、`/erased`、`/uploads` → `http://localhost:5001`
- SPA 路由：`/auth*`、`/app*` → `app.html`
- 构建产物：`dist/`

---

## 后端开发规范

### 模块级副作用

- **禁止在模块顶层执行有副作用的操作**（创建目录、写文件、启动连接等）
- `core/config.py` 目录创建通过 `ensure_dirs()` 显式调用
- `load_dotenv()` 仅在入口文件或需要环境变量的模块中调用

### 数据库

- `with SessionLocal() as db:` 管理会话生命周期
- 写操作必须 `try/except` + `db.rollback()`
- ORM→dict 用 `_serialize_question()` 等统一辅助函数

### 线程安全

- 全局会话状态集中在 `core/state.py`，修改必须在 `session_lock` 保护下
- 锁内用原地修改（`.remove()`, `.append()`），**不要用推导式重新赋值**
- Agent 缓存通过 `_agent_cache_lock` 保护并发初始化

### LLM 与 Agent

- 结构化输出优先用 `create_agent` + `ToolStrategy`
- 已知问题：`ToolStrategy` 与 DeepSeek 的 `handle_errors` 重试不兼容，大数据量可能触发 400
- 不支持 function calling 的模型用 `model.with_structured_output()`
- `invoke_split` / `invoke_correction` 是统一调用入口，屏蔽 provider 差异
- API Provider 配置（key、模型名）存储在数据库中，用户通过系统设置页面管理

### OCR 数据处理

- `simplify_ocr_results()` 是 OCR → Agent 输入的唯一转换点，负责 block_label 归一化
- 新增 block_label 类型时必须在此函数添加映射
- 批次构建：2 页/批、1 页重叠滑动窗口；去重按内容丰富度保留

### 文件与路径

- 所有运行时路径通过 `core/config.py` 集中管理，禁止硬编码
- 文件名解析用 `os.path.splitext()`，**不要用 `rsplit('.', 1)`**
- 文件上传用 `uuid.uuid4().hex` 生成安全文件名

### 环境变量

- `.env` 放项目根目录，不入版本控制；`backend/.env.example` 作为模板
- `core/config.py` 的 `Settings` 使用 `env_prefix="APP_"`，从项目根目录 `.env` 读取
- LLM API Provider 配置已迁移到数据库，不再通过 `.env` 管理
- Flask 级配置（`SECRET_KEY`、`FLASK_DEBUG`、`LANGSMITH_*`）仍通过 `.env` 管理
- SMTP 邮件配置通过 `APP_SMTP_*` 变量管理（`core/mail.py`）
- 新增 `.env` 配置项必须同步更新 `backend/.env.example`
- 可选项用 `os.getenv("KEY")` + 代码中提供默认值

---

## 测试规范

### 测试组织

- 单元测试（无外部依赖）：`test_utils.py`, `test_crud.py`, `test_web_routes.py`, `test_web_helpers.py`, `test_schemas.py` 等
- 集成测试（依赖 API）：`test_split_integration.py`, `test_solve_integration.py`, `test_ocr_api.py`
- 集成测试必须添加 `skip_no_api_key` 保护
- 已知兼容性问题用 `@pytest.mark.xfail(reason="...")` 标记，不要删除测试
- 公共 fixture 在 `conftest.py`（`db` 内存数据库、`make_question` 工厂），优先复用
- 测试数据文件放 `tests/fixtures/`
- 前端测试环境：jsdom + @vue/test-utils，HeadlessUI 通过 `stubs` 跳过

### 测试原则

- **不要为了通过测试而修改测试脚本**——修复代码逻辑，而非放宽断言
- 新增功能/修复 bug 时同步补充测试
- 重构组件时同步更新选择器（类名、文本）

---

## Git 提交规范

格式：`<type>(<scope>): <中文描述>`

Type：`feat`（新功能）、`fix`（修复）、`refactor`（重构）、`test`、`docs`、`config`

原则：按逻辑拆分 commit，描述用中文，`.env` 永不提交。
