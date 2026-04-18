> ## Documentation Index
> Fetch the complete documentation index at: https://docs.langchain.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Runtime

## Overview

LangChain's [`create_agent`](https://reference.langchain.com/python/langchain/agents/#langchain.agents.create_agent) runs on LangGraph's runtime under the hood.

LangGraph exposes a [`Runtime`](https://reference.langchain.com/python/langgraph/runtime/#langgraph.runtime.Runtime) object with the following information:

1. **Context**: static information like user id, db connections, or other dependencies for an agent invocation
2. **Store**: a [BaseStore](https://reference.langchain.com/python/langgraph/store/#langgraph.store.base.BaseStore) instance used for [long-term memory](/oss/python/langchain/long-term-memory)
3. **Stream writer**: an object used for streaming information via the `"custom"` stream mode

<Tip>
  Runtime context provides **dependency injection** for your tools and middleware. Instead of hardcoding values or using global state, you can inject runtime dependencies (like database connections, user IDs, or configuration) when invoking your agent. This makes your tools more testable, reusable, and flexible.
</Tip>

You can access the runtime information within [tools](#inside-tools) and [middleware](#inside-middleware).

## Access

When creating an agent with [`create_agent`](https://reference.langchain.com/python/langchain/agents/#langchain.agents.create_agent), you can specify a `context_schema` to define the structure of the `context` stored in the agent [`Runtime`](https://reference.langchain.com/python/langgraph/runtime/#langgraph.runtime.Runtime).

When invoking the agent, pass the `context` argument with the relevant configuration for the run:

```python  theme={null}
from dataclasses import dataclass

from langchain.agents import create_agent


@dataclass
class Context:
    user_name: str

agent = create_agent(
    model="gpt-5-nano",
    tools=[...],
    context_schema=Context  # [!code highlight]
)

agent.invoke(
    {"messages": [{"role": "user", "content": "What's my name?"}]},
    context=Context(user_name="John Smith")  # [!code highlight]
)
```

### Inside tools

You can access the runtime information inside tools to:

* Access the context
* Read or write long-term memory
* Write to the [custom stream](/oss/python/langchain/streaming#custom-updates) (ex, tool progress / updates)

Use the `ToolRuntime` parameter to access the [`Runtime`](https://reference.langchain.com/python/langgraph/runtime/#langgraph.runtime.Runtime) object inside a tool.

```python  theme={null}
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime  # [!code highlight]

@dataclass
class Context:
    user_id: str

@tool
def fetch_user_email_preferences(runtime: ToolRuntime[Context]) -> str:  # [!code highlight]
    """Fetch the user's email preferences from the store."""
    user_id = runtime.context.user_id  # [!code highlight]

    preferences: str = "The user prefers you to write a brief and polite email."
    if runtime.store:  # [!code highlight]
        if memory := runtime.store.get(("users",), user_id):  # [!code highlight]
            preferences = memory.value["preferences"]

    return preferences
```

### Inside middleware

You can access runtime information in middleware to create dynamic prompts, modify messages, or control agent behavior based on user context.

Use the `Runtime` parameter to access the [`Runtime`](https://reference.langchain.com/python/langgraph/runtime/#langgraph.runtime.Runtime) object inside [node-style hooks](/oss/python/langchain/middleware/custom#node-style-hooks).  For [wrap-style hooks](/oss/python/langchain/middleware/custom#wrap-style-hooks), the `Runtime` object is available inside the [`ModelRequest`](https://reference.langchain.com/python/langchain/middleware/#langchain.agents.middleware.ModelRequest) parameter.

```python  theme={null}
from dataclasses import dataclass

from langchain.messages import AnyMessage
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import dynamic_prompt, ModelRequest, before_model, after_model
from langgraph.runtime import Runtime


@dataclass
class Context:
    user_name: str

# Dynamic prompts
@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    user_name = request.runtime.context.user_name  # [!code highlight]
    system_prompt = f"You are a helpful assistant. Address the user as {user_name}."
    return system_prompt

# Before model hook
@before_model
def log_before_model(state: AgentState, runtime: Runtime[Context]) -> dict | None:  # [!code highlight]
    print(f"Processing request for user: {runtime.context.user_name}")  # [!code highlight]
    return None

# After model hook
@after_model
def log_after_model(state: AgentState, runtime: Runtime[Context]) -> dict | None:  # [!code highlight]
    print(f"Completed request for user: {runtime.context.user_name}")  # [!code highlight]
    return None

agent = create_agent(
    model="gpt-5-nano",
    tools=[...],
    middleware=[dynamic_system_prompt, log_before_model, log_after_model],  # [!code highlight]
    context_schema=Context
)

agent.invoke(
    {"messages": [{"role": "user", "content": "What's my name?"}]},
    context=Context(user_name="John Smith")
)
```

***

<Callout icon="pen-to-square" iconType="regular">
  [Edit this page on GitHub](https://github.com/langchain-ai/docs/edit/main/src/oss/langchain/runtime.mdx) or [file an issue](https://github.com/langchain-ai/docs/issues/new/choose).
</Callout>

<Tip icon="terminal" iconType="regular">
  [Connect these docs](/use-these-docs) to Claude, VSCode, and more via MCP for real-time answers.
</Tip>
