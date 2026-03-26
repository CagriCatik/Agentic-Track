# 18.02 Taxonomy of Agents: Shallow vs. Deep

Before building Deep Agents, we must understand the landscape of AI agents currently in production and why the original agent architectures are insufficient for complex tasks.

---

## 1. The Baseline: Agentic Applications (e.g., Hybrid RAG)

At the simplest level of the agent domain, we have **Agentic Applications**. In these workflows, the LLM makes minor routing decisions—for example, deciding whether to perform a semantic search or to rephrase a user query before retrieving documents. While intelligent, the LLM acts as a simple router rather than an autonomous worker.

---

## 2. Shallow Agents (The ReAct Loop)

The architecture that started the agentic revolution is the **ReAct (Reason + Act)** loop. 

**How it works:**
1. The LLM acts as the brain.
2. It uses function calling to select a tool.
3. It executes the tool, observes the output, and feeds it back into its context.
4. It repeats this loop until it reaches a final answer.

**Why it is "Shallow":**
While the ReAct loop is excellent for simple tasks (like "Book me a flight"), it breaks down completely when assigned a long-horizon task (like "Research and write a 10-page thesis on quantum physics").

The limitation is the **Context Window**. 
In a standard ReAct loop, every single tool execution and observation is appended to the main prompt. If an agent loops 50 times, the prompt becomes massive. This leads to **Context Rot**:
- **Context Confusion & Contradiction:** The LLM loses the "signal in the noise" and hallucinates.
- **Latency & Cost:** The token count explodes, making each subsequent API call slower and more expensive.

> [!WARNING]
> The basic ReAct loop is a "Shallow Agent." It should absolutely be used in production for short, defined tasks, but it is not capable of long-horizon autonomy.

---

## 3. Deep Agents

Deep Agents are the bleeding edge of AI orchestration. They are capable of executing complex, multi-layered tasks that can run seamlessly for minutes, hours, or even days. 

Deep Agents can pause execution, ask the user for clarifying input, wait, and resume exactly where they left off.

**Examples of Deep Agents in Production:**
- **Deep Research Agents:** Tools like Perplexity's deep search, ChatGPT's research mode, or the open-source `GPT-Researcher`.
- **Coding Agents:** CLI tools like Claude Code, Devin, and Cursor. These agents can plan a feature, write code, run terminal commands, execute tests, capture screenshots of a browser, and fix their own bugs—mimicking a human Software Engineer.

### The Innovation is in the Application Layer

Currently, foundational LLM models (like GPT-4 or Claude 3.5) are improving linearly and gradually. However, the capabilities of *agents* are improving exponentially. 

This is because the true innovation right now is happening in the **Application Layer**. The magic of Claude Code is not just the Claude model itself—it is the brilliant orchestration, tooling, and context management wrapped around the model by the application developers. 

---

## The Four Pillars of a Deep Agent

To solve the "Context Rot" problem of Shallow Agents and successfully execute long-horizon tasks, Deep Agents must utilize smart context engineering. 

If you look under the hood of any state-of-the-art Deep Agent today, you will almost always find these four architectural pillars:

1. **A Planning Tool (Dynamic To-Do Lists):** An explicit mechanism for the agent to track progress and plan future steps.
2. **Sub-Agents (Hierarchical Delegation):** The ability for the main agent to spawn isolated child agents to handle specific chunks of work, preventing the main context window from bloating.
3. **A Shared File System:** A persistent storage layer where the agent can save intermediate results (disk space instead of prompt space).
4. **A Monstrous System Prompt:** A highly-engineered, massive set of base instructions dictating exact behaviors and constraints.

We will explore the implementation of these four pillars deeply in the upcoming lessons.