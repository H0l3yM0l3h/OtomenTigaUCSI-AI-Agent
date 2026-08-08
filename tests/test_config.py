from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from agent.config import _read_max_iterations


class ConfigTests(unittest.TestCase):
    def test_invalid_iteration_setting_becomes_diagnosable(self):
        with patch.dict(os.environ, {"MAX_ITERATIONS": "not-a-number"}):
            self.assertEqual(_read_max_iterations(), 0)

    def test_valid_iteration_setting_is_parsed(self):
        with patch.dict(os.environ, {"MAX_ITERATIONS": "40"}):
            self.assertEqual(_read_max_iterations(), 40)


if __name__ == "__main__":
    unittest.main()
