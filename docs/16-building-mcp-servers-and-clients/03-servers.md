# 16.03 Creating Custom MCP Servers

Before building our LangChain client, we need to implement the servers that this client will communicate with. We will write two simple MCP servers demonstrating both forms of transport protocols: **STDIO** (Standard I/O) and **SSE** (Server-Sent Events).

---

## Project Structure Setup

First, create a package to hold your server implementations.

```bash
mkdir servers
touch servers/__init__.py
```

---

## Server 1: The Math Server (STDIO)

Our first server will expose two basic tools: `add` and `multiply`. It communicates purely over standard input/output.

> [!IMPORTANT]
> Name this file `math_server.py`. **Do not name it `math.py`.** If you name it `math.py`, Python will shadow its own built-in `math` library and cause massive debugging headaches.

Create `servers/math_server.py`:

(You can copy the boilerplate logic from the LangChain MCP adapters repository).

This server uses **STDIO transport**. When spun up, it reads from `stdin` and writes JSON-RPC to `stdout`.

To start it locally:
```bash
uv run servers/math_server.py
```

---

## Server 2: The Weather Server (SSE)

Our second server exposes a dummy `get_weather` tool (which statically returns "hot as hell").

Unlike the Math server, this server uses **Server-Sent Events (SSE)**.
- Communication happens over HTTP.
- The client makes `POST` requests, and the server pushes messages asynchronously.

Create `servers/weather_server.py`. In the MCP configuration logic for this file, you flag the transport layer as SSE instead of STDIO.

Because it runs over HTTP, triggering this script spins up a local web server (usually on port `8000`).

To start it locally:
```bash
uv run servers/weather_server.py
```

Once running, the server listens for incoming HTTP connections on `localhost:8000`. We are now ready to build a client to connect to both of these servers.