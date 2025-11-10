# app/run.py
import sys, json, asyncio
from dotenv import load_dotenv
from mcp_client import MCPClient
from agent import make_planner
from graph import build_graph

async def main_async():
    load_dotenv()
    topic = sys.argv[1] if len(sys.argv) > 1 else "python decorators"

    async with MCPClient(server_cmd="python", server_args=["mcp_server/server.py"]) as mcp:
        planner = make_planner()

        async def exec_node(state):
            plan = state["plan"]
            tool, args = plan["tool"], plan["args"]
            res = await mcp.call_tool("mock_search", topic=topic, k=5, max_results=5)

            # ---- Normalize result for mock_search ----
            if tool == "mock_search":
                # res could be: list[str JSON], str(JSON array), list[dict], dict
                if isinstance(res, str):
                    try:
                        res = json.loads(res)
                    except Exception:
                        res = [{"title": res, "likes": 0, "views": 0, "url": ""}]
                if isinstance(res, dict):
                    res = [res]
                if isinstance(res, list):
                    fixed = []
                    for item in res:
                        if isinstance(item, str):
                            try:
                                item = json.loads(item)
                            except Exception:
                                item = {"title": item, "likes": 0, "views": 0, "url": ""}
                        fixed.append(item)
                    res = fixed
                state["result_raw"] = res

                k = state.get("k", 5)
                ranked = sorted(
                    res, key=lambda r: r.get("likes", 0) + r.get("views", 0),
                    reverse=True
                )[:k]
                state["final"] = ranked
            else:
                state["result_raw"] = res
                state["final"] = res
            return state

        app = build_graph(planner, exec_node)
        initial = {"topic": topic, "k": 5}
        print("Initial state ->", initial, flush=True)
        out = await app.ainvoke(initial)

        print("\n=== RESULT ===")
        print(out["final"])

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
