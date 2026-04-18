# LangChain Python 文档索引

> 本文档索引用于快速定位 LangChain 相关主题。遵循"按需检索、最小读取"原则。

---

## 快速查找表

| 主题 | 文件路径 | 核心内容 |
|------|---------|---------|
| 创建 Agent | [Core components/Agents.md](Core%20components/Agents.md) | create_agent、LangGraph、静态/动态模型、工具绑定、system_prompt |
| 模型使用 | [Core components/Models.md](Core%20components/Models.md) | init_chat_model、tool calling、structured output、multimodal、reasoning |
| 消息格式 | [Core components/Messages.md](Core%20components/Messages.md) | HumanMessage、AIMessage、SystemMessage、ToolMessage、content、metadata |
| 工具定义 | [Core components/Tools.md](Core%20components/Tools.md) | @tool decorator、function、Pydantic、schema、docstring |
| 对话记忆 | [Core components/Short-term memory.md](Core%20components/Short-term%20memory.md) | Checkpointer、thread_id、InMemorySaver、PostgresSaver、持久化 |
| 流式输出 | [Core components/Streaming/Overview.md](Core%20components/Streaming/Overview.md) | stream()/astream()、stream_mode、updates/messages/custom、实时反馈 |
| 前端集成 | [Core components/Streaming/Frontend.md](Core%20components/Streaming/Frontend.md) | useStream、React hook、generative UI、分支对话 |
| 结构化返回 | [Core components/Structured output.md](Core%20components/Structured%20output.md) | response_format、ProviderStrategy、ToolStrategy、Pydantic、strict |
| 中间件概述 | [Middleware/Overview.md](Middleware/Overview.md) | middleware、hook points、agent loop、before/after、执行控制 |
| 内置中间件 | [Middleware/Built-in middleware.md](Middleware/Built-in%20middleware.md) | Summarization、Human-in-the-loop、retry、fallback、rate limit、PII |
| 自定义中间件 | [Middleware/Custom middleware.md](Middleware/Custom%20middleware.md) | before_model、after_model、AgentMiddleware、decorator、jump_to |
| 安全护栏 | [Advanced usage/Guardrails.md](Advanced%20usage/Guardrails.md) | Guardrails、PIIMiddleware、redact/mask/block、prompt injection |
| 运行时上下文 | [Advanced usage/Runtime.md](Advanced%20usage/Runtime.md) | Runtime、Context、Store、ToolRuntime、依赖注入、context_schema |
| 上下文工程 | [Advanced usage/Context engineering.md](Advanced%20usage/Context%20engineering.md) | Model/Tool/Life-cycle Context、State、Store、middleware |
| MCP 集成 | [Advanced usage/MCP.md](Advanced%20usage/MCP.md) | Model Context Protocol、MultiServerMCPClient、stdio/http、FastMCP |
| 人机协作 | [Advanced usage/Human-in-the-loop.md](Advanced%20usage/Human-in-the-loop.md) | HumanInTheLoopMiddleware、interrupt、approve/edit/reject |
| 多 Agent 概述 | [Advanced usage/Multi-agent/Overview.md](Advanced%20usage/Multi-agent/Overview.md) | 上下文管理、分布式开发、并行化、5种模式 |
| 子 Agent 模式 | [Advanced usage/Multi-agent/Subagents.md](Advanced%20usage/Multi-agent/Subagents.md) | Supervisor、工具调用、集中控制、无直接交互 |
| Agent 交接模式 | [Advanced usage/Multi-agent/Handoffs.md](Advanced%20usage/Multi-agent/Handoffs.md) | 状态驱动、Command、工具转换、持久状态 |
| 技能模式 | [Advanced usage/Multi-agent/Skills.md](Advanced%20usage/Multi-agent/Skills.md) | load_skill、提示驱动、渐进式披露、llms.txt |
| 路由模式 | [Advanced usage/Multi-agent/Router.md](Advanced%20usage/Multi-agent/Router.md) | 分类路由、Send、并行调用、结果综合 |
| 自定义工作流 | [Advanced usage/Multi-agent/Custom workflow.md](Advanced%20usage/Multi-agent/Custom%20workflow.md) | LangGraph、StateGraph、确定性+智能、混合模式 |
| RAG 检索 | [Advanced usage/Retrieval.md](Advanced%20usage/Retrieval.md) | Vector Store、Embeddings、Document Loaders、Agentic RAG |
| 长期记忆 | [Advanced usage/Long-term memory.md](Advanced%20usage/Long-term%20memory.md) | InMemoryStore、namespace、put/get/search、跨对话、embedding |
| 可视化开发 | [Agent development/LangSmith Studio.md](Agent%20development/LangSmith%20Studio.md) | LangSmith Studio、LangGraph CLI、langgraph.json、Agent Server |
| Agent 测试 | [Agent development/Test.md](Agent%20development/Test.md) | GenericFakeChatModel、InMemorySaver、AgentEvals、trajectory match |
| 聊天界面 | [Agent development/Agent Chat UI.md](Agent%20development/Agent%20Chat%20UI.md) | Agent Chat UI、Next.js、time-travel、generative UI |
| 部署到生产 | [Deploy with LangSmith/Deployment.md](Deploy%20with%20LangSmith/Deployment.md) | LangSmith deployment、GitHub、langgraph-sdk、API endpoint |
| 可观测性 | [Deploy with LangSmith/Observability.md](Deploy%20with%20LangSmith/Observability.md) | LANGSMITH_TRACING、traces、tracing_context、observability |

