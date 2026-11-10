# 第 8 小时 · 把一次多轮调用变成可复现的测试

**选修，可在第 6 小时后单独学习。** 本节写一个可调用的对象 `ReplayModel`。给它两次调用与一次 final，它就依次给出这三个动作。这样可以稳定复现重复调用、未知工具、脚本耗尽，适合测试 Agent 运行器是否正确处理既定动作。

## 0–15 分钟 · 从 Java 的测试替身过渡到 Python 对象

```python
from agent_lab.extra import ReplayModel

model = ReplayModel([{"kind": "final", "text": "完成"}])
print(model.calls)
print(model([]))
print(model.calls)
```

输出是 `0`、动作字典、`1`。`class ReplayModel` 定义类，`__init__(self, actions)` 初始化每个实例的状态，`self.calls` 类似 Java 的 `this.calls`。Python 用 `self` 显式接收实例。定义了 `__call__` 后，对象本身就能以 `model(history)` 的形式调用，和第 4 小时的 `Model` 契约兼容，无需引入框架。

`iter(actions)` 创建携带当前位置的迭代器；`next(it)` 取一个动作，耗尽后抛 `StopIteration`。若在每轮都重新执行 `iter(actions)`，位置会回到开头，循环可能连续拿到同一个动作。因此迭代器应当在初始化时创建，每条测试用例各建一个实例。

## 15–30 分钟 · 从 JSON 案例里拆出期望观察

打开 [replay_cases.json](../replay_cases.json)。第一条请求限制返回一个地点，第二条故意使用未登记的工具。先检查动作序列和每条观察，再运行以下片段：

```python
import json
from pathlib import Path

path = Path("replay_cases.json")
with path.open(encoding="utf-8") as file:
    cases = json.load(file)

for case in cases:
    action = case["actions"][0]
    print(action["name"], json.loads(action["arguments"]))
```

`with` 进入并退出文件上下文，即使读取失败也会关闭文件，类似 Java 的 try-with-resources。外层 JSON 文件读取后，`arguments` 仍是一个字符串；这里的第二次解析面向这个嵌套字段。脚本如果需要相对于自身定位文件，可以像 [check.py](../check.py) 那样用 `Path(__file__).with_name(...)`。

## 30–48 分钟 · 实现并验证回放对象

1. 在 [practice.py](../practice.py) 完成 `ReplayModel`。保存迭代器，把实例属性 `calls` 初始化为零。
2. 每次 `__call__` 取一个动作，成功后计数并返回。练习里动作已固定，所以可以不读取传入的 `history`。耗尽时用 `raise AssertionError("回放动作已耗尽") from exc`，保留底层异常链，且本次不增加计数。
3. 运行 `python check.py 8`。打开 `H08.test_cases_from_json` 查看断言：它同时比较最终文本、每次工具返回的观察以及实际模型调用次数。阅读 `with self.subTest(...)` 和 `assertEqual(实际, 预期)`，分别对应标记当前数据行和比较两值。
4. 复制 JSON 中第一条用例，改成连续两次工具调用，分别查「自习」与「咖啡」，使用不同 ID，最后才给 final。补两条期望观察 `{"ok": true, "items": ["青禾自习室"]}` 和 `{"ok": true, "items": ["南门咖啡"]}`。再次运行同一命令，这条新增用例也会参与断言。

## 48–60 分钟 · 设计一个只看最终文本抓不到的错误

暂时把用例里第一个预期地点从「青禾自习室」写成「错误地点」，保留最终文本。回放模型会照样给出固定的 final，观察值断言却会失败；读懂失败信息后改回来。进一步思考：如果运行器执行了工具，却忘记把结果交给模型，仅检查工具记录仍可能全部通过。第 4 小时的 `test_feedback_links_the_call` 在模型回调里直接读取角色顺序、调用 ID 与实际结果，从另一侧检查了同一件事。

这里能验证的是给定动作轨迹下程序的行为。在线模型是否会选对工具、是否能正确总结观察，需要用真正的模型和评测样本回答。面试时可以用这个例子讲清楚：为什么使用确定性的测试替身，以及它留下哪些需要单独评估的问题。

[参考实现 · ReplayModel](../agent_lab/extra.py) · [Python 教程 · 类与迭代器](https://docs.python.org/zh-cn/3.12/tutorial/classes.html) · [标准库 · unittest](https://docs.python.org/zh-cn/3.12/library/unittest.html)
