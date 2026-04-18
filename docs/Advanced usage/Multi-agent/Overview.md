> ## Documentation Index
> Fetch the complete documentation index at: https://docs.langchain.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Multi-agent

Multi-agent systems coordinate specialized components to tackle complex workflows. However, not every complex task requires this approach — a single agent with the right (sometimes dynamic) tools and prompt can often achieve similar results.

## Why multi-agent?

When developers say they need "multi-agent," they're usually looking for one or more of these capabilities:

* <Icon icon="brain" /> **Context management**: Provide specialized knowledge without overwhelming the model's context window. If context were infinite and latency zero, you could dump all knowledge into a single prompt — but since it's not, you need patterns to selectively surface relevant information.
* <Icon icon="users" /> **Distributed development**: Allow different teams to develop and maintain capabilities independently, composing them into a larger system with clear boundaries.
* <Icon icon="code-branch" /> **Parallelization**: Spawn specialized workers for subtasks and execute them concurrently for faster results.

Multi-agent patterns are particularly valuable when a single agent has too many [tools](/oss/python/langchain/tools) and makes poor decisions about which to use, when tasks require specialized knowledge with extensive context (long prompts and domain-specific tools), or when you need to enforce sequential constraints that unlock capabilities only after certain conditions are met.

<Tip>
  At the center of multi-agent design is **[context engineering](/oss/python/langchain/context-engineering)**—deciding what information each agent sees. The quality of your system depends on ensuring each agent has access to the right data for its task.
</Tip>

## Patterns

Here are the main patterns for building multi-agent systems, each suited to different use cases:

| Pattern                                                                  | How it works                                                                                                                                                                                        |
| ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [**Subagents**](/oss/python/langchain/multi-agent/subagents)             | A main agent coordinates subagents as tools. All routing passes through the main agent, which decides when and how to invoke each subagent.                                                         |
| [**Handoffs**](/oss/python/langchain/multi-agent/handoffs)               | Behavior changes dynamically based on state. Tool calls update a state variable that triggers routing or configuration changes, switching agents or adjusting the current agent's tools and prompt. |
| [**Skills**](/oss/python/langchain/multi-agent/skills)                   | Specialized prompts and knowledge loaded on-demand. A single agent stays in control while loading context from skills as needed.                                                                    |
| [**Router**](/oss/python/langchain/multi-agent/router)                   | A routing step classifies input and directs it to one or more specialized agents. Results are synthesized into a combined response.                                                                 |
| [**Custom workflow**](/oss/python/langchain/multi-agent/custom-workflow) | Build bespoke execution flows with [LangGraph](/oss/python/langgraph/overview), mixing deterministic logic and agentic behavior. Embed other patterns as nodes in your workflow.                    |

### Choosing a pattern

Use this table to match your requirements to the right pattern:

<div className="compact-first-col">
  | Pattern                                                      | Distributed development | Parallelization | Multi-hop | Direct user interaction |
  | ------------------------------------------------------------ | :---------------------: | :-------------: | :-------: | :---------------------: |
  | [**Subagents**](/oss/python/langchain/multi-agent/subagents) |          ⭐⭐⭐⭐⭐          |      ⭐⭐⭐⭐⭐      |   ⭐⭐⭐⭐⭐   |            ⭐            |
  | [**Handoffs**](/oss/python/langchain/multi-agent/handoffs)   |            —            |        —        |   ⭐⭐⭐⭐⭐   |          ⭐⭐⭐⭐⭐          |
  | [**Skills**](/oss/python/langchain/multi-agent/skills)       |          ⭐⭐⭐⭐⭐          |       ⭐⭐⭐       |   ⭐⭐⭐⭐⭐   |          ⭐⭐⭐⭐⭐          |
  | [**Router**](/oss/python/langchain/multi-agent/router)       |           ⭐⭐⭐           |      ⭐⭐⭐⭐⭐      |     —     |           ⭐⭐⭐           |
</div>

