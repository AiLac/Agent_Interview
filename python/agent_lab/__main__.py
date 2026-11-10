"""Run from python/: python -m agent_lab [--stream] [query]."""

import argparse
import asyncio
import json

from .advanced import stream_agent
from .core import run_agent


async def show_events(query: str, stream) -> None:
    async for event in stream(query):
        print(json.dumps(event, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="离线地点查询 Agent 教学案例")
    parser.add_argument("query", nargs="?", default="安静")
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--practice", action="store_true", help="运行自己写的 practice.py")
    args = parser.parse_args()
    run, stream = run_agent, stream_agent
    if args.practice:
        import practice
        run, stream = practice.run_agent, practice.stream_agent
    if args.stream:
        asyncio.run(show_events(args.query, stream))
    else:
        print(run(args.query))


if __name__ == "__main__":
    main()
