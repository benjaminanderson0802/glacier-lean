"""Declared audit coverage for routes and node types with runtime side effects.

Tests compare the live FastAPI route table and node catalog with these declarations.
"""

# Each route is paired with the event it emits when it successfully causes an effect.
AUDITED_ROUTES = {
    "PUT /api/environments/{env_id}": "flow.saved",
    "POST /api/environments/{env_id}/run": "run.started",
    "POST /api/runs/{run_id}/approve": "run.approved",
    "PUT /api/memory/note": "vault.note_written",
    "POST /api/memory/undo": "vault.note_undone",
    "POST /api/memory/rename": "vault.note_renamed",
    "POST /api/runs/{run_id}/undo": "run.undone",
    "POST /api/environments/{env_id}/restore": "flow.restored",
    "PUT /api/secrets/{name}": "secret.set",
    "DELETE /api/secrets/{name}": "secret.deleted",
    "POST /api/files": "file.uploaded",
    "POST /api/projects": "project.created",
    "POST /api/status/rebuild": "status.rebuilt",
    "POST /api/starter/apply": "starter.applied",
    "POST /api/templates/import/{proposal_id}/approve": "template.approved",
    "POST /api/memory/hygiene/{proposal_id}": "memory.hygiene_applied",
    "POST /api/hooks/{env_id}": "run.started",
    "POST /api/imports": "memory.imported",
    "POST /api/imports/refresh": "memory.imports_refreshed",
    "POST /api/sessions/{session_id}/save-to-memory": "memory.session_saved",
    "POST /api/assistant/proposals/{proposal_id}/apply": "assistant.proposal_applied",
    "POST /api/assistant/conversations/{conversation_id}/rename": "assistant.conversation_renamed",
    "POST /api/claims/{cid}/decision": "claim.decided",
    "POST /api/claims/{cid}/rerun": "run.started",
    "POST /api/memory/hygiene/scan": "memory.hygiene_scanned",
    "POST /api/templates/import": "template.reviewed",
    "POST /api/claims": "claim.filed",
    "POST /api/assistant/plan": "assistant.plan_requested",
    "DELETE /api/environments/{env_id}": "flow.deleted",
    "POST /api/environments/{env_id}/undo-delete": "flow.delete_undone",
    "DELETE /api/runs/{run_id}": "run.deleted",
    "POST /api/runs/{run_id}/undo-delete": "run.delete_undone",
    "POST /api/build/interview": "build.interview_turn",
    "POST /api/build/vision": "build.vision_confirmed",
    "POST /api/build/spec": "build.spec_approved",
    "POST /api/build/plan": "build.plan_requested",
    "POST /api/teams": "team.plan_approved",
    "POST /api/teams/{team_id}/run": "team.run_started",
    "POST /api/teams/{team_id}/pause": "team.pause_requested",
    "POST /api/teams/{team_id}/stop": "team.stop_requested",
    "POST /api/teams/{team_id}/tasks/{task_id}/approve": "team.task_approval",
    "POST /api/teams/{team_id}/features/{feature_id}/grade": "team.feature_graded",
}

# Runtime nodes that can perform an external or local side effect when executed.
AUDITED_NODES = {
    "command": "step.command_executed",
    "codex": "outbound.model_call",
    "note": "vault.note_written",
    "http_request": "outbound.http_request",
    "fetch_page": "outbound.web_fetch",
    "web_search": "outbound.web_search",
    "read_document": "outbound.document_fetch",
    "acp_agent": "outbound.agent_call",
    "local_ai": "outbound.model_call",
    "flow": "run.child_started",
}

SIDE_EFFECT_NODE_TYPES = set(AUDITED_NODES)
