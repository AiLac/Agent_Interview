# 第 6 小时 · 用异步生成器把执行过程交给调用方

**本节产物**是流式的 `stream_agent`。调用者可以先显示“正在查地点”，等工具结果到达再展示地点。课程按工具调用和回答的粒度发布事件；真实模型逐 token 输出还需要消费模型提供方的增量响应。

## 0–14 分钟 · 先摸清 yield 的暂停点

```python
def phases():
    yield "开始"
    print("工具在这里运行")
    yield "完成"

it = phases()
print(next(it))
print(next(it))
```

第一次 `next` 得到「开始」，此时中间的 `print` 尚未执行。第二次才继续。再调用一次 `next` 会触发 `StopIteration`，普通 `for` 会处理这个结束信号。Java 的 Iterator 可以帮助理解“取下一项”；Python 的生成器还把局部变量和暂停位置保存在生成器对象中。

| 函数体 | 调用后得到 | 取结果的写法 |
| --- | --- | --- |
| `def` 中用 `return` | 返回值 | `result = f()` |
| `def` 中用 `yield` | 同步生成器 | `for item in f()` |
| `async def` 中无 `yield` | 协程对象 | `result = await f()` |
| `async def` 中用 `yield` | 异步生成器 | `async for event in f()` |

`await stream_agent(...)` 会得到类型错误；该对象要逐项消费。异步生成器用空的 `return` 表示结束，最终文本可放在最后一个 `yield` 的事件中。

## 14–28 分钟 · 用一条命令找到三种事件

```bash
python -m agent_lab --stream 安静
```

第一行是 `tool_call`，包括 `name="search_places"` 和 `id="c1"`。第二行是 `tool_result`，同一 ID 下能看到 `catalog` 和 `notes` 的各自结果。第三行是 `final`。笔记还返回了「东桥阅览室」，为什么最终只有两个地点？跟到 [advanced.py](../agent_lab/advanced.py) 的 `async_dispatch`：按来源顺序合并、对名称去重，最后按默认 `limit=2` 截断。流中第二行保留了这段推导所需的信息。

注意两个等待层次。工具模块内部等两个来源后返回一份完整观察。Agent 在外层先 `yield tool_call`，下游再拉取时才 `await tool(...)`。工具结束后才 `yield tool_result`。在这段实现中，调用方停在第一个事件时，本轮工具尚未启动。

## 28–48 分钟 · 把第 4 小时的循环改为可消费的流

在 [practice.py](../practice.py) 实现 `stream_agent`。沿用同步循环的历史和预算规则，用下面的事件契约对照实现：

| 分支 | 调用者收到 | 恢复执行后做什么 |
| --- | --- | --- |
| call，工具执行前 | `{"type": "tool_call", "id": ..., "name": ...}` | await 异步工具 |
| call，结果已写回历史 | `{"type": "tool_result", "id": ..., "result": ...}` | 进入下一轮模型决策 |
| final | `{"type": "final", "text": ...}` | return，结束迭代 |

保留未知动作与轮数耗尽的异常。首次遇到 `AsyncIterator[dict]` 可读作“调用者可以异步地逐个取出字典”。本例的模型替身是同步纯函数，网络模型的异步调用需要在适配处等待；同步与异步取决于接口契约。

```bash
python check.py 6
python -m agent_lab --practice --stream 安静
python -m agent_lab --practice --stream 海滩
```

## 48–60 分钟 · 6 小时综合验收

1. 写一个只取第一项的消费者：在 `async def main()` 中创建 `stream = stream_agent("安静")`，打印 `await anext(stream)` 后执行 `await stream.aclose()`。在工具入口临时打印一行，验证这一路径没有执行工具。
2. 换成 `async for event in stream_agent("安静")` 读完整条流。只在 `event["type"] == "final"` 时打印文本，再改为只打印来源状态。两种展示可以共用同一生产者。
3. 让模型直接给 final、让一个来源超时、让模型永远发 call，各选一条前面写过的测试定位故障。能解释“什么时候执行”和“为什么停止”，即可在这里结束本课程。

[参考实现 · stream_agent](../agent_lab/advanced.py) · [Python 语言参考 · 异步生成器](https://docs.python.org/zh-cn/3.12/reference/expressions.html#asynchronous-generator-functions)
