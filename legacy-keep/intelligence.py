"""Worker behavior and runtime policy. Values are preferences, never authority."""
from datetime import datetime,timezone
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
import math,re

PARAMETERS={'maf_ollama':{'temperature','top_p','max_tokens'},'openai_compatible':{'temperature','top_p','max_tokens'},'codex':{'reasoning_effort'}}

def utc(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('Time must include UTC offset')
    return result.astimezone(timezone.utc)

def validate_runtime(runtime):
    provider=runtime['provider'];params=runtime.get('parameters',{})
    if set(params)-PARAMETERS[provider]:raise ValueError('Unsupported runtime parameter')
    for key,value in params.items():
        if key=='reasoning_effort':
            if value not in ('low','medium','high'):raise ValueError('Unsupported verified reasoning effort')
        elif type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Parameter must be finite numeric')
        elif key=='temperature' and not 0<=value<=2:raise ValueError('Temperature outside 0..2')
        elif key=='top_p' and not 0<value<=1:raise ValueError('top_p outside (0,1]')
        elif key=='max_tokens' and (type(value)!=int or not 1<=value<=32768):raise ValueError('Invalid output token limit')
    endpoint=runtime.get('endpoint')
    if endpoint:
        p=urlsplit(endpoint)
        if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or p.query or p.fragment:raise ValueError('Use a credential-free endpoint URL')
        if p.scheme=='http' and p.hostname not in ('127.0.0.1','localhost','::1'):raise ValueError('Remote endpoints require HTTPS')
    if provider=='openai_compatible' and (not endpoint or not runtime.get('library_id')):raise ValueError('Custom runtime requires a registered Model Library entry and endpoint')
    if runtime.get('adapter') and not runtime.get('library_id'):raise ValueError('Adapter selection requires Model Library validation')

def validate_schedules(schedules,worker):
    if len(schedules)>20 or len({x['id'] for x in schedules})!=len(schedules):raise ValueError('At most 20 uniquely named schedules')
    for s in schedules:
        ZoneInfo(s['timezone'])
        if s['kind'] in ('ONCE','INTERVAL'):
            if not s['at']:raise ValueError('Schedule needs an explicit timezone-aware start time')
            utc(s['at'])
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',s['time']):raise ValueError('Expected HH:MM')
        if not s['weekdays'] or any(type(d)!=int or d not in range(7) for d in s['weekdays']):raise ValueError('Weekdays are integers 0..6')
        if s['kind']=='EVENT' and s['event']!='WEBHOOK' and (not s['source_worker'] or s['source_worker']==worker):raise ValueError('Event schedule requires a different explicit source worker')

BEHAVIOR_MEANINGS={
 'goal_adherence':'Higher means less tolerance for deviation from the active objective.',
 'exploration':'Higher means compare more alternative approaches within scope.',
 'creativity':'Higher favors novel approaches while preserving every constraint.',
 'speed':'Higher favors an early useful result and time-boxed investigation.',
 'thoroughness':'Higher favors deeper verification and coverage.',
 'autonomy':'Higher resolves ordinary low-risk ambiguity independently within permissions.',
 'risk_tolerance':'Higher tolerates reversible uncertainty only within authorized actions.',
 'human_escalation':'Higher means ask for human guidance sooner when ambiguity or blockers matter.'}

def behavior_instructions(config):
    from .config import Behavior
    weights=Behavior.model_validate(config.get('behavior',{})).model_dump()
    return 'Glacier operating preferences (0-100; not neural weights or permissions):\n'+'\n'.join(f'{k}={weights[k]}: {meaning}' for k,meaning in BEHAVIOR_MEANINGS.items())+'\nConstraints and Step 6 permissions always take priority. Speed does not excuse false claims; exploration does not change the objective. Stop and report denied or pending actions; never self-approve.'

def extractive_summary(core,worker,task=None):
    """Public records only, bounded and explicitly lossy; never hidden reasoning."""
    import json
    w=core.worker(worker)
    sid=w['active_session_id']
    if not sid:return None,None
    session=core.store.one('sessions',sid)
    if task and session['task_id']!=task:raise ValueError('Active session belongs to another task')
    rows=core.store.rows('SELECT role,content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 6',(sid,))
    text='GLACIER_MANAGED context transfer: bounded public conversation excerpts, not lossless state.\n'+'\n'.join(r['role']+': '+r['content'][:600] for r in reversed(rows))
    return session['task_id'],text


def transfer(core,worker,task,summary):
    from .storage import now
    if summary:
        core.db.execute('INSERT INTO lifecycle_transfers VALUES(?,?,?,?,NULL) ON CONFLICT(worker_id) DO UPDATE SET task_id=excluded.task_id,summary=excluded.summary,created_at=excluded.created_at,consumed_at=NULL',(worker,task,summary,now()))


def swap_model(core,worker,model_id,policy='FRESH_CONTEXT',parameters=None,adapter=None,expected_revision=None):
    import json
    if policy not in ('FRESH_CONTEXT','TRANSFER_SUMMARY','KEEP_IF_COMPATIBLE'):raise ValueError('Unknown context policy')
    current=core.worker(worker)
    if expected_revision is not None and current['revision']!=expected_revision:raise ValueError('Stale worker configuration revision; reload before model change')
    cfg=json.loads(current['config']);item=core.models.get(model_id);p=item['model_profile']
    old=cfg['runtime'];runtime={'provider':p['provider'],'model':p['model'],'structured':old['structured'],'library_id':model_id,'endpoint':p['endpoint'],'parameters':parameters or {},'adapter':adapter}
    core.models.resolve(runtime)
    if policy=='KEEP_IF_COMPATIBLE':
        # Keep is intentionally narrow: identical brain/settings only.
        if any(old.get(k)!=runtime.get(k) for k in ('provider','model','parameters','adapter','endpoint')):raise ValueError('Raw context cannot be kept across different brains/settings; use FRESH_CONTEXT or TRANSFER_SUMMARY')
        return {'worker':worker,'status':'UNCHANGED','context':'KEPT'}
    task,summary=extractive_summary(core,worker) if policy=='TRANSFER_SUMMARY' else (None,None)
    if summary and not p['local']:
        private=core.db.execute("SELECT 1 FROM memory_records WHERE source_worker=? AND privacy='LOCAL_ONLY' LIMIT 1",(worker,)).fetchone()
        if (task and core.task(task)['execution_policy']=='LOCAL_ONLY') or private:raise ValueError('Private context cannot be transferred to a remote runtime; choose fresh context')
    cfg['runtime']=runtime
    with core.store.transaction():
        result=core.save_worker(cfg,source='user:model swap '+policy,expected_revision=expected_revision if expected_revision is not None else current['revision'])
        if summary:transfer(core,worker,task,summary)
        else:core.db.execute('DELETE FROM lifecycle_transfers WHERE worker_id=?',(worker,))
        core.store.event(worker,'MODEL_CHANGED',{'model_id':model_id,'context_policy':policy,'previous_provider':old['provider'],'provider':runtime['provider']})
    return result


def rollback(core,worker,revision,expected_revision=None):
    import json
    rows=core.store.rows('SELECT new_value FROM config_history WHERE worker_id=? AND id=?',(worker,revision))
    if not rows:raise ValueError('Configuration revision does not belong to this worker')
    with core.store.transaction():
        current=core.worker(worker)
        if expected_revision is not None and current['revision']!=expected_revision:raise ValueError('Stale worker configuration revision; reload before rollback')
        result=core.save_worker(json.loads(rows[0]['new_value']),source='user:rollback to revision '+str(revision),expected_revision=current['revision'])
        core.store.event(worker,'CONFIGURATION_ROLLED_BACK',{'revision':revision,'scope':'configuration only; no files, memory records, external actions or history reverted'})
    return result


def compact(core,worker):
    w=core.worker(worker)
    if w['status']=='WORKING':raise ValueError('Pause the worker before compacting context')
    task,summary=extractive_summary(core,worker)
    if not summary:raise ValueError('No active context')
    with core.store.transaction():
        core._reset(worker,'Glacier-managed extractive compaction')
        transfer(core,worker,task,summary)
        core.store.event(worker,'CONTEXT_COMPACTED',{'method':'GLACIER_MANAGED','lossless':False},task)
    return {'worker':worker,'method':'GLACIER_MANAGED','fresh_context_on_next_turn':True}

async def compact_native(core,worker):
    import asyncio,json,os
    from .storage import now
    w=core.worker(worker)
    if w['status']=='WORKING' or not w['active_session_id']:raise ValueError('Native compaction requires an idle worker with an active context')
    session=core.store.one('sessions',w['active_session_id']);cfg=json.loads(session['config'])
    if cfg['runtime']['provider']!='codex':raise ValueError('Native compaction is unavailable for this runtime')
    from .adapters import CodexAdapter
    from .tools import ToolEngine
    engine=ToolEngine(core,session['task_id'],session['id'])
    with core.store.transaction():
        if core.worker(worker)['status']=='WORKING':raise ValueError('Worker became busy')
        core.db.execute('INSERT INTO lifecycle_operations VALUES(?,?,?,?)',(worker,os.getpid(),'NATIVE_COMPACTION',now()))
        core.db.execute("UPDATE workers SET status='WORKING' WHERE id=?",(worker,))
    def checkpoint(snapshot):core.db.execute('UPDATE sessions SET snapshot=?,checkpoint_at=? WHERE id=?',(json.dumps(snapshot),now(),session['id']))
    def emit(kind,payload):core.store.event(worker,kind,payload,session['task_id'],session['id'])
    adapter=CodexAdapter(cfg,core.workspace(core.task(session['task_id'])),checkpoint,emit);adapter.managed_tools=engine
    success=False
    try:
        await adapter.prepare(json.loads(session['snapshot']))
        await adapter.request('thread/compact/start',{'threadId':adapter.external_id})
        async with asyncio.timeout(120):
            while True:
                event=adapter.pending.popleft() if adapter.pending else await adapter.receive()
                params=event.get('params',{})
                if params.get('threadId')==adapter.external_id and (event.get('method')=='thread/compacted' or (event.get('method')=='item/completed' and params.get('item',{}).get('type')=='contextCompaction')):break
        success=True;emit('CONTEXT_COMPACTED',{'method':'NATIVE','runtime':'codex','rollback_supported':False})
        return {'method':'NATIVE','status':'COMPLETED','worker':worker}
    finally:
        await adapter.close();await engine.close()
        with core.store.transaction():
            core.db.execute('DELETE FROM lifecycle_operations WHERE worker_id=?',(worker,))
            core.db.execute('UPDATE workers SET status=? WHERE id=?',(w['status'] if success else 'ERROR',worker))
            if not success:emit('CONTEXT_COMPACTION_FAILED',{'method':'NATIVE'})
