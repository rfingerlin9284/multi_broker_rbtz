import time
from multi_broker_phoenix.hive.brain_seat_router import BrainSeatRouter


class AIRepairAgent:
    def __init__(self, interval_s: int = 20):
        self.interval_s = interval_s
        self.router = BrainSeatRouter()

    def run_forever(self):
        backoff = {"grok": 60, "deepseek": 60}
        while True:
            snap = self.router.snapshot()

            for name, st in snap.items():
                if name in ("grok", "deepseek") and not st["ok"]:
                    self.router.soft_disable(name, backoff[name], st["reason"])

            time.sleep(self.interval_s)
