# 第 3 小时 · 从一段 JSON 找到要执行的函数

**本节产物**是 `dispatch(name, raw)`。假设模型生成工具名 `search_places`，同时生成一段 JSON 字符串。运行器需要把它转换成 Python 可用的参数，找到已登记的函数，并把成功或失败组织成下一轮可读取的观察。

## 0–12 分钟 · 分清传输文本和内存对象

```python
import json

raw = '{"query":"安静","limit":1}'
args = json.loads(raw)
print(type(raw).__name__, type(args).__name__, args["limit"] + 1)
print(json.dumps({"ok": True, "items": []}, ensure_ascii=False))
```

第一行输出是 `str dict 2`。Java 中用 Jackson 从字符串读取对象，在这里对应 `json.loads`。反向用 `dumps` 得到字符串；输出里 Python 的 `True` 会变成 JSON 的 `true`。读取已打开的文件则用 `json.load(file)`。实际 SDK 有的给你字符串，有的已经提供字典。先看返回值的形状，重复反序列化会得到 `TypeError`。

在解释器里单独对 `json.loads("{")` 求值，读 traceback 的最后一行，再向上找调用位置。`JSONDecodeError` 属于 `ValueError`，本课用一次 `except ValueError` 处理 JSON 语法错误与参数值错误。它只包住参数解析，避免工具内部真正的代码错误被记录成“用户参数非法”。

## 12–28 分钟 · 读懂边界校验和参数对象

打开 [core.py](../agent_lab/core.py) 中的 `SearchArgs` 和 `parse_args`。按执行顺序给下面的输入标注“会走到哪一行”。

| 原始字符串 | 解析后的对象 | 校验结果 |
| --- | --- | --- |
| `{"query":" 安静 "}` | 字典 | `SearchArgs(query="安静", limit=2)` |
| `[]` | 列表 | 期望对象，拒绝 |
| `{"query":"安静","limit":true}` | 字典，limit 为布尔值 | 期望整数，拒绝 |
| `{"query":"安静","limti":1}` | 字典，有未知键 | 拒绝拼错的键 |

`set(args) - {"query", "limit"}` 取未知键集合。前面的 `or` 短路，非字典输入直接进入错误分支。`1 <= limit <= 5` 表示两个边界都成立。Python 中 `isinstance(True, int)` 为真，所以例子用 `type(limit) is int` 严格区分两者。

`@dataclass(frozen=True)` 帮类生成按字段初始化等方法。可以暂时把这个简单对象读成 Java record：`args.query` 和 `args.limit` 是属性。构造器接受类型标注并不等于自动验证外部输入，可以直接试 `SearchArgs("安静", "错")`。本例把校验集中在 `parse_args`，随后才构造参数对象。

读 SDK 参数签名时还会看到三种常用写法。`list[str]` 表示元素应是字符串，`dict[str, int]` 表示键和值的预期类型。`limit: int | None` 表示允许整数或 None；是否能省略这个形参，要看它有没有默认值。例如 `def f(limit: int | None): ...` 仍需传参，而 `def f(limit: int | None = None): ...` 可以直接调用 `f()`。试在解释器里各调用一次，观察哪一步抛出 `TypeError`。

## 28–48 分钟 · 把函数作为值传递

```python
from agent_lab.core import local_search

registry = {"search_places": local_search}
fn = registry["search_places"]
print(fn("安静", limit=1))
print(fn(**{"query": "安静", "limit": 1}))
```

表中存的是函数对象，写成 `local_search()` 会在建表时就尝试执行。赋值给 `fn` 后，用括号才调用。第二种写法中调用端的 `**` 按键展开为关键字参数；键名要和形参对应。真实工具可以通过注册表限制可执行的函数，不应直接根据输入文本执行 Python 表达式。

在 [practice.py](../practice.py) 实现 `dispatch`：

1. `TOOLS.get(name)` 查不到时返回 `{"ok": False, "error": "unknown_tool"}`。
2. 调用提供的 `parse_args(raw)`。抛出 `ValueError` 时返回 `{"ok": False, "error": "invalid_args"}`。
3. 向函数传入已校验的查询词和上限。即使列表为空也返回 `{"ok": True, "items": 结果列表}`。运行 `python check.py 3`。

## 48–60 分钟 · 用三个相似请求做排错

保持工具名不变，依次传 `'{"query":"海滩"}'`、`'{"query":""}'` 和 `'{"query":"安静","limit":"1"}'`。第一个请求成功执行，后两个应在执行地点查询前结束。然后只把第一个请求的工具名改为 `search_place`，观察错误码如何变化。能指出“哪一步决定不调用函数”，比记住异常名称更有用。

[参考实现 · parse_args 与 dispatch](../agent_lab/core.py) · [Python 教程 · 错误与异常](https://docs.python.org/zh-cn/3.12/tutorial/errors.html) · [标准库 · dataclasses](https://docs.python.org/zh-cn/3.12/library/dataclasses.html)
