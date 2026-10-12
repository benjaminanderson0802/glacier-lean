import json, os, sys, tempfile, shlex
from pathlib import Path
repo=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(repo/'glacier/backend/tests'))
sys.path.insert(0,str(repo/'glacier/backend'))
from conftest import Server, env
root=Path(tempfile.mkdtemp(prefix='cl-quality-live-'))
clip_home=root/'clips'
clip_home.mkdir()
(clip_home/'HOLD').touch()
config=clip_home/'config.json'
config.write_text(json.dumps({'live': True, 'channels':['@one']}))
engine_home=root/'engine'
engine_home.mkdir()
server=Server(engine_home).start()
try:
    command=shlex.join([sys.executable,'-m','scripts.distributor','--config',str(config),'--home',str(clip_home),'--live'])
    flow=env('cl-quality-smoke',[('distribute','command',{'cmd':command,'cwd':str(repo/'ventures/whop-clipping'),'timeout':'120'})],[])
    server.put('/api/environments/cl-quality-smoke',flow)
    run=server.post('/api/environments/cl-quality-smoke/run')['run_id']
    result=server.wait_run(run)
    assert result['status']=='done', result
    output=result['outputs']['distribute']
    assert '"held": true' in output and '"uploads": 0' in output, output
    print(json.dumps({'engine':'real uvicorn backend','run_id':run,'status':result['status'],'output':output,'home':str(root)},indent=2))
finally:
    server.stop()
