"""Hours 1–4: one local tool and a bounded, synchronous agent loop."""

import json
from collections.abc import Callable
from dataclasses import dataclass

# All names, tags and observations are invented for this lesson.
PLACES = [
    {"name": "青禾自习室", "tags": ["自习", "安静"]},
    {"name": "北岸图书馆", "tags": ["阅读", "安静"]},
    {"name": "南门咖啡", "tags": ["咖啡", "讨论"]},
]


def make_message(role: str, content: str) -> dict:
    return {"role": role, "content": content}


def find_places(rows: list[dict], query: str, *, limit: int = 2) -> list[str]:
    word = query.strip()
    if not word:
        return []
    matches = []
    for row in rows:
        if word in row["name"] or word in row.get("tags", []):
            matches.append(row["name"])
    return matches[:limit]


@dataclass(frozen=True)
class SearchArgs:
    query: str
    limit: int = 2


def parse_args(raw: str) -> SearchArgs:
    args = json.loads(raw)
    if not isinstance(args, dict) or set(args) - {"query", "limit"}:
        raise ValueError("参数须是仅含 query、limit 的对象")
    query = args.get("query")
    limit = args.get("limit", 2)
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query 须是非空字符串")
    if type(limit) is not int or not 1 <= limit <= 5:
        raise ValueError("limit 须是 1 到 5 的整数")
    return SearchArgs(query.strip(), limit)


def local_search(query: str, *, limit: int = 2) -> list[str]:
    return find_places(PLACES, query, limit=limit)


TOOLS = {"search_places": local_search}


def dispatch(name: str, raw: str) -> dict:
    tool = TOOLS.get(name)
    if tool is None:
        return {"ok": False, "error": "unknown_tool"}
    try:
        args = parse_args(raw)
    except ValueError:
        return {"ok": False, "error": "invalid_args"}
    return {"ok": True, "items": tool(args.query, limit=args.limit)}


# The model's two possible actions use a local teaching format.
Model = Callable[[list[dict]], dict]
Tool = Callable[[str, str], dict]


def demo_model(history: list[dict]) -> dict:
    last = history[-1]
    if last["role"] == "user":
        return {
            "kind": "call", "id": "c1", "name": "search_places",
            "arguments": json.dumps({"query": last["content"]}, ensure_ascii=False),
        }
    observation = json.loads(last["content"])
    if not observation["ok"]:
        answer = f"工具失败（{observation['error']}）"
    else:
        answer = "、".join(observation["items"]) or "没有找到地点"
    return {"kind": "final", "text": answer}


def record_call(history: list[dict], action: dict, result: dict) -> None:
    history.append({"role": "assistant", "call": action})
    history.append({
        "role": "tool", "call_id": action["id"],
        "content": json.dumps(result, ensure_ascii=False),
    })


def run_agent(query: str, model: Model = demo_model, tool: Tool = dispatch,
              *, max_steps: int = 3) -> str:
    history = [make_message("user", query)]
    for _ in range(max_steps):
        action = model(history)
        if action["kind"] == "final":
            return action["text"]
        if action["kind"] != "call":
            raise ValueError("未知动作")
        result = tool(action["name"], action["arguments"])
        record_call(history, action, result)
    raise RuntimeError("模型轮数已用尽")
