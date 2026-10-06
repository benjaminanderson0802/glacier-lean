from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .storage import require_no_secret


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Runtime(StrictModel):
    provider: Literal['maf_ollama','codex','openai_compatible']
    model: str | None = None
    structured: bool = False
    library_id: str | None = None
    endpoint: str | None = None
    parameters: dict = Field(default_factory=dict)
    adapter: str | None = None


class Context(StrictModel):
    reset_on_task_complete: bool = False
    fresh_on_task_start: bool = True
    checkpoint_interval_seconds: int = Field(default=30,ge=5,le=3600)
    compaction: Literal['UNAVAILABLE','GLACIER_MANAGED'] = 'UNAVAILABLE'
    compact_after_messages: int = Field(default=40,ge=4,le=1000)


class Permissions(StrictModel):
    filesystem: Literal['none','task','read-only'] = 'none'
    network: Literal[False] = False
    capabilities: dict[str, Literal['ALLOW','DENY','APPROVAL']] = Field(default_factory=dict)
    web_origins: list[str] = Field(default_factory=list)
    github_repositories: list[str] = Field(default_factory=list)


class Memory(StrictModel):
    mode: Literal['task'] = 'task'  # legacy field retained; explicit records now support all scopes
    task: Literal['NONE','READ','READ_WRITE'] = 'READ_WRITE'
    worker: Literal['NONE','READ','READ_WRITE'] = 'NONE'
    project: Literal['NONE','READ','READ_WRITE'] = 'NONE'
    organization: Literal['NONE','READ','READ_WRITE'] = 'NONE'
    on_completion: Literal['KEEP','SUMMARIZE','SELECTIVE','WIPE'] = 'KEEP'
    on_failure: Literal['KEEP','WIPE'] = 'KEEP'
    on_cancellation: Literal['KEEP','WIPE'] = 'KEEP'
    summary_scope: Literal['TASK','WORKER'] = 'WORKER'
    promote_categories: dict[str,Literal['WORKER','PROJECT']] = Field(default_factory=dict)
    max_records_per_scope: int = Field(default=200,ge=1,le=10000)
    max_chars_per_scope: int = Field(default=256000,ge=1000,le=10000000)
    selected_categories: list[str] = Field(default_factory=list)
    ttl_seconds: int | None = Field(default=None,ge=1,le=315360000)
    context_limit: int = Field(default=8000,ge=0,le=32000)


class Behavior(StrictModel):
    goal_adherence: int = Field(default=80,ge=0,le=100)
    exploration: int = Field(default=40,ge=0,le=100)
    creativity: int = Field(default=40,ge=0,le=100)
    speed: int = Field(default=60,ge=0,le=100)
    thoroughness: int = Field(default=70,ge=0,le=100)
    autonomy: int = Field(default=50,ge=0,le=100)
    risk_tolerance: int = Field(default=20,ge=0,le=100)
    human_escalation: int = Field(default=70,ge=0,le=100)


class Schedule(StrictModel):
    id: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,63}$')
    kind: Literal['ONCE','INTERVAL','DAILY','EVENT']
    title: str = Field(min_length=1,max_length=200)
    objective: str = Field(min_length=1,max_length=20000)
    enabled: bool = False
    at: str | None = None
    interval_seconds: int = Field(default=3600,ge=30,le=31536000)
    time: str = '02:00'
    timezone: str = 'UTC'
    weekdays: list[int] = Field(default_factory=lambda:list(range(7)))
    event: Literal['TASK_COMPLETED','RUNTIME_ERROR','WEBHOOK'] = 'TASK_COMPLETED'
    source_worker: str | None = None
    source_task: str | None = None
    environment_version: str | None = None
    environment_inputs: dict = Field(default_factory=dict)


class Lifecycle(StrictModel):
    turn_timeout_seconds: int = Field(default=240,ge=1,le=1200)
    sleep_on_completion: bool = False
    on_failure: Literal['ERROR','IDLE'] = 'ERROR'
    on_cancellation: Literal['IDLE','SLEEPING'] = 'IDLE'


class ExecutionPolicy(StrictModel):
    privacy: Literal['ANY','LOCAL_ONLY'] = 'ANY'
    fallback_model: str | None = None
    allow_cloud_fallback: bool = False
    required_features: list[Literal['tools','structured','codex_session']] = Field(default_factory=list)


class Auditor(StrictModel):
    worker: str = 'bob'
    enabled: Literal[False] = False


class ProductAccess(StrictModel):
    enabled: bool = False
    privacy: Literal['LOCAL_ONLY','ANY'] = 'LOCAL_ONLY'
    projects: list[str] = Field(default_factory=list,max_length=20)
    workers: list[str] = Field(default_factory=list,max_length=30)
    created_worker_prefix: str = Field(default='assistant-created-',pattern=r'^[a-z][a-z0-9_-]{2,40}-$')
    max_commands: int = Field(default=20,ge=1,le=100)


class WorkerConfig(StrictModel):
    id: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,63}$')
    name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    description: str = ''
    execution_policy: ExecutionPolicy = Field(default_factory=ExecutionPolicy)
    behavior: Behavior = Field(default_factory=Behavior)
    lifecycle: Lifecycle = Field(default_factory=Lifecycle)
    schedules: list[Schedule] = Field(default_factory=list)
    instructions: list[str] = Field(min_length=1)
    capability_assignments: dict[str, str] = Field(default_factory=dict)
    capability_project: str | None = None
    runtime: Runtime
    permissions: Permissions = Field(default_factory=Permissions)
    context: Context = Field(default_factory=Context)
    memory: Memory = Field(default_factory=Memory)
    auditor: Auditor = Field(default_factory=Auditor)
    product_access: ProductAccess = Field(default_factory=ProductAccess)


def validate(data):
    require_no_secret(data)
    cfg = WorkerConfig.model_validate(data).model_dump()
    if cfg['runtime']['provider'] in ('maf_ollama','openai_compatible'):
        if not cfg['runtime']['model'] or cfg['permissions']['filesystem'] != 'none' or cfg['runtime']['structured']:
            raise ValueError('Local worker requires a model, no filesystem tools, and unstructured mode')
    elif cfg['permissions']['filesystem'] not in ('none','task','read-only'):
        raise ValueError('Codex worker requires task or read-only filesystem permissions')
    if cfg['runtime']['structured'] and cfg['permissions']['filesystem'] != 'read-only':
        raise ValueError('Structured auditor requires read-only mode')
    from .intelligence import validate_runtime, validate_schedules
    validate_runtime(cfg['runtime'])
    validate_schedules(cfg['schedules'],cfg['id'])
    if cfg['memory']['on_completion']=='SUMMARIZE' and cfg['memory']['summary_scope']=='WORKER' and cfg['memory']['worker']!='READ_WRITE':raise ValueError('Worker summary retention requires worker memory READ_WRITE')
    for scope in cfg['memory']['promote_categories'].values():
        if cfg['memory'][scope.lower()]!='READ_WRITE':raise ValueError('Configured promotion requires destination write access')
    return cfg
