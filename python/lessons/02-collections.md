# 第 2 小时 · 三个候选地点为何只返回两个

先把模型放在一旁，直接问它将要调用的地点工具。「安静」明明不在「青禾自习室」这个名称里，为什么它仍然命中了？答案藏在一层容易略过的方括号里。

## 打开一条地点记录

```python
from agent_lab.core import PLACES

row = PLACES[0]
print(row["name"])
print(row["tags"])
print("安静" in row["name"], "安静" in row["tags"])
```

```text
青禾自习室
['自习', '安静']
False True
```

`PLACES` 是地点列表，`PLACES[0]` 取第一条记录。`row["name"]` 是一个字符串，`row["tags"]` 是由字符串组成的列表。两处 `in` 都读作“在里面吗”，具体比较却取决于右边的值。`"图书" in "北岸图书馆"` 检查子串；`"安" in ["自习", "安静"]` 要求某个完整标签等于「安」，结果为假。这就解释了同一条记录怎样凭标签入选。

## 一次查询的中间结果

下面用最普通的循环查询「安静」。多加的一行打印能让我们看到 `matches` 在每条记录处理完后有什么变化。`row.get("tags", [])` 表示缺少标签键时，用空列表参与判断。地点的 `name` 是必填字段，代码用 `row["name"]` 直接取。

```python
from agent_lab.core import PLACES

word = " 安静 ".strip()
matches = []
for row in PLACES:
    if word in row["name"] or word in row.get("tags", []):
        matches.append(row["name"])
    print(row["name"], matches)

print(matches[:1])
```

```text
青禾自习室 ['青禾自习室']
北岸图书馆 ['青禾自习室', '北岸图书馆']
南门咖啡 ['青禾自习室', '北岸图书馆']
['青禾自习室']
```

`strip()` 得到去掉首尾空白的新字符串；要使用处理后的结果，应当像这里一样接住返回值。`for row in PLACES` 每次把下一条记录绑定给 `row`，`if` 决定是否追加。观察 `print` 的缩进，它属于 `for`，所以打印三次；`append` 多缩进一级，只在条件成立时执行。最后一次取 `[:1]` 才施加数量上限。切片的右边界不包含在内，`[:1]` 返回最多一项的**列表**；即使零条命中也安全。`matches[0]` 则取一个**元素**，空列表会抛出 `IndexError`。

源代码在循环前还会检查 `if not word: return []`。原因可以亲手验证：`"" in "南门咖啡"` 为真。只输入空格时，若省略这行检查，三个地点会全部匹配，恰好得到一个看起来正常的错误答案。

## 读懂把循环写在一行的代码

Python 允许用**列表推导式**遍历输入、过滤元素，并立即构造一个新列表。这里用刚才的规则查询有「安静」标签的地点。右边只检查标签，这次输入下仍然得到相同的两条记录。

```python
from agent_lab.core import PLACES

word = "安静"
names = [row["name"] for row in PLACES if word in row.get("tags", [])]
for pos, name in enumerate(names, start=1):
    print(f"{pos}. {name}")
```

```text
1. 青禾自习室
2. 北岸图书馆
```

先读中间的 `for row in PLACES` 找数据源，再读 `if` 决定保留谁，最后回到最左侧的 `row["name"]` 看写入结果的值。熟悉 Java Stream 的读者可以按遍历、`filter`、`map` 三个动作还原。`enumerate` 每次产生一对「序号、名称」，循环头的两个变量依次接住它们，这叫**解包**。`f"{pos}. {name}"` 是格式化字符串，花括号中的表达式会被替换成当时的值。

## 把筛选函数接进工具

在 `practice.py` 完成 `find_places(rows, query, *, limit=2)`，保留输入顺序。签名中单独的 `*` 要求调用者显式写 `limit=1`；等号表示缺省时取 2。函数里的 `matches = []` 每次调用都会执行。如果把它改成形参的默认值 `matches=[]`，默认列表会在定义函数时创建，下一次查询可能拿到上一次留下的结果。

运行 `python check.py 2`，再亲自试三组输入。查「图书」应凭名称命中一条，查「安」应得到空列表，查「 安静 」并设置 `limit=1` 应只得到「青禾自习室」。现在你手里已有一个普通函数；下一步要解决的是模型只给出了字符串 `"search_places"` 时，程序怎样找到并调用它。[练习文件](../practice.py) · [参考实现](../agent_lab/core.py) · [下一课：执行工具](03-tools.md)
