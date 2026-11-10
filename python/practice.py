"""你的练习区。每小时替换一个函数体，运行 python check.py 小时编号。"""

from collections.abc import AsyncIterator

from agent_lab.advanced import AsyncTool, Source, async_dispatch as dispatch_to_sources
from agent_lab.core import Model, PLACES, Tool, demo_model, parse_args, record_call

# H01
def make_message(role: str, content: str) -> dict:
    raise NotImplementedError("请完成 H01")


# H02
def find_places(rows: list[dict], query: str, *, limit: int = 2) -> list[str]:
    raise NotImplementedError("请完成 H02")


def local_search(query: str, *, limit: int = 2) -> list[str]:
    return find_places(PLACES, query, limit=limit)


TOOLS = {"search_places": local_search}


# H03：校验器已提供，此处的工具表调用你在 H02 完成的函数。
def dispatch(name: str, raw: str) -> dict:
    raise NotImplementedError("请完成 H03")


# H04：model 和 tool 可由调用者传入。record_call 可直接复用。
def run_agent(query: str, model: Model = demo_model, tool: Tool | None = None,
              *, max_steps: int = 3) -> str:
    # 默认用本练习的 dispatch。显式传入的 tool 优先。
    if tool is None:
        tool = dispatch
    raise NotImplementedError("请完成 H04")


# H05
async def lookup_sources(query: str, sources: dict[str, Source], *, timeout_s: float) -> list[dict]:
    raise NotImplementedError("请完成 H05")


async def async_dispatch(name: str, raw: str) -> dict:
    return await dispatch_to_sources(name, raw, lookup=lookup_sources)


# H06
async def stream_agent(query: str, model: Model = demo_model, tool: AsyncTool = async_dispatch,
                       *, max_steps: int = 3) -> AsyncIterator[dict]:
    raise NotImplementedError("请完成 H06")
    yield  # 保持异步生成器签名；实现后替换为实际事件。


# H07
def observe(log: list[dict]):
    raise NotImplementedError("请完成 H07")


# H08
class ReplayModel:
    def __init__(self, actions: list[dict]):
        raise NotImplementedError("请完成 H08")

    def __call__(self, history: list[dict]) -> dict:
        raise NotImplementedError("请完成 H08")