* **Distributed development**: Can different teams maintain components independently?
* **Parallelization**: Can multiple agents execute concurrently?
* **Multi-hop**: Does the pattern support calling multiple subagents in series?
* **Direct user interaction**: Can subagents converse directly with the user?

<Tip>
  You can mix patterns! For example, a **subagents** architecture can invoke tools that invoke custom workflows or router agents. Subagents can even use the **skills** pattern to load context on-demand. The possibilities are endless!
</Tip>

### Visual overview

<Tabs>
  <Tab title="Subagents">
    A main agent coordinates subagents as tools. All routing passes through the main agent.

    <Frame>
      <img src="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-subagents.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=f924dde09057820b08f0c577e08fcfe7" alt="Subagents pattern: main agent coordinates subagents as tools" data-og-width="1020" width="1020" data-og-height="734" height="734" data-path="oss/langchain/multi-agent/images/pattern-subagents.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-subagents.png?w=280&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=4e4b085ef1308d78eaff8bf4b3473985 280w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-subagents.png?w=560&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=fede88320efe5b670c511fc9e1f05b5c 560w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-subagents.png?w=840&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=e7c449b2e80796f22530336c3af2a4f5 840w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-subagents.png?w=1100&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=dfb45ccef7213cf137cca21aec90e124 1100w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-subagents.png?w=1650&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=5caaa5cf326cacb4673867768a6cc199 1650w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-subagents.png?w=2500&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=aed1142e36c9d14ad3112fb79b3bd5e7 2500w" />
    </Frame>
  </Tab>

  <Tab title="Handoffs">
    Agents transfer control to each other via tool calls. Each agent can hand off to others or respond directly to the user.

    <Frame>
      <img src="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-handoffs.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=57d935e6a8efab4afb3faa385113f4dd" alt="Handoffs pattern: agents transfer control via tool calls" data-og-width="1568" width="1568" data-og-height="464" height="464" data-path="oss/langchain/multi-agent/images/pattern-handoffs.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-handoffs.png?w=280&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=cfc3b5e2b23a6d1b8915dfb170cd5159 280w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-handoffs.png?w=560&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=71294e02aa7f60075a01ac2faffa77b7 560w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-handoffs.png?w=840&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=c80cb9704fdea99dfec1d02bb94ad471 840w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-handoffs.png?w=1100&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=dcc57244df656014e4ccb49d807a0c05 1100w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-handoffs.png?w=1650&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=dbe088f5b86489170d1bf85ce28c7995 1650w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-handoffs.png?w=2500&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=e10a8a34caedade736d649706421f45e 2500w" />
    </Frame>
  </Tab>

  <Tab title="Skills">
    A single agent loads specialized prompts and knowledge on-demand while staying in control.

    <Frame>
      <img src="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-skills.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=119131d1f19be1f0c6fb1e30f080b427" alt="Skills pattern: single agent loads specialized context on-demand" data-og-width="874" width="874" data-og-height="734" height="734" data-path="oss/langchain/multi-agent/images/pattern-skills.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-skills.png?w=280&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=80b62b337804e3c8b20056bfdad6b74f 280w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-skills.png?w=560&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=7c7645d87fb5c213871d652e111dfa44 560w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-skills.png?w=840&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=6f5f754c599781ba55be20c283d98fcd 840w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-skills.png?w=1100&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=19fe978ad163ef295c837896ceaa1caf 1100w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-skills.png?w=1650&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=9f41caacf89ff268990dc6d1724bd8cb 1650w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-skills.png?w=2500&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=39c6340df7aec5e939cee67d9ad98a40 2500w" />
    </Frame>
  </Tab>

  <Tab title="Router">
    A routing step classifies input and directs it to specialized agents. Results are synthesized.

    <Frame>
      <img src="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-router.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=ceab32819240ba87f3a132357cc78b09" alt="Router pattern: routing step classifies input to specialized agents" data-og-width="1560" width="1560" data-og-height="556" height="556" data-path="oss/langchain/multi-agent/images/pattern-router.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-router.png?w=280&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=857ddacf141ce0b362c08ca8b75bf719 280w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-router.png?w=560&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=4991e9d3838ecd4ff21d800d19b51bff 560w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-router.png?w=840&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=3416f6aae1a525ca9b1d90ab1e91ee0c 840w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-router.png?w=1100&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=1a8ab6586a362986a00571d5f3a2d3a5 1100w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-router.png?w=1650&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=0fe06944e3e7fa6e49342753c4852b1a 1650w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/pattern-router.png?w=2500&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=f82cee5c5666099a5a66b363d76362d8 2500w" />
    </Frame>
  </Tab>
