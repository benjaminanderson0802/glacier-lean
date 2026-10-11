"""Keep UI change proposals within the review validator's diff budget."""

from routes import assistant_chat
import ui_change


def test_ui_change_diff_schema_matches_the_validator_limit():
    diff = assistant_chat._ui_change_schema()["properties"]["ui_change"]["properties"]["diff"]

    assert diff["minLength"] == 1
    assert diff["maxLength"] == ui_change.MAX_DIFF_CHARS
