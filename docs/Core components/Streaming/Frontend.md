> ## Documentation Index
> Fetch the complete documentation index at: https://docs.langchain.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Frontend

> Build generative UIs with real-time streaming from LangChain agents, LangGraph graphs, and custom APIs

The `useStream` React hook provides seamless integration with LangGraph streaming capabilities. It handles all the complexities of streaming, state management, and branching logic, letting you focus on building great generative UI experiences.

Key features:

* <Icon icon="messages" size={16} /> **Messages streaming** — Handle a stream of message chunks to form a complete message
* <Icon icon="arrows-rotate" size={16} /> **Automatic state management** — for messages, interrupts, loading states, and errors
* <Icon icon="code-branch" size={16} /> **Conversation branching** — Create alternate conversation paths from any point in the chat history
* <Icon icon="palette" size={16} /> **UI-agnostic design** — Bring your own components and styling

## Installation

Install the LangGraph SDK to use the `useStream` hook in your React application:

## Basic usage

The `useStream` hook connects to any LangGraph graph, whether that's running on from your own endpoint, or deployed using [LangSmith deployments](/langsmith/deployments).

```tsx  theme={null}
import { useStream } from "@langchain/langgraph-sdk/react";

function Chat() {
  const stream = useStream({
    assistantId: "agent",
    // Local development
    apiUrl: "http://localhost:2024",
    // Production deployment (LangSmith hosted)
    // apiUrl: "https://your-deployment.us.langgraph.app"
  });

  const handleSubmit = (message: string) => {
    stream.submit({
      messages: [
        { content: message, type: "human" }
      ],
    });
  };

  return (
    <div>
      {stream.messages.map((message, idx) => (
        <div key={message.id ?? idx}>
          {message.type}: {message.content}
        </div>
      ))}

      {stream.isLoading && <div>Loading...</div>}
      {stream.error && <div>Error: {stream.error.message}</div>}
    </div>
  );
}
```

<Tip>
  Learn how to [deploy your agents to LangSmith](/oss/python/langchain/deploy) for production-ready hosting with built-in observability, authentication, and scaling.
</Tip>