</Tabs>

## Performance comparison

Different patterns have different performance characteristics. Understanding these tradeoffs helps you choose the right pattern for your latency and cost requirements.

**Key metrics:**

* **Model calls**: Number of LLM invocations. More calls = higher latency (especially if sequential) and higher per-request API costs.
* **Tokens processed**: Total [context window](/oss/python/langchain/context-engineering) usage across all calls. More tokens = higher processing costs and potential context limits.

### One-shot request

> **User:** "Buy coffee"

A specialized coffee agent/skill can call a `buy_coffee` tool.

| Pattern                                                      | Model calls | Best fit |
| ------------------------------------------------------------ | :---------: | :------: |
| [**Subagents**](/oss/python/langchain/multi-agent/subagents) |      4      |          |
| [**Handoffs**](/oss/python/langchain/multi-agent/handoffs)   |      3      |     ✅    |
| [**Skills**](/oss/python/langchain/multi-agent/skills)       |      3      |     ✅    |
| [**Router**](/oss/python/langchain/multi-agent/router)       |      3      |     ✅    |

<Tabs>
  <Tab title="Subagents">
    **4 model calls:**

    <Frame>
      <img src="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-subagents.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=bd4eeef41d8870bfa887dd0aa97d0b79" alt="Subagents one-shot: 4 model calls for buy coffee request" data-og-width="1568" width="1568" data-og-height="1124" height="1124" data-path="oss/langchain/multi-agent/images/oneshot-subagents.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-subagents.png?w=280&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=61db98521f4ddbff3470418212a40062 280w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-subagents.png?w=560&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=75249046f64486df8a6c91e1edbc5d62 560w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-subagents.png?w=840&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=216b75c4c0ead34cba19997fd5be0af9 840w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-subagents.png?w=1100&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=3a19d53746a5b198be654ba18de483c1 1100w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-subagents.png?w=1650&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=23ff9b888cad16345faa881cf9aa808e 1650w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-subagents.png?w=2500&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=8976a6ec78331547b646dd15eb90f0a9 2500w" />
    </Frame>
  </Tab>

  <Tab title="Handoffs">
    **3 model calls:**

    <Frame>
      <img src="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-handoffs.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=42ec50519ff04f034050dc77cf869907" alt="Handoffs one-shot: 3 model calls for buy coffee request" data-og-width="1568" width="1568" data-og-height="948" height="948" data-path="oss/langchain/multi-agent/images/oneshot-handoffs.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-handoffs.png?w=280&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=09d4a564874688723b0c3989ca5ba375 280w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-handoffs.png?w=560&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=390c244f99c977b7b6e103baa71e733a 560w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-handoffs.png?w=840&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=c6de66fbc171439126a9fec2078c2026 840w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-handoffs.png?w=1100&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=f4db2c899f5f78607c678eeed60e8d3a 1100w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-handoffs.png?w=1650&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=b43e0e123b612068f814561e7927c20c 1650w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-handoffs.png?w=2500&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=2a680c44fb25d22e6875ec3deab4e6e6 2500w" />
    </Frame>
  </Tab>

  <Tab title="Skills">
    **3 model calls:**

    <Frame>
      <img src="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-skills.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=c8dbf69ed4509e30e5280e7e8a391dab" alt="Skills one-shot: 3 model calls for buy coffee request" data-og-width="1568" width="1568" data-og-height="1036" height="1036" data-path="oss/langchain/multi-agent/images/oneshot-skills.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-skills.png?w=280&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=d20670af1435da771a4c5a01f99b075c 280w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-skills.png?w=560&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=7796c447ae2e3f1688c2f8ecbf3a3770 560w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-skills.png?w=840&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=e440c69718e244529033b329afb56349 840w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-skills.png?w=1100&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=addcee916efbca5df45784b7622fa458 1100w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-skills.png?w=1650&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=bf6608052d6e239b67645dab3676ceed 1650w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-skills.png?w=2500&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=6347e03b16c67944960d58ae54238db0 2500w" />
    </Frame>
  </Tab>

  <Tab title="Router">
    **3 model calls:**

    <Frame>
      <img src="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-router.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=be5707931d3e520e3ae66af544f2cf2f" alt="Router one-shot: 3 model calls for buy coffee request" data-og-width="1568" width="1568" data-og-height="994" height="994" data-path="oss/langchain/multi-agent/images/oneshot-router.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-router.png?w=280&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=070b6ca92336de4dcf999436b8f9501f 280w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-router.png?w=560&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=6e80de6b0ca070638c3cc2db208144e7 560w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-router.png?w=840&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=14f1dd29ae24651f8f229f6b30b49504 840w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-router.png?w=1100&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=39f3c2af6344753e6efa0cfdfabd8d55 1100w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-router.png?w=1650&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=bcb39a16af3f1e479cfccc41bfc9d92a 1650w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/oneshot-router.png?w=2500&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=ae9bc9a3ba4b2c83d1633008212109ef 2500w" />
    </Frame>
  </Tab>
