# 第 8 小时 · 最终回答相同，怎样找出中间的错误

把地点工具的 `limit=1` 忽略掉，工具就会多返回一个地点。如果测试里的模型总是回答「已查询」，测试能发现这次改动吗？取决于你断言了什么。只检查最后三个字，两次执行都会通过；如果还能检查工具实际交回的地点列表，错误就有了具体位置。

要稳定重现这一幕，可以事先写下模型第一轮请求什么、第二轮回答什么。每次测试都从头读同一份动作序列，这称为**回放**。工具和运行器仍会执行，模型的下一步动作则由测试控制。你可以把它理解成给 Mockito 的替身设置连续两次返回值。

## 让一个对象记住上次读到了哪里

```python
from agent_lab.extra import ReplayModel

actions = [
    {"kind": "call", "id": "c1", "name": "search_places", "arguments": '{"query":"安静"}'},
    {"kind": "final", "text": "已查询"},
]
model = ReplayModel(actions)
print(model.calls)
print(model([])["kind"], model.calls)
print(model([])["kind"], model.calls)

try:
    model([])
except AssertionError as error:
    print(str(error), model.calls)
```

```text
0
call 1
final 2
回放动作已耗尽 2
```

`ReplayModel(actions)` 创建一个实例。`__init__(self, actions)` 初始化它，`self` 是本次操作的实例，写 `self.calls = 0` 相当于给这个对象保存计数器。`self._actions = iter(actions)` 保存一个**迭代器**，它负责记住下一项的位置。`next(self._actions)` 每成功取出一个动作，位置就前进一步。如果在每次调用时重新执行 `iter(actions)`，就会反复读到第一条。

这里的 `model` 明明是对象，为什么还能写 `model([])`？类定义了 `__call__`，实例于是支持函数调用语法，运行器可以像调用 `demo_model(history)` 一样使用它。传入空历史也能工作，因为本课的回放对象只按顺序读脚本。第三次调用时底层抛出 `StopIteration`，回放对象用 `raise AssertionError(...) from exc` 提供可读的错误，同时保留底层异常作为原因。计数只在取值成功后递增。[回放对象源码](../agent_lab/extra.py)

## 把一次真实执行对上一份预期

仓库的第一条用例要求只返回「青禾自习室」。打开 JSON 会看到两层结构。最外层是用例列表，里面的 `actions` 是模型脚本，`expected_observations` 是测试作者期望工具返回的内容。每次动作的 `arguments` 在这份文件里仍以字符串存储，运行器会把它原样交给工具。[案例文件](../replay_cases.json)

```python
import json
from pathlib import Path
from agent_lab.core import dispatch, run_agent
from agent_lab.extra import ReplayModel

with Path("replay_cases.json").open(encoding="utf-8") as file:
    case = json.load(file)[0]

seen = []
def observed_tool(name, raw):
    result = dispatch(name, raw)
    seen.append(result)
    return result

model = ReplayModel(case["actions"])
answer = run_agent(case["query"], model, observed_tool)
print(answer, model.calls)
print(seen)
print(seen == case["expected_observations"])
```

```text
已查询 2
[{'ok': True, 'items': ['青禾自习室']}]
True
```

`with ... as file` 把打开的文件交给代码块，在退出时关闭，类似 Java 的 try-with-resources。`json.load(file)` 接收文件对象；第 3 课的 `json.loads(raw)` 接收已在内存里的字符串。脚本从课程的 `python/` 目录运行，所以相对路径能找到用例。检查器用 `Path(__file__).with_name("replay_cases.json")` 相对于自身定位文件。

## 哪个断言能让错误暴露

做一个可撤销的小实验。在上面的临时脚本中，把 `result = dispatch(name, raw)` 改成 `result = dispatch(name, '{"query":"安静","limit":2}')`，再看同样的三行输出。这模拟适配器丢失了模型指定的上限。你仍会看到 `已查询 2`，因为模型的第二个动作写死了最终文本；`seen` 多出了「北岸图书馆」，最后一行变为 `False`。这样可以把排查范围从整段对话缩到参数传递和工具执行之间。

| 想核对什么 | 到哪里观察 | 这个观察能发现什么 |
| --- | --- | --- |
| 最终交给用户的文字 | `answer` | 终止时返回了哪个文本 |
| 工具真实执行的结果 | `observed_tool` 里的 `seen` | 工具是否按上限只返回一条 |
| 模型第二轮实际收到的历史 | 在模型回调里读取 `history[-1]` | 运行器是否把正确的观察和调用 ID 写回 |
| 多轮是否按预期停止 | `model.calls` | 实际模型决策次数是否与回放脚本相符 |

第二、三行有一个重要差别。工具返回过某个结果，不能单凭这一点得知模型也收到了它。第 4 课的检查 `H04.test_feedback_links_the_call` 在模型回调里核对 ID 和解析后的地点；第 8 课的检查 `H08.test_cases_from_json` 则在工具调用处收集结果，和用例一起比较。两个观察点分别落在写入历史的前后。[逐课检查源码](../check.py)

## 给下一次回归留一个案例

先在 `practice.py` 完成 `ReplayModel`，运行 `python check.py 8`。接着给 `replay_cases.json` 增加一条用例，让模型先查「自习」，再查「咖啡」，两次 call 的 ID 各不相同，最后返回 final。你应当能写出两条按顺序排列的 `items`，第一条只有「青禾自习室」，第二条只有「南门咖啡」。再执行同一条命令，测试会逐条读取用例。

当最终文本正确而某条观察错误时，先看工具收到的原始参数，再看模型下一轮收到的历史。这正好回到了课程起点：同一次用户请求里的不同参与者各自读到什么，由 Python 程序实际传递的值决定。回放能验证给定动作下的程序行为；评估在线模型能否自行选对工具，还需要让真实模型在评测样本上做决策。[练习文件](../practice.py) · [返回课程首页](../README.md)
