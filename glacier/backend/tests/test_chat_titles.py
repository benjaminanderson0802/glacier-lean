import chat_titles


def test_injected_context_is_not_a_title():
    raw = "<environment_context> <cwd>C:\\Users\\benja\\Documents</cwd> <shell>powershell</shell> </environment_context>"
    assert chat_titles.clean_title(raw) == ""
    assert chat_titles.first_title([raw, "  make it visible in sites\nfor me  "]) == "make it visible in sites for me"


def test_truncated_block_and_goal_wrapper_are_dropped():
    assert chat_titles.clean_title("<codex_internal_context source=\"goal\"> Continue working toward the act") == ""
    assert chat_titles.clean_title("<system-reminder>x</system-reminder>\nFix the parser") == "Fix the parser"


def test_json_content_parts_use_their_text():
    raw = '[{"type": "text", "text": "<system-reminder>\\nscratch</system-reminder>"}, {"type": "text", "text": "Plan a refactor"}]'
    assert chat_titles.clean_title(raw) == "Plan a refactor"
    truncated = '[{"type": "text", "text": "<system-reminder>\\nThe user started this session without choosing a pro'
    assert chat_titles.clean_title(truncated) == ""


def test_background_sessions_are_automated():
    assert chat_titles.is_automated("", "C:\\work")
    assert chat_titles.is_automated("Reply with exactly: ok", "C:\\work")
    assert chat_titles.is_automated("SMOKE TEST for Forge (role: builder).", "C:\\work")
    assert chat_titles.is_automated("You are the TROUBLESHOOTER. CAPABILITY FIX JOB", "C:\\work")
    assert chat_titles.is_automated("hello", "C:\\Users\\benja\\AppData\\Local\\Temp\\tmp0sb6k4q6")
    assert not chat_titles.is_automated("make it visible in sites for me", "C:\\Users\\benja\\Documents\\Codex\\x")


def test_agents_md_and_role_prompts():
    agents = "# AGENTS.md instructions for C:\\Users\\benja\\proj\n\n<INSTRUCTIONS>\nbe nice\n</INSTRUCTIONS>"
    assert chat_titles.first_title([agents, "why did my chats disappear?"]) == "why did my chats disappear?"
    assert chat_titles.is_automated("You are Glacier's Architect.", "C:\\work")
    assert chat_titles.is_automated("Glacier V1 basic TALK acceptance probe. Reply with exactly X", "C:\\work")