---

## 按场景查找

### Agent 开发
- **创建基础 Agent**: [Agents.md](Core%20components/Agents.md) + [Tools.md](Core%20components/Tools.md)
- **配置模型**: [Models.md](Core%20components/Models.md)
- **添加记忆**: [Short-term memory.md](Core%20components/Short-term%20memory.md)
- **获取结构化输出**: [Structured output.md](Core%20components/Structured%20output.md)

### 实时交互
- **实现流式输出**: [Streaming/Overview.md](Core%20components/Streaming/Overview.md)
- **构建聊天 UI**: [Streaming/Frontend.md](Core%20components/Streaming/Frontend.md)

### 消息处理
- **理解消息格式**: [Messages.md](Core%20components/Messages.md)
- **处理多模态内容**: [Models.md](Core%20components/Models.md) + [Messages.md](Core%20components/Messages.md)

### Agent 控制与优化
- **添加中间件**: [Middleware/Overview.md](Middleware/Overview.md)
- **使用内置中间件**: [Middleware/Built-in middleware.md](Middleware/Built-in%20middleware.md)
- **自定义执行逻辑**: [Middleware/Custom middleware.md](Middleware/Custom%20middleware.md)

### 高级功能
- **实现安全护栏**: [Guardrails.md](Advanced%20usage/Guardrails.md)
- **使用运行时上下文**: [Runtime.md](Advanced%20usage/Runtime.md)
- **优化上下文**: [Context engineering.md](Advanced%20usage/Context%20engineering.md)
- **集成 MCP 工具**: [MCP.md](Advanced%20usage/MCP.md)
- **添加人工审批**: [Human-in-the-loop.md](Advanced%20usage/Human-in-the-loop.md)

### 多 Agent 系统
- **多 Agent 概述**: [Multi-agent/Overview.md](Advanced%20usage/Multi-agent/Overview.md) - 选择合适的多 Agent 模式
- **子 Agent（集中控制）**: [Multi-agent/Subagents.md](Advanced%20usage/Multi-agent/Subagents.md) - 主 Agent 协调多个子 Agent
- **交接（状态驱动）**: [Multi-agent/Handoffs.md](Advanced%20usage/Multi-agent/Handoffs.md) - Agent 间动态转移控制权
- **技能（按需加载）**: [Multi-agent/Skills.md](Advanced%20usage/Multi-agent/Skills.md) - 渐进式加载专门知识
- **路由（并行分发）**: [Multi-agent/Router.md](Advanced%20usage/Multi-agent/Router.md) - 分类并并行调用专门 Agent
- **自定义工作流**: [Multi-agent/Custom workflow.md](Advanced%20usage/Multi-agent/Custom%20workflow.md) - LangGraph 自定义执行流

### 知识增强
- **RAG 检索**: [Retrieval.md](Advanced%20usage/Retrieval.md)
- **长期记忆**: [Long-term memory.md](Advanced%20usage/Long-term%20memory.md)

### Agent 开发工具
- **可视化开发和调试**: [LangSmith Studio.md](Agent%20development/LangSmith%20Studio.md)
- **测试 Agent**: [Test.md](Agent%20development/Test.md)
- **构建聊天界面**: [Agent Chat UI.md](Agent%20development/Agent%20Chat%20UI.md)

### 生产部署
- **部署到 LangSmith**: [Deployment.md](Deploy%20with%20LangSmith/Deployment.md)
- **监控和追踪**: [Observability.md](Deploy%20with%20LangSmith/Observability.md)

---

## Core components

### [Agents](Core%20components/Agents.md)
**Agent 系统 - 结合语言模型与工具的推理系统**

