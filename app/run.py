# app/run.py
import os, sys
from dotenv import load_dotenv
from mcp_client import MCPClient
from agent import make_planner, make_executor
from graph import build_graph

def main():
    load_dotenv()
    if len(sys.argv) < 2:
        print("Usage: python app/run.py \"<topic or expression>\"")
        sys.exit(1)

    topic = sys.argv[1]
    with MCPClient(server_cmd="python", server_args=["mcp_server/server.py"]).__enter__() as mcp:
        planner = make_planner()

        # inject a sync wrapper around MCP calls for executor node
        def exec_sync_node(state):
            plan = state.get("plan")
            tool, args = plan["tool"], plan["args"]
            res = mcp.call_tool_sync(tool, **args)
            state["result_raw"] = res
            if tool == "mock_search":
                k = state.get("k", 5)
                ranked = sorted(res, key=lambda r: r.get("likes", 0) + r.get("views", 0), reverse=True)[:k]
                state["final"] = ranked
            else:
                state["final"] = res
            return state

        app = build_graph(planner, exec_sync_node)
        out = app.invoke({"topic": topic, "k": 5})
        print("\n=== RESULT ===")
        print(out["final"])

if __name__ == "__main__":
    main()
