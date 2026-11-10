"""Hours 7–8: transparent instrumentation and a replayable model."""

from functools import wraps


def observe(log: list[dict]):
    def decorate(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            try:
                value = func(*args, **kwargs)
            except Exception as exc:
                log.append({"fn": func.__name__, "status": "raised", "error": type(exc).__name__})
                raise
            log.append({"fn": func.__name__, "status": "returned"})
            return value
        return wrapped
    return decorate


class ReplayModel:
    def __init__(self, actions: list[dict]):
        self._actions = iter(actions)
        self.calls = 0

    def __call__(self, history: list[dict]) -> dict:
        try:
            action = next(self._actions)
        except StopIteration as exc:
            raise AssertionError("回放动作已耗尽") from exc
        self.calls += 1
        return action
