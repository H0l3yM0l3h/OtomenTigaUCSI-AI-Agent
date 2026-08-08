from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent.tools.code_executor import execute_python_code, execute_script_file


class CodeExecutorTests(unittest.TestCase):
    def test_generated_code_uses_active_environment(self):
        result = execute_python_code.invoke({"code": "import sys; print(sys.executable)"})

        self.assertIn("[STDOUT]", result)
        self.assertIn("python", result.lower())

    def test_script_arguments_preserve_quoted_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir, "args.py")
            script.write_text("import sys; print(sys.argv[1:])", encoding="utf-8")

            result = execute_script_file.invoke(
                {"file_path": str(script), "arguments": '--name "Otomen Tiga"'}
            )

        self.assertIn("Otomen Tiga", result)

    def test_timeout_is_bounded(self):
        result = execute_python_code.invoke({"code": "print('no')", "timeout": 301})
        self.assertIn("timeout must be between", result)


if __name__ == "__main__":
    unittest.main()
