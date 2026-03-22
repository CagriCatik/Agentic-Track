# 12.03 — Section Resources

## Overview

This lesson provides references to the academic paper, implementation resources, and tools used throughout the Reflexion Agent section.

---

## Research Paper

| Resource | Details |
|---|---|
| **Paper** | *Reflexion: Language Agents with Verbal Reinforcement Learning* |
| **Authors** | Noah Shinn, Federico Cassano, Ashwin Gopinath, Karthik Narasimhan, Shunyu Yao |
| **Institutions** | Northeastern University, MIT, Princeton University |
| **Key Idea** | Agents that verbally reflect on task feedback signals, maintaining a self-reflective text in episodic memory to improve decision-making in subsequent trials |

The Reflexion paper formalizes the pattern of **iterative self-improvement through verbal self-reflection** — exactly what this section implements.

---

## Implementation References

| Resource | Description |
|---|---|
| **LangChain Blog** | The LangChain team (particularly Lance Martin) published a blog post implementing the Reflexion architecture with LangGraph. This course's implementation is a refactored, simplified version of that work. |
| **Course Repository** | All code for this section is available in the course repository under `projects/reflexion-agent` branch. |

---

## Tools & Services

| Tool | Purpose | Link |
|---|---|---|
| **OpenAI GPT-4 Turbo** | LLM for article generation, self-critique, and revision | [platform.openai.com](https://platform.openai.com) |
| **Tavily Search API** | Web search engine optimized for LLM applications | [tavily.com](https://tavily.com) |
| **LangSmith** | Tracing and observability for LangChain/LangGraph | [smith.langchain.com](https://smith.langchain.com) |
| **LangGraph** | Graph-based workflow orchestration framework | [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/) |
