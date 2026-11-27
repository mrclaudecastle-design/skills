#!/usr/bin/env python3
"""stopwatch: time each step of a reply so lag can be found, not guessed.

    from stopwatch import Stopwatch
    sw = Stopwatch()
    with sw.step("hear"):  ...
    with sw.step("think"): ...
    with sw.step("speak"): ...
    print(sw.report())
"""
import time
from contextlib import contextmanager

# How long each step may take before a caller notices, in milliseconds.
BUDGET_MS = {"hear": 300, "think": 500, "speak": 250}
TOTAL_BUDGET_MS = 1000


class Stopwatch:
    def __init__(self, budget=None, clock=time.perf_counter):
        self.budget = dict(BUDGET_MS if budget is None else budget)
        self.clock = clock
        self.times = {}

    @contextmanager
    def step(self, name: str):
        start = self.clock()
        try:
            yield
        finally:
            self.times[name] = self.times.get(name, 0.0) + (self.clock() - start) * 1000

    @property
    def total_ms(self) -> float:
        return sum(self.times.values())

    def slow_steps(self) -> list[str]:
        return [n for n, ms in self.times.items() if self.budget.get(n) and ms > self.budget[n]]

    def report(self) -> str:
        lines = []
        for name, ms in self.times.items():
            limit = self.budget.get(name)
            flag = "  SLOW" if limit and ms > limit else ""
            lines.append(f"{name:8}{ms:8.0f} ms" + (f"  (limit {limit})" if limit else "") + flag)
        flag = "  SLOW" if self.total_ms > TOTAL_BUDGET_MS else ""
        lines.append(f"{'total':8}{self.total_ms:8.0f} ms  (limit {TOTAL_BUDGET_MS}){flag}")
        return "\n".join(lines)


if __name__ == "__main__":
    sw = Stopwatch()
    for name, secs in [("hear", 0.05), ("think", 0.12), ("speak", 0.03)]:
        with sw.step(name):
            time.sleep(secs)
    print(sw.report())