<Accordion title="`useStream` parameters">
  <ParamField body="assistantId" type="string" required>
    The ID of the agent to connect to. When using LangSmith deployments, this must match the agent ID shown in your deployment dashboard. For custom API deployments or local development, this can be any string that your server uses to identify the agent.
  </ParamField>

  <ParamField body="apiUrl" type="string">
    The URL of the LangGraph server. Defaults to `http://localhost:2024` for local development.
  </ParamField>

  <ParamField body="apiKey" type="string">
    API key for authentication. Required when connecting to deployed agents on LangSmith.
  </ParamField>

  <ParamField body="threadId" type="string">
    Connect to an existing thread instead of creating a new one. Useful for resuming conversations.
  </ParamField>

  <ParamField body="onThreadId" type="(id: string) => void">
    Callback invoked when a new thread is created. Use this to persist the thread ID for later use.
  </ParamField>

  <ParamField body="reconnectOnMount" type="boolean | (() => Storage)">
    Automatically resume an ongoing run when the component mounts. Set to `true` to use session storage, or provide a custom storage function.
  </ParamField>

  <ParamField body="onCreated" type="(run: Run) => void">
    Callback invoked when a new run is created. Useful for persisting run metadata for resumption.
  </ParamField>

  <ParamField body="onError" type="(error: Error) => void">
    Callback invoked when an error occurs during streaming.
  </ParamField>

  <ParamField body="onFinish" type="(state: StateType, run?: Run) => void">
    Callback invoked when the stream completes successfully with the final state.
  </ParamField>

  <ParamField body="onCustomEvent" type="(data: unknown, context: { mutate }) => void">
    Handle custom events emitted from your agent using the `writer`. See [Custom streaming events](#custom-streaming-events).
  </ParamField>

  <ParamField body="onUpdateEvent" type="(data: unknown, context: { mutate }) => void">
    Handle state update events after each graph step.
  </ParamField>

  <ParamField body="onMetadataEvent" type="(metadata: { run_id, thread_id }) => void">
    Handle metadata events with run and thread information.
  </ParamField>

  <ParamField body="messagesKey" type="string" default="messages">
    The key in the graph state that contains the messages array.
  </ParamField>

  <ParamField body="throttle" type="boolean" default="true">
    Batch state updates for better rendering performance. Disable for immediate updates.
  </ParamField>

  <ParamField body="initialValues" type="StateType | null">
    Initial state values to display while the first stream is loading. Useful for showing cached thread data immediately.
  </ParamField>
</Accordion>

<Accordion title="`useStream` return values">
  <ParamField body="messages" type="Message[]">
    All messages in the current thread, including both human and AI messages.
  </ParamField>

  <ParamField body="values" type="StateType">
    The current graph state values. Type is inferred from the agent or graph type parameter.
  </ParamField>

  <ParamField body="isLoading" type="boolean">
    Whether a stream is currently in progress. Use this to show loading indicators.
  </ParamField>

  <ParamField body="error" type="Error | null">
    Any error that occurred during streaming. `null` when no error.
  </ParamField>

  <ParamField body="interrupt" type="Interrupt | undefined">
    Current interrupt requiring user input, such as human-in-the-loop approval requests.
  </ParamField>

  <ParamField body="toolCalls" type="ToolCallWithResult[]">
    All tool calls across all messages, with their results and state (`pending`, `completed`, or `error`).
  </ParamField>

  <ParamField body="submit" type="(input, options?) => Promise<void>">
    Submit new input to the agent. Pass `null` as input when resuming from an interrupt with a command. Options include `checkpoint` for branching, `optimisticValues` for optimistic updates, and `threadId` for optimistic thread creation.
  </ParamField>

  <ParamField body="stop" type="() => void">
    Stop the current stream immediately.
  </ParamField>

  <ParamField body="joinStream" type="(runId: string) => void">
    Resume an existing stream by run ID. Use with `onCreated` for manual stream resumption.
  </ParamField>

  <ParamField body="setBranch" type="(branch: string) => void">
    Switch to a different branch in the conversation history.
  </ParamField>

  <ParamField body="getToolCalls" type="(message) => ToolCall[]">
    Get all tool calls for a specific AI message.
  </ParamField>

  <ParamField body="getMessagesMetadata" type="(message) => MessageMetadata">
    Get metadata for a message, including streaming info like `langgraph_node` for identifying the source node, and `firstSeenState` for branching.
  </ParamField>

  <ParamField body="experimental_branchTree" type="BranchTree">
    Tree representation of the thread for advanced branching controls in non-message based graphs.
  </ParamField>
</Accordion>

## Thread management

Keep track of conversations with built-in thread management. You can access the current thread ID and get notified when new threads are created:

```tsx  theme={null}
import { useState } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";

function Chat() {
  const [threadId, setThreadId] = useState<string | null>(null);

  const stream = useStream({
    apiUrl: "http://localhost:2024",
    assistantId: "agent",
    threadId: threadId,
    onThreadId: setThreadId,
  });

  // threadId is updated when a new thread is created
  // Store it in URL params or localStorage for persistence
}
```

We recommend storing the `threadId` to let users resume conversations after page refreshes.

### Resume after page refresh

The `useStream` hook can automatically resume an ongoing run upon mounting by setting `reconnectOnMount: true`. This is useful for continuing a stream after a page refresh, ensuring no messages and events generated during the downtime are lost.

```tsx  theme={null}
const stream = useStream({
  apiUrl: "http://localhost:2024",
  assistantId: "agent",
  reconnectOnMount: true,
});
```

By default the ID of the created run is stored in `window.sessionStorage`, which can be swapped by passing a custom storage function:

```tsx  theme={null}
const stream = useStream({
  apiUrl: "http://localhost:2024",
  assistantId: "agent",
  reconnectOnMount: () => window.localStorage,
});
```

For manual control over the resumption process, use the run callbacks to persist metadata and `joinStream` to resume:

```tsx  theme={null}
import { useStream } from "@langchain/langgraph-sdk/react";
import { useEffect, useRef } from "react";

function Chat({ threadId }: { threadId: string | null }) {
  const stream = useStream({
    apiUrl: "http://localhost:2024",
    assistantId: "agent",
    threadId,
    onCreated: (run) => {
      // Persist run ID when stream starts
      window.sessionStorage.setItem(`resume:${run.thread_id}`, run.run_id);
    },
    onFinish: (_, run) => {
      // Clean up when stream completes
      window.sessionStorage.removeItem(`resume:${run?.thread_id}`);
    },
  });

  // Resume stream on mount if there's a stored run ID
  const joinedThreadId = useRef<string | null>(null);
  useEffect(() => {
    if (!threadId) return;
    const runId = window.sessionStorage.getItem(`resume:${threadId}`);
    if (runId && joinedThreadId.current !== threadId) {
      stream.joinStream(runId);
      joinedThreadId.current = threadId;
    }
  }, [threadId]);

  const handleSubmit = (text: string) => {
    // Use streamResumable to ensure events aren't lost
    stream.submit(
      { messages: [{ type: "human", content: text }] },
      { streamResumable: true }
    );
  };
}
```

<Card title="Try the session persistence example" icon="rotate" href="https://github.com/langchain-ai/langgraphjs/tree/main/examples/ui-react/src/examples/session-persistence">
  See a complete implementation of stream resumption with `reconnectOnMount` and thread persistence in the `session-persistence` example.
</Card>

## Optimistic updates

You can optimistically update the client state before performing a network request, providing immediate feedback to the user:

```tsx  theme={null}
const stream = useStream({
  apiUrl: "http://localhost:2024",
  assistantId: "agent",
});

const handleSubmit = (text: string) => {
  const newMessage = { type: "human" as const, content: text };

  stream.submit(
    { messages: [newMessage] },
    {
      optimisticValues(prev) {
        const prevMessages = prev.messages ?? [];
        return { ...prev, messages: [...prevMessages, newMessage] };
      },
    }
  );
};
```

### Optimistic thread creation

Use the `threadId` option in `submit` to enable optimistic UI patterns where you need to know the thread ID before the thread is created:

```tsx  theme={null}
import { useState } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";

function Chat() {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [optimisticThreadId] = useState(() => crypto.randomUUID());

  const stream = useStream({
    apiUrl: "http://localhost:2024",
    assistantId: "agent",
    threadId,
    onThreadId: setThreadId,
  });

  const handleSubmit = (text: string) => {
    // Navigate immediately without waiting for thread creation
    window.history.pushState({}, "", `/threads/${optimisticThreadId}`);

    // Create thread with the predetermined ID
    stream.submit(
      { messages: [{ type: "human", content: text }] },
      { threadId: optimisticThreadId }
    );
  };
}
```

### Cached thread display

Use the `initialValues` option to display cached thread data immediately while the history is being loaded from the server:

```tsx  theme={null}
function Chat({ threadId, cachedData }) {
  const stream = useStream({
    apiUrl: "http://localhost:2024",
    assistantId: "agent",
    threadId,
    initialValues: cachedData?.values,
  });

  // Shows cached messages instantly, then updates when server responds
}
```

## Branching

Create alternate conversation paths by editing previous messages or regenerating AI responses. Use `getMessagesMetadata()` to access checkpoint information for branching:

<CodeGroup>
  ```tsx Chat.tsx theme={null}
  import { useStream } from "@langchain/langgraph-sdk/react";
  import { BranchSwitcher } from "./BranchSwitcher";

  function Chat() {
    const stream = useStream({
      apiUrl: "http://localhost:2024",
      assistantId: "agent",
    });

    return (
      <div>
        {stream.messages.map((message) => {
          const meta = stream.getMessagesMetadata(message);
          const parentCheckpoint = meta?.firstSeenState?.parent_checkpoint;

          return (
            <div key={message.id}>
              <div>{message.content as string}</div>

              {/* Edit human messages */}
              {message.type === "human" && (
                <button
                  onClick={() => {
                    const newContent = prompt("Edit message:", message.content as string);
                    if (newContent) {
                      stream.submit(
                        { messages: [{ type: "human", content: newContent }] },
                        { checkpoint: parentCheckpoint }
                      );
                    }
                  }}
                >
                  Edit
                </button>
              )}

              {/* Regenerate AI messages */}
              {message.type === "ai" && (
                <button
                  onClick={() => stream.submit(undefined, { checkpoint: parentCheckpoint })}
                >
                  Regenerate
                </button>
              )}

              {/* Switch between branches */}
              <BranchSwitcher
                branch={meta?.branch}
                branchOptions={meta?.branchOptions}
                onSelect={(branch) => stream.setBranch(branch)}
              />
            </div>
          );
        })}
      </div>
    );
  }
  ```

  ```tsx BranchSwitcher.tsx theme={null}
  /**
   * Component for navigating between conversation branches.
   * Shows the current branch position and allows switching between alternatives.
   */
  export function BranchSwitcher({
    branch,
    branchOptions,
    onSelect,
  }: {
    branch: string | undefined;
    branchOptions: string[] | undefined;
    onSelect: (branch: string) => void;
  }) {
    if (!branchOptions || !branch) return null;
    const index = branchOptions.indexOf(branch);

    return (
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={index <= 0}
          onClick={() => onSelect(branchOptions[index - 1])}
        >
          ←
        </button>
        <span>{index + 1} / {branchOptions.length}</span>
        <button
          type="button"
          disabled={index >= branchOptions.length - 1}
          onClick={() => onSelect(branchOptions[index + 1])}
        >
          →
        </button>
      </div>
    );
  }
  ```
</CodeGroup>

For advanced use cases, use the `experimental_branchTree` property to get the tree representation of the thread for non-message based graphs.

<Card title="Try the branching example" icon="code-branch" href="https://github.com/langchain-ai/langgraphjs/tree/main/examples/ui-react/src/examples/branching-chat">
  See a complete implementation of conversation branching with edit, regenerate, and branch switching in the `branching-chat` example.
</Card>

## Type-safe streaming

The `useStream` hook supports full type inference when used with agents created via @\[`createAgent`] or graphs created with [`StateGraph`](https://reference.langchain.com/python/langgraph/graphs/#langgraph.graph.state.StateGraph). Pass `typeof agent` or `typeof graph` as the type parameter to automatically infer tool call types.

### With `createAgent`

When using @\[`createAgent`], tool call types are automatically inferred from the tools you register to your agent:

<CodeGroup>
  ```python agent.py theme={null}
  from langchain import create_agent, tool

  @tool
  def get_weather(location: str) -> str:
      """Get weather for a location."""
      return f"Weather in {location}: Sunny, 72°F"

  agent = create_agent(
      model="openai:gpt-4o-mini",
      tools=[get_weather],
  )
  ```

  ```tsx Chat.tsx theme={null}
  import { useStream } from "@langchain/langgraph-sdk/react";
  import type { AgentState } from "./types";

  function Chat() {
    // Use the manually defined state type
    const stream = useStream<AgentState>({
      assistantId: "agent",
      apiUrl: "http://localhost:2024",
    });

    // stream.toolCalls[0].call.name is typed as "get_weather"
    // stream.toolCalls[0].call.args is typed as { location: string }
  }
  ```

  ```typescript types.ts theme={null}
  import type { Message } from "@langchain/langgraph-sdk";

  // Define tool call types to match your Python agent
  export type GetWeatherToolCall = {
    name: "get_weather";
    args: { location: string };
    id?: string;
  };

  export type AgentToolCalls = GetWeatherToolCall;

  export interface AgentState {
    messages: Message<AgentToolCalls>[];
  }
  ```
</CodeGroup>

### With `StateGraph`

For custom [`StateGraph`](https://reference.langchain.com/python/langgraph/graphs/#langgraph.graph.state.StateGraph) applications, the state types are inferred from the graph's annotation:

<CodeGroup>
  ```python graph.py theme={null}
  from langgraph.graph import StateGraph, START, END
  from langgraph.graph.message import add_messages
  from langchain_openai import ChatOpenAI
  from typing import TypedDict, Annotated

  class State(TypedDict):
      messages: Annotated[list, add_messages]

  model = ChatOpenAI(model="gpt-4o-mini")

  async def agent(state: State) -> dict:
      response = await model.ainvoke(state["messages"])
      return {"messages": [response]}

  workflow = StateGraph(State)
  workflow.add_node("agent", agent)
  workflow.add_edge(START, "agent")
  workflow.add_edge("agent", END)

  graph = workflow.compile()
  ```

  ```tsx Chat.tsx theme={null}
  import { useStream } from "@langchain/langgraph-sdk/react";
  import type { GraphState } from "./types";

  function Chat() {
    // Use the manually defined state type
    const stream = useStream<GraphState>({
      assistantId: "my-graph",
      apiUrl: "http://localhost:2024",
    });

    // stream.values is typed based on your defined state
  }
  ```

  ```typescript types.ts theme={null}
  import type { Message } from "@langchain/langgraph-sdk";

  // Define state to match your Python graph's State TypedDict
  export interface GraphState {
    messages: Message[];
  }
  ```
</CodeGroup>

### With Annotation types

If you're using LangGraph.js, you can reuse your graph's annotation types. Make sure to only import types to avoid importing the entire LangGraph.js runtime:

### Advanced type configuration

You can specify additional type parameters for interrupts, custom events, and configurable options:

## Rendering tool calls

Use `getToolCalls` to extract and render tool calls from AI messages. Tool calls include the call details, result (if completed), and state.

<CodeGroup>
  ```python agent.py theme={null}
  from langchain import create_agent, tool

  @tool
  def get_weather(location: str) -> str:
      """Get the current weather for a location."""
      return f'{{"status": "success", "content": "Weather in {location}: Sunny, 72°F"}}'

  agent = create_agent(
      model="openai:gpt-4o-mini",
      tools=[get_weather],
  )
  ```

  ```tsx Chat.tsx theme={null}
  import { useStream } from "@langchain/langgraph-sdk/react";
  import type { AgentState, AgentToolCalls } from "./types";
  import { ToolCallCard } from "./ToolCallCard";
  import { MessageBubble } from "./MessageBubble";

  function Chat() {
    const stream = useStream<AgentState>({
      assistantId: "agent",
      apiUrl: "http://localhost:2024",
    });

    return (
      <div className="flex flex-col gap-4">
        {stream.messages.map((message, idx) => {
          if (message.type === "ai") {
            const toolCalls = stream.getToolCalls(message);

            if (toolCalls.length > 0) {
              return (
                <div key={message.id ?? idx} className="flex flex-col gap-2">
                  {toolCalls.map((toolCall) => (
                    <ToolCallCard key={toolCall.id} toolCall={toolCall} />
                  ))}
                </div>
              );
            }
          }

          return <MessageBubble key={message.id ?? idx} message={message} />;
        })}
      </div>
    );
  }
  ```

  ```tsx ToolCallCard.tsx theme={null}
  import type { ToolCallWithResult, ToolCallState } from "@langchain/langgraph-sdk/react";
  import type { ToolMessage } from "@langchain/langgraph-sdk";
  import type { AgentToolCalls, GetWeatherToolCall } from "./types";
  import { parseToolResult } from "./utils";
  import { WeatherCard } from "./WeatherCard";
  import { GenericToolCallCard } from "./GenericToolCallCard";

  export function ToolCallCard({
    toolCall,
  }: {
    toolCall: ToolCallWithResult<AgentToolCalls>;
  }) {
    const { call, result, state } = toolCall;

    if (call.name === "get_weather") {
      return <WeatherCard call={call} result={result} state={state} />;
    }

    return <GenericToolCallCard call={call} result={result} state={state} />;
  }
  ```

  ```tsx WeatherCard.tsx theme={null}
  import type { ToolCallState } from "@langchain/langgraph-sdk/react";
  import type { ToolMessage } from "@langchain/langgraph-sdk";
  import type { GetWeatherToolCall } from "./types";
  import { parseToolResult } from "./utils";

  export function WeatherCard({
    call,
    result,
    state,
  }: {
    call: GetWeatherToolCall;
    result?: ToolMessage;
    state: ToolCallState;
  }) {
    const isLoading = state === "pending";
    const parsedResult = parseToolResult(result);

    return (
      <div className="relative overflow-hidden rounded-xl">
        <div className="absolute inset-0 bg-gradient-to-br from-sky-600 to-indigo-600" />
        <div className="relative p-4">
          <div className="flex items-center gap-2 text-white/80 text-xs mb-3">
            <span className="font-medium">{call.args.location}</span>
            {isLoading && <span className="ml-auto">Loading...</span>}
          </div>
          {parsedResult.status === "error" ? (
            <div className="bg-red-500/20 rounded-lg p-3 text-red-200 text-sm">
              {parsedResult.content}
            </div>
          ) : (
            <div className="text-white text-lg font-medium">
              {parsedResult.content || "Fetching weather..."}
            </div>
          )}
        </div>
      </div>
    );
  }
  ```

  ```typescript types.ts theme={null}
  import type { Message } from "@langchain/langgraph-sdk";

  // Define tool call types to match your Python agent's tools
  export type GetWeatherToolCall = {
    name: "get_weather";
    args: { location: string };
    id?: string;
  };

  // Union of all tool calls in your agent
  export type AgentToolCalls = GetWeatherToolCall;

  // Define state type with your tool calls
  export interface AgentState {
    messages: Message<AgentToolCalls>[];
  }
  ```

  ```typescript utils.ts theme={null}
  import type { ToolMessage } from "@langchain/langgraph-sdk";

  export function parseToolResult(result?: ToolMessage): {
    status: string;
    content: string;
  } {
    if (!result) return { status: "pending", content: "" };
    try {
      return JSON.parse(result.content as string);
    } catch {
      return { status: "success", content: result.content as string };
    }
  }
  ```
</CodeGroup>

<Card title="Try the tool calling example" icon="hammer" href="https://github.com/langchain-ai/langgraphjs/tree/main/examples/ui-react/src/examples/tool-calling-agent">
  See a complete implementation of tool call rendering with weather, calculator, and note-taking tools in the `tool-calling-agent` example.
</Card>

## Custom streaming events

Stream custom data from your agent using the `writer` in your tools or nodes. Handle these events in the UI with the `onCustomEvent` callback.

<CodeGroup>
  ```python agent.py theme={null}
  import asyncio
  import time
  from langchain import create_agent, tool
  from langchain.types import ToolRuntime

  @tool
  async def analyze_data(data_source: str, *, config: ToolRuntime) -> str:
      """Analyze data with progress updates."""
      steps = ["Connecting...", "Fetching...", "Processing...", "Done!"]

      for i, step in enumerate(steps):
          # Emit progress events during execution
          if config.writer:
              config.writer({
                  "type": "progress",
                  "id": f"analysis-{int(time.time() * 1000)}",
                  "message": step,
                  "progress": ((i + 1) / len(steps)) * 100,
              })
          await asyncio.sleep(0.5)

      return '{"result": "Analysis complete"}'

  agent = create_agent(
      model="openai:gpt-4o-mini",
      tools=[analyze_data],
  )
  ```

  ```tsx Chat.tsx theme={null}
  import { useState, useCallback } from "react";
  import { useStream } from "@langchain/langgraph-sdk/react";
  import type { AgentState } from "./types";

  interface ProgressData {
    type: "progress";
    id: string;
    message: string;
    progress: number;
  }

  function isProgressData(data: unknown): data is ProgressData {
    return (
      typeof data === "object" &&
      data !== null &&
      "type" in data &&
      (data as ProgressData).type === "progress"
    );
  }

  function CustomStreamingUI() {
    const [progressData, setProgressData] = useState<Map<string, ProgressData>>(
      new Map()
    );

    const handleCustomEvent = useCallback((data: unknown) => {
      if (isProgressData(data)) {
        setProgressData((prev) => {
          const updated = new Map(prev);
          updated.set(data.id, data);
          return updated;
        });
      }
    }, []);

    const stream = useStream<AgentState>({
      assistantId: "custom-streaming",
      apiUrl: "http://localhost:2024",
      onCustomEvent: handleCustomEvent,
    });

    return (
      <div>
        {Array.from(progressData.values()).map((data) => (
          <div key={data.id} className="bg-neutral-800 rounded-lg p-4 mb-4">
            <div className="flex justify-between mb-2">
              <span className="text-sm text-white">{data.message}</span>
              <span className="text-xs text-neutral-400">{data.progress}%</span>
            </div>
            <div className="w-full bg-neutral-700 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all"
                style={{ width: `${data.progress}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    );
  }
  ```

  ```typescript types.ts theme={null}
  import type { Message } from "@langchain/langgraph-sdk";

  // Define tool calls to match your Python agent
  export type AnalyzeDataToolCall = {
    name: "analyze_data";
    args: { data_source: string };
    id?: string;
  };

  export type AgentToolCalls = AnalyzeDataToolCall;

  export interface AgentState {
    messages: Message<AgentToolCalls>[];
  }
  ```
</CodeGroup>

<Card title="Try the custom streaming example" icon="bolt" href="https://github.com/langchain-ai/langgraphjs/tree/main/examples/ui-react/src/examples/custom-streaming">
  See a complete implementation of custom events with progress bars, status badges, and file operation cards in the `custom-streaming` example.
</Card>

## Event handling

The `useStream` hook provides callback options that give you access to different types of streaming events. You don't need to explicitly configure stream modes—just pass callbacks for the event types you want to handle:

### Available callbacks

| Callback          | Description                                                  | Stream mode |
| ----------------- | ------------------------------------------------------------ | ----------- |
| `onUpdateEvent`   | Called when a state update is received after each graph step | `updates`   |
| `onCustomEvent`   | Called when a custom event is received from your graph       | `custom`    |
| `onMetadataEvent` | Called with run and thread metadata                          | `metadata`  |
| `onError`         | Called when an error occurs                                  | -           |
| `onFinish`        | Called when the stream completes                             | -           |

## Multi-agent streaming

When working with multi-agent systems or graphs with multiple nodes, use message metadata to identify which node generated each message. This is particularly useful when multiple LLMs run in parallel and you want to display their outputs with distinct visual styling.

<CodeGroup>
  ```python agent.py theme={null}
  from langchain_openai import ChatOpenAI
  from langgraph.graph import StateGraph, START, END, Send
  from langgraph.graph.state import CompiledStateGraph
  from langchain.messages import BaseMessage, AIMessage
  from typing import TypedDict, Annotated
  import operator

  # Use different model instances for variety
  analytical_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
  creative_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.9)
  practical_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)

  class State(TypedDict):
      messages: Annotated[list[BaseMessage], operator.add]
      topic: str
      analytical_research: str
      creative_research: str
      practical_research: str

  def fan_out_to_researchers(state: State) -> list[Send]:
      return [
          Send("researcher_analytical", state),
          Send("researcher_creative", state),
          Send("researcher_practical", state),
      ]

  def dispatcher(state: State) -> dict:
      last_message = state["messages"][-1] if state["messages"] else None
      topic = last_message.content if last_message else ""
      return {"topic": topic}

  async def researcher_analytical(state: State) -> dict:
      response = await analytical_model.ainvoke([
          {"role": "system", "content": "You are an analytical research expert."},
          {"role": "user", "content": f"Research: {state['topic']}"},
      ])
      return {
          "analytical_research": response.content,
          "messages": [AIMessage(content=response.content, name="researcher_analytical")],
      }

  # Similar nodes for creative and practical researchers...

  workflow = StateGraph(State)
  workflow.add_node("dispatcher", dispatcher)
  workflow.add_node("researcher_analytical", researcher_analytical)
  workflow.add_node("researcher_creative", researcher_creative)
  workflow.add_node("researcher_practical", researcher_practical)
  workflow.add_edge(START, "dispatcher")
  workflow.add_conditional_edges("dispatcher", fan_out_to_researchers)
  workflow.add_edge("researcher_analytical", END)
  workflow.add_edge("researcher_creative", END)
  workflow.add_edge("researcher_practical", END)

  agent: CompiledStateGraph = workflow.compile()
  ```

  ```tsx Chat.tsx theme={null}
  import { useStream } from "@langchain/langgraph-sdk/react";
  import type { AgentState } from "./types";
  import { MessageBubble } from "./MessageBubble";

  // Node configuration for visual display
  const NODE_CONFIG: Record<string, { label: string; color: string }> = {
    researcher_analytical: { label: "Analytical Research", color: "cyan" },
    researcher_creative: { label: "Creative Research", color: "purple" },
    researcher_practical: { label: "Practical Research", color: "emerald" },
  };

  function MultiAgentChat() {
    const stream = useStream<AgentState>({
      assistantId: "parallel-research",
      apiUrl: "http://localhost:2024",
    });

    return (
      <div className="flex flex-col gap-4">
        {stream.messages.map((message, idx) => {
          if (message.type !== "ai") {
            return <MessageBubble key={message.id ?? idx} message={message} />;
          }

          const metadata = stream.getMessagesMetadata?.(message);
          const nodeName =
            (metadata?.streamMetadata?.langgraph_node as string) ||
            (message as { name?: string }).name;

          const config = nodeName ? NODE_CONFIG[nodeName] : null;

          if (!config) {
            return <MessageBubble key={message.id ?? idx} message={message} />;
          }

          return (
            <div
              key={message.id ?? idx}
              className={`bg-${config.color}-950/30 border border-${config.color}-500/30 rounded-xl p-4`}
            >
              <div className={`text-sm font-semibold text-${config.color}-400 mb-2`}>
                {config.label}
              </div>
              <div className="text-neutral-200 whitespace-pre-wrap">
                {typeof message.content === "string" ? message.content : ""}
              </div>
            </div>
          );
        })}
      </div>
    );
  }
  ```

  ```typescript types.ts theme={null}
  import type { Message } from "@langchain/langgraph-sdk";

  // State matches your Python agent's State TypedDict
  export interface AgentState {
    messages: Message[];
    topic: string;
    analytical_research: string;
    creative_research: string;
    practical_research: string;
  }
  ```
</CodeGroup>

<Card title="Try the parallel research example" icon="users" href="https://github.com/langchain-ai/langgraphjs/tree/main/examples/ui-react/src/examples/parallel-research">
  See a complete implementation of multi-agent streaming with three parallel researchers and distinct visual styling in the `parallel-research` example.
</Card>

## Human-in-the-loop

Handle interrupts when the agent requires human approval for tool execution. Learn more in the [How to handle interrupts](/oss/python/langgraph/interrupts#pause-using-interrupt) guide.

<CodeGroup>
  ```python agent.py theme={null}
  from langchain import create_agent, tool, human_in_the_loop_middleware
  from langchain_openai import ChatOpenAI
  from langgraph.checkpoint.memory import MemorySaver

  model = ChatOpenAI(model="gpt-4o-mini")

  @tool
  def send_email(to: str, subject: str, body: str) -> dict:
      """Send an email. Requires human approval."""
      return {
          "status": "success",
          "content": f'Email sent to {to} with subject "{subject}"',
      }

  @tool
  def delete_file(path: str) -> dict:
      """Delete a file. Requires human approval."""
      return {"status": "success", "content": f'File "{path}" deleted'}

  @tool
  def read_file(path: str) -> dict:
      """Read file contents. No approval needed."""
      return {"status": "success", "content": f"Contents of {path}..."}

  agent = create_agent(
      model=model,
      tools=[send_email, delete_file, read_file],
      middleware=[
          human_in_the_loop_middleware(
              interrupt_on={
                  "send_email": {
                      "allowed_decisions": ["approve", "edit", "reject"],
                      "description": "📧 Review email before sending",
                  },
                  "delete_file": {
                      "allowed_decisions": ["approve", "reject"],
                      "description": "🗑️ Confirm file deletion",
                  },
                  "read_file": False,  # Safe - auto-approved
              }
          ),
      ],
      checkpointer=MemorySaver(),
  )
  ```

  ```tsx Chat.tsx theme={null}
  import { useState } from "react";
  import { useStream } from "@langchain/langgraph-sdk/react";
  import type { AgentState, HITLRequest, HITLResponse } from "./types";
  import { MessageBubble } from "./MessageBubble";

  function HumanInTheLoopChat() {
    const stream = useStream<AgentState, { InterruptType: HITLRequest }>({
      assistantId: "human-in-the-loop",
      apiUrl: "http://localhost:2024",
    });

    const [isProcessing, setIsProcessing] = useState(false);
    const hitlRequest = stream.interrupt?.value as HITLRequest | undefined;

    const handleApprove = async (index: number) => {
      if (!hitlRequest) return;
      setIsProcessing(true);

      try {
        const decisions: HITLResponse["decisions"] =
          hitlRequest.actionRequests.map((_, i) =>
            i === index ? { type: "approve" } : { type: "approve" }
          );

        await stream.submit(null, {
          command: { resume: { decisions } as HITLResponse },
        });
      } finally {
        setIsProcessing(false);
      }
    };

    const handleReject = async (index: number, reason: string) => {
      if (!hitlRequest) return;
      setIsProcessing(true);

      try {
        const decisions: HITLResponse["decisions"] =
          hitlRequest.actionRequests.map((_, i) =>
            i === index
              ? { type: "reject", message: reason }
              : { type: "reject", message: "Rejected along with other actions" }
          );

        await stream.submit(null, {
          command: { resume: { decisions } as HITLResponse },
        });
      } finally {
        setIsProcessing(false);
      }
    };

    return (
      <div>
        {stream.messages.map((message, idx) => (
          <MessageBubble key={message.id ?? idx} message={message} />
        ))}

        {hitlRequest && hitlRequest.actionRequests.length > 0 && (
          <div className="bg-amber-900/20 border border-amber-500/30 rounded-xl p-4 mt-4">
            <h3 className="text-amber-400 font-semibold mb-4">
              Action requires approval
            </h3>

            {hitlRequest.actionRequests.map((action, idx) => (
              <div key={idx} className="bg-neutral-900 rounded-lg p-4 mb-4 last:mb-0">
                <div className="text-sm font-mono text-white mb-2">{action.name}</div>
                <pre className="text-xs bg-black rounded p-2 mb-3 overflow-x-auto">
                  {JSON.stringify(action.args, null, 2)}
                </pre>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleApprove(idx)}
                    disabled={isProcessing}
                    className="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleReject(idx, "User rejected")}
                    disabled={isProcessing}
                    className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-sm rounded-lg"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
  ```

  ```typescript types.ts theme={null}
  import type { Message } from "@langchain/langgraph-sdk";

  // Tool call types matching your Python agent
  export type SendEmailToolCall = {
    name: "send_email";
    args: { to: string; subject: string; body: string };
    id?: string;
  };

  export type DeleteFileToolCall = {
    name: "delete_file";
    args: { path: string };
    id?: string;
  };

  export type ReadFileToolCall = {
    name: "read_file";
    args: { path: string };
    id?: string;
  };

  export type AgentToolCalls = SendEmailToolCall | DeleteFileToolCall | ReadFileToolCall;

  export interface AgentState {
    messages: Message<AgentToolCalls>[];
  }

  // HITL types
  export interface HITLRequest {
    actionRequests: Array<{
      name: string;
      args: Record<string, unknown>;
    }>;
  }

  export interface HITLResponse {
    decisions: Array<
      | { type: "approve" }
      | { type: "reject"; message: string }
      | { type: "edit"; newArgs: Record<string, unknown> }
    >;
  }
  ```
</CodeGroup>

<Card title="Try the human-in-the-loop example" icon="hand" href="https://github.com/langchain-ai/langgraphjs/tree/main/examples/ui-react/src/examples/human-in-the-loop">
  See a complete implementation of approval workflows with approve, reject, and edit actions in the `human-in-the-loop` example.
</Card>

## Reasoning models

<Warning>
  Extended reasoning/thinking support is currently experimental. The streaming interface for reasoning tokens varies by provider (OpenAI vs. Anthropic) and may change as abstractions are developed.
</Warning>

When using models with extended reasoning capabilities (like OpenAI's reasoning models or Anthropic's extended thinking), the thinking process is embedded in the message content. You'll need to extract and display it separately.

<CodeGroup>
  ```python agent.py theme={null}
  from langchain import create_agent
  from langchain_openai import ChatOpenAI

  # Use a reasoning-capable model
  # For OpenAI: o1, o1-mini, o1-preview
  # For Anthropic: claude-sonnet-4-20250514 with extended thinking enabled
  model = ChatOpenAI(model="o1-mini")

  agent = create_agent(
      model=model,
      tools=[],  # Reasoning models work best for complex reasoning tasks
  )
  ```

  ```tsx Chat.tsx theme={null}
  import { useStream } from "@langchain/langgraph-sdk/react";
  import type { AgentState } from "./types";
  import { getReasoningFromMessage, getTextContent } from "./utils";
  import { MessageBubble } from "./MessageBubble";

  function ReasoningChat() {
    const stream = useStream<AgentState>({
      assistantId: "reasoning-agent",
      apiUrl: "http://localhost:2024",
    });

    return (
      <div className="flex flex-col gap-4">
        {stream.messages.map((message, idx) => {
          if (message.type === "ai") {
            const reasoning = getReasoningFromMessage(message);
            const textContent = getTextContent(message);

            return (
              <div key={message.id ?? idx}>
                {reasoning && (
                  <div className="mb-4">
                    <div className="text-xs font-medium text-amber-400/80 mb-2">
                      Reasoning
                    </div>
                    <div className="bg-amber-950/50 border border-amber-500/20 rounded-2xl px-4 py-3">
                      <div className="text-sm text-amber-100/90 whitespace-pre-wrap">
                        {reasoning}
                      </div>
                    </div>
                  </div>
                )}

                {textContent && (
                  <div className="text-neutral-100 whitespace-pre-wrap">
                    {textContent}
                  </div>
                )}
              </div>
            );
          }

          return <MessageBubble key={message.id ?? idx} message={message} />;
        })}

        {stream.isLoading && (
          <div className="flex items-center gap-2 text-amber-400/70">
            <span className="text-sm">Thinking...</span>
          </div>
        )}
      </div>
    );
  }
  ```

  ```typescript types.ts theme={null}
  import type { Message } from "@langchain/langgraph-sdk";

  export interface AgentState {
    messages: Message[];
  }
  ```

  ```typescript utils.ts theme={null}
  import type { Message, AIMessage } from "@langchain/langgraph-sdk";

  /**
   * Extracts reasoning/thinking content from an AI message.
   * Supports both OpenAI reasoning and Anthropic extended thinking.
   */
  export function getReasoningFromMessage(message: Message): string | undefined {
    type MessageWithExtras = AIMessage & {
      additional_kwargs?: {
        reasoning?: {
          summary?: Array<{ type: string; text: string }>;
        };
      };
      contentBlocks?: Array<{ type: string; thinking?: string }>;
    };

    const msg = message as MessageWithExtras;

    // Check for OpenAI reasoning in additional_kwargs
    if (msg.additional_kwargs?.reasoning?.summary) {
      const content = msg.additional_kwargs.reasoning.summary
        .filter((item) => item.type === "summary_text")
        .map((item) => item.text)
        .join("");
      if (content.trim()) return content;
    }

    // Check for Anthropic thinking in contentBlocks
    if (msg.contentBlocks?.length) {
      const thinking = msg.contentBlocks
        .filter((b) => b.type === "thinking" && b.thinking)
        .map((b) => b.thinking)
        .join("\n");
      if (thinking) return thinking;
    }

    // Check for thinking in message.content array
    if (Array.isArray(msg.content)) {
      const thinking = msg.content
        .filter((b): b is { type: "thinking"; thinking: string } =>
          typeof b === "object" && b?.type === "thinking" && "thinking" in b
        )
        .map((b) => b.thinking)
        .join("\n");
      if (thinking) return thinking;
    }

    return undefined;
  }

  /**
   * Extracts text content from a message.
   */
  export function getTextContent(message: Message): string {
    if (typeof message.content === "string") return message.content;
    if (Array.isArray(message.content)) {
      return message.content
        .filter((c): c is { type: "text"; text: string } => c.type === "text")
        .map((c) => c.text)
        .join("");
    }
    return "";
  }
  ```
</CodeGroup>

<Card title="Try the reasoning example" icon="brain" href="https://github.com/langchain-ai/langgraphjs/tree/main/examples/ui-react/src/examples/reasoning-agent">
  See a complete implementation of reasoning token display with OpenAI and Anthropic models in the `reasoning-agent` example.
</Card>

## Custom state types

For custom LangGraph applications, embed your tool call types in your state's messages property.

## Custom transport

For custom API endpoints or non-standard deployments, use the `transport` option with `FetchStreamTransport` to connect to any streaming API.

## Related

* [Streaming overview](/oss/python/langchain/streaming/overview) — Server-side streaming with LangChain agents
* [useStream API Reference](https://reference.langchain.com/javascript/functions/_langchain_langgraph-sdk.react.useStream.html) — Full API documentation
* [Agent Chat UI](/oss/python/langchain/ui) — Pre-built chat interface for LangGraph agents
* [Human-in-the-loop](/oss/python/langchain/human-in-the-loop) — Configuring interrupts for human review
* [Multi-agent systems](/oss/python/langchain/multi-agent) — Building agents with multiple LLMs

***

<Callout icon="pen-to-square" iconType="regular">
  [Edit this page on GitHub](https://github.com/langchain-ai/docs/edit/main/src/oss/langchain/streaming/frontend.mdx) or [file an issue](https://github.com/langchain-ai/docs/issues/new/choose).
</Callout>

<Tip icon="terminal" iconType="regular">
  [Connect these docs](/use-these-docs) to Claude, VSCode, and more via MCP for real-time answers.
</Tip>
