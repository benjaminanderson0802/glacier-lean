import json
import unittest
from unittest.mock import patch

import run_live


class FakeResponse:
    status_code = 200

    def __init__(self, text):
        self.text = text
        self._lines = iter(text.splitlines())

    def __enter__(self): return self
    def __exit__(self, *_): return False
    def raise_for_status(self): pass
    def iter_lines(self, decode_unicode=True): return self._lines
    def json(self): return json.loads(self.text)


class FakeSession:
    def __init__(self):
        self.requests = []
        self.environments = []
        self.last_proposal = None

    def post(self, url, json=None, headers=None, stream=False, timeout=None):
        self.requests.append((url, json, headers, stream))
        if url.endswith("/api/assistant/chat"):
            prompt = json["message"]
            if "unplannable" in prompt:
                event = {"type": "RUN_ERROR", "message": "The assistant could not answer. Please try again."}
                return FakeResponse("data: " + json_module.dumps(event) + "\n\n")
            if "weekday" in prompt:
                proposal = {"id": "p1", "flow": {"id": "weekday-backup", "name": "Backup", "goal": prompt,
                    "nodes": [{"id": "schedule", "type": "schedule", "config": {"cron": "0 9 * * 1-5"}}],
                    "edges": [], "acceptance": [{"kind": "human", "question": "Did the backup finish?"}]}}
                self.last_proposal = proposal
                events = [{"type": "TOOL_CALL_ARGS", "toolCallId": "t", "delta": json_module.dumps(proposal)},
                          {"type": "TOOL_CALL_END", "toolCallId": "t"}, {"type": "RUN_FINISHED"}]
            else:
                events = [{"type": "TEXT_MESSAGE_CONTENT", "delta": "I can help you build and run automations."},
                          {"type": "RUN_FINISHED"}]
            return FakeResponse("".join("data: " + json_module.dumps(e) + "\n\n" for e in events))
        if "/apply" in url:
            if json["approve"]:
                self.environments.append({"id": self.last_proposal["flow"]["id"]})
                return FakeResponse(json_module.dumps({"saved": True, "undo_id": "u1"}))
            return FakeResponse(json_module.dumps({"discarded": True}))
        if url.endswith("/api/environments"):
            return FakeResponse(json_module.dumps(self.environments))
        raise AssertionError(url)

    def get(self, url, headers=None, timeout=None):
        self.requests.append((url, None, headers, False))
        return FakeResponse(json_module.dumps(self.environments))


def fake_session():
    return FakeSession()


json_module = json


class LiveAskDryRunTests(unittest.TestCase):
    def test_dry_run_exercises_chat_approval_and_rejection_without_network(self):
        session = FakeSession()
        result = run_live.run_dry(session=session)
        self.assertTrue(result["question"]["passed"])
        self.assertTrue(result["approve"]["passed"])
        self.assertTrue(result["reject"]["passed"])
        self.assertGreaterEqual(len(session.requests), 5)
        self.assertEqual("What can you do for me?", session.requests[0][1]["message"])

    def test_bad_plan_error_is_plain_text_and_does_not_crash(self):
        client = run_live.Client("http://fake.invalid", "dry-token", session=FakeSession())
        result = client.chat("unplannable automation")
        self.assertFalse(result["finished"])
        self.assertEqual("The assistant could not answer. Please try again.", result["error"])


if __name__ == "__main__":
    unittest.main()