核心概念：
- `create_agent()` - 创建生产级 agent
- 静态模型 vs 动态模型选择
- 工具绑定与使用
- 系统提示配置
- LangGraph 图结构运行时

关键代码：
```python
from langchain.agents import create_agent
agent = create_agent("openai:gpt-5", tools=tools)
```

---

### [Models](Core%20components/Models.md)
**LLM 模型 - AI 推理引擎**

核心概念：
- `init_chat_model()` - 初始化聊天模型
- 工具调用 (Tool calling)
- 结构化输出 (Structured output)
- 多模态支持 (Multimodal)
- 推理能力 (Reasoning)

支持的使用方式：
1. 在 Agent 中使用
2. 独立调用（文本生成、分类、提取）

关键代码：
```python
from langchain.chat_models import init_chat_model
model = init_chat_model("gpt-4.1")
```

---

### [Messages](Core%20components/Messages.md)
**消息 - 模型交互的基本单位**

核心概念：
- 消息类型: `SystemMessage`, `HumanMessage`, `AIMessage`, `ToolMessage`
- 消息内容: 文本、图片、音频、文档等
- 消息元数据: 响应信息、消息 ID、token 使用量

三种提示方式：
1. 文本提示 (Text prompts)
2. 消息提示 (Message prompts)
3. 字典格式 (Dictionary format)

关键代码：
```python
from langchain.messages import HumanMessage, AIMessage, SystemMessage
messages = [SystemMessage("..."), HumanMessage("...")]
response = model.invoke(messages)
```

---

### [Tools](Core%20components/Tools.md)
**工具 - 扩展 Agent 能力的可调用函数**

核心概念：
- `@tool` 装饰器定义工具
- 类型提示定义输入模式
- docstring 作为工具描述
- Pydantic 模型定义复杂输入

工具定制：
- 自定义工具名称
- 自定义工具描述
- 高级模式定义

关键代码：
```python
from langchain.tools import tool

@tool
def search_database(query: str, limit: int = 10) -> str:
    """Search the customer database for records."""
    return f"Found {limit} results for '{query}'"
```

---

### [Short-term memory](Core%20components/Short-term%20memory.md)
**短期记忆 - 线程级对话持久化**

核心概念：
- Checkpointer - 状态持久化机制
- Thread - 组织多轮交互的会话
- 上下文窗口管理
- 消息历史记录

生产环境选项：
- `InMemorySaver` - 内存存储（开发测试）
- `PostgresSaver` - PostgreSQL 存储（生产）
- SQLite、Azure Cosmos DB 等

关键代码：
```python
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    "gpt-5",
    tools=[get_user_info],
    checkpointer=InMemorySaver(),
)

agent.invoke(
    {"messages": [{"role": "user", "content": "Hi!"}]},
    {"configurable": {"thread_id": "1"}},
)
```

---

### [Streaming](Core%20components/Streaming/)

#### [Overview](Core%20components/Streaming/Overview.md)
**流式系统 - 实时更新推送**

核心概念：
- `stream()` / `astream()` 方法
- Stream modes:
  - `updates` - Agent 步骤进度
  - `messages` - LLM token 流
  - `custom` - 自定义数据流

使用场景：
- 提升用户体验（实时反馈）
- 降低延迟感知
- 显示进度状态

关键代码：
```python
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "..."}]},
    stream_mode="updates",
):
    for step, data in chunk.items():
        print(f"step: {step}")
```

#### [Frontend](Core%20components/Streaming/Frontend.md)
**前端集成 - React 流式 UI**

核心概念：
- `useStream` React hook
- 自动状态管理（消息、加载、错误）
- 对话分支
- UI 无关设计

关键功能：
- 消息流处理
- 自动重连
- 错误处理
- 中断处理

关键代码：
```tsx
import { useStream } from "@langchain/langgraph-sdk/react";

const stream = useStream({
  assistantId: "agent",
  apiUrl: "http://localhost:2024",
});

stream.submit({ messages: [{ content: "...", type: "human" }] });
```

---

### [Structured output](Core%20components/Structured%20output.md)
**结构化输出 - 返回预定义格式的数据**

核心概念：
- `response_format` 参数
- `ProviderStrategy` - 使用原生 API
- `ToolStrategy` - 使用工具调用模拟
- 自动策略选择

支持的格式：
- Pydantic 模型
- Dataclasses
- TypedDict
- JSON Schema

关键代码：
```python
from pydantic import BaseModel

class Response(BaseModel):
    answer: str
    confidence: float

agent = create_agent(
    "gpt-5",
    tools=[],
    response_format=Response,
)

result = agent.invoke({"messages": [...]})
structured_data = result["structured_response"]  # Response 实例
```

