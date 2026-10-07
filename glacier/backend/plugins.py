"""Plug-in loading, so several builders can add step types and API routes in parallel without editing shared files.

Step plug-in  = a module in nodes/ (or <extra dir>/nodes/) defining NODE = {
    "catalog": {...same shape as an entry of glacier/contract/node_types.json, plus optional "worker": true...},
    "run": callable(ctx: dict) -> dict }
  ctx keys: env_id, run_id, node_id, config (dict), prev (previous worker result dict or None), home (GLACIER_HOME),
            log (callable(text) to stream live output while running)
  return:   {"state": "done"|"failed", "output": str, "exit_code"?: int, "branch"?: str, "usage"?: Usage}
            Usage = {"model": str, "route": str, "tokens_in": int, "tokens_out": int, "cost_usd": float}
  "worker": true makes the step behave like command/codex (has exit_code; a check can branch on it).
Route plug-in = a module in routes/ defining `router` (a fastapi.APIRouter). Paths must start with /api/.
Extra plug-in folders: GLACIER_PLUGIN_DIRS (os.pathsep separated), each with nodes/ and/or routes/ inside."""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
NODES: dict[str, dict] = {}


def _dirs(sub: str) -> list[str]:
    extra = [d for d in os.environ.get("GLACIER_PLUGIN_DIRS", "").split(os.pathsep) if d]
    return [p for p in [os.path.join(HERE, sub)] + [os.path.join(d, sub) for d in extra] if os.path.isdir(p)]


def _modules(sub: str):
    for d in _dirs(sub):
        for name in sorted(os.listdir(d)):
            if name.endswith(".py") and not name.startswith("_"):
                path = os.path.join(d, name)
                mod_name = f"glacier_plugin_{sub}_{abs(hash(path))}_{name[:-3]}"
                spec = importlib.util.spec_from_file_location(mod_name, path)
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)
                yield path, mod


def load_nodes(core_types: set[str]) -> list[dict]:
    """Registers step plug-ins; returns their catalog entries. A plug-in may not redefine a core type."""
    catalog = []
    for path, mod in _modules("nodes"):
        node = getattr(mod, "NODE", None)
        if not isinstance(node, dict) or not callable(node.get("run")) or not isinstance(node.get("catalog"), dict):
            raise RuntimeError(f"step plug-in {path} must define NODE = {{'catalog': {{...}}, 'run': fn}}")
        t = node["catalog"].get("type")
        if not t or t in core_types or t in NODES:
            raise RuntimeError(f"step plug-in {path}: type {t!r} is missing or already defined")
        NODES[t] = node
        catalog.append(node["catalog"])
    return catalog


def load_routes(app) -> None:
    for path, mod in _modules("routes"):
        router = getattr(mod, "router", None)
        if router is None:
            raise RuntimeError(f"route plug-in {path} must define `router` (fastapi.APIRouter)")
        for r in router.routes:
            if not getattr(r, "path", "").startswith("/api/"):
                raise RuntimeError(f"route plug-in {path}: path {r.path!r} must start with /api/")
        app.include_router(router)


def is_worker(kind: str) -> bool:
    return kind in ("command", "codex", "flow") or bool(NODES.get(kind, {}).get("catalog", {}).get("worker"))
