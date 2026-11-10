"""Hours 5–6: concurrent I/O and a pull-based stream of agent events."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable

from .core import Model, demo_model, local_search, make_message, parse_args, record_call

Source = Callable[[str], Awaitable[list[str]]]
AsyncTool = Callable[[str, str], Awaitable[dict]]


async def catalog(query: str) -> list[str]:
    await asyncio.sleep(0.02)  # Simulate waiting for I/O.
    return local_search(query, limit=5)


async def notes(query: str) -> list[str]:
    await asyncio.sleep(0.01)
    return ["青禾自习室", "东桥阅览室"] if query == "安静" else []


async def lookup_sources(query: str, sources: dict[str, Source], *, timeout_s: float) -> list[dict]:
    async def one(name: str, source: Source) -> dict:
        try:
            items = await asyncio.wait_for(source(query), timeout=timeout_s)
        except TimeoutError:
            return {"source": name, "ok": False, "error": "timeout"}
        return {"source": name, "ok": True, "items": items}

    return await asyncio.gather(*(one(name, source) for name, source in sources.items()))


async def async_dispatch(name: str, raw: str, *, lookup=lookup_sources) -> dict:
    if name != "search_places":
        return {"ok": False, "error": "unknown_tool"}
    try:
        args = parse_args(raw)
    except ValueError:
        return {"ok": False, "error": "invalid_args"}
    results = await lookup(args.query, {"catalog": catalog, "notes": notes}, timeout_s=1)
    names = []
    for result in results:
        if result["ok"]:
            names.extend(result["items"])
    if all(not result["ok"] for result in results):
        return {"ok": False, "error": "sources_unavailable", "sources": results}
    return {"ok": True, "items": list(dict.fromkeys(names))[:args.limit], "sources": results}


async def stream_agent(query: str, model: Model = demo_model, tool: AsyncTool = async_dispatch,
                       *, max_steps: int = 3) -> AsyncIterator[dict]:
    history = [make_message("user", query)]
    for _ in range(max_steps):
        action = model(history)
        if action["kind"] == "final":
            yield {"type": "final", "text": action["text"]}
            return
        if action["kind"] != "call":
            raise ValueError("未知动作")
        yield {"type": "tool_call", "id": action["id"], "name": action["name"]}
        result = await tool(action["name"], action["arguments"])
        record_call(history, action, result)
        yield {"type": "tool_result", "id": action["id"], "result": result}
    raise RuntimeError("模型轮数已用尽")