</Tabs>

**Key insight:** Handoffs, Skills, and Router are most efficient for single tasks (3 calls each). Subagents adds one extra call because results flow back through the main agent—this overhead provides centralized control.

### Repeat request

> **Turn 1:** "Buy coffee"
> **Turn 2:** "Buy coffee again"

The user repeats the same request in the same conversation.

<div className="compact-first-col">
  | Pattern                                                      | Turn 2 calls | Total (both turns) | Best fit |
  | ------------------------------------------------------------ | :----------: | :----------------: | :------: |
  | [**Subagents**](/oss/python/langchain/multi-agent/subagents) |       4      |          8         |          |
  | [**Handoffs**](/oss/python/langchain/multi-agent/handoffs)   |       2      |          5         |     ✅    |
  | [**Skills**](/oss/python/langchain/multi-agent/skills)       |       2      |          5         |     ✅    |
  | [**Router**](/oss/python/langchain/multi-agent/router)       |       3      |          6         |          |
</div>

<Tabs>
  <Tab title="Subagents">
    **4 calls again → 8 total**

    * Subagents are **stateless by design**—each invocation follows the same flow
    * The main agent maintains conversation context, but subagents start fresh each time
    * This provides strong context isolation but repeats the full flow
  </Tab>

  <Tab title="Handoffs">
    **2 calls → 5 total**

    * The coffee agent is **still active** from turn 1 (state persists)
    * No handoff needed—agent directly calls `buy_coffee` tool (call 1)
    * Agent responds to user (call 2)
    * **Saves 1 call by skipping the handoff**
  </Tab>

  <Tab title="Skills">
    **2 calls → 5 total**

    * The skill context is **already loaded** in conversation history
    * No need to reload—agent directly calls `buy_coffee` tool (call 1)
    * Agent responds to user (call 2)
    * **Saves 1 call by reusing loaded skill**
  </Tab>

  <Tab title="Router">
    **3 calls again → 6 total**

    * Routers are **stateless**—each request requires an LLM routing call
    * Turn 2: Router LLM call (1) → Milk agent calls buy\_coffee (2) → Milk agent responds (3)
    * Can be optimized by wrapping as a tool in a stateful agent
  </Tab>
</Tabs>

**Key insight:** Stateful patterns (Handoffs, Skills) save 40-50% of calls on repeat requests. Subagents maintain consistent cost per request—this stateless design provides strong context isolation but at the cost of repeated model calls.

### Multi-domain

> **User:** "Compare Python, JavaScript, and Rust for web development"

