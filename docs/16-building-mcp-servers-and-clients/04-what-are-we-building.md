# 16.04 What are we building?

Now that our custom STDIO (Math) and SSE (Weather) servers are written, we will integrate them with the **LangChain Multi-MCP Server Client**.

---

## Why use SSE Servers?

While STDIO servers are fantastic for local execution, communicating entirely through standard execution pipes over a terminal, **SSE Servers operate over HTTP**. 

The standard deployment architecture for an SSE server is to host it remotely in the cloud. By deploying an SSE server to an Enterprise cloud environment, every agent and team member in your organization can connect their local clients to a single source of truth for your internal tools.

### The Missing Piece: Authorization & RBAC

When you deploy a server to the public internet or an enterprise cloud, you do not want to give access to everyone anonymously. You need:
- **Authentication:** Verifying who the user is.
- **Role-Based Access Control (RBAC):** Restricting exactly which tools a specific user can invoke based on their role.

> [!WARNING]
> Native Auth and RBAC are not yet fully standardized components of the core Model Context Protocol design at this time. As the protocol matures and formal security specs are adopted, we will revisit cloud deployments with full authentication.