---

## Middleware

### [Overview](Middleware/Overview.md)
**中间件概述 - Agent 执行流程控制**

核心概念：
- Middleware - 在 agent 执行的每个步骤插入自定义逻辑
- Agent loop - 模型调用、工具执行、结果处理的循环
- Hook points - before/after model、before/after tools

使用场景：
- 日志记录、分析和调试
- 提示转换、工具选择、输出格式化
- 重试、降级和提前终止逻辑
- 速率限制、护栏和 PII 检测

关键代码：
```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware, HumanInTheLoopMiddleware

agent = create_agent(
    model="gpt-4o",
    tools=[...],
    middleware=[
        SummarizationMiddleware(...),
        HumanInTheLoopMiddleware(...)
    ],
)
```

---

### [Built-in middleware](Middleware/Built-in%20middleware.md)
**内置中间件 - 常见场景的预构建解决方案**

Provider-agnostic middleware（11种）：
1. **Summarization** - 对话历史自动摘要（接近 token 限制时）
2. **Human-in-the-loop** - 暂停执行等待人工批准
3. **Model call limit** - 限制模型调用次数
4. **Tool call limit** - 限制工具调用次数
5. **Model fallback** - 主模型失败时自动降级
6. **PII detection** - 检测和处理个人身份信息
7. **To-do list** - 为 agent 提供任务规划能力
8. **LLM tool selector** - 用 LLM 预选相关工具
9. **Tool retry** - 工具调用失败自动重试
10. **Model retry** - 模型调用失败自动重试
11. **Context editing** - 修剪或清除对话上下文

关键示例：
```python
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-4o",
    tools=[...],
    middleware=[
        SummarizationMiddleware(
            model="gpt-4o-mini",
            trigger=("tokens", 4000),  # 达到 4000 tokens 时触发
            keep=("messages", 20),     # 保留最近 20 条消息
        ),
    ],
)
```

---

### [Custom middleware](Middleware/Custom%20middleware.md)
**自定义中间件 - 实现自定义钩子函数**

两种钩子风格：
1. **Node-style hooks** - 在特定执行点顺序运行
   - `before_agent` - Agent 开始前（每次调用一次）
   - `before_model` - 每次模型调用前
   - `after_model` - 每次模型响应后
   - `after_agent` - Agent 完成后（每次调用一次）

2. **Wrap-style hooks** - 包裹每次模型或工具调用
   - 更细粒度的控制

实现方式：
- **装饰器方式** - 使用 `@before_model`, `@after_model` 装饰器
- **类方式** - 继承 `AgentMiddleware` 类

关键代码（装饰器方式）：
```python
from langchain.agents.middleware import before_model, after_model, AgentState
from langchain.messages import AIMessage
from langgraph.runtime import Runtime
from typing import Any

@before_model(can_jump_to=["end"])
def check_message_limit(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    if len(state["messages"]) >= 50:
        return {
            "messages": [AIMessage("Conversation limit reached.")],
            "jump_to": "end"
        }
    return None

@after_model
def log_response(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    print(f"Model returned: {state['messages'][-1].content}")
    return None
```

关键代码（类方式）：
```python
from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain.messages import AIMessage
from langgraph.runtime import Runtime
from typing import Any

class MessageLimitMiddleware(AgentMiddleware):
    def __init__(self, max_messages: int = 50):
        super().__init__()
        self.max_messages = max_messages

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        if len(state["messages"]) == self.max_messages:
            return {
                "messages": [AIMessage("Conversation limit reached.")],
                "jump_to": "end"
            }
        return None
```

---

## Advanced usage

### [Guardrails](Advanced%20usage/Guardrails.md)
**安全护栏 - 实现安全检查和内容过滤**

核心概念：
- 安全护栏 - 在 agent 执行关键点验证和过滤内容
- 确定性护栏 - 基于规则（regex、关键词）
- 模型护栏 - 基于 LLM 的语义理解

使用场景：
- 防止 PII 泄露
- 检测和阻止提示注入攻击
- 阻止不当或有害内容
- 强制业务规则和合规要求
- 验证输出质量和准确性

关键代码（PII 检测）：
```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware

agent = create_agent(
    model="gpt-4o",
    tools=[...],
    middleware=[
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        PIIMiddleware("credit_card", strategy="mask", apply_to_input=True),
        PIIMiddleware("api_key", strategy="block", apply_to_input=True),
    ],
)
```

---

### [Runtime](Advanced%20usage/Runtime.md)
**运行时 - 访问上下文、Store 和流写入器**

