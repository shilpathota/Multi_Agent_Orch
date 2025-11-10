# app/mcp_client.py
import json
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    def __init__(self, server_cmd: str = "python", server_args: List[str] = None):
        self.server_cmd = server_cmd
        self.server_args = server_args or ["mcp_server/server.py"]
        self._stack: Optional[AsyncExitStack] = None
        self.session: Optional[ClientSession] = None

    async def __aenter__(self):
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        params = StdioServerParameters(command=self.server_cmd, args=self.server_args)
        read_stream, write_stream = await self._stack.enter_async_context(stdio_client(params))
        self.session = await self._stack.enter_async_context(ClientSession(read_stream, write_stream))
        await self.session.initialize()
        return self

    async def __aexit__(self, *exc):
        await self._stack.aclose()

    async def list_tools(self) -> List[str]:
        resp = await self.session.list_tools()
        return [t.name for t in resp.tools]

    async def call_tool(self, name: str, **kwargs) -> Any:
        result = await self.session.call_tool(name, arguments=kwargs)
        outs = []
        for c in (result.content or []):
            # text parts
            if getattr(c, "text", None):
                outs.append(c.text)
            # typed data parts (e.g., {"type": "application/json", "data": ...})
            elif hasattr(c, "type") and hasattr(c, "data"):
                outs.append({"type": c.type, "data": c.data})

        # normalize common shapes
        if len(outs) == 1:
            one = outs[0]
            # single JSON string -> parse
            if isinstance(one, str):
                s = one.strip()
                if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
                    try:
                        return json.loads(s)
                    except Exception:
                        pass
                return one
            # {type,data} envelope -> unwrap json
            if isinstance(one, dict) and "type" in one and "data" in one:
                if str(one["type"]).lower() in ("application/json", "json"):
                    return one["data"]
                return one
            return one

        # list of JSON strings -> parse each
        if outs and all(isinstance(x, str) for x in outs):
            parsed = []
            for x in outs:
                try:
                    parsed.append(json.loads(x))
                except Exception:
                    parsed.append(x)
            return parsed

        return outs
