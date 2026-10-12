"""Regression coverage for a common morning schedule request."""

from routes import assistant_chat


def test_every_morning_goal_is_routed_to_flow_planning_when_chat_says_plain_reply():
    answer = {"reply": "I can help create a morning flow.", "automation": False}

    assert assistant_chat._is_automation(
        "Every morning summarise my notes folder and save it to memory.", answer
    )
