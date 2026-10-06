"""Bounded assistant plans over existing workers and Environment services."""
import json
from .canonical import CanonicalState,digest
from .environments import EnvironmentService

class SystemAssistant:
    def __init__(self,core):self.core=core;self.env=EnvironmentService(core)
    def bundle(self,slots,privacy='LOCAL_ONLY'):
        required=('planner','researcher','builder','reviewer')
        if set(slots)!=set(required):raise ValueError('Provide planner, researcher, builder and independent reviewer slots')
        if slots['builder']==slots['reviewer']:raise ValueError('Independent QA worker required')
        nodes=[{'id':'intake','kind':'TRANSFORM','config':{'value':{'status':'EXPLICIT_ASSIGNMENT_REQUIRED'}}}]
        edges=[];last='intake'
        for role in required:
            self.core.worker(slots[role])
            nodes.append({'id':role,'kind':'AI_TASK','worker':slots[role],'inputs':{'previous':'object'},
              'config':{'objective':{'planner':'Produce a bounded proposal only. Respect immutable user input.',
              'researcher':'Check the proposed approach using available authorized evidence. Report gaps.',
              'builder':'Prepare a candidate in your task workspace only. No production apply.',
              'reviewer':'Independently review supplied candidate evidence. Report missing evidence as FAIL. Never grant approval.'}[role]}})
            edges.append({'source':last,'target':role,'port':'previous'});last=role
        graph={'privacy':privacy,'nodes':nodes,'connections':edges,'max_nodes':10,'deadline_seconds':1200}
        self.env.validate(graph)
        return {'name':'System Assistant candidate','graph':graph,'slots':slots,'apply':'UNAVAILABLE until independent gates and explicit approval',
                'automatic_install':False,'hidden_reasoning':False}
    def plan(self,operation,slots,privacy='LOCAL_ONLY'):
        tiers={'EXPLAIN':0,'PERSONALIZE':1,'CONFIGURE':2,'AUTHORITY':3,'MODIFY_GLACIER':4}
        if operation not in tiers:raise ValueError('Unknown assistant operation')
        bundle=self.bundle(slots,privacy)
        return {'operation':operation,'tier':tiers[operation],'bundle':bundle,'graph_hash':digest(bundle['graph']),
                'canonical_revision':CanonicalState(self.core).snapshot()['revision'],
                'worker_revisions':{w:self.core.worker(w)['revision'] for w in set(slots.values())},
                'status':'PROPOSED','required_gates':['Guardian','checkpoint','independent candidate QA','exact explicit approval'] if tiers[operation]==4 else ['Guardian']+(['explicit approval'] if tiers[operation]>=3 else []),
                'authority_granted':False}
    def validate_plan(self,plan):
        current=self.plan(plan['operation'],plan['bundle']['slots'],plan['bundle']['graph']['privacy'])
        if current!=plan:raise ValueError('Stale or changed Assistant proposal')
        return current
    def show_plan(self,run_id=None):
        if not run_id:return {'environments':self.env.list(),'status':'Choose a published Environment or run','authority_granted':False}
        run=self.env.inspect(run_id);version=self.env.version(run['version_id'])
        return {'run_id':run_id,'state':run['state'],'version':version,'pins':run['pins'],'attempts':run['attempts'],
                'approvals':'Existing task approval records; no graph-level blanket authority','authority_granted':False}
    def show_sources(self,run_id=None):
        if not run_id:return {'models':self.core.models.list(),'harness_scope':'Glacier-owned runtime sessions only','hidden_reasoning_included':False}
        run=self.env.inspect(run_id);tasks=[a['task_id'] for a in run['attempts'] if a['task_id']]
        return {'run_id':run_id,'version_id':run['version_id'],'worker_pins':run['pins'],'tasks':tasks,
                'artifacts':[a for t in tasks for a in self.core.artifacts(t)],
                'tools':[dict(r) for t in tasks for r in self.core.db.execute('SELECT id,capability,status FROM tool_calls WHERE task_id=?',(t,))],
                'evidence_scope':'Persisted execution receipts only; no hidden reasoning or inferred sources','hidden_reasoning_included':False}
