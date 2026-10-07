"""Worker step that asks the configured model gateway for any available model."""
import gateway


def run(ctx: dict, routes: list[dict] | None = None) -> dict:
    return gateway.complete(ctx, routes=routes)


NODE = {
    "catalog": {
        "type": "ai_any",
        "label": "AI (any model)",
        "description": "Asks an available model, trying your routes in order.",
        "worker": True,
        "fields": [
            {"key": "prompt", "label": "Task ({env} {run} {prev_output})", "placeholder": "Summarize: {prev_output}", "default": "", "multiline": True},
            {"key": "routes", "label": "Model routes", "placeholder": "all available routes", "default": "", "optional": True},
            {"key": "timeout", "label": "Time limit (seconds)", "placeholder": "600", "default": "600", "optional": True},
        ],
        "branches": None,
    },
    "run": run,
}
