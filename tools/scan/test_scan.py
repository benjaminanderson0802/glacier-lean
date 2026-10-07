import json
from datetime import date, timedelta
from pathlib import Path

import scan


def test_offline_fixture_parses_mcp_github_and_ollama_sources(tmp_path):
    today = date(2026, 10, 7)
    fixture = {
        "mcp": {
            "servers": [
                {"name": "mcp-new", "license": "MIT", "url": "https://example.test/mcp", "updated_at": str(today), "description": "MCP helper", "stars": 80}
            ]
        },
        "github_mcp": {"items": [{"name": "github-mcp", "license": "Apache-2.0", "url": "https://github.com/example/mcp", "updated_at": str(today), "description": "MCP server", "stars": 70}]},
        "github_agents": {"items": [{"name": "github-agent", "license": "BSD-3-Clause", "url": "https://github.com/example/agent", "updated_at": str(today), "description": "Agent tool", "stars": 60}]},
        "github_ollama": {"items": [{"name": "github-ollama", "license": "MIT", "url": "https://github.com/example/ollama", "updated_at": str(today), "description": "Ollama tool", "stars": 50}]},
        "ollama": {"models": [{"name": "model-new", "license": "Apache-2.0", "url": "https://ollama.com/library/model-new", "updated_at": str(today), "description": "Local model"}]},
    }
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")

    records = scan.load_records(path, today=today)

    assert {record.name for record in records} == {
        "mcp-new", "github-mcp", "github-agent", "github-ollama", "model-new"
    }


def test_license_activity_and_github_star_filters(tmp_path):
    today = date(2026, 10, 7)
    old = str(today - timedelta(days=91))
    fixture = {
        "mcp": {"servers": [
            {"name": "closed", "license": "SSPL", "url": "https://example.test/closed", "updated_at": str(today), "stars": 100},
            {"name": "stale", "license": "MIT", "url": "https://example.test/stale", "updated_at": old, "stars": 100},
        ]},
        "github_mcp": {"items": [
            {"name": "unpopular", "license": "MIT", "url": "https://github.com/example/unpopular", "updated_at": str(today), "stars": 49},
            {"name": "good", "license": "MIT", "url": "https://github.com/example/good", "updated_at": str(today), "stars": 50},
        ]},
        "github_agents": {"items": []}, "github_ollama": {"items": []},
        "ollama": {"models": []},
    }
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")

    records = scan.load_records(path, today=today)

    assert [record.name for record in records] == ["good"]


def test_already_installed_tools_are_skipped(tmp_path):
    setup = tmp_path / "setup"
    setup.mkdir()
    (setup / "requirements.txt").write_text("requests==2.32.0\n", encoding="utf-8")
    (setup / "install_tools.sh").write_text("npm install -g @example/already\n", encoding="utf-8")
    fixture = {
        "mcp": {"servers": [
            {"name": "requests", "license": "MIT", "url": "https://pypi.org/project/requests", "updated_at": "2026-10-07"},
            {"name": "@example/already", "license": "MIT", "url": "https://example.test/already", "updated_at": "2026-10-07"},
            {"name": "new-tool", "license": "MIT", "url": "https://example.test/new", "updated_at": "2026-10-07"},
        ]},
        "github_mcp": {"items": []}, "github_agents": {"items": []},
        "github_ollama": {"items": []}, "ollama": {"models": []},
    }
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")

    records = scan.load_records(path, today=date(2026, 10, 7))
    remaining = scan.skip_installed(records, setup_root=setup)

    assert [record.name for record in remaining] == ["new-tool"]


def test_report_is_dated_and_proposal_only(tmp_path):
    fixture = {
        "mcp": {"servers": [{"name": "new-tool", "license": "MIT", "url": "https://example.test/new", "updated_at": "2026-10-07", "description": "A helpful tool"}]},
        "github_mcp": {"items": []}, "github_agents": {"items": []},
        "github_ollama": {"items": []}, "ollama": {"models": []},
    }
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    output = tmp_path / "proposals"

    report_path = scan.run(fixture=fixture_path, output_dir=output, today=date(2026, 10, 7))

    assert report_path.name == "proposals-2026-10-07.md"
    report = report_path.read_text(encoding="utf-8")
    assert "new-tool" in report
    assert "MIT" in report
    assert "https://example.test/new" in report
    assert "Roadmap step" in report
    assert "proposal" in report.lower()
    assert not (tmp_path / "installed").exists()
