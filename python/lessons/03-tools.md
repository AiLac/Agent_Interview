# 第 3 小时 · 工具名怎样找到一段可执行代码

用户输入「安静」，模型给运行器的第一份响应里没有任何地点。它给了一个工具名和一段参数文本。可以把这件事类比成收到一个 RPC 请求：有人说明想调用哪个方法、传什么参数，服务端还得找到实现并真正执行。Python 在这里有个很方便的特性，函数本身可以作为值放进字典。

## 看看模型究竟交来了什么

```python
from agent_lab.core import demo_model, make_message

action = demo_model([make_message("user", "安静")])
print(action["kind"], action["name"], action["id"])
print(type(action["arguments"]).__name__, action["arguments"])
```

```text
call search_places c1
str {"query": "安静"}
```

`call` 告诉运行器下一步执行工具，`c1` 标记这一次调用。最容易看错的是第二行：终端打印的内容长得像一个对象，而 `type(...).__name__` 显示，Python 此刻拿到的是字符串。`raw["query"]` 对字符串无效；只有把里面的 JSON 解析出来，才能按字段取值。课程采用这个简化的动作格式，接入具体 SDK 时要看它交回的是文本还是已解析对象。

```python
import json
from agent_lab.core import parse_args

raw = '{"query":" 安静 ","limit":1}'
data = json.loads(raw)
args = parse_args(raw)
print(type(data).__name__, repr(data["query"]))
print(type(args).__name__, repr(args.query), args.limit)
```

```text
dict ' 安静 '
SearchArgs '安静' 1
```

`json.loads` 类似用 Jackson 读 JSON 文本，它保留了查询词中的空格。`parse_args` 内部也做解析，但还会检查键、类型与范围，然后去掉空格，构造 `SearchArgs`。`repr` 把字符串连同引号一起显示，便于观察空格。过了这一层边界，调用方可以用属性 `args.query` 读取已经检查过的词。逆方向的 `json.dumps` 会从内存对象生成文本，第 4 课存工具消息时会用到它。

## 为什么解析成功还要检查类型

下面两份输入都符合 JSON 语法。第一个请求省略上限，课程约定默认返回两条。第二个请求把上限写成了布尔值。它也能解析成功，但用来指定地点数量就失去了含义。

| 原始参数 | 运行器怎样处理 |
| --- | --- |
| `{"query":"安静"}` | 使用默认 `limit=2` |
| `{"query":"安静","limit":true}` | 返回 `invalid_args`；`true` 转换成了 Python 的 `True` |
| `{"query":"安静","limti":1}` | 返回 `invalid_args`；出现了未声明的键 |
| `{"query":"海滩"}` | 正常执行，得到空列表 |

打开 `parse_args`，`set(args)` 把字典的键收集成集合，减去 `{"query", "limit"}` 后剩下的就是多出来的键。`type(limit) is int` 要求恰好为整数类型。这样写有一个具体原因：Python 中 `isinstance(True, int)` 为真，这里希望把布尔值拒绝掉。校验后的 `SearchArgs` 用 `@dataclass(frozen=True)` 声明，Python 帮它生成初始化方法等常用代码，并限制给已有实例的字段重新赋值。可以把这个简单参数对象对应到 Java record。字段类型提示本身不会替程序检查 JSON。[校验器与数据类源码](../agent_lab/core.py)

## 从函数名到一次实际调用

```python
from agent_lab.core import TOOLS, dispatch

fn = TOOLS["search_places"]
print(fn.__name__)
print(fn(**{"query": "安静", "limit": 1}))
print(dispatch("search_places", '{"query":"海滩"}'))
print(dispatch("missing", "{}"))
```

```text
local_search
['青禾自习室']
{'ok': True, 'items': []}
{'ok': False, 'error': 'unknown_tool'}
```

第一行中的 `fn` 绑定到函数对象。在建表时写 `local_search` 可以保存这个函数，以后再传参数。写 `local_search(...)` 则会当场执行，并把返回值放入字典。到了 `fn(...)` 才真正发起本次查询。调用端的 `**` 按键展开字典，等价于 `fn(query="安静", limit=1)`。真实入口 `dispatch` 使用校验完的属性传参。

把工具不认识、参数不合法、合法查询零命中看成三条执行路径，就能解释为什么结果里需要 `ok`。运行器通过 `TOOLS.get(name)` 找到函数，查不到时得到 `None` 并返回 `unknown_tool`。只有校验器周围的 `try/except ValueError` 会把错误变成 `invalid_args`。工具本身如果抛编程错误，仍能在 traceback 中看到实际出错位置。

## 把一次失败定位到一行

在 `practice.py` 写出 `dispatch`，复用 `TOOLS` 和 `parse_args`，运行 `python check.py 3`。另外准备一个合法请求，先把工具名改错，再把名字改回去、把原始参数删掉最后一个右花括号。前者在查表时就结束；后者进入解析器后才失败。如果在地点函数第一行打断点，这两次都不会停在那里。现在把工具名和参数都修好，下一课就能看到结果如何被交给模型。[练习文件](../practice.py) · [下一课：第二轮模型调用](04-loop.md)
