# 第 6 小时 · 收到第一条事件时，工具执行了吗

运行 `python -m agent_lab --stream 安静`，第一行很快出现：`tool_call`。如果此刻就关闭输出流，地点工具是否已经启动？只看事件名字无法判断。答案取决于生产者先执行工具，还是先把事件交给调用者。要找出它，先看 Python 怎样让一个函数停在半途。

## 一次调用，分两次交出值

```python
def steps():
    yield "已准备"
    print("执行工具")
    yield "拿到结果"

stream = steps()
print("第一次取", next(stream))
print("第二次取", next(stream))
```

```text
第一次取 已准备
执行工具
第二次取 拿到结果
```

函数体含有 `yield` 后，调用 `steps()` 会得到一个**生成器**。它记得局部变量，也记得上次运行到了哪一行。第一次 `next` 让函数向前走，到第一个 `yield` 就把值交给调用者并暂停。第二次 `next` 从暂停位置继续，所以中间的打印此刻才发生。再次索取且已经执行到末尾时，会收到 `StopIteration`，普通 `for` 会自动处理这个结束信号。`return` 则结束函数，调用者不能靠下一次索取回到 `return` 后面。

## 在第一条事件和工具执行之间停下来

`stream_agent` 既要在工具运行时异步等待，又要按次交出事件。Python 把含 `yield` 的 `async def` 函数称为**异步生成器函数**。`stream = stream_agent(...)` 得到可逐项读取的对象；`await anext(stream)` 请求下一项，并允许本次请求为了等待 I/O 而挂起。

给它一个带计数的工具。下面连续读三个事件，每次读取后都打印累计调用次数。

```python
import asyncio
from agent_lab.advanced import stream_agent

async def main():
    calls = []

    async def counted_tool(name, raw):
        calls.append(name)
        return {"ok": True, "items": ["青禾自习室"]}

    stream = stream_agent("安静", tool=counted_tool)
    first = await anext(stream)
    print(first["type"], first["id"], len(calls))
    second = await anext(stream)
    print(second["type"], second["id"], len(calls))
    third = await anext(stream)
    print(third["type"], third["text"], len(calls))
    await stream.aclose()

asyncio.run(main())
```

```text
tool_call c1 0
tool_result c1 1
final 青禾自习室 1
```

第一行的 `0` 回答了开头的问题。源码先 `yield` 出调用事件，消费者再次索取时，才走到 `await tool(...)`。工具返回后，`record_call` 先把观察写进历史，接着生产者交出 `tool_result`。第三次索取时，模型已经能读取新历史，所以返回 `final`。如果只想验证提前退出，把脚本缩短到打印第一行就 `await stream.aclose()`，工具计数会一直是零。[查看这三处暂停的位置](../agent_lab/advanced.py)

第 5 课的 `await` 和这里的 `yield` 都可能让你看到“暂停”，接手的人不同。`await tool(...)` 表示本任务等工具给一个结果，等待期间事件循环可调度其他任务。`yield event` 则把一个已经构造好的事件交给消费者，生成器等待消费者下一次索取。界面此时可以刷新，或者直接关闭这条流。

## 谁把事件变成了屏幕上的文字

命令行使用 `async for`，依次等待下一项，收到结束信号时退出。让同一个生产者只打印每条事件里最关心的字段，可以直接看出为什么笔记中的「东桥阅览室」出现在工具结果中，却没有进入终端的最终回答。

```python
import asyncio
from agent_lab.advanced import stream_agent

async def main():
    async for event in stream_agent("安静"):
        if event["type"] == "tool_result":
            for source in event["result"]["sources"]:
                print(source["source"], source["items"])
        elif event["type"] == "final":
            print("最终回答", event["text"])

asyncio.run(main())
```

```text
catalog ['青禾自习室', '北岸图书馆']
notes ['青禾自习室', '东桥阅览室']
最终回答 青禾自习室、北岸图书馆
```

`async_dispatch` 按来源顺序合并列表，通过 `dict.fromkeys` 把重复名称收成一个键，再按默认上限 2 截断。笔记里的新地点排在第三，因此最终文本里没有它。这里流动的是一次工具调用中的**事件**，每个事件是一个字典。模型逐 token 输出需要生产者提供更细的文本增量；消费者仅仅换用 `async for` 并不会把一条完整回答切成 token。

## 完成六小时的端到端练习

在 `practice.py` 写出 `stream_agent`。参考第 4 课的历史和轮数处理，在工具执行前、结果写入后和最终回答时分别交出上述事件。遇到 final 时先 `yield` 再用空的 `return` 结束；未知动作和预算耗尽仍应抛出相应异常。运行 `python check.py 6`，再运行 `python -m agent_lab --practice --stream 海滩`。你应当能在看到最后一行前，根据第二行的 `ok` 与 `items` 预测「没有找到地点」。

如果只有 6 小时，可以在这里结束。想读懂框架中贴在工具函数上方的 `@`，继续第 7 课；准备把今天的故障存成可复现的用例，可以直接读第 8 课。[练习文件](../practice.py) · [第 7 课：装饰器](07-decorators.md) · [第 8 课：回放测试](08-replay.md)
