"""Keep planner guidance clear about workspace files and Memory notes."""

import assistant


def test_memory_summaries_read_file_contents_and_save_the_summary_to_memory():
    prompt = assistant._prompt("Summarize notes and save the result to memory", [])

    assert "reads one file from the flow workspace" in prompt
    assert "read Markdown file contents, not only their names" in prompt
    assert "do not broaden a named folder to the whole workspace" in prompt
    assert "use a note step with the result" in prompt
    assert "include `{prev_output}` in that AI step's prompt" in prompt
    assert "Approval prompts are shown literally" in prompt
    assert "do not put `{prev_output}` in them" in prompt
    assert "command steps write to the flow workspace, not Memory" in prompt
    assert "only follow a command or AI worker" in prompt
    assert "exit_code == 0" in prompt
    assert "run with /bin/sh and must use POSIX shell syntax" in prompt
    assert "relative command folders are inside the flow workspace" in prompt
