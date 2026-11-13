# 第 1 小时 · 「安静」怎样变成第一条消息

运行 `python -m agent_lab 安静` 时，命令行交给程序的是两个汉字。几行代码以后，模型收到的是一个列表。如果直接把字符串传给模型，模型怎样知道这句话来自用户？等工具也给出一段文字，模型又怎样知道那是查询结果？运行器从第一步就给数据补上了身份。

## 从屏幕上的文字到内存里的消息

先在 `python/` 下运行这段代码。它只构造输入并把中间值打印出来，没有调用模型。

```python
from agent_lab.core import make_message

query = "安静"
message = make_message("user", query)
history = [message]

print(query)
print(message)
print(history)
```

```text
安静
{'role': 'user', 'content': '安静'}
[{'role': 'user', 'content': '安静'}]
```

第一行是字符串 `str`。第二行是一条消息，用**字典**（`dict`）按键保存值。要取正文，写 `message["content"]`。可以把它读成 Java 的 `message.get("content")`，但要留意缺键时的差别，Python 的方括号会抛出 `KeyError`。第三行在消息外面又多了一层方括号，这是**列表**（`list`）。历史需要维护先后顺序，所以即使现在只有一条消息，也放进列表。

怎样读 `history[-1]["content"]`？先执行 `history[-1]`，负索引 `-1` 取列表末项，得到字典。再对这个字典按键取值，才得到「安静」。两对方括号长得一样，操作由左侧对象的类型决定。等第 4 课把工具消息追加进来，完全相同的表达式就会取到工具返回的正文。

## 一个函数究竟承诺了什么

现在打开 `make_message`。它只有一个动作。下面把相同的函数写在脚本里，传入一个空字符串，再检查返回值。[对应源码](../agent_lab/core.py)

```python
def make_message(role: str, content: str) -> dict:
    return {"role": role, "content": content}

message = make_message("assistant", "")
print(message["role"])
print(len(message["content"]))
```

```text
assistant
0
```

`def` 给函数起名，圆括号列出形参，行末冒号引出函数体。缩进四个空格的 `return` 属于函数体，后面没有缩进的 `message = ...` 在调用方。`"role"` 带引号，是固定的字段名，右边的 `role` 没有引号，读取本次调用实际传入的值。看懂这一行，就能读懂许多 Python SDK 构造请求的代码。

`role: str` 和 `-> dict` 是**类型提示**。它们告诉人和 IDE 这里期望字符串、返回字典，解释器不会据此自动拒绝其他类型。这个函数保存原文，所以空字符串也保留。Python 在条件判断里会把空串、空列表、零和 `None` 都视为假。`None` 表示没有值；如果明确只想判断没有值，应写 `value is None`。第 3 课会处理「空字符串作为查询词是否合法」，那是工具参数的约定。

## 为什么第二条消息可能改写第一条

假设有人为节省一次构造，把上一条消息赋给 `second`，再修改它的内容。先猜第一行会打印什么。

```python
first = {"role": "user", "content": "安静"}
second = first
second["content"] = "咖啡"
print(first["content"])

independent = dict(first)
print(first == independent, first is independent)
```

```text
咖啡
True False
```

和 Java 对象引用赋值一样，`second = first` 让两个名字指向同一个字典。通过任何一个名字写字段，另一个都能读到新值。`dict(first)` 新建外层字典，所以 `==` 比较内容时结果为真，`is` 比较是否为同一个对象时结果为假。这里的字段都是字符串；如果某个值也是列表，浅复制后那个内层列表仍可能共享。每次调用 `make_message` 时现场创建字典，就能让每条消息有自己的字段。

回到命令 `python -m agent_lab 安静`。`-m` 让 Python 按模块名启动这个包，入口在 `agent_lab/__main__.py`。入口解析出查询词，再传给 `run_agent`。源码末尾的 `if __name__ == "__main__"` 让命令行启动时执行 `main()`，而其他模块可以单独导入这里定义的函数。[入口源码](../agent_lab/__main__.py)

## 动手把消息交给下一步

在 `practice.py` 完成 `make_message`，运行 `python check.py 1`。接着自己写两次调用，把结果放进同一列表，用 `history.append(...)` 再加入第三条，打印 `len(history)` 和 `history[-1]["role"]`。`append` 会直接修改原列表，返回 `None`；把它的返回值赋回 `history` 会丢掉原来指向列表的名字。

最后试着解释，`history[-1]` 和 `history[-1]["content"]` 分别交付什么。如果能在运行前说出「一条消息字典」和「其中的正文字符串」，就可以进入地点工具，看看同样一套列表与字典怎样容纳多条候选记录。[练习文件](../practice.py) · [下一课：筛选地点](02-collections.md)
