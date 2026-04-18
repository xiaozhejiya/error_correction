> ## Documentation Index
> Fetch the complete documentation index at: https://docs.langchain.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Custom middleware

Build custom middleware by implementing hooks that run at specific points in the agent execution flow.

## Hooks

Middleware provides two styles of hooks to intercept agent execution:

<CardGroup cols={2}>
  <Card title="Node-style hooks" icon="share-nodes" href="#node-style-hooks">
    Run sequentially at specific execution points.
  </Card>

  <Card title="Wrap-style hooks" icon="container-storage" href="#wrap-style-hooks">
    Run around each model or tool call.
  </Card>
</CardGroup>

### Node-style hooks

Run sequentially at specific execution points. Use for logging, validation, and state updates.

**Available hooks:**

* `before_agent` - Before agent starts (once per invocation)
* `before_model` - Before each model call
* `after_model` - After each model response
* `after_agent` - After agent completes (once per invocation)

**Example:**

<Tabs>
  <Tab title="Decorator">
    ```python  theme={null}
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
  </Tab>

  <Tab title="Class">
    ```python  theme={null}
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

        def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
            print(f"Model returned: {state['messages'][-1].content}")
            return None
    ```
  </Tab>
</Tabs>

### Wrap-style hooks

Intercept execution and control when the handler is called. Use for retries, caching, and transformation.

You decide if the handler is called zero times (short-circuit), once (normal flow), or multiple times (retry logic).

**Available hooks:**

* `wrap_model_call` - Around each model call
* `wrap_tool_call` - Around each tool call

**Example:**

<Tabs>
  <Tab title="Decorator">
    ```python  theme={null}
    from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
    from typing import Callable


    @wrap_model_call
    def retry_model(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        for attempt in range(3):
            try:
                return handler(request)
            except Exception as e:
                if attempt == 2:
                    raise
                print(f"Retry {attempt + 1}/3 after error: {e}")
    ```
  </Tab>

  <Tab title="Class">
    ```python  theme={null}
    from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
    from typing import Callable

    class RetryMiddleware(AgentMiddleware):
        def __init__(self, max_retries: int = 3):
            super().__init__()
            self.max_retries = max_retries

        def wrap_model_call(
            self,
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse],
        ) -> ModelResponse:
            for attempt in range(self.max_retries):
                try:
                    return handler(request)
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise
                    print(f"Retry {attempt + 1}/{self.max_retries} after error: {e}")
    ```
  </Tab>
</Tabs>

## Create middleware

You can create middleware in two ways:

<CardGroup cols={2}>
  <Card title="Decorator-based middleware" icon="at" href="#decorator-based-middleware">
    Quick and simple for single-hook middleware. Use decorators to wrap individual functions.
  </Card>

  <Card title="Class-based middleware" icon="brackets-curly" href="#class-based-middleware">
    More powerful for complex middleware with multiple hooks or configuration.
  </Card>
</CardGroup>

### Decorator-based middleware

Quick and simple for single-hook middleware. Use decorators to wrap individual functions.

**Available decorators:**

**Node-style:**

* [`@before_agent`](https://reference.langchain.com/python/langchain/middleware/#langchain.agents.middleware.before_agent) - Runs before agent starts (once per invocation)
* [`@before_model`](https://reference.langchain.com/python/langchain/middleware/#langchain.agents.middleware.before_model) - Runs before each model call
* [`@after_model`](https://reference.langchain.com/python/langchain/middleware/#langchain.agents.middleware.after_model) - Runs after each model response
* [`@after_agent`](https://reference.langchain.com/python/langchain/middleware/#langchain.agents.middleware.after_agent) - Runs after agent completes (once per invocation)

**Wrap-style:**

* [`@wrap_model_call`](https://reference.langchain.com/python/langchain/middleware/#langchain.agents.middleware.wrap_model_call) - Wraps each model call with custom logic
* [`@wrap_tool_call`](https://reference.langchain.com/python/langchain/middleware/#langchain.agents.middleware.wrap_tool_call) - Wraps each tool call with custom logic

**Convenience:**

* [`@dynamic_prompt`](https://reference.langchain.com/python/langchain/middleware/#langchain.agents.middleware.dynamic_prompt) - Generates dynamic system prompts

**Example:**

```python  theme={null}
from langchain.agents.middleware import (
    before_model,
    wrap_model_call,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain.agents import create_agent
from langgraph.runtime import Runtime
from typing import Any, Callable


@before_model
def log_before_model(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    print(f"About to call model with {len(state['messages'])} messages")
    return None

@wrap_model_call
def retry_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    for attempt in range(3):
        try:
            return handler(request)
        except Exception as e:
            if attempt == 2:
                raise
            print(f"Retry {attempt + 1}/3 after error: {e}")

agent = create_agent(
    model="gpt-4o",
    middleware=[log_before_model, retry_model],
    tools=[...],
)
```

**When to use decorators:**

* Single hook needed
* No complex configuration
* Quick prototyping

### Class-based middleware

More powerful for complex middleware with multiple hooks or configuration. Use classes when you need to define both sync and async implementations for the same hook, or when you want to combine multiple hooks in a single middleware.

**Example:**

```python  theme={null}
from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langgraph.runtime import Runtime
from typing import Any, Callable

class LoggingMiddleware(AgentMiddleware):
    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        print(f"About to call model with {len(state['messages'])} messages")
        return None

    def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        print(f"Model returned: {state['messages'][-1].content}")
        return None

agent = create_agent(
    model="gpt-4o",
    middleware=[LoggingMiddleware()],
    tools=[...],
)
```

**When to use classes:**

* Defining both sync and async implementations for the same hook
* Multiple hooks needed in a single middleware
* Complex configuration required (e.g., configurable thresholds, custom models)
* Reuse across projects with init-time configuration

## Custom state schema

Middleware can extend the agent's state with custom properties. This enables middleware to:

* **Track state across execution**: Maintain counters, flags, or other values that persist throughout the agent's execution lifecycle

* **Share data between hooks**: Pass information from `before_model` to `after_model` or between different middleware instances

* **Implement cross-cutting concerns**: Add functionality like rate limiting, usage tracking, user context, or audit logging without modifying the core agent logic

* **Make conditional decisions**: Use accumulated state to determine whether to continue execution, jump to different nodes, or modify behavior dynamically

<Tabs>
  <Tab title="Decorator">
    ```python  theme={null}
    from langchain.agents import create_agent
    from langchain.messages import HumanMessage
    from langchain.agents.middleware import AgentState, before_model, after_model
    from typing_extensions import NotRequired
    from typing import Any
    from langgraph.runtime import Runtime


    class CustomState(AgentState):
        model_call_count: NotRequired[int]
        user_id: NotRequired[str]


    @before_model(state_schema=CustomState, can_jump_to=["end"])
    def check_call_limit(state: CustomState, runtime: Runtime) -> dict[str, Any] | None:
        count = state.get("model_call_count", 0)
        if count > 10:
            return {"jump_to": "end"}
        return None


    @after_model(state_schema=CustomState)
    def increment_counter(state: CustomState, runtime: Runtime) -> dict[str, Any] | None:
        return {"model_call_count": state.get("model_call_count", 0) + 1}


    agent = create_agent(
        model="gpt-4o",
        middleware=[check_call_limit, increment_counter],
        tools=[],
    )

    # Invoke with custom state
    result = agent.invoke({
        "messages": [HumanMessage("Hello")],
        "model_call_count": 0,
        "user_id": "user-123",
    })
    ```
  </Tab>

  <Tab title="Class">
    ```python  theme={null}
    from langchain.agents import create_agent
    from langchain.messages import HumanMessage
    from langchain.agents.middleware import AgentState, AgentMiddleware
    from typing_extensions import NotRequired
    from typing import Any


    class CustomState(AgentState):
        model_call_count: NotRequired[int]
        user_id: NotRequired[str]


    class CallCounterMiddleware(AgentMiddleware[CustomState]):
        state_schema = CustomState

        def before_model(self, state: CustomState, runtime) -> dict[str, Any] | None:
            count = state.get("model_call_count", 0)
            if count > 10:
                return {"jump_to": "end"}
            return None

        def after_model(self, state: CustomState, runtime) -> dict[str, Any] | None:
            return {"model_call_count": state.get("model_call_count", 0) + 1}


    agent = create_agent(
        model="gpt-4o",
        middleware=[CallCounterMiddleware()],
        tools=[],
    )

    # Invoke with custom state
    result = agent.invoke({
        "messages": [HumanMessage("Hello")],
        "model_call_count": 0,
        "user_id": "user-123",
    })
    ```
  </Tab>
</Tabs>

## Execution order

When using multiple middleware, understand how they execute:

```python  theme={null}
agent = create_agent(
    model="gpt-4o",
    middleware=[middleware1, middleware2, middleware3],
    tools=[...],
)
```

<Accordion title="Execution flow">
  **Before hooks run in order:**

  1. `middleware1.before_agent()`
  2. `middleware2.before_agent()`
  3. `middleware3.before_agent()`

  **Agent loop starts**

  4. `middleware1.before_model()`
  5. `middleware2.before_model()`
  6. `middleware3.before_model()`

  **Wrap hooks nest like function calls:**

  7. `middleware1.wrap_model_call()` → `middleware2.wrap_model_call()` → `middleware3.wrap_model_call()` → model

  **After hooks run in reverse order:**

  8. `middleware3.after_model()`
  9. `middleware2.after_model()`
  10. `middleware1.after_model()`

  **Agent loop ends**

  11. `middleware3.after_agent()`
  12. `middleware2.after_agent()`
  13. `middleware1.after_agent()`
</Accordion>

**Key rules:**

* `before_*` hooks: First to last
* `after_*` hooks: Last to first (reverse)
* `wrap_*` hooks: Nested (first middleware wraps all others)

## Agent jumps

To exit early from middleware, return a dictionary with `jump_to`:

**Available jump targets:**

* `'end'`: Jump to the end of the agent execution (or the first `after_agent` hook)
* `'tools'`: Jump to the tools node
* `'model'`: Jump to the model node (or the first `before_model` hook)

<Tabs>
  <Tab title="Decorator">
    ```python  theme={null}
    from langchain.agents.middleware import after_model, hook_config, AgentState
    from langchain.messages import AIMessage
    from langgraph.runtime import Runtime
    from typing import Any


    @after_model
    @hook_config(can_jump_to=["end"])
    def check_for_blocked(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        last_message = state["messages"][-1]
        if "BLOCKED" in last_message.content:
            return {
                "messages": [AIMessage("I cannot respond to that request.")],
                "jump_to": "end"
            }
        return None
    ```
  </Tab>

  <Tab title="Class">
    ```python  theme={null}
    from langchain.agents.middleware import AgentMiddleware, hook_config, AgentState
    from langchain.messages import AIMessage
    from langgraph.runtime import Runtime
    from typing import Any

    class BlockedContentMiddleware(AgentMiddleware):
        @hook_config(can_jump_to=["end"])
        def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
            last_message = state["messages"][-1]
            if "BLOCKED" in last_message.content:
                return {
                    "messages": [AIMessage("I cannot respond to that request.")],
                    "jump_to": "end"
                }
            return None
    ```
  </Tab>
</Tabs>

## Best practices

1. Keep middleware focused - each should do one thing well
2. Handle errors gracefully - don't let middleware errors crash the agent
3. **Use appropriate hook types**:
   * Node-style for sequential logic (logging, validation)
   * Wrap-style for control flow (retry, fallback, caching)
4. Clearly document any custom state properties
5. Unit test middleware independently before integrating
6. Consider execution order - place critical middleware first in the list
7. Use built-in middleware when possible

## Examples

### Dynamic model selection

<Tabs>
  <Tab title="Decorator">
    ```python  theme={null}
    from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
    from langchain.chat_models import init_chat_model
    from typing import Callable


    complex_model = init_chat_model("gpt-4o")
    simple_model = init_chat_model("gpt-4o-mini")

    @wrap_model_call
    def dynamic_model(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        # Use different model based on conversation length
        if len(request.messages) > 10:
            model = complex_model
        else:
            model = simple_model
        return handler(request.override(model=model))
    ```
  </Tab>

  <Tab title="Class">
    ```python  theme={null}
    from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
    from langchain.chat_models import init_chat_model
    from typing import Callable

    complex_model = init_chat_model("gpt-4o")
    simple_model = init_chat_model("gpt-4o-mini")

    class DynamicModelMiddleware(AgentMiddleware):
        def wrap_model_call(
            self,
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse],
        ) -> ModelResponse:
            # Use different model based on conversation length
            if len(request.messages) > 10:
                model = complex_model
            else:
                model = simple_model
            return handler(request.override(model=model))
    ```
  </Tab>
</Tabs>

### Tool call monitoring

<Tabs>
  <Tab title="Decorator">
    ```python  theme={null}
    from langchain.agents.middleware import wrap_tool_call
    from langchain.tools.tool_node import ToolCallRequest
    from langchain.messages import ToolMessage
    from langgraph.types import Command
    from typing import Callable


    @wrap_tool_call
    def monitor_tool(
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        print(f"Executing tool: {request.tool_call['name']}")
        print(f"Arguments: {request.tool_call['args']}")
        try:
            result = handler(request)
            print(f"Tool completed successfully")
            return result
        except Exception as e:
            print(f"Tool failed: {e}")
            raise
    ```
  </Tab>

  <Tab title="Class">
    ```python  theme={null}
    from langchain.tools.tool_node import ToolCallRequest
    from langchain.agents.middleware import AgentMiddleware
    from langchain.messages import ToolMessage
    from langgraph.types import Command
    from typing import Callable

    class ToolMonitoringMiddleware(AgentMiddleware):
        def wrap_tool_call(
            self,
            request: ToolCallRequest,
            handler: Callable[[ToolCallRequest], ToolMessage | Command],
        ) -> ToolMessage | Command:
            print(f"Executing tool: {request.tool_call['name']}")
            print(f"Arguments: {request.tool_call['args']}")
            try:
                result = handler(request)
                print(f"Tool completed successfully")
                return result
            except Exception as e:
                print(f"Tool failed: {e}")
                raise
    ```
  </Tab>
</Tabs>

### Dynamically selecting tools

Select relevant tools at runtime to improve performance and accuracy. This section covers filtering pre-registered tools. For registering tools that are discovered at runtime (e.g., from MCP servers), see [Runtime tool registration](/oss/python/langchain/agents#dynamic-tools).

**Benefits:**

* **Shorter prompts** - Reduce complexity by exposing only relevant tools
* **Better accuracy** - Models choose correctly from fewer options
* **Permission control** - Dynamically filter tools based on user access

<Tabs>
  <Tab title="Decorator">
    ```python  theme={null}
    from langchain.agents import create_agent
    from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
    from typing import Callable


    @wrap_model_call
    def select_tools(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Middleware to select relevant tools based on state/context."""
        # Select a small, relevant subset of tools based on state/context
        relevant_tools = select_relevant_tools(request.state, request.runtime)
        return handler(request.override(tools=relevant_tools))

    agent = create_agent(
        model="gpt-4o",
        tools=all_tools,  # All available tools need to be registered upfront
        middleware=[select_tools],
    )
    ```
  </Tab>

  <Tab title="Class">
    ```python  theme={null}
    from langchain.agents import create_agent
    from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
    from typing import Callable


    class ToolSelectorMiddleware(AgentMiddleware):
        def wrap_model_call(
            self,
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse],
        ) -> ModelResponse:
            """Middleware to select relevant tools based on state/context."""
            # Select a small, relevant subset of tools based on state/context
            relevant_tools = select_relevant_tools(request.state, request.runtime)
            return handler(request.override(tools=relevant_tools))

    agent = create_agent(
        model="gpt-4o",
        tools=all_tools,  # All available tools need to be registered upfront
        middleware=[ToolSelectorMiddleware()],
    )
    ```
  </Tab>
</Tabs>

### Working with system messages

Modify system messages in middleware using the `system_message` field on `ModelRequest`. The `system_message` field contains a [`SystemMessage`](https://reference.langchain.com/python/langchain/messages/#langchain.messages.SystemMessage) object (even if the agent was created with a string `system_prompt`).

**Example: Adding context to system message**

<Tabs>
  <Tab title="Decorator">
    ```python  theme={null}
    from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
    from langchain.messages import SystemMessage
    from typing import Callable


    @wrap_model_call
    def add_context(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        # Always work with content blocks
        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": "Additional context."}
        ]
        new_system_message = SystemMessage(content=new_content)
        return handler(request.override(system_message=new_system_message))
    ```
  </Tab>

  <Tab title="Class">
    ```python  theme={null}
    from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
    from langchain.messages import SystemMessage
    from typing import Callable


    class ContextMiddleware(AgentMiddleware):
        def wrap_model_call(
            self,
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse],
        ) -> ModelResponse:
            # Always work with content blocks
            new_content = list(request.system_message.content_blocks) + [
                {"type": "text", "text": "Additional context."}
            ]
            new_system_message = SystemMessage(content=new_content)
            return handler(request.override(system_message=new_system_message))
    ```
  </Tab>
</Tabs>

**Example: Working with cache control (Anthropic)**

When working with Anthropic models, you can use structured content blocks with cache control directives to cache large system prompts:

<Tabs>
  <Tab title="Decorator">
    ```python  theme={null}
    from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
    from langchain.messages import SystemMessage
    from typing import Callable


    @wrap_model_call
    def add_cached_context(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        # Always work with content blocks
        new_content = list(request.system_message.content_blocks) + [
            {
                "type": "text",
                "text": "Here is a large document to analyze:\n\n<document>...</document>",
                # content up until this point is cached
                "cache_control": {"type": "ephemeral"}
            }
        ]

        new_system_message = SystemMessage(content=new_content)
        return handler(request.override(system_message=new_system_message))
    ```
  </Tab>

  <Tab title="Class">
    ```python  theme={null}
    from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
    from langchain.messages import SystemMessage
    from typing import Callable


    class CachedContextMiddleware(AgentMiddleware):
        def wrap_model_call(
            self,
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse],
        ) -> ModelResponse:
            # Always work with content blocks
            new_content = list(request.system_message.content_blocks) + [
                {
                    "type": "text",
                    "text": "Here is a large document to analyze:\n\n<document>...</document>",
                    "cache_control": {"type": "ephemeral"}  # This content will be cached
                }
            ]

            new_system_message = SystemMessage(content=new_content)
            return handler(request.override(system_message=new_system_message))
    ```
  </Tab>
</Tabs>

**Notes:**

* `ModelRequest.system_message` is always a [`SystemMessage`](https://reference.langchain.com/python/langchain/messages/#langchain.messages.SystemMessage) object, even if the agent was created with `system_prompt="string"`
* Use `SystemMessage.content_blocks` to access content as a list of blocks, regardless of whether the original content was a string or list
* When modifying system messages, use `content_blocks` and append new blocks to preserve existing structure
* You can pass [`SystemMessage`](https://reference.langchain.com/python/langchain/messages/#langchain.messages.SystemMessage) objects directly to `create_agent`'s `system_prompt` parameter for advanced use cases like cache control

## Additional resources

* [Middleware API reference](https://reference.langchain.com/python/langchain/middleware/)
* [Built-in middleware](/oss/python/langchain/middleware/built-in)
* [Testing agents](/oss/python/langchain/test)

***

<Callout icon="pen-to-square" iconType="regular">
  [Edit this page on GitHub](https://github.com/langchain-ai/docs/edit/main/src/oss/langchain/middleware/custom.mdx) or [file an issue](https://github.com/langchain-ai/docs/issues/new/choose).
</Callout>

<Tip icon="terminal" iconType="regular">
  [Connect these docs](/use-these-docs) to Claude, VSCode, and more via MCP for real-time answers.
</Tip>
