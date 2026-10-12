import json, os, pathlib, socket, subprocess, sys, tempfile, time
import httpx
ROOT=pathlib.Path('/home/glacier/w/workers/gf-E-PH9')
OUT=ROOT/'evidence/ph9'
PYTHON='/home/glacier/w/glacier-lean/.venv/bin/python'
home=pathlib.Path(tempfile.mkdtemp(prefix='glacier-e-ph9-'))
repo=home/'checkout'
subprocess.run(['git','clone','--quiet','--shared',str(ROOT),str(repo)],check=True)
(repo/'.venv').symlink_to('/home/glacier/w/glacier-lean/.venv')
(repo/'glacier/web/node_modules').symlink_to(ROOT/'glacier/web/node_modules')
with (repo/'.git/info/exclude').open('a') as f: f.write('\n.venv\nglacier/web/node_modules\n')
sock=socket.socket(); sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]; sock.close()
api=f'http://127.0.0.1:{port}'
env=dict(os.environ,GLACIER_HOME=str(home),GLACIER_PYTHON=PYTHON,GLACIER_API_URL=api)
log=(OUT/'maintenance-backend.log').open('w')
server=subprocess.Popen([PYTHON,'-m','uvicorn','app:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT/'glacier/backend',env=env,stdout=log,stderr=subprocess.STDOUT)
metadata={'home':str(home),'checkout':str(repo),'api':api,'backend_pid':server.pid,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()}
(OUT/'maintenance-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
try:
    for _ in range(600):
        if (home/'.engine-token').exists():
            token=(home/'.engine-token').read_text().strip()
            try:
                if httpx.get(api+'/api/health',headers={'Authorization':'Bearer '+token}).status_code==200: break
            except httpx.HTTPError: pass
        time.sleep(.2)
    else: raise RuntimeError('backend did not start')
    sys.path.insert(0,str(ROOT/'setup/selfbuild'))
    import run_card
    with httpx.Client(base_url=api,headers={'Authorization':'Bearer '+token},timeout=30) as client:
        run_card.install_maintenance(client,repo)
        r=client.post('/api/environments/self-maintenance/run'); r.raise_for_status()
        run_id=r.json()['run_id']; metadata['run_id']=run_id
        (OUT/'maintenance-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
        print('Started maintenance',run_id,api,flush=True)
        last=None
        deadline=time.monotonic()+7000
        while time.monotonic()<deadline:
            r=client.get('/api/runs/'+run_id); r.raise_for_status(); run=r.json()
            (OUT/'maintenance-run.json').write_text(json.dumps(run,indent=2)+'\n')
            state=(run['status'],str(run.get('node_states')))
            if state!=last: print(state,flush=True); last=state
            if run['status'] in ('done','failed','rejected'): break
            time.sleep(5)
        for p in (home/'vault/proposals').glob('maintenance-*.md') if (home/'vault/proposals').exists() else []:
            (OUT/p.name).write_bytes(p.read_bytes())
        for p in (home/'tool-scan').glob('*') if (home/'tool-scan').exists() else []:
            if p.is_file(): (OUT/('tool-scan-'+p.name)).write_bytes(p.read_bytes())
        health=repo/'setup/.health/health-report.json'
        if health.exists(): (OUT/'maintenance-health.json').write_bytes(health.read_bytes())
        (OUT/'maintenance-git-status.txt').write_text(subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True))
        print('Final',run['status'],'verified',run.get('verified'),flush=True)
finally:
    server.terminate()
    try: server.wait(timeout=10)
    except subprocess.TimeoutExpired: server.kill(); server.wait()
    log.close()