核心概念：
- `Runtime` 对象 - 提供运行时信息
  - Context: 静态信息（用户 ID、数据库连接）
  - Store: 长期记忆存储
  - Stream writer: 自定义流写入

依赖注入：
- 在 tools 和 middleware 中访问运行时信息
- 不使用全局状态或硬编码值

关键代码（在 Tool 中使用）：
```python
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime

@dataclass
class Context:
    user_id: str

@tool
def fetch_user_email_preferences(runtime: ToolRuntime[Context]) -> str:
    """Fetch the user's email preferences from the store."""
    user_id = runtime.context.user_id

    preferences: str = "The user prefers brief emails."
    if runtime.store:
        if memory := runtime.store.get(("users",), user_id):
            preferences = memory.value["preferences"]

    return preferences
```

关键代码（配置 Context）：
```python
from dataclasses import dataclass
from langchain.agents import create_agent

@dataclass
class Context:
    user_name: str

agent = create_agent(
    model="gpt-5-nano",
    tools=[...],
    context_schema=Context
)

agent.invoke(
    {"messages": [{"role": "user", "content": "What's my name?"}]},
    context=Context(user_name="John Smith")
)
```

---

### [Context engineering](Advanced%20usage/Context%20engineering.md)
**上下文工程 - 提供正确的信息和工具**

核心概念：
- Agent 失败的主要原因：缺少正确的上下文
- 上下文工程 = 以正确的格式提供正确的信息
- Agent loop: Model call → Tool execution → 循环

三种上下文类型：
1. **Model Context（瞬态）** - 进入模型调用的内容（指令、消息、工具）
2. **Tool Context（持久）** - 工具可访问和产生的内容（state、store）
3. **Life-cycle Context（持久）** - 模型和工具调用之间的逻辑（摘要、护栏）

三种数据源：
1. **Runtime Context** - 对话级静态配置（用户 ID、API keys）
2. **State** - 短期记忆（当前消息、工具结果）
3. **Store** - 长期记忆（用户偏好、历史数据）

实现机制：
- 使用 Middleware 钩入 agent 生命周期
- 更新上下文或跳转到不同步骤

---

### [MCP](Advanced%20usage/MCP.md)
**Model Context Protocol - 标准化工具和上下文协议**

核心概念：
- MCP - 开放协议，标准化应用如何向 LLM 提供工具和上下文
- `langchain-mcp-adapters` - LangChain 的 MCP 适配器库
- `MultiServerMCPClient` - 连接多个 MCP 服务器

Transport 类型：
- `stdio` - 本地子进程通信
- `http` - 基于 HTTP 的远程服务器

关键代码：
```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

client = MultiServerMCPClient({
    "math": {
        "transport": "stdio",
        "command": "python",
        "args": ["/path/to/math_server.py"],
    },
    "weather": {
        "transport": "http",
        "url": "http://localhost:8000/mcp",
    }
})

tools = await client.get_tools()
agent = create_agent("claude-sonnet-4-5-20250929", tools)
```

创建自定义服务器：
- 使用 FastMCP 库创建 MCP 服务器

---

### [Human-in-the-loop](Advanced%20usage/Human-in-the-loop.md)
**人机协作 - 添加人工监督**

核心概念：
- HITL Middleware - 为工具调用添加人工监督
- 使用 LangGraph 的 interrupt 机制暂停执行
- 需要 checkpointer 持久化状态

三种决策类型：
- ✅ `approve` - 批准并按原样执行
- ✏️ `edit` - 修改后执行
- ❌ `reject` - 拒绝并提供反馈

关键代码：
```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="gpt-4o",
    tools=[write_file_tool, execute_sql_tool, read_data_tool],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "write_file": True,  # 允许所有决策
                "execute_sql": {"allowed_decisions": ["approve", "reject"]},  # 不允许编辑
                "read_data": False,  # 无需审批
            },
        ),
    ],
    checkpointer=InMemorySaver(),  # 生产环境使用 PostgresSaver
)
```

---

### [Multi-agent](Advanced%20usage/Multi-agent/)

#### [Overview](Advanced%20usage/Multi-agent/Overview.md)
**多 Agent 系统 - 协调专门组件**

为什么需要多 Agent：
- **上下文管理** - 选择性提供专门知识
- **分布式开发** - 不同团队独立开发和维护
- **并行化** - 并发执行子任务

五种模式：

