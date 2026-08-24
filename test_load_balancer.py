import unittest
from unittest.mock import patch

import load_balancer


class LeastConnectionsTests(unittest.TestCase):
    def setUp(self):
        with load_balancer.lock:
            load_balancer.active[:] = [0] * len(load_balancer.BACKENDS)

    def test_selection_reserves_minimum_before_next_selection(self):
        with load_balancer.lock:
            load_balancer.active[:] = [2, 0, 3]

        with patch("builtins.print"):
            first = load_balancer.pick_least_connections()
            second = load_balancer.pick_least_connections()

        self.assertEqual((first, second), (1, 1))
        self.assertEqual(load_balancer.active, [2, 2, 3])

    def test_release_returns_count_to_zero(self):
        with patch("builtins.print"):
            index = load_balancer.pick_least_connections()
            load_balancer.release(index)

        self.assertEqual(load_balancer.active, [0, 0, 0])


if __name__ == "__main__":
    unittest.main()