# app/mcp_client.py
import asyncio
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
        stdio = await self._stack.enter_async_context(stdio_client(params))
        self.stdio, self.write = stdio
        self.session = await self._stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()
        return self

    async def __aexit__(self, *exc):
        await self._stack.aclose()

    async def list_tools(self) -> List[str]:
        resp = await self.session.list_tools()
        return [t.name for t in resp.tools]

    async def call_tool(self, name: str, **kwargs) -> Any:
        result = await self.session.call_tool(name, arguments=kwargs)
        # gather text parts or typed objects
        outs = []
        for c in (result.content or []):
            if hasattr(c, "text") and c.text:
                outs.append(c.text)
            elif hasattr(c, "type") and hasattr(c, "data"):
                outs.append({"type": c.type, "data": c.data})
        return outs[0] if len(outs) == 1 else outs
