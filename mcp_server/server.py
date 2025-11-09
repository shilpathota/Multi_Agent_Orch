# mcp_server/server.py
from mcp.server.fastmcp import FastMCP
from typing import List
import ast, operator

mcp = FastMCP("local_tools")

@mcp.tool()
async def mock_search(topic: str) -> List[dict]:
    """
    Return mock top items for a topic (no external calls).
    """
    base = [
        {"title": f"{topic} — Beginner’s Guide", "url": "https://example.com/1", "likes": 1280, "views": 120_000},
        {"title": f"Advanced {topic} in 10 minutes", "url": "https://example.com/2", "likes": 980, "views": 95_000},
        {"title": f"{topic} Mistakes to Avoid", "url": "https://example.com/3", "likes": 720, "views": 70_000},
        {"title": f"{topic} Crash Course", "url": "https://example.com/4", "likes": 1500, "views": 220_000},
        {"title": f"Top Tools for {topic}", "url": "https://example.com/5", "likes": 640, "views": 61_000},
    ]
    return base

# very small safe-eval for +,-,*,/,(), integers
_ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.USub: operator.neg}
def _safe_eval(node):
    if isinstance(node, ast.Num): return node.n
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ops: return _ops[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _ops: return _ops[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    raise ValueError("Only simple arithmetic is allowed.")

@mcp.tool()
async def calc(expression: str) -> float:
    """
    Evaluate simple arithmetic like '1 + 2*(3-1)'.
    """
    tree = ast.parse(expression, mode="eval")
    return float(_safe_eval(tree.body))

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
