# Java 开发者的 Agent Python 课

**目标是拿到一段 Python Agent 源码，能沿着一次请求找到四件事：谁构造消息、谁选择工具、谁真正执行、结果怎样回到下一轮。** 你已经会 Java 后端开发，可以直接从一次调用进入语言细节。6 小时完成一个能运行的例子；有 7 或 8 小时，再加上调用记录与故障回放。

案例使用虚构地点。输入「安静」，本地模型替身发出一次 `search_places` 请求，Python 执行工具，模型替身读取结果后给出「青禾自习室、北岸图书馆」。进阶版同时查询两个模拟来源，终端可以在调用完成前先收到开始事件。所有代码使用 **Python 3.12 标准库**，可断网运行。动作字段是本课程的教学格式，真实模型 SDK 或 MCP 的消息格式需单独适配。

## 先学哪些 Python

| 掌握到什么程度 | 语法与概念 | 对应的 Agent 工作 |
| --- | --- | --- |
| 能独立写 | 缩进、赋值、字符串、真值、`if/for/return`、`list/dict/set`、切片与推导式 | 构造消息、提取工具名、筛选结果 |
| 能独立写 | 函数对象、默认值、关键字传参、`* / **` 的不同位置、模块导入、JSON、异常 | 用工具名找到函数，解析模型参数，把错误传给下一轮 |
| 能读懂并修改 | 类型提示、`None`、类与实例、`self`、`@dataclass`、`Callable` | 看懂 SDK 签名，区分消息字典、参数对象、模型回调 |
| 进阶必修 | 协程、可等待对象、`gather`、超时、`yield`、`async for` | 并发等待工具，按事件输出进度和最终答案 |
| 按时间选修 | 闭包、装饰器、`@wraps`、`__call__`、迭代器、`unittest` | 读懂工具装饰器，给每次调用留记录，离线复现多轮失败 |

元类、描述符内部实现、多进程调优和模型训练可以留到遇到具体代码再学。阅读含 `@tool`、`async def` 的框架代码，先找到原函数签名、包装它的函数、消费结果的调用方，这三个位置通常能解释执行时机。

## 课表与交付物

| 小时 | 讲义 | 当小时写出来的东西 |
| --- | --- | --- |
| 1 · 入门 | [从 PowerShell 启动程序，构造消息](lessons/01-messages.md) | `make_message`，能判断两条消息是否意外共享对象 |
| 2 · 入门 | [读懂嵌套数据和推导式](lessons/02-collections.md) | `find_places`，能解释过滤、保序、截断的顺序 |
| 3 · 入门 | [把 JSON 请求分派给 Python 函数](lessons/03-tools.md) | `dispatch`，区分空结果、非法参数、未知工具 |
| 4 · 入门 | [把一次工具调用接回模型](lessons/04-loop.md) | `run_agent`，能追踪调用 ID，给模型设置轮数上限 |
| 5 · 进阶必修 | [并发等待两个工具来源](lessons/05-async.md) | `lookup_sources`，一个来源超时时保留另一个的结果 |
| 6 · 进阶必修 | [逐步消费 Agent 事件](lessons/06-stream.md) | `stream_agent`，用 `async for` 依次看到请求、观察、回答 |
| 7 · 进阶选修 | [拆开装饰器，记录工具执行](lessons/07-decorators.md) | `observe`，透传实参、返回值与异常 |
| 8 · 进阶选修 | [用回放模型复现工具错误](lessons/08-replay.md) | `ReplayModel`，写断言检查模型实际收到的观察 |

**6 小时**顺序完成 1–6。**7 小时**在此前提下加第 7 或第 8 课，两课彼此独立。**8 小时**全部完成。每行 60 分钟，包含阅读、动手、调试和自测。首次安装解释器的下载时间另计。

## 从这里启动

在仓库根目录打开 Windows PowerShell。已有 Python 3.12 的情况下，以下命令不需要下载依赖，也无需激活脚本。

```powershell
cd python
py -0p
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m agent_lab 安静
.\.venv\Scripts\python.exe check.py --reference
```

macOS / Linux 使用下列命令。

```bash
cd python
python3.12 -m venv .venv
.venv/bin/python -m agent_lab 安静
.venv/bin/python check.py --reference
```

第一个程序应输出 `青禾自习室、北岸图书馆`，第二个命令末尾应显示 `OK`。各讲义为了简洁统一写 `python`。如果未激活环境，在 Windows 上将其替换为 `.\.venv\Scripts\python.exe`，在 macOS / Linux 上替换为 `.venv/bin/python`。以下命令的工作目录始终是仓库内的 `python/`。

## 怎样练，怎样知道自己学会了

1. 每课先预测小例子的输出，再运行。讲义中的独立 Python 片段可在交互解释器或临时脚本中执行。标注“签名”“节选”“骨架”的代码用于对照，完整上下文在相应源码里。
2. 在 [practice.py](practice.py) 完成当小时的同名函数。运行 `python check.py 1` 检查第 1 课，数字可以换成 1–8。未作答时出现 `NotImplementedError` 是起始状态。H03 的工具表会调用你在 H02 写的函数。
3. 卡住时先看检查器里的具体输入与预期值，再对照参考实现。带 `--reference` 的命令检查参考答案；检查自己的代码时去掉该参数。[逐课检查器](check.py) · [入门参考](agent_lab/core.py) · [进阶必修参考](agent_lab/advanced.py) · [选修参考](agent_lab/extra.py)
4. 完成第 4 课后运行 `python -m agent_lab --practice 安静`。完成第 6 课后运行 `python -m agent_lab --practice --stream 安静`。去掉 `--practice` 可随时观察参考程序。课程把终端参数解析放在 [__main__.py](agent_lab/__main__.py)。
5. 最后换一个输入，例如「海滩」。如果输出「没有找到地点」，从工具观察里的 `ok` 和 `items` 解释这是怎样产生的。再临时让模型永远发起工具调用，解释哪个函数终止循环。能够从外部行为定位到代码，才算完成这次练习。

**常见环境问题。** 出现 `No module named agent_lab` 时先看当前目录是否包含 `agent_lab/`。出现相对导入错误时用 `python -m agent_lab` 启动包。IDEA 与终端行为不一致时分别打印 `sys.executable`，将项目解释器指向同一个虚拟环境。以后要安装 SDK，可以用同一解释器执行 `python -m pip install 包名`。

系统查阅入口：[Python 3.12 中文教程](https://docs.python.org/zh-cn/3.12/tutorial/)。