Each language agent/skill contains \~2000 tokens of documentation. All patterns can make parallel tool calls.

| Pattern                                                      | Model calls | Total tokens | Best fit |
| ------------------------------------------------------------ | :---------: | :----------: | :------: |
| [**Subagents**](/oss/python/langchain/multi-agent/subagents) |      5      |     \~9K     |     ✅    |
| [**Handoffs**](/oss/python/langchain/multi-agent/handoffs)   |      7+     |    \~14K+    |          |
| [**Skills**](/oss/python/langchain/multi-agent/skills)       |      3      |     \~15K    |          |
| [**Router**](/oss/python/langchain/multi-agent/router)       |      5      |     \~9K     |     ✅    |

<Tabs>
  <Tab title="Subagents">
    **5 calls, \~9K tokens**

    <Frame>
      <img src="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-subagents.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=9cc5d2d46bfa98b7ceeacdc473512c94" alt="Subagents multi-domain: 5 calls with parallel execution" data-og-width="1568" width="1568" data-og-height="1232" height="1232" data-path="oss/langchain/multi-agent/images/multidomain-subagents.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-subagents.png?w=280&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=5fe561bdba901844e7ff2f33c5b755b9 280w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-subagents.png?w=560&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=616e2db7119923be7df575f0f440cf94 560w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-subagents.png?w=840&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=87e0bf0604e4f575c405bfcc6a25b7a9 840w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-subagents.png?w=1100&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=a78066e1fed60cc1120b3c241c08421b 1100w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-subagents.png?w=1650&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=935dd968e204ca6f51d7be2712211bf7 1650w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-subagents.png?w=2500&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=dd73db2d3a95b61932d245d8599d59ab 2500w" />
    </Frame>

    Each subagent works in **isolation** with only its relevant context. Total: **9K tokens**.
  </Tab>

  <Tab title="Handoffs">
    **7+ calls, \~14K+ tokens**

    <Frame>
      <img src="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-handoffs.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=7ede44260515e49ff1d0217f0030d66d" alt="Handoffs multi-domain: 7+ sequential calls" data-og-width="1568" width="1568" data-og-height="834" height="834" data-path="oss/langchain/multi-agent/images/multidomain-handoffs.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-handoffs.png?w=280&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=e486eb835bf7487d767ecaa1ca22df59 280w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-handoffs.png?w=560&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=6e2bece8beadc12596c98c26107f32d2 560w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-handoffs.png?w=840&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=66c600cc7a50f250f48ae5e987d7b42f 840w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-handoffs.png?w=1100&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=9e1e2baa021f2b85c159c48cf21a22e8 1100w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-handoffs.png?w=1650&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=9b659576b5308ee2145dd46f1136e7ed 1650w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-handoffs.png?w=2500&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=07dfd7985275da31defbc8be51193f50 2500w" />
    </Frame>

    Handoffs executes **sequentially**—can't research all three languages in parallel. Growing conversation history adds overhead. Total: **\~14K+ tokens**.
  </Tab>

  <Tab title="Skills">
    **3 calls, \~15K tokens**

    <Frame>
      <img src="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-skills.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=2162584b6076aee83396760bc6de4cf4" alt="Skills multi-domain: 3 calls with accumulated context" data-og-width="1560" width="1560" data-og-height="988" height="988" data-path="oss/langchain/multi-agent/images/multidomain-skills.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-skills.png?w=280&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=14bca819ac7fb2d20c4852c2ee0c938f 280w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-skills.png?w=560&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=4ff1878944fb9794a96d31413b0ce21a 560w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-skills.png?w=840&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=cf16e178a983c0e78b79bacd9b214e23 840w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-skills.png?w=1100&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=24df8f7395f2dd07b8ee824f74a41219 1100w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-skills.png?w=1650&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=7c4e2b20202d7c90da0c035e7b875768 1650w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-skills.png?w=2500&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=a100546e4fac49bef2f44e09dc56cf01 2500w" />
    </Frame>

    After loading, **every subsequent call processes all 6K tokens of skill documentation**. Subagents processes 67% fewer tokens overall due to context isolation. Total: **15K tokens**.
  </Tab>

  <Tab title="Router">
    **5 calls, \~9K tokens**

    <Frame>
      <img src="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-router.png?fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=ef11573bc65e5a2996d671bb3030ca6b" alt="Router multi-domain: 5 calls with parallel execution" data-og-width="1568" width="1568" data-og-height="1052" height="1052" data-path="oss/langchain/multi-agent/images/multidomain-router.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-router.png?w=280&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=d29d6a10afd985bddd9ee1ca53f16375 280w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-router.png?w=560&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=bd198b0a507d183c55142eae8689e8b4 560w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-router.png?w=840&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=85fa4448d00b20cf476ce782031498d4 840w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-router.png?w=1100&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=fd03ff3623e5e0aba9adff7103f85969 1100w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-router.png?w=1650&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=5b72257f679e5e837af544548084b6bc 1650w, https://mintcdn.com/langchain-5e9cc07a/CRpSg52QqwDx49Bw/oss/langchain/multi-agent/images/multidomain-router.png?w=2500&fit=max&auto=format&n=CRpSg52QqwDx49Bw&q=85&s=d00dccb3ad36508a4a50d52f093b3e10 2500w" />
    </Frame>

    Router uses an **LLM for routing**, then invokes agents in parallel. Similar to Subagents but with explicit routing step. Total: **9K tokens**.
  </Tab>
