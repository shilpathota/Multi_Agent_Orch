# app/graph.py
from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END


class GraphState(TypedDict, total=False):
    topic: str
    k: int
    plan: Dict[str, Any]
    result_raw: Any
    final: List[Dict[str, Any]]

def build_graph(planner_node, executor_node):

    graph = StateGraph(GraphState)
    graph.add_node("plan", planner_node)
    graph.add_node("execute", executor_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", END)
    return graph.compile()
