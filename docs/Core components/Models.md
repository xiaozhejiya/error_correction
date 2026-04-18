> ## Documentation Index
> Fetch the complete documentation index at: https://docs.langchain.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Models

[LLMs](https://en.wikipedia.org/wiki/Large_language_model) are powerful AI tools that can interpret and generate text like humans. They're versatile enough to write content, translate languages, summarize, and answer questions without needing specialized training for each task.

In addition to text generation, many models support:

* <Icon icon="hammer" size={16} /> [Tool calling](#tool-calling) - calling external tools (like databases queries or API calls) and use results in their responses.
* <Icon icon="shapes" size={16} /> [Structured output](#structured-output) - where the model's response is constrained to follow a defined format.
* <Icon icon="image" size={16} /> [Multimodality](#multimodal) - process and return data other than text, such as images, audio, and video.
* <Icon icon="brain" size={16} /> [Reasoning](#reasoning) - models perform multi-step reasoning to arrive at a conclusion.

Models are the reasoning engine of [agents](/oss/python/langchain/agents). They drive the agent's decision-making process, determining which tools to call, how to interpret results, and when to provide a final answer.

The quality and capabilities of the model you choose directly impact your agent's baseline reliability and performance. Different models excel at different tasks - some are better at following complex instructions, others at structured reasoning, and some support larger context windows for handling more information.

LangChain's standard model interfaces give you access to many different provider integrations, which makes it easy to experiment with and switch between models to find the best fit for your use case.

<Info>
  For provider-specific integration information and capabilities, see the provider's [chat model page](/oss/python/integrations/chat).
</Info>

## Basic usage

Models can be utilized in two ways:

1. **With agents** - Models can be dynamically specified when creating an [agent](/oss/python/langchain/agents#model).
2. **Standalone** - Models can be called directly (outside of the agent loop) for tasks like text generation, classification, or extraction without the need for an agent framework.

The same model interface works in both contexts, which gives you the flexibility to start simple and scale up to more complex agent-based workflows as needed.

### Initialize a model

The easiest way to get started with a standalone model in LangChain is to use [`init_chat_model`](https://reference.langchain.com/python/langchain/models/#langchain.chat_models.init_chat_model) to initialize one from a chat model provider of your choice (examples below):

<Tabs>
  <Tab title="OpenAI">
    👉 Read the [OpenAI chat model integration docs](/oss/python/integrations/chat/openai/)

    ```shell  theme={null}
    pip install -U "langchain[openai]"
    ```

    <CodeGroup>
      ```python init_chat_model theme={null}
      import os
      from langchain.chat_models import init_chat_model

      os.environ["OPENAI_API_KEY"] = "sk-..."

      model = init_chat_model("gpt-4.1")
      ```

      ```python Model Class theme={null}
      import os
      from langchain_openai import ChatOpenAI

      os.environ["OPENAI_API_KEY"] = "sk-..."

      model = ChatOpenAI(model="gpt-4.1")
      ```
    </CodeGroup>
  </Tab>

  <Tab title="Anthropic">
    👉 Read the [Anthropic chat model integration docs](/oss/python/integrations/chat/anthropic/)

    ```shell  theme={null}
    pip install -U "langchain[anthropic]"
    ```

    <CodeGroup>
      ```python init_chat_model theme={null}
      import os
      from langchain.chat_models import init_chat_model

      os.environ["ANTHROPIC_API_KEY"] = "sk-..."

      model = init_chat_model("claude-sonnet-4-5-20250929")
      ```

      ```python Model Class theme={null}
      import os
      from langchain_anthropic import ChatAnthropic

      os.environ["ANTHROPIC_API_KEY"] = "sk-..."

      model = ChatAnthropic(model="claude-sonnet-4-5-20250929")
      ```
    </CodeGroup>
  </Tab>

  <Tab title="Azure">
    👉 Read the [Azure chat model integration docs](/oss/python/integrations/chat/azure_chat_openai/)

    ```shell  theme={null}
    pip install -U "langchain[openai]"
    ```

    <CodeGroup>
      ```python init_chat_model theme={null}
      import os
      from langchain.chat_models import init_chat_model

      os.environ["AZURE_OPENAI_API_KEY"] = "..."
      os.environ["AZURE_OPENAI_ENDPOINT"] = "..."
      os.environ["OPENAI_API_VERSION"] = "2025-03-01-preview"

      model = init_chat_model(
          "azure_openai:gpt-4.1",
          azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
      )
      ```

      ```python Model Class theme={null}
      import os
      from langchain_openai import AzureChatOpenAI

      os.environ["AZURE_OPENAI_API_KEY"] = "..."
      os.environ["AZURE_OPENAI_ENDPOINT"] = "..."
      os.environ["OPENAI_API_VERSION"] = "2025-03-01-preview"

      model = AzureChatOpenAI(
          model="gpt-4.1",
          azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"]
      )
      ```
    </CodeGroup>
  </Tab>

  <Tab title="Google Gemini">
    👉 Read the [Google GenAI chat model integration docs](/oss/python/integrations/chat/google_generative_ai/)

    ```shell  theme={null}
    pip install -U "langchain[google-genai]"
    ```

    <CodeGroup>
      ```python init_chat_model theme={null}
      import os
      from langchain.chat_models import init_chat_model

      os.environ["GOOGLE_API_KEY"] = "..."

      model = init_chat_model("google_genai:gemini-2.5-flash-lite")
      ```

      ```python Model Class theme={null}
      import os
      from langchain_google_genai import ChatGoogleGenerativeAI

      os.environ["GOOGLE_API_KEY"] = "..."

      model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
      ```
    </CodeGroup>
  </Tab>

  <Tab title="AWS Bedrock">
    👉 Read the [AWS Bedrock chat model integration docs](/oss/python/integrations/chat/bedrock/)

    ```shell  theme={null}
    pip install -U "langchain[aws]"
    ```

    <CodeGroup>
      ```python init_chat_model theme={null}
      from langchain.chat_models import init_chat_model

      # Follow the steps here to configure your credentials:
      # https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html

      model = init_chat_model(
          "anthropic.claude-3-5-sonnet-20240620-v1:0",
          model_provider="bedrock_converse",
      )
      ```

      ```python Model Class theme={null}
      from langchain_aws import ChatBedrock

      model = ChatBedrock(model="anthropic.claude-3-5-sonnet-20240620-v1:0")
      ```
    </CodeGroup>
  </Tab>

  <Tab title="HuggingFace">
    👉 Read the [HuggingFace chat model integration docs](/oss/python/integrations/chat/huggingface/)

    ```shell  theme={null}
    pip install -U "langchain[huggingface]"
    ```

    <CodeGroup>
      ```python init_chat_model theme={null}
      import os
      from langchain.chat_models import init_chat_model

      os.environ["HUGGINGFACEHUB_API_TOKEN"] = "hf_..."

      model = init_chat_model(
          "microsoft/Phi-3-mini-4k-instruct",
          model_provider="huggingface",
          temperature=0.7,
          max_tokens=1024,
      )
      ```

      ```python Model Class theme={null}
      import os
      from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

      os.environ["HUGGINGFACEHUB_API_TOKEN"] = "hf_..."

      llm = HuggingFaceEndpoint(
          repo_id="microsoft/Phi-3-mini-4k-instruct",
          temperature=0.7,
          max_length=1024,
      )
      model = ChatHuggingFace(llm=llm)
      ```
    </CodeGroup>
  </Tab>
</Tabs>

```python  theme={null}
response = model.invoke("Why do parrots talk?")
```

See [`init_chat_model`](https://reference.langchain.com/python/langchain/models/#langchain.chat_models.init_chat_model) for more detail, including information on how to pass model [parameters](#parameters).

### Supported models

LangChain supports all major model providers, including OpenAI, Anthropic, Google, Azure, AWS Bedrock, and more. Each provider offers a variety of models with different capabilities. For a full list of supported models in LangChain, see the [integrations page](/oss/python/integrations/providers/overview).

### Key methods

<Card title="Invoke" href="#invoke" icon="paper-plane" arrow="true" horizontal>
  The model takes messages as input and outputs messages after generating a complete response.
</Card>

<Card title="Stream" href="#stream" icon="tower-broadcast" arrow="true" horizontal>
  Invoke the model, but stream the output as it is generated in real-time.
</Card>

<Card title="Batch" href="#batch" icon="grip" arrow="true" horizontal>
  Send multiple requests to a model in a batch for more efficient processing.
</Card>

<Info>
  In addition to chat models, LangChain provides support for other adjacent technologies, such as embedding models and vector stores. See the [integrations page](/oss/python/integrations/providers/overview) for details.
</Info>

## Parameters

A chat model takes parameters that can be used to configure its behavior. The full set of supported parameters varies by model and provider, but standard ones include:

<ParamField body="model" type="string" required>
  The name or identifier of the specific model you want to use with a provider. You can also specify both the model and its provider in a single argument using the '{model_provider}:{model}' format, for example, 'openai:o1'.
</ParamField>

<ParamField body="api_key" type="string">
  The key required for authenticating with the model's provider. This is usually issued when you sign up for access to the model. Often accessed by setting an <Tooltip tip="A variable whose value is set outside the program, typically through functionality built into the operating system or microservice.">environment variable</Tooltip>.
</ParamField>

<ParamField body="temperature" type="number">
  Controls the randomness of the model's output. A higher number makes responses more creative; lower ones make them more deterministic.
</ParamField>

<ParamField body="max_tokens" type="number">
  Limits the total number of <Tooltip tip="The basic unit that a model reads and generates. Providers may define them differently, but in general, they can represent a whole or part of word.">tokens</Tooltip> in the response, effectively controlling how long the output can be.
</ParamField>

<ParamField body="timeout" type="number">
  The maximum time (in seconds) to wait for a response from the model before canceling the request.
</ParamField>

<ParamField body="max_retries" type="number">
  The maximum number of attempts the system will make to resend a request if it fails due to issues like network timeouts or rate limits.
</ParamField>

Using [`init_chat_model`](https://reference.langchain.com/python/langchain/models/#langchain.chat_models.init_chat_model), pass these parameters as inline <Tooltip tip="Arbitrary keyword arguments" cta="Learn more" href="https://www.w3schools.com/python/python_args_kwargs.asp">`**kwargs`</Tooltip>:

```python Initialize using model parameters theme={null}
model = init_chat_model(
    "claude-sonnet-4-5-20250929",
    # Kwargs passed to the model:
    temperature=0.7,
    timeout=30,
    max_tokens=1000,
)
```

<Info>
  Each chat model integration may have additional params used to control provider-specific functionality.

  For example, [`ChatOpenAI`](https://reference.langchain.com/python/integrations/langchain_openai/ChatOpenAI) has `use_responses_api` to dictate whether to use the OpenAI Responses or Completions API.

  To find all the parameters supported by a given chat model, head to the [chat model integrations](/oss/python/integrations/chat) page.
</Info>

***

## Invocation

A chat model must be invoked to generate an output. There are three primary invocation methods, each suited to different use cases.

### Invoke

The most straightforward way to call a model is to use [`invoke()`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.invoke) with a single message or a list of messages.

```python Single message theme={null}
response = model.invoke("Why do parrots have colorful feathers?")
print(response)
```

A list of messages can be provided to a chat model to represent conversation history. Each message has a role that models use to indicate who sent the message in the conversation.

See the [messages](/oss/python/langchain/messages) guide for more detail on roles, types, and content.

```python Dictionary format theme={null}
conversation = [
    {"role": "system", "content": "You are a helpful assistant that translates English to French."},
    {"role": "user", "content": "Translate: I love programming."},
    {"role": "assistant", "content": "J'adore la programmation."},
    {"role": "user", "content": "Translate: I love building applications."}
]

response = model.invoke(conversation)
print(response)  # AIMessage("J'adore créer des applications.")
```

```python Message objects theme={null}
from langchain.messages import HumanMessage, AIMessage, SystemMessage

conversation = [
    SystemMessage("You are a helpful assistant that translates English to French."),
    HumanMessage("Translate: I love programming."),
    AIMessage("J'adore la programmation."),
    HumanMessage("Translate: I love building applications.")
]

response = model.invoke(conversation)
print(response)  # AIMessage("J'adore créer des applications.")
```

<Info>
  If the return type of your invocation is a string, ensure that you are using a chat model as opposed to a LLM. Legacy, text-completion LLMs return strings directly. LangChain chat models are prefixed with "Chat", e.g., [`ChatOpenAI`](https://reference.langchain.com/python/integrations/langchain_openai/ChatOpenAI)(/oss/integrations/chat/openai).
</Info>

### Stream

Most models can stream their output content while it is being generated. By displaying output progressively, streaming significantly improves user experience, particularly for longer responses.

Calling [`stream()`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.stream) returns an <Tooltip tip="An object that progressively provides access to each item of a collection, in order.">iterator</Tooltip> that yields output chunks as they are produced. You can use a loop to process each chunk in real-time:

<CodeGroup>
  ```python Basic text streaming theme={null}
  for chunk in model.stream("Why do parrots have colorful feathers?"):
      print(chunk.text, end="|", flush=True)
  ```

  ```python Stream tool calls, reasoning, and other content theme={null}
  for chunk in model.stream("What color is the sky?"):
      for block in chunk.content_blocks:
          if block["type"] == "reasoning" and (reasoning := block.get("reasoning")):
              print(f"Reasoning: {reasoning}")
          elif block["type"] == "tool_call_chunk":
              print(f"Tool call chunk: {block}")
          elif block["type"] == "text":
              print(block["text"])
          else:
              ...
  ```
</CodeGroup>

As opposed to [`invoke()`](#invoke), which returns a single [`AIMessage`](https://reference.langchain.com/python/langchain/messages/#langchain.messages.AIMessage) after the model has finished generating its full response, `stream()` returns multiple [`AIMessageChunk`](https://reference.langchain.com/python/langchain/messages/#langchain.messages.AIMessageChunk) objects, each containing a portion of the output text. Importantly, each chunk in a stream is designed to be gathered into a full message via summation:

```python Construct an AIMessage theme={null}
full = None  # None | AIMessageChunk
for chunk in model.stream("What color is the sky?"):
    full = chunk if full is None else full + chunk
    print(full.text)

# The
# The sky
# The sky is
# The sky is typically
# The sky is typically blue
# ...

print(full.content_blocks)
# [{"type": "text", "text": "The sky is typically blue..."}]
```

The resulting message can be treated the same as a message that was generated with [`invoke()`](#invoke) – for example, it can be aggregated into a message history and passed back to the model as conversational context.

<Warning>
  Streaming only works if all steps in the program know how to process a stream of chunks. For instance, an application that isn't streaming-capable would be one that needs to store the entire output in memory before it can be processed.
</Warning>

<Accordion title="Advanced streaming topics">
  <Accordion title="Streaming events">
    LangChain chat models can also stream semantic events using `astream_events()`.

    This simplifies filtering based on event types and other metadata, and will aggregate the full message in the background. See below for an example.

    ```python  theme={null}
    async for event in model.astream_events("Hello"):

        if event["event"] == "on_chat_model_start":
            print(f"Input: {event['data']['input']}")

        elif event["event"] == "on_chat_model_stream":
            print(f"Token: {event['data']['chunk'].text}")

        elif event["event"] == "on_chat_model_end":
            print(f"Full message: {event['data']['output'].text}")

        else:
            pass
    ```

    ```txt  theme={null}
    Input: Hello
    Token: Hi
    Token:  there
    Token: !
    Token:  How
    Token:  can
    Token:  I
    ...
    Full message: Hi there! How can I help today?
    ```

    <Tip>
      See the [`astream_events()`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.astream_events) reference for event types and other details.
    </Tip>
  </Accordion>

  <Accordion title="&#x22;Auto-streaming&#x22; chat models">
    LangChain simplifies streaming from chat models by automatically enabling streaming mode in certain cases, even when you're not explicitly calling the streaming methods. This is particularly useful when you use the non-streaming invoke method but still want to stream the entire application, including intermediate results from the chat model.

    In [LangGraph agents](/oss/python/langchain/agents), for example, you can call `model.invoke()` within nodes, but LangChain will automatically delegate to streaming if running in a streaming mode.

    #### How it works

    When you `invoke()` a chat model, LangChain will automatically switch to an internal streaming mode if it detects that you are trying to stream the overall application. The result of the invocation will be the same as far as the code that was using invoke is concerned; however, while the chat model is being streamed, LangChain will take care of invoking [`on_llm_new_token`](https://reference.langchain.com/python/langchain_core/callbacks/#langchain_core.callbacks.base.AsyncCallbackHandler.on_llm_new_token) events in LangChain's callback system.

    Callback events allow LangGraph `stream()` and `astream_events()` to surface the chat model's output in real-time.
  </Accordion>
</Accordion>

### Batch

Batching a collection of independent requests to a model can significantly improve performance and reduce costs, as the processing can be done in parallel:

```python Batch theme={null}
responses = model.batch([
    "Why do parrots have colorful feathers?",
    "How do airplanes fly?",
    "What is quantum computing?"
])
for response in responses:
    print(response)
```

<Note>
  This section describes a chat model method [`batch()`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.batch), which parallelizes model calls client-side.

  It is **distinct** from batch APIs supported by inference providers, such as [OpenAI](https://platform.openai.com/docs/guides/batch) or [Anthropic](https://platform.claude.com/docs/en/build-with-claude/batch-processing#message-batches-api).
</Note>

By default, [`batch()`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.batch) will only return the final output for the entire batch. If you want to receive the output for each individual input as it finishes generating, you can stream results with [`batch_as_completed()`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.batch_as_completed):

```python Yield batch responses upon completion theme={null}
for response in model.batch_as_completed([
    "Why do parrots have colorful feathers?",
    "How do airplanes fly?",
    "What is quantum computing?"
]):
    print(response)
```

<Note>
  When using [`batch_as_completed()`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.batch_as_completed), results may arrive out of order. Each includes the input index for matching to reconstruct the original order as needed.
</Note>

<Tip>
  When processing a large number of inputs using [`batch()`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.batch) or [`batch_as_completed()`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.batch_as_completed), you may want to control the maximum number of parallel calls. This can be done by setting the [`max_concurrency`](https://reference.langchain.com/python/langchain_core/runnables/#langchain_core.runnables.RunnableConfig.max_concurrency) attribute in the [`RunnableConfig`](https://reference.langchain.com/python/langchain_core/runnables/#langchain_core.runnables.RunnableConfig) dictionary.

  ```python Batch with max concurrency theme={null}
  model.batch(
      list_of_inputs,
      config={
          'max_concurrency': 5,  # Limit to 5 parallel calls
      }
  )
  ```

  See the [`RunnableConfig`](https://reference.langchain.com/python/langchain_core/runnables/#langchain_core.runnables.RunnableConfig) reference for a full list of supported attributes.
</Tip>

For more details on batching, see the [reference](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.batch).

***

## Tool calling

Models can request to call tools that perform tasks such as fetching data from a database, searching the web, or running code. Tools are pairings of:

1. A schema, including the name of the tool, a description, and/or argument definitions (often a JSON schema)
2. A function or <Tooltip tip="A method that can suspend execution and resume at a later time">coroutine</Tooltip> to execute.

<Note>
  You may hear the term "function calling". We use this interchangeably with "tool calling".
</Note>

Here's the basic tool calling flow between a user and a model:

```mermaid  theme={null}
sequenceDiagram
    participant U as User
    participant M as Model
    participant T as Tools

    U->>M: "What's the weather in SF and NYC?"
    M->>M: Analyze request & decide tools needed

    par Parallel Tool Calls
        M->>T: get_weather("San Francisco")
        M->>T: get_weather("New York")
    end

    par Tool Execution
        T-->>M: SF weather data
        T-->>M: NYC weather data
    end

    M->>M: Process results & generate response
    M->>U: "SF: 72°F sunny, NYC: 68°F cloudy"
```

To make tools that you have defined available for use by a model, you must bind them using [`bind_tools`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.bind_tools). In subsequent invocations, the model can choose to call any of the bound tools as needed.

Some model providers offer <Tooltip tip="Tools that are executed server-side, such as web search and code interpreters">built-in tools</Tooltip> that can be enabled via model or invocation parameters (e.g. [`ChatOpenAI`](/oss/python/integrations/chat/openai), [`ChatAnthropic`](/oss/python/integrations/chat/anthropic)). Check the respective [provider reference](/oss/python/integrations/providers/overview) for details.

<Tip>
  See the [tools guide](/oss/python/langchain/tools) for details and other options for creating tools.
</Tip>

```python Binding user tools theme={null}
from langchain.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get the weather at a location."""
    return f"It's sunny in {location}."


model_with_tools = model.bind_tools([get_weather])  # [!code highlight]

response = model_with_tools.invoke("What's the weather like in Boston?")
for tool_call in response.tool_calls:
    # View tool calls made by the model
    print(f"Tool: {tool_call['name']}")
    print(f"Args: {tool_call['args']}")
```

When binding user-defined tools, the model's response includes a **request** to execute a tool. When using a model separately from an [agent](/oss/python/langchain/agents), it is up to you to execute the requested tool and return the result back to the model for use in subsequent reasoning. When using an [agent](/oss/python/langchain/agents), the agent loop will handle the tool execution loop for you.

Below, we show some common ways you can use tool calling.

<AccordionGroup>
  <Accordion title="Tool execution loop" icon="arrow-rotate-right">
    When a model returns tool calls, you need to execute the tools and pass the results back to the model. This creates a conversation loop where the model can use tool results to generate its final response. LangChain includes [agent](/oss/python/langchain/agents) abstractions that handle this orchestration for you.

    Here's a simple example of how to do this:

    ```python Tool execution loop theme={null}
    # Bind (potentially multiple) tools to the model
    model_with_tools = model.bind_tools([get_weather])

    # Step 1: Model generates tool calls
    messages = [{"role": "user", "content": "What's the weather in Boston?"}]
    ai_msg = model_with_tools.invoke(messages)
    messages.append(ai_msg)

    # Step 2: Execute tools and collect results
    for tool_call in ai_msg.tool_calls:
        # Execute the tool with the generated arguments
        tool_result = get_weather.invoke(tool_call)
        messages.append(tool_result)

    # Step 3: Pass results back to model for final response
    final_response = model_with_tools.invoke(messages)
    print(final_response.text)
    # "The current weather in Boston is 72°F and sunny."
    ```

    Each [`ToolMessage`](https://reference.langchain.com/python/langchain/messages/#langchain.messages.ToolMessage) returned by the tool includes a `tool_call_id` that matches the original tool call, helping the model correlate results with requests.
  </Accordion>

  <Accordion title="Forcing tool calls" icon="asterisk">
    By default, the model has the freedom to choose which bound tool to use based on the user's input. However, you might want to force choosing a tool, ensuring the model uses either a particular tool or **any** tool from a given list:

    <CodeGroup>
      ```python Force use of any tool theme={null}
      model_with_tools = model.bind_tools([tool_1], tool_choice="any")
      ```

      ```python Force use of specific tools theme={null}
      model_with_tools = model.bind_tools([tool_1], tool_choice="tool_1")
      ```
    </CodeGroup>
  </Accordion>

  <Accordion title="Parallel tool calls" icon="layer-group">
    Many models support calling multiple tools in parallel when appropriate. This allows the model to gather information from different sources simultaneously.

    ```python Parallel tool calls theme={null}
    model_with_tools = model.bind_tools([get_weather])

    response = model_with_tools.invoke(
        "What's the weather in Boston and Tokyo?"
    )


    # The model may generate multiple tool calls
    print(response.tool_calls)
    # [
    #   {'name': 'get_weather', 'args': {'location': 'Boston'}, 'id': 'call_1'},
    #   {'name': 'get_weather', 'args': {'location': 'Tokyo'}, 'id': 'call_2'},
    # ]


    # Execute all tools (can be done in parallel with async)
    results = []
    for tool_call in response.tool_calls:
        if tool_call['name'] == 'get_weather':
            result = get_weather.invoke(tool_call)
        ...
        results.append(result)
    ```

    The model intelligently determines when parallel execution is appropriate based on the independence of the requested operations.

    <Tip>
      Most models supporting tool calling enable parallel tool calls by default. Some (including [OpenAI](/oss/python/integrations/chat/openai) and [Anthropic](/oss/python/integrations/chat/anthropic)) allow you to disable this feature. To do this, set `parallel_tool_calls=False`:

      ```python  theme={null}
      model.bind_tools([get_weather], parallel_tool_calls=False)
      ```
    </Tip>
  </Accordion>

  <Accordion title="Streaming tool calls" icon="rss">
    When streaming responses, tool calls are progressively built through [`ToolCallChunk`](https://reference.langchain.com/python/langchain/messages/#langchain.messages.ToolCallChunk). This allows you to see tool calls as they're being generated rather than waiting for the complete response.

    ```python Streaming tool calls theme={null}
    for chunk in model_with_tools.stream(
        "What's the weather in Boston and Tokyo?"
    ):
        # Tool call chunks arrive progressively
        for tool_chunk in chunk.tool_call_chunks:
            if name := tool_chunk.get("name"):
                print(f"Tool: {name}")
            if id_ := tool_chunk.get("id"):
                print(f"ID: {id_}")
            if args := tool_chunk.get("args"):
                print(f"Args: {args}")

    # Output:
    # Tool: get_weather
    # ID: call_SvMlU1TVIZugrFLckFE2ceRE
    # Args: {"lo
    # Args: catio
    # Args: n": "B
    # Args: osto
    # Args: n"}
    # Tool: get_weather
    # ID: call_QMZdy6qInx13oWKE7KhuhOLR
    # Args: {"lo
    # Args: catio
    # Args: n": "T
    # Args: okyo
    # Args: "}
    ```

    You can accumulate chunks to build complete tool calls:

    ```python Accumulate tool calls theme={null}
    gathered = None
    for chunk in model_with_tools.stream("What's the weather in Boston?"):
        gathered = chunk if gathered is None else gathered + chunk
        print(gathered.tool_calls)
    ```
  </Accordion>
</AccordionGroup>

***

## Structured output

Models can be requested to provide their response in a format matching a given schema. This is useful for ensuring the output can be easily parsed and used in subsequent processing. LangChain supports multiple schema types and methods for enforcing structured output.

<Tip>
  To learn about structured output, see [Structured output](/oss/python/langchain/structured-output).
</Tip>

<Tabs>
  <Tab title="Pydantic">
    [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/#basic-model-usage) provide the richest feature set with field validation, descriptions, and nested structures.

    ```python  theme={null}
    from pydantic import BaseModel, Field

    class Movie(BaseModel):
        """A movie with details."""
        title: str = Field(..., description="The title of the movie")
        year: int = Field(..., description="The year the movie was released")
        director: str = Field(..., description="The director of the movie")
        rating: float = Field(..., description="The movie's rating out of 10")

    model_with_structure = model.with_structured_output(Movie)
    response = model_with_structure.invoke("Provide details about the movie Inception")
    print(response)  # Movie(title="Inception", year=2010, director="Christopher Nolan", rating=8.8)
    ```
  </Tab>

  <Tab title="TypedDict">
    Python's `TypedDict` provides a simpler alternative to Pydantic models, ideal when you don't need runtime validation.

    ```python  theme={null}
    from typing_extensions import TypedDict, Annotated

    class MovieDict(TypedDict):
        """A movie with details."""
        title: Annotated[str, ..., "The title of the movie"]
        year: Annotated[int, ..., "The year the movie was released"]
        director: Annotated[str, ..., "The director of the movie"]
        rating: Annotated[float, ..., "The movie's rating out of 10"]

    model_with_structure = model.with_structured_output(MovieDict)
    response = model_with_structure.invoke("Provide details about the movie Inception")
    print(response)  # {'title': 'Inception', 'year': 2010, 'director': 'Christopher Nolan', 'rating': 8.8}
    ```
  </Tab>

  <Tab title="JSON Schema">
    Provide a [JSON Schema](https://json-schema.org/understanding-json-schema/about) for maximum control and interoperability.

    ```python  theme={null}
    import json

    json_schema = {
        "title": "Movie",
        "description": "A movie with details",
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The title of the movie"
            },
            "year": {
                "type": "integer",
                "description": "The year the movie was released"
            },
            "director": {
                "type": "string",
                "description": "The director of the movie"
            },
            "rating": {
                "type": "number",
                "description": "The movie's rating out of 10"
            }
        },
        "required": ["title", "year", "director", "rating"]
    }

    model_with_structure = model.with_structured_output(
        json_schema,
        method="json_schema",
    )
    response = model_with_structure.invoke("Provide details about the movie Inception")
    print(response)  # {'title': 'Inception', 'year': 2010, ...}
    ```
  </Tab>
</Tabs>

<Note>
  **Key considerations for structured output**

  * **Method parameter**: Some providers support different methods for structured output:
    * `'json_schema'`: Uses dedicated structured output features offered by the provider.
    * `'function_calling'`: Derives structured output by forcing a [tool call](#tool-calling) that follows the given schema.
    * `'json_mode'`: A precursor to `'json_schema'` offered by some providers. Generates valid JSON, but the schema must be described in the prompt.
  * **Include raw**: Set `include_raw=True` to get both the parsed output and the raw AI message.
  * **Validation**: Pydantic models provide automatic validation. `TypedDict` and JSON Schema require manual validation.

  See your [provider's integration page](/oss/python/integrations/providers/overview) for supported methods and configuration options.
</Note>

<Accordion title="Example: Message output alongside parsed structure">
  It can be useful to return the raw [`AIMessage`](https://reference.langchain.com/python/langchain/messages/#langchain.messages.AIMessage) object alongside the parsed representation to access response metadata such as [token counts](#token-usage). To do this, set [`include_raw=True`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.with_structured_output\(include_raw\)) when calling [`with_structured_output`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.with_structured_output):

  ```python  theme={null}
  from pydantic import BaseModel, Field

  class Movie(BaseModel):
      """A movie with details."""
      title: str = Field(..., description="The title of the movie")
      year: int = Field(..., description="The year the movie was released")
      director: str = Field(..., description="The director of the movie")
      rating: float = Field(..., description="The movie's rating out of 10")

  model_with_structure = model.with_structured_output(Movie, include_raw=True)  # [!code highlight]
  response = model_with_structure.invoke("Provide details about the movie Inception")
  response
  # {
  #     "raw": AIMessage(...),
  #     "parsed": Movie(title=..., year=..., ...),
  #     "parsing_error": None,
  # }
  ```
</Accordion>

<Accordion title="Example: Nested structures">
  Schemas can be nested:

  <CodeGroup>
    ```python Pydantic BaseModel theme={null}
    from pydantic import BaseModel, Field

    class Actor(BaseModel):
        name: str
        role: str

    class MovieDetails(BaseModel):
        title: str
        year: int
        cast: list[Actor]
        genres: list[str]
        budget: float | None = Field(None, description="Budget in millions USD")

    model_with_structure = model.with_structured_output(MovieDetails)
    ```

    ```python TypedDict theme={null}
    from typing_extensions import Annotated, TypedDict

    class Actor(TypedDict):
        name: str
        role: str

    class MovieDetails(TypedDict):
        title: str
        year: int
        cast: list[Actor]
        genres: list[str]
        budget: Annotated[float | None, ..., "Budget in millions USD"]

    model_with_structure = model.with_structured_output(MovieDetails)
    ```
  </CodeGroup>
</Accordion>

***

## Advanced topics

### Model profiles

<Info>
  Model profiles require `langchain>=1.1`.
</Info>

LangChain chat models can expose a dictionary of supported features and capabilities through a `.profile` attribute:

```python  theme={null}
model.profile
# {
#   "max_input_tokens": 400000,
#   "image_inputs": True,
#   "reasoning_output": True,
#   "tool_calling": True,
#   ...
# }
```

Refer to the full set of fields in the [API reference](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.BaseChatModel.profile).

Much of the model profile data is powered by the [models.dev](https://github.com/sst/models.dev) project, an open source initiative that provides model capability data. These data are augmented with additional fields for purposes of use with LangChain. These augmentations are kept aligned with the upstream project as it evolves.

Model profile data allow applications to work around model capabilities dynamically. For example:

1. [Summarization middleware](/oss/python/langchain/middleware/built-in#summarization) can trigger summarization based on a model's context window size.
2. [Structured output](/oss/python/langchain/structured-output) strategies in `create_agent` can be inferred automatically (e.g., by checking support for native structured output features).
3. Model inputs can be gated based on supported [modalities](#multimodal) and maximum input tokens.

<Accordion title="Updating or overwriting profile data">
  Model profile data can be changed if it is missing, stale, or incorrect.

  **Option 1 (quick fix)**

  You can instantiate a chat model with any valid profile:

  ```python  theme={null}
  custom_profile = {
      "max_input_tokens": 100_000,
      "tool_calling": True,
      "structured_output": True,
      # ...
  }
  model = init_chat_model("...", profile=custom_profile)
  ```

  The `profile` is also a regular `dict` and can be updated in place. If the model instance is shared, consider using `model_copy` to avoid mutating shared state.

  ```python  theme={null}
  new_profile = model.profile | {"key": "value"}
  model.model_copy(update={"profile": new_profile})
  ```

  **Option 2 (fix data upstream)**

  The primary source for the data is the [models.dev](https://models.dev/) project. This data is merged with additional fields and overrides in LangChain [integration packages](/oss/python/integrations/providers/overview) and are shipped with those packages.

  Model profile data can be updated through the following process:

  1. (If needed) update the source data at [models.dev](https://models.dev/) through a pull request to its [repository on GitHub](https://github.com/sst/models.dev).
  2. (If needed) update additional fields and overrides in `langchain_<package>/data/profile_augmentations.toml` through a pull request to the LangChain [integration package](/oss/python/integrations/providers/overview)\`.
  3. Use the [`langchain-model-profiles`](https://pypi.org/project/langchain-model-profiles/) CLI tool to pull the latest data from [models.dev](https://models.dev/), merge in the augmentations and update the profile data:

  ```bash  theme={null}
  pip install langchain-model-profiles
  ```

  ```bash  theme={null}
  langchain-profiles refresh --provider <provider> --data-dir <data_dir>
  ```

  This command:

  * Downloads the latest data for `<provider>` from models.dev
  * Merges augmentations from `profile_augmentations.toml` in `<data_dir>`
  * Writes merged profiles to `profiles.py` in `<data_dir>`

  For example: from [`libs/partners/anthropic`](https://github.com/langchain-ai/langchain/tree/master/libs/partners/anthropic) in the [LangChain monorepo](https://github.com/langchain-ai/langchain):

  ```bash  theme={null}
  uv run --with langchain-model-profiles --provider anthropic --data-dir langchain_anthropic/data
  ```
</Accordion>

<Warning>
  Model profiles are a beta feature. The format of a profile is subject to change.
</Warning>

### Multimodal

Certain models can process and return non-textual data such as images, audio, and video. You can pass non-textual data to a model by providing [content blocks](/oss/python/langchain/messages#message-content).

<Tip>
  All LangChain chat models with underlying multimodal capabilities support:

  1. Data in the cross-provider standard format (see [our messages guide](/oss/python/langchain/messages))
  2. OpenAI [chat completions](https://platform.openai.com/docs/api-reference/chat) format
  3. Any format that is native to that specific provider (e.g., Anthropic models accept Anthropic native format)
</Tip>

See the [multimodal section](/oss/python/langchain/messages#multimodal) of the messages guide for details.

<Tooltip tip="Not all LLMs are made equally!" cta="See reference" href="https://models.dev/">Some models</Tooltip> can return multimodal data as part of their response. If invoked to do so, the resulting [`AIMessage`](https://reference.langchain.com/python/langchain/messages/#langchain.messages.AIMessage) will have content blocks with multimodal types.

```python Multimodal output theme={null}
response = model.invoke("Create a picture of a cat")
print(response.content_blocks)
# [
#     {"type": "text", "text": "Here's a picture of a cat"},
#     {"type": "image", "base64": "...", "mime_type": "image/jpeg"},
# ]
```

See the [integrations page](/oss/python/integrations/providers/overview) for details on specific providers.

### Reasoning

Many models are capable of performing multi-step reasoning to arrive at a conclusion. This involves breaking down complex problems into smaller, more manageable steps.

**If supported by the underlying model,** you can surface this reasoning process to better understand how the model arrived at its final answer.

<CodeGroup>
  ```python Stream reasoning output theme={null}
  for chunk in model.stream("Why do parrots have colorful feathers?"):
      reasoning_steps = [r for r in chunk.content_blocks if r["type"] == "reasoning"]
      print(reasoning_steps if reasoning_steps else chunk.text)
  ```

  ```python Complete reasoning output theme={null}
  response = model.invoke("Why do parrots have colorful feathers?")
  reasoning_steps = [b for b in response.content_blocks if b["type"] == "reasoning"]
  print(" ".join(step["reasoning"] for step in reasoning_steps))
  ```
</CodeGroup>

Depending on the model, you can sometimes specify the level of effort it should put into reasoning. Similarly, you can request that the model turn off reasoning entirely. This may take the form of categorical "tiers" of reasoning (e.g., `'low'` or `'high'`) or integer token budgets.

For details, see the [integrations page](/oss/python/integrations/providers/overview) or [reference](https://reference.langchain.com/python/integrations/) for your respective chat model.

### Local models

LangChain supports running models locally on your own hardware. This is useful for scenarios where either data privacy is critical, you want to invoke a custom model, or when you want to avoid the costs incurred when using a cloud-based model.

[Ollama](/oss/python/integrations/chat/ollama) is one of the easiest ways to run chat and embedding models locally.

### Prompt caching

Many providers offer prompt caching features to reduce latency and cost on repeat processing of the same tokens. These features can be **implicit** or **explicit**:

* **Implicit prompt caching:** providers will automatically pass on cost savings if a request hits a cache. Examples: [OpenAI](/oss/python/integrations/chat/openai) and [Gemini](/oss/python/integrations/chat/google_generative_ai).
* **Explicit caching:** providers allow you to manually indicate cache points for greater control or to guarantee cost savings. Examples:
  * [`ChatOpenAI`](https://reference.langchain.com/python/integrations/langchain_openai/ChatOpenAI) (via `prompt_cache_key`)
  * Anthropic's [`AnthropicPromptCachingMiddleware`](/oss/python/integrations/chat/anthropic#prompt-caching)
  * [Gemini](https://reference.langchain.com/python/integrations/langchain_google_genai/).
  * [AWS Bedrock](/oss/python/integrations/chat/bedrock#prompt-caching)

<Warning>
  Prompt caching is often only engaged above a minimum input token threshold. See [provider pages](/oss/python/integrations/chat) for details.
</Warning>

Cache usage will be reflected in the [usage metadata](/oss/python/langchain/messages#token-usage) of the model response.

### Server-side tool use

Some providers support server-side [tool-calling](#tool-calling) loops: models can interact with web search, code interpreters, and other tools and analyze the results in a single conversational turn.

If a model invokes a tool server-side, the content of the response message will include content representing the invocation and result of the tool. Accessing the [content blocks](/oss/python/langchain/messages#standard-content-blocks) of the response will return the server-side tool calls and results in a provider-agnostic format:

```python Invoke with server-side tool use theme={null}
from langchain.chat_models import init_chat_model

model = init_chat_model("gpt-4.1-mini")

tool = {"type": "web_search"}
model_with_tools = model.bind_tools([tool])

response = model_with_tools.invoke("What was a positive news story from today?")
print(response.content_blocks)
```

```python Result expandable theme={null}
[
    {
        "type": "server_tool_call",
        "name": "web_search",
        "args": {
            "query": "positive news stories today",
            "type": "search"
        },
        "id": "ws_abc123"
    },
    {
        "type": "server_tool_result",
        "tool_call_id": "ws_abc123",
        "status": "success"
    },
    {
        "type": "text",
        "text": "Here are some positive news stories from today...",
        "annotations": [
            {
                "end_index": 410,
                "start_index": 337,
                "title": "article title",
                "type": "citation",
                "url": "..."
            }
        ]
    }
]
```

This represents a single conversational turn; there are no associated [ToolMessage](/oss/python/langchain/messages#tool-message) objects that need to be passed in as in client-side [tool-calling](#tool-calling).

See the [integration page](/oss/python/integrations/chat) for your given provider for available tools and usage details.

### Rate limiting

Many chat model providers impose a limit on the number of invocations that can be made in a given time period. If you hit a rate limit, you will typically receive a rate limit error response from the provider, and will need to wait before making more requests.

To help manage rate limits, chat model integrations accept a `rate_limiter` parameter that can be provided during initialization to control the rate at which requests are made.

<Accordion title="Initialize and use a rate limiter" icon="gauge-high">
  LangChain in comes with (an optional) built-in [`InMemoryRateLimiter`](https://reference.langchain.com/python/langchain_core/rate_limiters/#langchain_core.rate_limiters.InMemoryRateLimiter). This limiter is thread safe and can be shared by multiple threads in the same process.

  ```python Define a rate limiter theme={null}
  from langchain_core.rate_limiters import InMemoryRateLimiter

  rate_limiter = InMemoryRateLimiter(
      requests_per_second=0.1,  # 1 request every 10s
      check_every_n_seconds=0.1,  # Check every 100ms whether allowed to make a request
      max_bucket_size=10,  # Controls the maximum burst size.
  )

  model = init_chat_model(
      model="gpt-5",
      model_provider="openai",
      rate_limiter=rate_limiter  # [!code highlight]
  )
  ```

  <Warning>
    The provided rate limiter can only limit the number of requests per unit time. It will not help if you need to also limit based on the size of the requests.
  </Warning>
</Accordion>

### Base URL or proxy

For many chat model integrations, you can configure the base URL for API requests, which allows you to use model providers that have OpenAI-compatible APIs or to use a proxy server.

<Accordion title="Base URL" icon="link">
  Many model providers offer OpenAI-compatible APIs (e.g., [Together AI](https://www.together.ai/), [vLLM](https://github.com/vllm-project/vllm)). You can use [`init_chat_model`](https://reference.langchain.com/python/langchain/models/#langchain.chat_models.init_chat_model) with these providers by specifying the appropriate `base_url` parameter:

  ```python  theme={null}
  model = init_chat_model(
      model="MODEL_NAME",
      model_provider="openai",
      base_url="BASE_URL",
      api_key="YOUR_API_KEY",
  )
  ```

  <Note>
    When using direct chat model class instantiation, the parameter name may vary by provider. Check the respective [reference](/oss/python/integrations/providers/overview) for details.
  </Note>
</Accordion>

<Accordion title="Proxy configuration" icon="shield">
  For deployments requiring HTTP proxies, some model integrations support proxy configuration:

  ```python  theme={null}
  from langchain_openai import ChatOpenAI

  model = ChatOpenAI(
      model="gpt-4o",
      openai_proxy="http://proxy.example.com:8080"
  )
  ```

  <Note>
    Proxy support varies by integration. Check the specific model provider's [reference](/oss/python/integrations/providers/overview) for proxy configuration options.
  </Note>
</Accordion>

### Log probabilities

Certain models can be configured to return token-level log probabilities representing the likelihood of a given token by setting the `logprobs` parameter when initializing the model:

```python  theme={null}
model = init_chat_model(
    model="gpt-4o",
    model_provider="openai"
).bind(logprobs=True)

response = model.invoke("Why do parrots talk?")
print(response.response_metadata["logprobs"])
```

### Token usage

A number of model providers return token usage information as part of the invocation response. When available, this information will be included on the [`AIMessage`](https://reference.langchain.com/python/langchain/messages/#langchain.messages.AIMessage) objects produced by the corresponding model. For more details, see the [messages](/oss/python/langchain/messages) guide.

<Note>
  Some provider APIs, notably OpenAI and Azure OpenAI chat completions, require users opt-in to receiving token usage data in streaming contexts. See the [streaming usage metadata](/oss/python/integrations/chat/openai#streaming-usage-metadata) section of the integration guide for details.
</Note>

You can track aggregate token counts across models in an application using either a callback or context manager, as shown below:

<Tabs>
  <Tab title="Callback handler">
    ```python  theme={null}
    from langchain.chat_models import init_chat_model
    from langchain_core.callbacks import UsageMetadataCallbackHandler

    model_1 = init_chat_model(model="gpt-4o-mini")
    model_2 = init_chat_model(model="claude-haiku-4-5-20251001")

    callback = UsageMetadataCallbackHandler()
    result_1 = model_1.invoke("Hello", config={"callbacks": [callback]})
    result_2 = model_2.invoke("Hello", config={"callbacks": [callback]})
    print(callback.usage_metadata)
    ```

    ```python  theme={null}
    {
        'gpt-4o-mini-2024-07-18': {
            'input_tokens': 8,
            'output_tokens': 10,
            'total_tokens': 18,
            'input_token_details': {'audio': 0, 'cache_read': 0},
            'output_token_details': {'audio': 0, 'reasoning': 0}
        },
        'claude-haiku-4-5-20251001': {
            'input_tokens': 8,
            'output_tokens': 21,
            'total_tokens': 29,
            'input_token_details': {'cache_read': 0, 'cache_creation': 0}
        }
    }
    ```
  </Tab>

  <Tab title="Context manager">
    ```python  theme={null}
    from langchain.chat_models import init_chat_model
    from langchain_core.callbacks import get_usage_metadata_callback

    model_1 = init_chat_model(model="gpt-4o-mini")
    model_2 = init_chat_model(model="claude-haiku-4-5-20251001")

    with get_usage_metadata_callback() as cb:
        model_1.invoke("Hello")
        model_2.invoke("Hello")
        print(cb.usage_metadata)
    ```

    ```python  theme={null}
    {
        'gpt-4o-mini-2024-07-18': {
            'input_tokens': 8,
            'output_tokens': 10,
            'total_tokens': 18,
            'input_token_details': {'audio': 0, 'cache_read': 0},
            'output_token_details': {'audio': 0, 'reasoning': 0}
        },
        'claude-haiku-4-5-20251001': {
            'input_tokens': 8,
            'output_tokens': 21,
            'total_tokens': 29,
            'input_token_details': {'cache_read': 0, 'cache_creation': 0}
        }
    }
    ```
  </Tab>
</Tabs>

### Invocation config

When invoking a model, you can pass additional configuration through the `config` parameter using a [`RunnableConfig`](https://reference.langchain.com/python/langchain_core/runnables/#langchain_core.runnables.RunnableConfig) dictionary. This provides run-time control over execution behavior, callbacks, and metadata tracking.

Common configuration options include:

```python Invocation with config theme={null}
response = model.invoke(
    "Tell me a joke",
    config={
        "run_name": "joke_generation",      # Custom name for this run
        "tags": ["humor", "demo"],          # Tags for categorization
        "metadata": {"user_id": "123"},     # Custom metadata
        "callbacks": [my_callback_handler], # Callback handlers
    }
)
```

These configuration values are particularly useful when:

* Debugging with [LangSmith](https://docs.langchain.com/langsmith/home) tracing
* Implementing custom logging or monitoring
* Controlling resource usage in production
* Tracking invocations across complex pipelines

<Accordion title="Key configuration attributes">
  <ParamField body="run_name" type="string">
    Identifies this specific invocation in logs and traces. Not inherited by sub-calls.
  </ParamField>

  <ParamField body="tags" type="string[]">
    Labels inherited by all sub-calls for filtering and organization in debugging tools.
  </ParamField>

  <ParamField body="metadata" type="object">
    Custom key-value pairs for tracking additional context, inherited by all sub-calls.
  </ParamField>

  <ParamField body="max_concurrency" type="number">
    Controls the maximum number of parallel calls when using [`batch()`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.batch) or [`batch_as_completed()`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.batch_as_completed).
  </ParamField>

  <ParamField body="callbacks" type="array">
    Handlers for monitoring and responding to events during execution.
  </ParamField>

  <ParamField body="recursion_limit" type="number">
    Maximum recursion depth for chains to prevent infinite loops in complex pipelines.
  </ParamField>
</Accordion>

<Tip>
  See full [`RunnableConfig`](https://reference.langchain.com/python/langchain_core/runnables/#langchain_core.runnables.RunnableConfig) reference for all supported attributes.
</Tip>

### Configurable models

You can also create a runtime-configurable model by specifying [`configurable_fields`](https://reference.langchain.com/python/langchain_core/language_models/#langchain_core.language_models.chat_models.BaseChatModel.configurable_fields). If you don't specify a model value, then `'model'` and `'model_provider'` will be configurable by default.

```python  theme={null}
from langchain.chat_models import init_chat_model

configurable_model = init_chat_model(temperature=0)

configurable_model.invoke(
    "what's your name",
    config={"configurable": {"model": "gpt-5-nano"}},  # Run with GPT-5-Nano
)
configurable_model.invoke(
    "what's your name",
    config={"configurable": {"model": "claude-sonnet-4-5-20250929"}},  # Run with Claude
)
```

<Accordion title="Configurable model with default values">
  We can create a configurable model with default model values, specify which parameters are configurable, and add prefixes to configurable params:

  ```python  theme={null}
  first_model = init_chat_model(
          model="gpt-4.1-mini",
          temperature=0,
          configurable_fields=("model", "model_provider", "temperature", "max_tokens"),
          config_prefix="first",  # Useful when you have a chain with multiple models
  )

  first_model.invoke("what's your name")
  ```

  ```python  theme={null}
  first_model.invoke(
      "what's your name",
      config={
          "configurable": {
              "first_model": "claude-sonnet-4-5-20250929",
              "first_temperature": 0.5,
              "first_max_tokens": 100,
          }
      },
  )
  ```

  See the [`init_chat_model`](https://reference.langchain.com/python/langchain/models/#langchain.chat_models.init_chat_model) reference for more details on `configurable_fields` and `config_prefix`.
</Accordion>

<Accordion title="Using a configurable model declaratively">
  We can call declarative operations like `bind_tools`, `with_structured_output`, `with_configurable`, etc. on a configurable model and chain a configurable model in the same way that we would a regularly instantiated chat model object.

  ```python  theme={null}
  from pydantic import BaseModel, Field


  class GetWeather(BaseModel):
      """Get the current weather in a given location"""

          location: str = Field(..., description="The city and state, e.g. San Francisco, CA")


  class GetPopulation(BaseModel):
      """Get the current population in a given location"""

          location: str = Field(..., description="The city and state, e.g. San Francisco, CA")


  model = init_chat_model(temperature=0)
  model_with_tools = model.bind_tools([GetWeather, GetPopulation])

  model_with_tools.invoke(
      "what's bigger in 2024 LA or NYC", config={"configurable": {"model": "gpt-4.1-mini"}}
  ).tool_calls
  ```

  ```
  [
      {
          'name': 'GetPopulation',
          'args': {'location': 'Los Angeles, CA'},
          'id': 'call_Ga9m8FAArIyEjItHmztPYA22',
          'type': 'tool_call'
      },
      {
          'name': 'GetPopulation',
          'args': {'location': 'New York, NY'},
          'id': 'call_jh2dEvBaAHRaw5JUDthOs7rt',
          'type': 'tool_call'
      }
  ]
  ```

  ```python  theme={null}
  model_with_tools.invoke(
      "what's bigger in 2024 LA or NYC",
      config={"configurable": {"model": "claude-sonnet-4-5-20250929"}},
  ).tool_calls
  ```

  ```
  [
      {
          'name': 'GetPopulation',
          'args': {'location': 'Los Angeles, CA'},
          'id': 'toolu_01JMufPf4F4t2zLj7miFeqXp',
          'type': 'tool_call'
      },
      {
          'name': 'GetPopulation',
          'args': {'location': 'New York City, NY'},
          'id': 'toolu_01RQBHcE8kEEbYTuuS8WqY1u',
          'type': 'tool_call'
      }
  ]
  ```
</Accordion>

***

<Callout icon="pen-to-square" iconType="regular">
  [Edit this page on GitHub](https://github.com/langchain-ai/docs/edit/main/src/oss/langchain/models.mdx) or [file an issue](https://github.com/langchain-ai/docs/issues/new/choose).
</Callout>

<Tip icon="terminal" iconType="regular">
  [Connect these docs](/use-these-docs) to Claude, VSCode, and more via MCP for real-time answers.
</Tip>