| 模式 | 工作原理 | 分布式开发 | 并行化 | 多跳 | 用户交互 |
|------|---------|-----------|--------|------|---------|
| **Subagents** | 主 agent 协调子 agent 作为工具 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| **Handoffs** | 基于状态动态改变行为 | — | — | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Skills** | 按需加载专门提示和知识 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Router** | 路由步骤分类并分发到专门 agent | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | — | ⭐⭐⭐ |
| **Custom workflow** | 使用 LangGraph 自定义执行流 | 完全自定义 | 完全自定义 | 完全自定义 | 完全自定义 |

#### [Subagents](Advanced%20usage/Multi-agent/Subagents.md)
**子 Agent 模式 - 主 Agent 协调子 Agent**

关键特征：
- 集中控制 - 所有路由通过主 agent
- 无直接用户交互 - 子 agent 返回结果给主 agent
- 子 agent 作为工具 - 通过工具调用
- 并行执行 - 主 agent 可在一轮中调用多个子 agent

关键代码：
```python
from langchain.tools import tool
from langchain.agents import create_agent

# 创建子 agent
subagent = create_agent(model="claude-sonnet-4", tools=[...])

# 包装为工具
@tool("research", description="Research a topic and return findings")
def call_research_agent(query: str):
    result = subagent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content

# 主 agent
main_agent = create_agent(model="claude-sonnet-4", tools=[call_research_agent])
```

#### [Handoffs](Advanced%20usage/Multi-agent/Handoffs.md)
**交接模式 - 基于状态动态改变行为**

关键特征：
- 状态驱动 - 基于状态变量改变行为
- 工具转换 - 工具更新状态变量以在状态间移动
- 直接用户交互 - 每个状态的配置直接处理用户消息
- 持久状态 - 状态在对话轮次间保持

关键代码：
```python
from langchain.tools import tool
from langgraph.types import Command
from langchain.messages import ToolMessage

@tool
def transfer_to_specialist(runtime) -> Command:
    """Transfer to the specialist agent."""
    return Command(
        update={
            "messages": [ToolMessage("Transferring to specialist", tool_call_id=...)]
        },
        goto="specialist"
    )
```

#### [Skills](Advanced%20usage/Multi-agent/Skills.md)
**技能模式 - 按需加载专门能力**

关键特征：
- 提示驱动专门化 - 技能主要由专门提示定义
- 渐进式披露 - 基于上下文或用户需求提供技能
- 团队分布 - 不同团队独立开发和维护技能
- 轻量级组合 - 技能比完整子 agent 更简单

关键代码：
```python
from langchain.tools import tool
from langchain.agents import create_agent

@tool
def load_skill(skill_name: str) -> str:
    """Load a specialized skill prompt.

    Available skills:
    - write_sql: SQL query writing expert
    - review_legal_doc: Legal document reviewer
    """
    # 从文件/数据库加载技能内容
    ...

agent = create_agent(
    model="gpt-4o",
    tools=[load_skill],
    system_prompt="You are a helpful assistant with skills..."
)
```

#### [Router](Advanced%20usage/Multi-agent/Router.md)
**路由模式 - 分类并分发到专门 Agent**

关键特征：
- 路由器分解查询
- 零个或多个专门 agent 并行调用
- 结果综合为统一响应

关键代码（单 Agent）：
```python
from langgraph.types import Command

def classify_query(query: str) -> str:
    """Use LLM to classify query."""
    ...

def route_query(state: State) -> Command:
    """Route to the appropriate agent."""
    active_agent = classify_query(state["query"])
    return Command(goto=active_agent)
```

#### [Custom workflow](Advanced%20usage/Multi-agent/Custom%20workflow.md)
**自定义工作流 - 使用 LangGraph 定义执行流**

关键特征：
- 完全控制图结构
- 混合确定性逻辑和智能行为
- 支持顺序步骤、条件分支、循环、并行执行
- 将其他模式嵌入为节点

关键代码：
```python
from langchain.agents import create_agent
from langgraph.graph import StateGraph, START, END

agent = create_agent(model="openai:gpt-4o", tools=[...])

def agent_node(state: State) -> dict:
    """A LangGraph node that invokes a LangChain agent."""
    result = agent.invoke({"messages": [{"role": "user", "content": state["query"]}]})
    return {"answer": result["messages"][-1].content}

workflow = (
    StateGraph(State)
    .add_node("agent", agent_node)
    .add_edge(START, "agent")
    .add_edge("agent", END)
)
```

---

### [Retrieval](Advanced%20usage/Retrieval.md)
**检索增强生成（RAG）- 获取相关外部知识**

核心概念：
- LLM 的两个限制：有限上下文、静态知识
- RAG - 在查询时获取相关外部知识
- Knowledge base - 文档或结构化数据仓库

