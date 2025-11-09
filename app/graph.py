# app/graph.py
from typing import Dict, Any
from langgraph.graph import StateGraph, END

def build_graph(planner_node, executor_node):
    class S(dict): pass  # minimal dict state

    graph = StateGraph(S)
    graph.add_node("plan", planner_node)
    graph.add_node("execute", executor_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", END)
    return graph.compile()
