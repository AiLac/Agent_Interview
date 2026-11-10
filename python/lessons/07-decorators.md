# 第 7 小时 · 遇到 @tool 时，追踪它包装了什么

**选修，可在第 6 小时后单独学习。** 本节实现 `@observe(log)`，在保留同步函数调用方式的同时记录正常返回或抛错。这个例子能帮你读框架的装饰器；各个 SDK 的 `@tool` 具体返回什么对象，需要看该 SDK 的实现。

## 0–15 分钟 · 把 @ 还原成普通赋值

```python
from agent_lab.extra import observe

records = []

@observe(records)
def count_names(names, *, limit=2):
    """统计展示的名称。"""
    return len(names[:limit])

print(records)
print(count_names(["A", "B"], limit=1))
print(records)
```

依次得到空列表、数字 1、一条 `status="returned"` 的记录。可以把定义读成两步：先定义原函数，再执行 `count_names = observe(records)(count_names)`。第一层接收日志容器，第二层接收待包装函数。调用者后来写 `count_names(...)` 时才进入第三层 wrapper。它仍能读到外层的 `records` 与原函数，因为闭包保存了这些绑定。Java 中可以用高阶函数或代理去理解调用前后加行为；这里的替换发生在 Python 执行函数定义时。

## 15–28 分钟 · 辨认星号所在的位置

| 表达式 | 谁处理参数 | 结果 |
| --- | --- | --- |
| 定义端 `def f(*args, **kwargs)` | 被调用函数 | 多余位置实参收为元组，关键字实参收为字典 |
| 调用端 `func(*args, **kwargs)` | 包装器调用原函数 | 把元组和字典再次展开 |
| 定义端 `def f(q, *, limit=2)` | 被调用函数 | 要求 limit 通过关键字传入 |
| 定义端 `def f(q, /)` | 被调用函数 | q 只允许按位置传入，读第三方签名时会见到 |

试把 `func(*args, **kwargs)` 改成 `func(args, kwargs)`：原函数将得到两个位置参数，本应传给 `limit` 的关键字丢失。再看 `from functools import wraps`。在 wrapper 上写 `@wraps(func)` 会保留名称、文档字符串等元数据，并给出 `__wrapped__` 链接。这对读取函数签名或帮助文本的工具框架很有用。

## 28–48 分钟 · 完成包装器

在 [practice.py](../practice.py) 补上 import 并实现 `observe(log)`。普通返回时追加 `{"fn": 原函数名, "status": "returned"}`，原样返回原结果。发生普通异常时记录异常类型名，例如 `{"fn":"broken","status":"raised","error":"ValueError"}`，然后用裸 `raise` 重新抛出。这样调用者还能根据异常类型和原 traceback 排查故障。最外层返回装饰器，装饰器返回包装后的函数。

```bash
python check.py 7
```

再用自己写的版本包装实际工具，验证 `ok=False` 的业务结果与 Python 异常的区别：

```python
from agent_lab.core import dispatch, run_agent
from practice import observe

log = []
tracked = observe(log)(dispatch)
print(tracked("missing", "{}"))
print(run_agent("安静", tool=tracked))
print(log)
```

两次调用都应记录 `returned`。第一次虽然是未知工具，`dispatch` 正常返回了一个错误字典。若日志要统计业务成功率，应额外读取返回对象里的 `ok`，而非把所有正常返回都当成成功。

## 48–60 分钟 · 对照 SDK 源码的阅读方法

拿一个已经装饰过的工具，打印 `tracked.__name__`、`tracked.__wrapped__.__name__`，再用 `inspect.signature(tracked)` 查看签名。暂时去掉 `@wraps`，重复观察。最后推测同步装饰器包住 `async def` 时何时写日志：它一拿到协程对象就会记录返回，真正的异步异常尚未发生。要观察异步执行，应让包装器也使用 `async def` 并在 `try` 里 `await func(...)`。本节的可运行装饰器用于同步工具。

[参考实现 · observe](../agent_lab/extra.py) · [标准库 · functools.wraps](https://docs.python.org/zh-cn/3.12/library/functools.html#functools.wraps)
