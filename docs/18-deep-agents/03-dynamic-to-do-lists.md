# 18.03 Pillar 1: Dynamic To-Do Lists

While basic Large Language Models use implicit reasoning techniques like "Chain-of-Thought" (prompting the model to "think step-by-step"), Deep Agents require something much more concrete to maintain focus over a long time horizon.

This brings us to the first pillar of Deep Agents: **The Explicit Planning Tool.**

---

## Implicit vs. Explicit Planning

- **Implicit Planning:** An LLM generates a text block of thoughts before producing an answer. Once the context window shrinks or the task shifts, those early thoughts are lost or diluted.
- **Explicit Planning:** The Deep Agent is equipped with a specific tool (e.g., `update_todo`) that allows it to deliberately read, write, and modify a structured Markdown to-do list on the file system.

## How the Dynamic Plan Works

In frameworks like LangChain or production tools like Claude Code, the agent actively manages a task list throughout its lifecycle.

1. **Initialization:** When given a massive objective, the agent first breaks it down into a markdown list of pending tasks.
2. **Continuous Updates:** Between tool executions, the agent actively updates the status of tasks (e.g., changing `[ ]` to `[/]` for in-progress, or `[x]` for completed).
3. **Adaptive Error Handling:** If a basic ReAct agent fails a tool call, it often loops blindly until it times out. A Deep Agent with a planning tool realizes the failure, halts the current task, and dynamically rewrites the to-do list to attempt a different approach or gather missing context.

### Real-World Example: Claude Code
If you monitor the network traffic or execution logs of Claude Code (the leading CLI coding agent), you will frequently see it calling an internal tool named `update_todo`. 

While the user never explicitly sees this list in the chat interface, the agent relies entirely on this document to steer itself. It gives the agent a persistent state of progress, much like how human engineers rely on Jira or Trello boards to stay organized without feeling overwhelmed.