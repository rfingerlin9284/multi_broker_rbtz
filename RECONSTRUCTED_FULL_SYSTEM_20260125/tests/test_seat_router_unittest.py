import unittest

from multi_broker_phoenix.ai.seat_router import AISeatRouter, BaseSeat


class FakeSeat(BaseSeat):
    def __init__(self, name, ok):
        super().__init__(name=name, preferred=False, mandatory=False)
        self._ok = ok

    def health_check(self):
        return self._ok, "OK" if self._ok else "DOWN"

    def chat(self, prompt: str, system_prompt: str):
        if not self._ok:
            return False, "DOWN"
        return True, '{"signal":"buy","confidence":0.7,"reasoning":"ok"}'


class SeatRouterTest(unittest.TestCase):
    def test_router_selects_healthy_seat(self):
        router = AISeatRouter(seats=[FakeSeat("a", True), FakeSeat("b", False)])
        res = router.chat("hello", "system")
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("seat"), "a")


if __name__ == "__main__":
    unittest.main()
