# 第 1 小时 · 从一条 user 消息开始

**本节产物**是 `make_message(role, content)`。给它 `"user"` 和 `"安静"`，调用者应拿到一条独立的消息字典。把输入换成空字符串，内容也应原样保留。

## 0–12 分钟 · 固定解释器，观察入口

按[课程首页](../README.md)启动参考程序。在 `python/` 目录执行：

```bash
python -c "import sys; print(sys.version); print(sys.executable)"
python -m agent_lab 安静
python -m agent_lab 海滩
```

第一条输出解释器版本与路径。把它和 IDEA 项目解释器对应起来，可以避免“命令行能执行、IDE 报依赖缺失”。`-m agent_lab` 会让 Python 找到这个包并执行它的 `__main__.py`。打开该文件最后三行：`if __name__ == "__main__"` 让入口在以主模块运行时调用；普通 `import` 可以复用函数而不启动 CLI。今天只跟到 `run_agent(args.query)` 即可。

## 12–27 分钟 · 用熟悉的 Java 读法拆开三行

Java 里可以先写 `Map<String, String> message`，再把它加入 `List`。Python 用字面量直接表达这两层结构。运行以下片段，再把 `[-1]` 换成 `[0]`。

```python
history = [{"role": "user", "content": "安静"}]
history.append({"role": "assistant", "content": "收到"})
last = history[-1]
print(f"{last['role']} 收到 {len(last['content'])} 个字符")
```

按从外向内读：`history` 是列表，`history[-1]` 取末项，末项是字典，再用字符串键取字段。输出是 `assistant 收到 2 个字符`。`f"...{表达式}..."` 会计算花括号中的表达式。引号内外分别用双引号和单引号，便于看清边界。`append` 原地修改列表，返回 `None`。试一下 `history = history.append(last)`，再打印变量，就能看到常见的赋值错误。

Python 把对象的类型放在值上，名字绑定到对象。函数写成 `def make_message(role: str, content: str) -> dict:`，冒号引出函数体，函数体通常缩进四个空格，`return` 把值交回调用者。参数名后的 `str` 和箭头后的 `dict` 提供类型提示，运行时校验需要程序自己实现。

## 27–42 分钟 · 谁持有同一个对象

先预测下面两个布尔值，再执行。

```python
a = {"role": "user", "content": "安静"}
b = a
c = dict(a)
b["content"] = "咖啡"
print(a["content"], c["content"])
print(a == b, a is c)
```

结果是 `咖啡 安静` 和 `True False`。`b = a` 绑定到同一个对象，和 Java 中给另一个变量赋同一对象引用相似。字典的 `==` 比较内容，`is` 比较身份。判断缺省标记用 `value is None`。空串、空列表、数字零、`None` 在条件中都为假；如果工具参数允许 `0`，单凭 `if not value` 就会误判。这里的浅复制足以隔开字符串字段；字典里若有列表，复制外层以后内层列表仍然共享。

## 42–55 分钟 · 实现并制造一次故障

1. 在 [practice.py](../practice.py) 实现 `make_message`。直接返回一个新字典，键名是 `role`、`content`。不要修改调用者给的字符串。
2. 执行 `python check.py 1`。再临时把 `content` 拼成 `contents`，重跑检查，找出预期值与实际值差在哪个键，然后改回去。
3. 在临时脚本中构造 user 和 assistant 两条消息并加入列表，只修改第二条的内容。打印第一条，确认它仍然是初次构造的值。

## 55–60 分钟 · 口述验收

如果把空字典放在函数外，函数每次都填充并返回它，两次调用后会留下什么？两个变量会同时看到最后一次写入。若希望每轮模型看到独立的历史消息，应在每次函数调用时创建新字典。现在回到程序入口，指出 `args.query` 是属性访问，而 `message["content"]` 是按键访问。

[参考实现 · core.py](../agent_lab/core.py) · [Python 教程 · 初步介绍](https://docs.python.org/zh-cn/3.12/tutorial/introduction.html)