检索管道：
1. Document Loaders - 从外部源摄取数据
2. Text Splitters - 将大文档分成小块
3. Embedding Models - 将文本转换为向量
4. Vector Stores - 存储和搜索 embeddings
5. Retrievers - 给定查询返回文档

两种 RAG 方法：
- **Agentic RAG** - 将知识库连接为 agent 的工具
- **2-Step RAG** - 查询并提供检索内容作为 LLM 上下文

---

### [Long-term memory](Advanced%20usage/Long-term%20memory.md)
**长期记忆 - 跨对话持久化**

核心概念：
- 使用 LangGraph persistence 的 memory store
- 以 JSON 文档形式存储记忆
- 分层组织：namespace（命名空间）+ key（键）

Store 操作：
- `put()` - 存储记忆
- `get()` - 通过 ID 获取记忆
- `search()` - 在命名空间内搜索，支持内容过滤和向量相似度

关键代码：
```python
from langgraph.store.memory import InMemoryStore

def embed(texts: list[str]) -> list[list[float]]:
    # 实际的 embedding 函数
    return [[1.0, 2.0] * len(texts)]

store = InMemoryStore(index={"embed": embed, "dims": 2})
user_id = "my-user"
namespace = (user_id, "chitchat")

# 存储
store.put(namespace, "a-memory", {"rules": ["User likes short language"]})

# 获取
item = store.get(namespace, "a-memory")

# 搜索
items = store.search(namespace, filter={"my-key": "my-value"}, query="language")
```

在工具中读取长期记忆：
```python
from langchain.tools import tool, ToolRuntime
from dataclasses import dataclass

@dataclass
class Context:
    user_id: str

@tool
def fetch_user_preferences(runtime: ToolRuntime[Context]) -> str:
    user_id = runtime.context.user_id
    if runtime.store:
        if memory := runtime.store.get(("users",), user_id):
            return memory.value["preferences"]
    return "No preferences found"
```

---

## Agent development

### [LangSmith Studio](Agent%20development/LangSmith%20Studio.md)
**可视化开发和调试 - 实时查看 Agent 执行过程**

核心概念：
- LangSmith Studio - 免费的可视化开发界面
- LangGraph CLI - 本地开发服务器
- Agent Server - 连接 agent 到 Studio

主要功能：
- 可视化 agent 步骤（提示、工具调用、结果、输出）
- 实时交互测试
- 检查中间状态
- 调试问题

设置步骤：
1. 安装 LangGraph CLI: `pip install --upgrade "langgraph-cli[inmem]"`
2. 准备 agent 代码
3. 配置环境变量（`.env` 文件中添加 `LANGSMITH_API_KEY`）
4. 创建 `langgraph.json` 配置文件
5. 启动开发服务器

关键代码（langgraph.json）：
```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent.py:agent"
  },
  "env": ".env"
}
```

关键代码（agent.py）：
```python
from langchain.agents import create_agent

def send_email(to: str, subject: str, body: str):
    """Send an email"""
    return f"Email sent to {to}"

agent = create_agent(
    "gpt-4o",
    tools=[send_email],
    system_prompt="You are an email assistant.",
)
```

---

### [Test](Agent%20development/Test.md)
**测试 Agent - 单元测试和集成测试**

核心概念：
- 单元测试 - 使用内存 mock 测试小型、确定性组件
- 集成测试 - 使用真实 LLM 测试整体行为
- AgentEvals - 专门用于测试 agent 轨迹的评估器

测试方法：

**单元测试：**
1. **Mocking Chat Model** - 使用 `GenericFakeChatModel`
```python
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

model = GenericFakeChatModel(messages=iter([
    AIMessage(content="", tool_calls=[ToolCall(name="foo", args={"bar": "baz"}, id="call_1")]),
    "bar"
]))
```

2. **InMemorySaver Checkpointer** - 模拟多轮对话
```python
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model,
    tools=[],
    checkpointer=InMemorySaver()
)

agent.invoke(
    {"messages": [HumanMessage(content="I live in Sydney")]},
    config={"configurable": {"thread_id": "session-1"}}
)
```

**集成测试：**
使用 `agentevals` 包：
- **Trajectory match** - 硬编码参考轨迹，逐步比较
  - 确定性、快速、成本低
  - 适用于已知预期行为的工作流

- **LLM judge** - 使用 LLM 评估 agent 输出
  - 灵活、适用于开放式任务
  - 需要额外 LLM 调用

---

### [Agent Chat UI](Agent%20development/Agent%20Chat%20UI.md)
**聊天界面 - 为 Agent 提供交互式 UI**

