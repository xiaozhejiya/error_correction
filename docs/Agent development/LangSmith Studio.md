> ## Documentation Index
> Fetch the complete documentation index at: https://docs.langchain.com/llms.txt
> Use this file to discover all available pages before exploring further.

# LangSmith Studio

When building agents with LangChain locally, it's helpful to visualize what's happening inside your agent, interact with it in real-time, and debug issues as they occur. **LangSmith Studio** is a free visual interface for developing and testing your LangChain agents from your local machine.

Studio connects to your locally running agent to show you each step your agent takes: the prompts sent to the model, tool calls and their results, and the final output. You can test different inputs, inspect intermediate states, and iterate on your agent's behavior without additional code or deployment.

This pages describes how to set up Studio with your local LangChain agent.

## Prerequisites

Before you begin, ensure you have the following:

* **A LangSmith account**: Sign up (for free) or log in at [smith.langchain.com](https://smith.langchain.com).
* **A LangSmith API key**: Follow the [Create an API key](/langsmith/create-account-api-key#create-an-api-key) guide.
* If you don't want data [traced](/langsmith/observability-concepts#traces) to LangSmith, set `LANGSMITH_TRACING=false` in your application's `.env` file. With tracing disabled, no data leaves your local server.

## Set up local Agent server

### 1. Install the LangGraph CLI

The [LangGraph CLI](/langsmith/cli) provides a local development server (also called [Agent Server](/langsmith/agent-server)) that connects your agent to Studio.

```shell  theme={null}
# Python >= 3.11 is required.
pip install --upgrade "langgraph-cli[inmem]"
```

### 2. Prepare your agent

If you already have a LangChain agent, you can use it directly. This example uses a simple email agent:

```python title="agent.py" theme={null}
from langchain.agents import create_agent

def send_email(to: str, subject: str, body: str):
    """Send an email"""
    email = {
        "to": to,
        "subject": subject,
        "body": body
    }
    # ... email sending logic

    return f"Email sent to {to}"

agent = create_agent(
    "gpt-4o",
    tools=[send_email],
    system_prompt="You are an email assistant. Always use the send_email tool.",
)
```

### 3. Environment variables

Studio requires a LangSmith API key to connect your local agent. Create a `.env` file in the root of your project and add your API key from [LangSmith](https://smith.langchain.com/settings).

<Warning>
  Ensure your `.env` file is not committed to version control, such as Git.
</Warning>

```bash .env theme={null}
LANGSMITH_API_KEY=lsv2...
```

### 4. Create a LangGraph config file

The LangGraph CLI uses a configuration file to locate your agent and manage dependencies. Create a `langgraph.json` file in your app's directory:

```json title="langgraph.json" theme={null}
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent.py:agent"
  },
  "env": ".env"
}
```

The [`create_agent`](https://reference.langchain.com/python/langchain/agents/#langchain.agents.create_agent) function automatically returns a compiled LangGraph graph, which is what the `graphs` key expects in the configuration file.

<Info>
  For detailed explanations of each key in the JSON object of the configuration file, refer to the [LangGraph configuration file reference](/langsmith/cli#configuration-file).
</Info>

At this point, the project structure will look like this:

```bash  theme={null}
my-app/
├── src
│   └── agent.py
├── .env
└── langgraph.json
```

### 5. Install dependencies

Install your project dependencies from the root directory:

<CodeGroup>
  ```shell pip theme={null}
  pip install langchain langchain-openai 
  ```

  ```shell uv theme={null}
  uv add langchain langchain-openai
  ```
</CodeGroup>

### 6. View your agent in Studio

Start the development server to connect your agent to Studio:

```shell  theme={null}
langgraph dev
```

<Warning>
  Safari blocks `localhost` connections to Studio. To work around this, run the above command with `--tunnel` to access Studio via a secure tunnel.
</Warning>

Once the server is running, your agent is accessible both via API at `http://127.0.0.1:2024` and through the Studio UI at `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`:

<Frame>
    <img src="https://mintcdn.com/langchain-5e9cc07a/TCDks4pdsHdxWmuJ/oss/images/studio_create-agent.png?fit=max&auto=format&n=TCDks4pdsHdxWmuJ&q=85&s=ebd259e9fa24af7d011dfcc568f74be2" alt="Agent view in the Studio UI" data-og-width="2836" width="2836" data-og-height="1752" height="1752" data-path="oss/images/studio_create-agent.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/langchain-5e9cc07a/TCDks4pdsHdxWmuJ/oss/images/studio_create-agent.png?w=280&fit=max&auto=format&n=TCDks4pdsHdxWmuJ&q=85&s=cf9c05bdd08661d4d546c540c7a28cbe 280w, https://mintcdn.com/langchain-5e9cc07a/TCDks4pdsHdxWmuJ/oss/images/studio_create-agent.png?w=560&fit=max&auto=format&n=TCDks4pdsHdxWmuJ&q=85&s=484b2fd56957d048bd89280ce97065a0 560w, https://mintcdn.com/langchain-5e9cc07a/TCDks4pdsHdxWmuJ/oss/images/studio_create-agent.png?w=840&fit=max&auto=format&n=TCDks4pdsHdxWmuJ&q=85&s=92991302ac24604022ab82ac22729f68 840w, https://mintcdn.com/langchain-5e9cc07a/TCDks4pdsHdxWmuJ/oss/images/studio_create-agent.png?w=1100&fit=max&auto=format&n=TCDks4pdsHdxWmuJ&q=85&s=ed366abe8dabc42a9d7c300a591e1614 1100w, https://mintcdn.com/langchain-5e9cc07a/TCDks4pdsHdxWmuJ/oss/images/studio_create-agent.png?w=1650&fit=max&auto=format&n=TCDks4pdsHdxWmuJ&q=85&s=d5865d3c4b0d26e9d72e50d474547a63 1650w, https://mintcdn.com/langchain-5e9cc07a/TCDks4pdsHdxWmuJ/oss/images/studio_create-agent.png?w=2500&fit=max&auto=format&n=TCDks4pdsHdxWmuJ&q=85&s=6b254add2df9cc3c10ac0c2bcb3a589c 2500w" />
</Frame>

With Studio connected to your local agent, you can iterate quickly on your agent's behavior. Run a test input, inspect the full execution trace including prompts, tool arguments, return values, and token/latency metrics. When something goes wrong, Studio captures exceptions with the surrounding state to help you understand what happened.

The development server supports hot-reloading—make changes to prompts or tool signatures in your code, and Studio reflects them immediately. Re-run conversation threads from any step to test your changes without starting over. This workflow scales from simple single-tool agents to complex multi-node graphs.

For more information on how to run Studio, refer to the following guides in the [LangSmith docs](/langsmith/home):

* [Run application](/langsmith/use-studio#run-application)
* [Manage assistants](/langsmith/use-studio#manage-assistants)
* [Manage threads](/langsmith/use-studio#manage-threads)
* [Iterate on prompts](/langsmith/observability-studio)
* [Debug LangSmith traces](/langsmith/observability-studio#debug-langsmith-traces)
* [Add node to dataset](/langsmith/observability-studio#add-node-to-dataset)

## Video guide

<Frame>
  <iframe className="w-full aspect-video rounded-xl" src="https://www.youtube.com/embed/Mi1gSlHwZLM?si=zA47TNuTC5aH0ahd" title="Studio" frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
</Frame>

<Tip>
  For more information about local and deployed agents, see [Set up local Agent Server](/oss/python/langchain/studio#setup-local-agent-server) and [Deploy](/oss/python/langchain/deploy).
</Tip>

***

<Callout icon="pen-to-square" iconType="regular">
  [Edit this page on GitHub](https://github.com/langchain-ai/docs/edit/main/src/oss/langchain/studio.mdx) or [file an issue](https://github.com/langchain-ai/docs/issues/new/choose).
</Callout>

<Tip icon="terminal" iconType="regular">
  [Connect these docs](/use-these-docs) to Claude, VSCode, and more via MCP for real-time answers.
</Tip>
