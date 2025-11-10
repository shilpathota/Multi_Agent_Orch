# mcp_server/server.py
from mcp.server.fastmcp import FastMCP
from typing import List
import ast, operator
import httpx
import os
from dotenv import load_dotenv

load_dotenv()  # <-- add this line

mcp = FastMCP("youtube_tools")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # set this in your env / .env

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

async def fetch_search(client: httpx.AsyncClient, q: str, max_results: int = 10, page_token: str = None):
    params = {
        "part": "snippet",
        "q": q,
        "type": "video",
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
    }
    if page_token:
        params["pageToken"] = page_token
    r = await client.get(SEARCH_URL, params=params, timeout=15.0)
    r.raise_for_status()
    return r.json()

async def fetch_videos_stats(client: httpx.AsyncClient, ids: List[str]):
    params = {
        "part": "snippet,statistics",
        "id": ",".join(ids),
        "key": YOUTUBE_API_KEY,
        "maxResults": len(ids),
    }
    r = await client.get(VIDEOS_URL, params=params, timeout=15.0)
    r.raise_for_status()
    return r.json()

@mcp.tool()  # expose as MCP tool name 'youtube_search'
async def youtube_search(topic: str, k: int = 5, max_results: int = 25) -> List[dict]:
    """
    Search YouTube for `topic` and return top-k videos ranked by (views + likes).
    - topic: search query string
    - k: number of final results
    - max_results: how many search results to fetch (<=50). Fewer search calls = lower quota usage.
    """
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY not set in environment")

    # clamp
    if max_results < 1 or max_results > 50:
        max_results = 25

    async with httpx.AsyncClient() as client:
        # 1) search for videos (this call costs ~100 quota units per docs)
        search_resp = await fetch_search(client, topic, max_results=max_results)
        items = search_resp.get("items", [])
        video_ids = [it["id"]["videoId"] for it in items if it.get("id") and it["id"].get("videoId")]

        if not video_ids:
            return []

        # 2) fetch statistics for the batch of video IDs (videos.list costs ~1 unit)
        # batch into chunks of 50 (API limit)
        videos = []
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i : i + 50]
            vjson = await fetch_videos_stats(client, chunk)
            for v in vjson.get("items", []):
                snippet = v.get("snippet", {})
                stats = v.get("statistics", {})
                videos.append({
                    "title": snippet.get("title"),
                    "url": f"https://www.youtube.com/watch?v={v.get('id')}",
                    "likes": int(stats.get("likeCount") or 0),
                    "views": int(stats.get("viewCount") or 0),
                    "publishedAt": snippet.get("publishedAt"),
                    "channelTitle": snippet.get("channelTitle"),
                    "id": v.get("id"),
                })

        # 3) rank by a simple score (views + likes). You can tweak weighting.
        ranked = sorted(videos, key=lambda r: (r.get("views", 0) + r.get("likes", 0)), reverse=True)

        # return top-k
        return ranked[:k]

@mcp.tool()
async def mock_search(topic: str) -> List[dict]:
    """
    Return mock top items for a topic (no external calls).
    """
    base = [
        {"title": f"{topic} in 7 minutes!", "url": "https://www.youtube.com/watch?v=U-G-mSd4KAE", "likes": 2800, "views": 83_000},
        {"title": f"{topic} in 1 minute", "url": "https://www.youtube.com/watch?v=BE-L7xu8pO4", "likes": 29000, "views": 602_000},
        {"title": f"Python tutorial for Beginners | {topic}", "url": "https://www.youtube.com/watch?v=yNzxXZfkLUA", "likes": 11_000, "views": 684_000},
        {"title": f"Python Tutorial: Decorators - Dynamically Alter The Functionality Of Your Functions", "url": "https://www.youtube.com/watch?v=FsAPt_9Bf3U", "likes": 20_000, "views": 977_000},
        {"title": f"{topic} : The Complete Guide", "url": "https://www.youtube.com/watch?v=QH5fw9kxDQA", "likes": 7600, "views": 183_000},
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