核心概念：
- Agent Chat UI - Next.js 聊天应用
- 开源、可定制
- 支持本地和部署的 agent

主要功能：
- 实时聊天
- 工具可视化
- 时间旅行调试
- 状态分叉
- 生成式 UI 支持

快速开始：
1. **使用托管版本**: 访问 [agentchat.vercel.app](https://agentchat.vercel.app)
2. **连接 agent**: 输入部署 URL 或本地服务器地址
3. **开始聊天**: UI 自动检测和渲染工具调用

本地开发：
```bash
# 使用 npx 创建项目
npx create-agent-chat-app --project-name my-chat-ui
cd my-chat-ui

# 安装依赖并启动
pnpm install
pnpm dev
```

或者克隆仓库：
```bash
git clone https://github.com/langchain-ai/agent-chat-ui.git
cd agent-chat-ui
pnpm install
pnpm dev
```

配置连接：
1. **Graph ID**: 在 `langgraph.json` 的 `graphs` 中找到
2. **Deployment URL**: Agent 服务器端点（如 `http://localhost:2024`）
3. **LangSmith API key（可选）**: 部署时需要

---

## Deploy with LangSmith

### [Deployment](Deploy%20with%20LangSmith/Deployment.md)
**生产部署 - 将 Agent 部署到 LangSmith 托管平台**

核心概念：
- LangSmith 托管平台 - 专为 agent 工作负载设计的托管平台
- 有状态、长时间运行的 agent
- 持久化状态和后台执行

主要优势：
- 基础设施管理 - LangSmith 处理托管、扩展和运维
- GitHub 集成 - 直接从仓库部署
- 专为 LangGraph 设计 - 非传统无状态 web 应用

部署步骤：
1. 创建 GitHub 仓库（公开或私有）
2. 确保应用兼容 LangGraph（包含 `langgraph.json`）
3. 在 LangSmith 中创建新部署
4. 连接 GitHub 账户
5. 选择仓库并提交部署（约15分钟）

部署后操作：
- 在 Studio 中测试应用
- 获取 API URL
- 使用 LangGraph SDK 调用 API

关键代码（Python SDK）：
```python
from langgraph_sdk import get_sync_client

client = get_sync_client(
    url="your-deployment-url",
    api_key="your-langsmith-api-key"
)

for chunk in client.runs.stream(
    None,    # Threadless run
    "agent", # Name of agent (from langgraph.json)
    input={
        "messages": [{
            "role": "human",
            "content": "What is LangGraph?",
        }],
    },
):
    print(chunk)
```

---

### [Observability](Deploy%20with%20LangSmith/Observability.md)
**可观测性 - 追踪和监控 Agent 执行**

核心概念：
- Traces - 记录 agent 执行的每个步骤
- LangSmith - 捕获、调试、评估和监控平台
- 自动追踪 - `create_agent` 自动支持追踪

Trace 包含内容：
- 初始用户输入
- 工具调用
- 模型交互
- 决策点
- 最终响应

启用追踪：
设置环境变量：
```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=<your-api-key>
```

无需额外代码：
```python
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-4o",
    tools=[send_email, search_web],
    system_prompt="You are a helpful assistant."
)

# 运行 agent - 所有步骤自动追踪
response = agent.invoke({
    "messages": [{"role": "user", "content": "Send a test email"}]
})
```

选择性追踪：
使用 `tracing_context` 上下文管理器：
```python
import langsmith as ls

# 这会被追踪
with ls.tracing_context(enabled=True):
    agent.invoke({"messages": [...]})

# 这不会被追踪（如果未设置 LANGSMITH_TRACING）
agent.invoke({"messages": [...]})
```

项目管理：
- 静态设置：`export LANGSMITH_PROJECT=my-project`
- 动态设置：使用 `tracing_context(project_name="...")`

用途：
- 调试问题
- 评估不同输入的性能
- 监控生产使用模式

---

## 更新日志

- 2025-01-26: 创建索引文件，添加 Core components 章节
- 2025-01-26: 添加 Middleware 章节（Overview、Built-in middleware、Custom middleware）
- 2025-01-26: 添加 Advanced usage 章节（Guardrails、Runtime、Context engineering、MCP、Human-in-the-loop、Multi-agent、Retrieval、Long-term memory）
- 2025-01-26: 添加 Agent development 章节（LangSmith Studio、Test、Agent Chat UI）
- 2025-01-26: 添加 Deploy with LangSmith 章节（Deployment、Observability）
- 2025-01-26: 质量优化 - 补充 Multi-agent 子页面、增强关键词可检索性（4-7个高价值关键词）
