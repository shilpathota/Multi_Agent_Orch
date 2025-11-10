# app/agents.py
import json, os
from pydantic import BaseModel
from typing import Dict, Any

from langchain_ollama import ChatOllama

MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

class Plan(BaseModel):
    tool: str
    args: Dict[str, Any]

def get_llm():
    # ChatOllama talks to http://localhost:11434 by default
    return ChatOllama(model=MODEL, temperature=0)

PLANNER_SYSTEM = """You are a planner. 
Given a user topic, choose ONE MCP tool to call: either 'mock_search' or 'calc'.
Return STRICT JSON with keys: tool, args. 
- For 'mock_search', args = {"topic": "<topic>"}.
- For 'calc', args = {"expression": "<arithmetic expression>"}.
No extra text.
"""


def make_planner():
    llm = get_llm()

    def plan_node(state: Dict[str, Any]) -> Dict[str, Any]:
        # DEBUG LINE (remove later)
        print("Planner received state:", state, flush=True)
        topic = state.get("topic")
        if not topic:
            # Give a readable error instead of KeyError
            raise ValueError(
                "Missing 'topic' in state. Invoke the graph with {'topic': '<your topic>'}."
            )
        prompt = f"{PLANNER_SYSTEM}\nUser topic: {topic}\nJSON:"
        resp = llm.invoke(prompt).content.strip()
        try:
            data = json.loads(resp)
            plan = Plan(**data)
        except Exception:
            plan = Plan(tool="mock_search", args={"topic": topic})
        state["plan"] = plan.model_dump()
        return state

    return plan_node

def make_executor(mcp_client):
    def exec_node(state: Dict[str, Any]) -> Dict[str, Any]:
        plan = state["plan"]
        tool, args = plan["tool"], plan["args"]
        result = mcp_client.call_tool_sync(tool, **args)  # we'll add sync helper
        state["result_raw"] = result
        # Very light post-format:
        if tool == "mock_search":
            # pick top-k by simple score (likes+views) just to show ranking
            k = state.get("k", 5)
            ranked = sorted(result, key=lambda r: r.get("likes", 0) + r.get("views", 0), reverse=True)[:k]
            state["final"] = ranked
        else:
            state["final"] = result
        return state
    return exec_node
