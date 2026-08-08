from __future__ import annotations

import unittest

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.core import CTFAgent


class _ScriptedToolModel:
    """Deterministic model double that requests one real harness tool."""

    def invoke(self, _messages):
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "execute_python_code",
                    "args": {"code": "print('UCSI26{graph_integration_smoke}')"},
                    "id": "integration-tool-call",
                    "type": "tool_call",
                }
            ],
        )


class GraphIntegrationTests(unittest.TestCase):
    def test_reason_tool_evidence_graph_end_to_end(self):
        agent = CTFAgent.__new__(CTFAgent)
        agent.verbose = False
        agent.llm_with_tools = _ScriptedToolModel()
        graph = agent._build_graph()

        result = graph.invoke(
            {
                "messages": [SystemMessage(content="test"), HumanMessage(content="run tool")],
                "challenge": "integration smoke test",
                "category": "misc",
                "flags_found": [],
                "iteration": 0,
                "max_iterations": 3,
                "status": "running",
            }
        )

        self.assertEqual(result["status"], "solved")
        self.assertEqual(result["flags_found"], ["UCSI26{graph_integration_smoke}"])
        self.assertEqual(result["iteration"], 1)


if __name__ == "__main__":
    unittest.main()
