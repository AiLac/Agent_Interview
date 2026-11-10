"""Checks for the eight lessons. Run python check.py --help from this directory."""

import argparse
import asyncio
import json
from pathlib import Path
import unittest

import agent_lab as reference
import practice
from agent_lab.core import PLACES

impl = practice


def call(call_id="t1", query="安静"):
    return {"kind": "call", "id": call_id, "name": "search_places",
            "arguments": json.dumps({"query": query}, ensure_ascii=False)}


class H01(unittest.TestCase):
    def test_message_fields(self):
        self.assertEqual(impl.make_message("user", "安静"), {"role": "user", "content": "安静"})

    def test_independent_messages(self):
        first = impl.make_message("user", "一")
        second = impl.make_message("assistant", "")
        self.assertEqual(second, {"role": "assistant", "content": ""})
        self.assertEqual(first["content"], "一")


class H02(unittest.TestCase):
    def test_tags_trim_limit_and_order(self):
        self.assertEqual(impl.find_places(PLACES, " 安静 "), ["青禾自习室", "北岸图书馆"])
        self.assertEqual(impl.find_places(PLACES, "安静", limit=1), ["青禾自习室"])

    def test_name_blank_and_missing_tags(self):
        rows = [{"name": "东桥书店"}, {"name": "南山", "tags": ["安静"]}]
        self.assertEqual(impl.find_places(rows, "书"), ["东桥书店"])
        for word in ("", "   ", "安"):
            with self.subTest(word=word):
                self.assertEqual(impl.find_places(rows, word), [])


class H03(unittest.TestCase):
    def test_valid_and_empty(self):
        self.assertEqual(impl.dispatch("search_places", '{"query":"海滩"}'), {"ok": True, "items": []})
        self.assertEqual(impl.dispatch("search_places", '{"query":" 安静 ","limit":1}'),
                         {"ok": True, "items": ["青禾自习室"]})

    def test_unknown(self):
        self.assertEqual(impl.dispatch("other", "{}"), {"ok": False, "error": "unknown_tool"})

    def test_invalid_args(self):
        for raw in ("{", "null", "[]", "{}", '{"query":2}', '{"query":" "}',
                    '{"query":"x","limit":true}', '{"query":"x","limit":0}',
                    '{"query":"x","limit":6}', '{"query":"x","extra":1}'):
            with self.subTest(raw=raw):
                self.assertEqual(impl.dispatch("search_places", raw), {"ok": False, "error": "invalid_args"})


class H04(unittest.TestCase):
    def test_feedback_links_the_call(self):
        def model(history):
            if len(history) == 1:
                self.assertEqual(history[0], {"role": "user", "content": "安静"})
                return call()
            self.assertEqual([m["role"] for m in history], ["user", "assistant", "tool"])
            self.assertEqual(history[1]["call"]["id"], history[2]["call_id"])
            self.assertEqual(json.loads(history[2]["content"])["items"], ["A"])
            return {"kind": "final", "text": "A"}

        self.assertEqual(impl.run_agent("安静", model, lambda name, raw: {"ok": True, "items": ["A"]}), "A")

    def test_final_skips_tool(self):
        self.assertEqual(impl.run_agent("你好", lambda h: {"kind": "final", "text": "你好"}, self.fail), "你好")

    def test_bounds_and_unknown_kind(self):
        calls = []
        def tool(name, raw):
            calls.append(name)
            return {"ok": True, "items": []}
        with self.assertRaises(RuntimeError):
            impl.run_agent("安静", lambda h: call(), tool, max_steps=2)
        self.assertEqual(calls, ["search_places"] * 2)
        with self.assertRaises(ValueError):
            impl.run_agent("安静", lambda h: {"kind": "other"}, tool)


class H05(unittest.IsolatedAsyncioTestCase):
    async def test_concurrency_and_source_order(self):
        ready = asyncio.Event()
        async def first(q):
            await ready.wait()
            return [q]
        async def second(q):
            ready.set()
            return []
        result = await impl.lookup_sources("安静", {"a": first, "b": second}, timeout_s=1)
        self.assertEqual(result, [{"source": "a", "ok": True, "items": ["安静"]},
                                  {"source": "b", "ok": True, "items": []}])

    async def test_partial_timeout(self):
        async def slow(q):
            await asyncio.Event().wait()
        async def fast(q):
            return [q]
        result = await impl.lookup_sources("咖啡", {"slow": slow, "fast": fast}, timeout_s=0.05)
        self.assertEqual(result, [{"source": "slow", "ok": False, "error": "timeout"},
                                  {"source": "fast", "ok": True, "items": ["咖啡"]}])

    async def test_empty_batch(self):
        self.assertEqual(await impl.lookup_sources("q", {}, timeout_s=1), [])