</Tabs>

**Key insight:** For multi-domain tasks, patterns with parallel execution (Subagents, Router) are most efficient. Skills has fewer calls but high token usage due to context accumulation. Handoffs is inefficient here—it must execute sequentially and can't leverage parallel tool calling for consulting multiple domains simultaneously.

### Summary

Here's how patterns compare across all three scenarios:

<div className="compact-first-col">
  | Pattern                                                      | One-shot | Repeat request |      Multi-domain     |
  | ------------------------------------------------------------ | :------: | :------------: | :-------------------: |
  | [**Subagents**](/oss/python/langchain/multi-agent/subagents) |  4 calls |  8 calls (4+4) |   5 calls, 9K tokens  |
  | [**Handoffs**](/oss/python/langchain/multi-agent/handoffs)   |  3 calls |  5 calls (3+2) | 7+ calls, 14K+ tokens |
  | [**Skills**](/oss/python/langchain/multi-agent/skills)       |  3 calls |  5 calls (3+2) |  3 calls, 15K tokens  |
  | [**Router**](/oss/python/langchain/multi-agent/router)       |  3 calls |  6 calls (3+3) |   5 calls, 9K tokens  |
</div>

**Choosing a pattern:**

<div className="compact-first-col">
  | Optimize for          | [Subagents](/oss/python/langchain/multi-agent/subagents) | [Handoffs](/oss/python/langchain/multi-agent/handoffs) | [Skills](/oss/python/langchain/multi-agent/skills) | [Router](/oss/python/langchain/multi-agent/router) |
  | --------------------- | :------------------------------------------------------: | :----------------------------------------------------: | :------------------------------------------------: | :------------------------------------------------: |
  | Single requests       |                                                          |                            ✅                           |                          ✅                         |                          ✅                         |
  | Repeat requests       |                                                          |                            ✅                           |                          ✅                         |                                                    |
  | Parallel execution    |                             ✅                            |                                                        |                                                    |                          ✅                         |
  | Large-context domains |                             ✅                            |                                                        |                                                    |                          ✅                         |
  | Simple, focused tasks |                                                          |                                                        |                          ✅                         |                                                    |
</div>

***

<Callout icon="pen-to-square" iconType="regular">
  [Edit this page on GitHub](https://github.com/langchain-ai/docs/edit/main/src/oss/langchain/multi-agent/index.mdx) or [file an issue](https://github.com/langchain-ai/docs/issues/new/choose).
</Callout>

<Tip icon="terminal" iconType="regular">
  [Connect these docs](/use-these-docs) to Claude, VSCode, and more via MCP for real-time answers.
</Tip>
