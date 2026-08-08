from __future__ import annotations

import unittest

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.core import CTFAgent, _tool_observed_flags


class StubModel:
    def __init__(self, response: AIMessage):
        self.response = response
        self.invoked = False

    def invoke(self, _messages):
        self.invoked = True
        return self.response


class EvidenceGateTests(unittest.TestCase):
    def make_agent(self, response: AIMessage) -> tuple[CTFAgent, StubModel]:
        model = StubModel(response)
        agent = CTFAgent.__new__(CTFAgent)
        agent.verbose = False
        agent.llm_with_tools = model
        return agent, model

    def test_tool_observation_is_accepted_without_another_model_call(self):
        flag = "UCSI26{verified_tool_output}"
        state = {
            "messages": [
                HumanMessage(content="Solve the challenge"),
                ToolMessage(content=f"server response: {flag}", tool_call_id="call-1"),
            ],
            "flags_found": [],
            "iteration": 1,
            "max_iterations": 10,
            "status": "running",
        }
        agent, model = self.make_agent(AIMessage(content="unused"))

        result = agent._reason_node(state)

        self.assertEqual(result["flags_found"], [flag])
        self.assertEqual(result["status"], "solved")
        self.assertFalse(model.invoked)

    def test_model_only_flag_is_not_accepted_as_evidence(self):
        state = {
            "messages": [HumanMessage(content="Solve the challenge")],
            "flags_found": [],
            "iteration": 0,
            "max_iterations": 10,
            "status": "running",
        }
        agent, model = self.make_agent(AIMessage(content="UCSI26{model_guess}"))

        result = agent._reason_node(state)

        self.assertTrue(model.invoked)
        self.assertEqual(result["flags_found"], [])
        self.assertEqual(result["status"], "running")

    def test_tool_flags_are_deduplicated(self):
        messages = [
            ToolMessage(content="UCSI26{same_flag}", tool_call_id="call-1"),
            ToolMessage(content="again UCSI26{same_flag}", tool_call_id="call-2"),
        ]
        self.assertEqual(_tool_observed_flags(messages), ["UCSI26{same_flag}"])


if __name__ == "__main__":
    unittest.main()