class H06(unittest.IsolatedAsyncioTestCase):
    async def test_events_are_lazy_and_linked(self):
        calls = []
        async def tool(name, raw):
            calls.append(name)
            return {"ok": True, "items": ["A"]}
        stream = impl.stream_agent("q", tool=tool)
        first = await anext(stream)
        self.assertEqual(calls, [])
        rest = [event async for event in stream]
        self.assertEqual(calls, ["search_places"])
        self.assertEqual([first["type"], *(e["type"] for e in rest)], ["tool_call", "tool_result", "final"])
        self.assertEqual(first["id"], rest[0]["id"])
        self.assertEqual(rest[-1]["text"], "A")

    async def test_final_only(self):
        events = [e async for e in impl.stream_agent("q", lambda h: {"kind": "final", "text": "ok"})]
        self.assertEqual(events, [{"type": "final", "text": "ok"}])

    async def test_budget_exhausted(self):
        async def tool(name, raw):
            return {"ok": True, "items": []}
        with self.assertRaises(RuntimeError):
            async for _ in impl.stream_agent("q", lambda h: call(), tool, max_steps=1):
                pass


class H07(unittest.TestCase):
    def test_metadata_args_and_return(self):
        log = []
        @impl.observe(log)
        def search(q, *, limit):
            """查地点。"""
            return [q] * limit
        self.assertEqual(search("安静", limit=2), ["安静", "安静"])
        self.assertEqual((search.__name__, search.__doc__), ("search", "查地点。"))
        self.assertEqual(log, [{"fn": "search", "status": "returned"}])

    def test_exception_is_reraised(self):
        log = []
        @impl.observe(log)
        def broken():
            raise ValueError("bad")
        with self.assertRaisesRegex(ValueError, "bad"):
            broken()
        self.assertEqual(log, [{"fn": "broken", "status": "raised", "error": "ValueError"}])


class H08(unittest.TestCase):
    def test_model_instances_and_exhaustion(self):
        final = {"kind": "final", "text": "完成"}
        a, b = impl.ReplayModel([final]), impl.ReplayModel([final])
        self.assertEqual(a([]), final)
        self.assertEqual((a.calls, b.calls), (1, 0))
        with self.assertRaises(AssertionError):
            a([])
        self.assertEqual(a.calls, 1)

    def test_two_calls_then_final(self):
        model = impl.ReplayModel([call("x", "自习"), call("y", "咖啡"), {"kind": "final", "text": "完成"}])
        seen = []
        def tool(name, raw):
            seen.append(json.loads(raw)["query"])
            return {"ok": True, "items": []}
        self.assertEqual(reference.run_agent("q", model, tool), "完成")
        self.assertEqual((model.calls, seen), (3, ["自习", "咖啡"]))

    def test_cases_from_json(self):
        path = Path(__file__).with_name("replay_cases.json")
        with path.open(encoding="utf-8") as file:
            cases = json.load(file)
        for case in cases:
            with self.subTest(query=case["query"]):
                model = impl.ReplayModel(case["actions"])
                observations = []
                def tool(name, raw):
                    result = reference.dispatch(name, raw)
                    observations.append(result)
                    return result
                answer = reference.run_agent(case["query"], model, tool)
                self.assertEqual(answer, case["expected_answer"])
                self.assertEqual(observations, case["expected_observations"])
                self.assertEqual(model.calls, len(case["actions"]))


HOURS = [H01, H02, H03, H04, H05, H06, H07, H08]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hour", type=int, choices=range(1, 9), nargs="?")
    parser.add_argument("--reference", action="store_true", help="检查课程参考实现")
    args = parser.parse_args()
    if args.reference:
        impl = reference
    selected = HOURS if args.hour is None else [HOURS[args.hour - 1]]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in selected)
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if outcome.wasSuccessful() else 1)
