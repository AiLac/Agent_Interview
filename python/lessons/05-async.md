# 第 5 小时 · 并发等待两个来源，为每个来源设超时

**本节产物**是 `lookup_sources(query, sources, *, timeout_s)`。同一查询同时访问目录和笔记。目录慢或超时时，调用者仍能看到笔记来源返回了什么。样本用 `asyncio.sleep` 模拟 I/O 等待，所有结果来自本地内存。

## 0–15 分钟 · 看清启动与等待的区别

```python
import asyncio

async def one():
    print("开始查")
    await asyncio.sleep(0)
    return ["A"]

async def main():
    pending = one()
    print("已创建")
    print(await pending)

asyncio.run(main())
```

顺序是「已创建」「开始查」「['A']」。调用协程函数先得到一个协程对象；这次 `await pending` 才让它运行。对照 Java，`CompletableFuture.supplyAsync(...)` 会提交任务，单独调用 `one()` 没有提交操作。事件循环驱动任务在等待点暂停与恢复。`async def` 中直接调用阻塞 HTTP 客户端或 `time.sleep` 会占住事件循环线程；替换外部服务时应选异步客户端，或把合适的同步 I/O 交给 `asyncio.to_thread`。

## 15–29 分钟 · 由串行写法推导并发写法

先运行第一种写法，再运行第二种，比较输出。把两次等待都放入 `main` 中，并用 `asyncio.run(main())` 启动。

```python
import asyncio
from agent_lab.advanced import catalog, notes

async def main():
    a = await catalog("安静")
    b = await notes("安静")
    print(a, b)
    both = await asyncio.gather(catalog("安静"), notes("安静"))
    print(both)

asyncio.run(main())
```

第一段要等目录返回才创建并等待笔记查询；第二段将两个协程交给 `gather` 调度。两者都得到目录、笔记两份结果。`gather` 的结果按传入顺序排列，即使笔记先结束，它也在第二个位置。观察耗时可以用 `time.perf_counter()`，本机计时会波动。[检查器](../check.py) 使用 `asyncio.Event` 证明真的发生并发：第一个来源必须等第二个来源发信号才能返回。串行实现会让第一个来源一直等到超时。

## 29–49 分钟 · 完成带来源信息的查询

`Source = Callable[[str], Awaitable[list[str]]]` 表示调用来源得到可等待对象，等待完成才得到名称列表。按下面的值形状实现 [practice.py](../practice.py) 中的 `lookup_sources`，需要自己 `import asyncio`。

1. 写一个内部协程 `one(name, source)`，用 `await asyncio.wait_for(source(query), timeout=timeout_s)` 等待。内部函数可以直接读外层的 `query` 和 `timeout_s`，这种绑定称为闭包。
2. 正常时返回 `{"source": name, "ok": True, "items": items}`。捕获 `TimeoutError` 返回 `{"source": name, "ok": False, "error": "timeout"}`。超时在各来源内部转换成数据；其他意外异常仍向外传播。
3. 遍历 `sources.items()` 建立协程列表 `jobs`，然后 `return await asyncio.gather(*jobs)`。调用端 `*jobs` 把一个列表展开为多个位置实参。空输入应得到 `[]`。
4. 运行 `python check.py 5`。再读参考实现最后一行，它把“建列表再展开”写成生成器表达式配合 `*`，调用含义一致。

## 49–60 分钟 · 制造一个永远等不到的来源

```python
import asyncio
from practice import lookup_sources
from agent_lab.advanced import notes

async def stalled(query):
    await asyncio.Event().wait()

async def main():
    rows = await lookup_sources("安静", {"慢源": stalled, "笔记": notes}, timeout_s=0.1)
    print([(row["source"], row["ok"]) for row in rows])

asyncio.run(main())
```

预期为 `[('慢源', False), ('笔记', True)]`。本例的超时针对单个来源。到期后 `wait_for` 请求取消并等待取消过程，真实耗时可能超过传入秒数。`gather` 默认会把未被捕获的异常交给等待者，其他已调度任务通常仍会继续；这里的部分成功仅针对显式处理的超时。把 `await` 写在循环里再收集“结果”，即使最后使用了 `gather` 也无法补回失去的并发。

[参考实现 · lookup_sources](../agent_lab/advanced.py) · [Python 3.12 · 协程、并发和超时](https://docs.python.org/zh-cn/3.12/library/asyncio-task.html)
