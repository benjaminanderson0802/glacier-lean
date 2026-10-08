"""The desktop app ships only what desktop/src-tauri/tauri.conf.json lists as resources. Rebuild that installed
layout from the config and check the backend starts from it, so a module or folder the backend needs can never
be left out of the installer again (the Windows installer once failed with "No module named 'glacier'")."""
import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TAURI = REPO / "desktop" / "src-tauri"


def _install(target: Path) -> None:
    resources = json.loads((TAURI / "tauri.conf.json").read_text(encoding="utf-8"))["bundle"]["resources"]
    for source, destination in resources.items():
        matches = glob.glob(str(TAURI / source))
        assert matches, f"resource {source} matches no files"
        for match in matches:
            if os.path.isdir(match):
                continue
            out = target / destination
            if destination.endswith("/"):
                out = out / os.path.basename(match)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(match, out)


def test_backend_starts_from_the_installed_layout(tmp_path):
    app_dir = tmp_path / "app"
    _install(app_dir)
    home = tmp_path / "home"
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH",)}
    env.update(GLACIER_HOME=str(home), GLACIER_TOKEN="layout-test-token")
    probe = (
        "import sys; sys.path.insert(0, '.')\n"
        "import app, import_service, template_registry\n"
        "from routes.releases import release_notes\n"
        "assert template_registry.BUNDLED_DIR.is_dir(), template_registry.BUNDLED_DIR\n"
        "assert str(template_registry.BUNDLED_DIR).startswith(sys.argv[1]), template_registry.BUNDLED_DIR\n"
        "assert any(template_registry.BUNDLED_DIR.glob('*.json'))\n"
        "assert release_notes()['version'] == '0.2.0'\n"
        "assert set(import_service._SOURCES) == {'chatgpt', 'claude'}\n"
        "print('ok')\n"
    )
    result = subprocess.run([sys.executable, "-I", "-c", probe, str(app_dir)], cwd=app_dir / "backend",
                            env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0 and result.stdout.strip().endswith("ok"), result.stderr[-3000:]
