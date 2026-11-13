# 第 7 小时 · 工具多了一层日志，原函数去了哪里

假设你想知道 Agent 到底调用过哪些工具。最直接的做法，是在每个函数里加一条日志。可这十几个工具真正共有的事情只有两件：接收一组参数、返回结果或抛出异常。能不能把记录写在它们的调用路径上，只写一次？

Python 的**装饰器**接收一个对象，并返回此后交给调用者使用的对象。对于这节课的同步工具，它接收原函数，返回一个负责写日志的包装函数。先不看 `@`，用普通的赋值跟一次调用。

## 函数在什么时候被替换

```python
from agent_lab.core import dispatch
from agent_lab.extra import observe

log = []
decorate = observe(log)
tracked = decorate(dispatch)
print(log)

result = tracked("missing", "{}")
print(result)
print(log)
```

```text
[]
{'ok': False, 'error': 'unknown_tool'}
[{'fn': 'dispatch', 'status': 'returned'}]
```

`observe(log)` 接收日志列表，返回函数 `decorate`。`decorate(dispatch)` 把原函数交给它，得到包装函数 `tracked`。到此日志仍然是空的，因为两次调用做的事只是准备一个新函数。最后一行真正调用 `tracked(...)` 时，包装器才接到工具名和参数，执行原函数，把状态写回最初的那个列表。

为什么 `observe` 早已返回，`tracked` 仍找得到 `log`？在 Python 中，内层函数可以在以后被调用时继续访问外层的变量，这种函数连同它能访问的这些绑定称为**闭包**。分别用两个列表调用 `observe`，会得到各自向不同列表写记录的装饰器。你也可以把 `tracked` 作为 `run_agent` 的 `tool` 参数传入，让整个运行器经过这层包装。

## 用 @ 写出同一件事

```python
from inspect import signature
from agent_lab.extra import observe

records = []

@observe(records)
def names(query, *, limit=1):
    """按上限重复名称。"""
    return [query] * limit

print(names("青禾", limit=2))
print(names.__name__, names.__doc__)
print(signature(names))
print(records)
```

```text
['青禾', '青禾']
names 按上限重复名称。
(query, *, limit=1)
[{'fn': 'names', 'status': 'returned'}]
```

可以把 `@observe(records)` 展开成定义原函数之后的一次赋值：`names = observe(records)(names)`。此后 `names(...)` 进入包装器。源码上的 `@wraps(func)` 复制了原函数的名称与文档字符串，并设置 `__wrapped__` 指回原函数，这也是 `inspect.signature` 默认能找到原签名的原因。读到真实 SDK 的 `@tool` 时，也可以沿这条线去看装饰器具体返回了函数还是工具对象。[包装器源码](../agent_lab/extra.py)

## 原来的实参如何穿过包装器

调用者传入一个位置参数 `"青禾"` 和一个关键字参数 `limit=2`。包装器定义里的 `*args` 把位置参数收成元组 `("青禾",)`，`**kwargs` 把关键字收成字典 `{"limit": 2}`。在调用端写 `func(*args, **kwargs)`，Python 再把二者展开，原函数看见的调用形状与最初相同。若写成 `func(args, kwargs)`，原函数会收到两个位置参数，而 `limit` 只接受关键字传参。

遇到复杂签名时，可以用一个短函数观察自己的参数。元组末尾的逗号表示这是单元素元组；空元组写作 `()`。第三方签名里若出现独立的 `/`，其左边的形参仅接受位置实参，与 `*` 右边的仅关键字规则相对应。

```python
def inspect_call(*args, **kwargs):
    print(args)
    print(kwargs)

inspect_call("青禾", limit=2)
```

```text
('青禾',)
{'limit': 2}
```

## 为什么报错的工具也可能记录 returned

回看开头：`dispatch` 查不到工具，按约定**正常返回**一个 `ok=False` 的字典。因此包装器记录 `returned`。如果函数真的执行了 `raise ValueError(...)`，包装器才会记录 `raised`，并用无参数的 `raise` 把原来的异常继续向外传。一个指标统计 Python 调用是否抛错，另一个指标统计业务查询是否成功；它们读的是不同的数据。

在 `practice.py` 完成 `observe`，导入 `functools.wraps`，运行 `python check.py 7`。把示例的函数改成抛出 `ValueError("bad")`，在调用方用 `try/except` 打印 `records`，你应看到 `error` 等于 `ValueError`。再想一下把这个同步包装器用到 `async def` 的后果：包装器拿到协程对象就会写下 `returned`，真正执行期间的异常会发生得更晚。如果目标是记录异步执行结果，包装器也需要在异常处理范围内 `await` 原函数。[练习文件](../practice.py) · [下一课：回放测试](08-replay.md)
