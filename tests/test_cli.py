from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

import run


class CliTests(unittest.TestCase):
    def test_parser_exposes_doctor(self):
        args = run.build_parser().parse_args(["doctor"])
        self.assertEqual(args.command, "doctor")
        self.assertFalse(args.strict)

    def test_challenges_json_is_machine_readable(self):
        args = run.build_parser().parse_args(["challenges", "--json"])
        output = io.StringIO()
        with redirect_stdout(output):
            result = run.cmd_challenges(args)

        self.assertEqual(result, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(len(payload), 9)
        self.assertEqual(sum(item["evidence"] == "Replay solver" for item in payload), 8)

    def test_challenge_portfolio_command_succeeds(self):
        self.assertEqual(run.main(["challenges"]), 0)

    def test_documented_only_capture_is_not_reported_as_a_solver(self):
        self.assertEqual(run.main(["solver", "helios"]), 2)


if __name__ == "__main__":
    unittest.main()
