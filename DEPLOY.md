# 部署指南

## 环境要求

| 组件 | 版本要求 |
|------|----------|
| Python | 3.11+ |
| Node.js | 18+ |
| PostgreSQL | 14+（需安装 pgvector 扩展） |
| pnpm / npm | 任意版本 |

---

## 1. 克隆项目

```bash
git clone <repo-url>
cd error_correction
```

## 2. 安装后端依赖

```bash
pip install -r requirements.txt
```

关键依赖说明：

| 包 | 用途 |
|---|---|
| `sqlalchemy>=2.0` | ORM |
| `psycopg[binary]>=3.2.0` | PostgreSQL 驱动 |
| `pgvector>=0.3.6` | pgvector 向量检索 |
| `flask` | Web 框架 |
| `langchain` | LLM Agent |

## 3. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

## 4. 配置 PostgreSQL + pgvector

### 4.1 安装 pgvector 扩展

**Windows（本地 PostgreSQL）：**

需要 Visual Studio 的 C++ 支持，打开 **x64 Native Tools Command Prompt**（管理员）：

```batch
set "PGROOT=C:\Program Files\PostgreSQL\18"
cd %TEMP%
git clone --branch v0.8.2 https://github.com/pgvector/pgvector.git
cd pgvector
nmake /F Makefile.win
nmake /F Makefile.win install
```

安装后重启 PostgreSQL 服务。

**Docker（推荐用于开发/部署）：**

```bash
docker pull pgvector/pgvector:pg16
docker run -d --name pg-vector \
  -e POSTGRES_PASSWORD=root \
  -p 15432:5432 \
  pgvector/pgvector:pg16
```

### 4.2 创建数据库

```sql
CREATE DATABASE ctb;
```

验证 pgvector 可用：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT '[1,2,3]'::vector;
```

## 5. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
# ===== 必填 =====
SECRET_KEY=your-random-secret-key-change-this
FLASK_DEBUG=false

# ===== PostgreSQL =====
APP_DATABASE_URL=postgresql+psycopg://postgres:密码@localhost:5432/ctb
APP_POSTGRES_VECTOR_DIMENSIONS=1536

# ===== RAG 语义检索（复用 OpenAI provider 的 key 和 base_url） =====
APP_RAG_EMBEDDING_MODEL=text-embedding-3-small

# ===== 平台托管 Provider（可选，用户未配置时回退） =====
APP_DEFAULT_OPENAI_API_KEY=sk-xxx
APP_DEFAULT_OPENAI_BASE_URL=https://api.openai.com/v1
APP_DEFAULT_OPENAI_MODEL_NAME=gpt-4o-mini
APP_DEFAULT_OPENAI_SUPPORTS_FUNCTION_CALLING=true

# ===== SMTP 邮件（可选，注册验证码/找回密码） =====
APP_SMTP_HOST=smtp.qq.com
APP_SMTP_PORT=587
APP_SMTP_USER=your-email@qq.com
APP_SMTP_PASSWORD=your-smtp-authorization-code
APP_SMTP_FROM=your-email@qq.com
APP_SMTP_USE_TLS=true
```

> **说明**：
> - `FLASK_DEBUG=true` 时，若 PostgreSQL 连接失败会自动回退到 SQLite
> - RAG Embedding 复用 `APP_DEFAULT_OPENAI_*` 的 key 和 base_url
> - 若未配置 OpenAI provider，RAG 将降级为 hash 模糊匹配

## 6. 初始化数据库

```bash
cd backend
python -m db.migrate
```

该命令会：
- 创建 pgvector 扩展
- 创建所有数据库表
- 添加 IVFFlat 向量索引
- 创建默认管理员账号（admin@admin.com / 123456）

## 7. 从 SQLite 迁移数据（可选）

如已有 SQLite 数据（`backend/runtime_data/error_book.db`），可迁移到 PostgreSQL：

```bash
cd backend
python -m db.migrate_sqlite_to_pg
```

迁移完成后验证：

```bash
python -c "
from db import SessionLocal
from db.models import User, Question
with SessionLocal() as db:
    print(f'用户: {db.query(User).count()}')
    print(f'题目: {db.query(Question).count()}')
"
```

> **注意**：`python -m db.migrate` 是增量迁移（安全），不会清空数据。
> 之前的 `rebuild()` 功能已移除默认调用。

## 8. 启动服务

### 开发模式（前后端分离，热更新）

```bash
# 终端 1：后端
cd backend
python web_app.py          # Flask on localhost:5001

# 终端 2：前端
cd frontend
npm run dev               # Vite dev server on localhost:5173
```

访问 http://localhost:5173

### 生产构建

```bash
cd frontend
npm run build             # 构建前端产物到 dist/

cd backend
python web_app.py          # 启动 API 服务 on localhost:5001
```

> **注意**：`web_app.py` 是纯 API 服务器，不提供前端页面。前端需通过 Vite dev server 或独立部署（如 Nginx）访问。

## 9. 运行测试

```bash
cd backend

# 全量测试
python -m pytest tests/ -v

# RAG 单元测试（SQLite 内存库，无需 PostgreSQL）
python -m pytest tests/test_rag.py -v

# pgvector 冒烟测试（需要 PostgreSQL 连接）
$env:APP_TEST_POSTGRES_URL="postgresql+psycopg://postgres:密码@localhost:5432/ctb"
python -m pytest tests/test_rag.py::test_pgvector_sql_compatibility_smoke -v

# 召回率基准测试
python -m pytest tests/test_rag_benchmark.py -v

# 前端测试
cd frontend
npm test
```

---

## 常见问题

### Q: pgvector 安装后 `CREATE EXTENSION vector` 报错

确认 PostgreSQL 服务已重启。Windows 下检查 `C:\Program Files\PostgreSQL\18\lib\` 是否有 `vector.dll`。

### Q: 启动时报 `ModuleNotFoundError: No module named 'psycopg'`

```bash
pip install "psycopg[binary]"
```

### Q: 启动时报 `extension "vector" is not available`

pgvector 未安装到 PostgreSQL。参考第 4.1 节安装。

### Q: `FLASK_DEBUG=true` 时数据写入了 SQLite 而非 PostgreSQL

检查 PostgreSQL 服务是否启动，`.env` 中密码是否正确。开发模式下连接失败会自动回退到 SQLite，启动日志会打印警告。

### Q: RAG 搜索无结果

确认：
1. 已配置 `APP_DEFAULT_OPENAI_API_KEY`（Embedding 需要）
2. 错题库中有数据
3. 后端日志中无 embedding 生成错误
