from __future__ import annotations

import importlib
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from agent.challenges import CHALLENGES, challenge_by_name, replayable_challenges


class PortfolioTests(unittest.TestCase):
    def test_portfolio_has_nine_unique_captures(self):
        self.assertEqual(len(CHALLENGES), 9)
        self.assertEqual(len({item.slug for item in CHALLENGES}), 9)
        self.assertEqual(len({item.flag for item in CHALLENGES}), 9)

    def test_eight_replay_modules_import(self):
        replayable = replayable_challenges()
        self.assertEqual(len(replayable), 8)
        for challenge in replayable:
            module = importlib.import_module(challenge.solver_module)
            self.assertTrue(callable(getattr(module, "solve", None)) or callable(getattr(module, "solve_remote", None)))

    def test_alias_resolution(self):
        self.assertEqual(challenge_by_name("saturn_exchange").slug, "saturn-exchange")
        self.assertEqual(challenge_by_name("helios-metadata-broker").slug, "helios")
        self.assertIsNone(challenge_by_name("not-a-challenge"))

    def test_missing_firmware_never_claims_success(self):
        from solvers import oldstock_router

        previous = os.getcwd()
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    result = oldstock_router.solve()
            finally:
                os.chdir(previous)

        self.assertIsNone(result)
        self.assertNotIn("FLAG FOUND", output.getvalue())


if __name__ == "__main__":
    unittest.main()
