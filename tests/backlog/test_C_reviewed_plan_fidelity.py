"""Independent PH5.2 check: approved edits must reach planning and remain visible."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest


REPO = Path(__file__).resolve().parents[2]
WEB = REPO / "glacier" / "web"
BACKEND = REPO / "glacier" / "backend"
PYTHON = Path.home() / "w" / "glacier-lean" / ".venv" / "bin" / "python"
EVIDENCE = REPO / "evidence" / "backlog2" / "C-PH5-PLAN-FIDELITY-TESTER"

REVIEWED_GOAL = "Reviewed goal sentinel: help orchard keepers track cold-storage lots."
REVIEWED_CHECK = "Reviewed check sentinel: a lot's cold-storage location remains visible after reload."
REVIEWED_REQUIREMENT = "The system shall retain a reviewed orchard lot location."
MODEL_CHECK = "MODEL-GENERATED CHECK SENTINEL: show a generic dashboard."


def _port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _wait(url: str, token: str | None = None, timeout: float = 120) -> None:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    deadline = time.monotonic() + timeout
    last = "no response"
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, headers=headers, timeout=1)
            if response.status_code < 500:
                return
            last = f"HTTP {response.status_code}: {response.text[:300]}"
        except httpx.HTTPError:
            last = "connection unavailable"
        time.sleep(.1)
    raise AssertionError(f"server did not become ready: {url} ({last})")


def _fake_planner(home: Path) -> Path:
    """Return a fake Codex CLI that records planner input and returns divergent checks."""
    executable = home / "fake-codex.py"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "a=sys.argv[1:]; out=a[a.index('-o')+1]; prompt=a[-1]\n"
        "open(os.environ['PLAN_PROMPT_LOG'],'w',encoding='utf-8').write(prompt)\n"
        "answer={\n"
        f"'spec':{{'requirements':['{REVIEWED_REQUIREMENT}'],'out_of_scope':[],'acceptance':['{MODEL_CHECK}']}},\n"
        "'features':[{'id':'lot-view','title':'Lot view','description':'Show lot details','acceptance':['Lot details load']}],\n"
        "'harness':{'startup_script':'start.sh','smoke_test':'smoke.sh','checks':[],'progress_log':'progress.md','decision_log':'decisions.md'},\n"
        "'team':{'worker_mode':'parallel','parallel_limit':3,'roles':[{'id':'builder','charter':'Build the lot view','supervisor':'lead','model':'default'},{'id':'evaluator','charter':'Check the lot view','supervisor':'lead','model':'default'},{'id':'lead','charter':'Coordinate work','supervisor':None,'model':'default'}],'supervisor':'lead','governor':'lead'},\n"
        "'tasks':[{'id':'build-lot','title':'Build lot view','role':'builder','description':'Implement lot view','depends_on':[],'acceptance':[{'kind':'command','cmd':'true','question':None,'rubric':None,'schema':None,'file':None,'engine':None,'model':None,'cwd':None,'required':True}],'requires_approval':True,'feature_id':'lot-view','contract':None},{'id':'evaluate-lot','title':'Evaluate lot view','role':'evaluator','description':'Check lot view','depends_on':['build-lot'],'acceptance':[{'kind':'command','cmd':'true','question':None,'rubric':None,'schema':None,'file':None,'engine':None,'model':None,'cwd':None,'required':True}],'requires_approval':False,'feature_id':'lot-view','contract':None}],\n"
        "'guards':{'max_retries':2,'task_timeout_seconds':30}}\n"
        "with open(out,'w',encoding='utf-8') as f: json.dump(answer,f)\n"
        "print(json.dumps({'type':'turn.completed'}))\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable


def test_real_backend_planner_receives_the_reviewed_vision_and_spec(tmp_path: Path):
    """Use the actual HTTP server and isolated home; the model deliberately proposes a different check."""
    assert PYTHON.exists(), f"project interpreter missing: {PYTHON}"
    home = tmp_path / "glacier-home"
    home.mkdir()
    prompt_log = home / "planner-prompt.txt"
    token = "reviewed-plan-test-token"
    api_port = _port()
    fake_cli = _fake_planner(home)
    env = {
        **os.environ,
        "GLACIER_HOME": str(home),
        "GLACIER_TOKEN": token,
        "CODEX_BIN": str(fake_cli),
        "GLACIER_CHAT_BIN": str(fake_cli),
        "PLAN_PROMPT_LOG": str(prompt_log),
        "GLACIER_OPENCODE_DATA": str(home / "no-opencode"),
        "GLACIER_CLAUDE_CODE_DATA": str(home / "no-claude"),
        "GLACIER_GEMINI_DATA": str(home / "no-gemini"),
        "GLACIER_OLLAMA_URL": "http://127.0.0.1:9",
    }
    backend_log = (home / "backend.log").open("w", encoding="utf-8")
    server = subprocess.Popen(
        [str(PYTHON), "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(api_port)],
        cwd=BACKEND, env=env, stdout=backend_log, stderr=subprocess.STDOUT, text=True,
    )
    api = f"http://127.0.0.1:{api_port}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        _wait(api + "/api/environments", token)
        reviewed_spec = {
            "requirements": [REVIEWED_REQUIREMENT],
            "acceptance": [REVIEWED_CHECK],
            "out_of_scope": ["No supplier accounts"],
        }
        reviewed_vision = {
            "goal": REVIEWED_GOAL,
            "done": [REVIEWED_CHECK],
            "requirements": [REVIEWED_REQUIREMENT],
            "out_of_scope": ["No supplier accounts"],
            "spec": reviewed_spec,
        }
        with httpx.Client(headers=headers, timeout=30) as client:
            approved = client.post(api + "/api/build/spec", json={"spec": reviewed_spec})
            assert approved.status_code == 200, approved.text
            saved = client.post(api + "/api/build/vision", json={"vision": reviewed_vision})
            assert saved.status_code == 200, saved.text
            path = saved.json()["path"]
            note = client.get(api + "/api/vault/note", params={"path": path})
            assert note.status_code == 200, note.text
            note_text = note.json()["body"]
            payload = note_text.split("```json\n", 1)[1].split("\n```", 1)[0]
            assert json.loads(payload) == reviewed_vision
            planned = client.post(api + "/api/build/plan", json={"vision_path": path, "engine": "codex"})
            assert planned.status_code == 200, planned.text
        plan = planned.json()["plan"]
        prompt = prompt_log.read_text(encoding="utf-8")
        assert REVIEWED_GOAL in prompt
        assert REVIEWED_CHECK in prompt
        assert REVIEWED_GOAL == plan["vision"]["goal"]
        assert plan["vision"]["spec"] == reviewed_spec
        # This divergent model check is intentionally present at the raw API boundary.
        # The screen must present the approved spec as authoritative after planning.
        assert plan["spec"]["acceptance"] == [MODEL_CHECK]
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        (EVIDENCE / "real-backend-api.json").write_text(json.dumps({
            "isolated_home": str(home), "vision_path": path,
            "reviewed_goal_seen_by_planner": REVIEWED_GOAL in prompt,
            "reviewed_check_seen_by_planner": REVIEWED_CHECK in prompt,
            "plan_vision_goal": plan["vision"]["goal"],
            "plan_vision_spec": plan["vision"]["spec"],
            "raw_model_acceptance": plan["spec"]["acceptance"],
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
        backend_log.close()


def test_mock_build_screen_displays_the_exact_reviewed_version_before_start(tmp_path: Path):
    """Exercise the shipped screen against its current mock and retain request/evidence logs."""
    node = shutil.which("node")
    assert node, "node is required for the existing Playwright UI harness"
    evidence_dir = EVIDENCE
    evidence_dir.mkdir(parents=True, exist_ok=True)
    playwright = subprocess.run(
        [node, "--input-type=module", "-e", "import('playwright')"],
        cwd=WEB, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if playwright.returncode:
        detail = "UI check unavailable: the shared web node_modules has no resolvable Playwright package.\n" + playwright.stdout
        (evidence_dir / "mock-ui.log").write_text(detail, encoding="utf-8")
        pytest.skip(detail)
    mock_port, ui_port = _port(), _port()
    script = r"""
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { chromium } from 'playwright'
const mockPort = Number(process.env.TEST_MOCK_PORT), uiPort = Number(process.env.TEST_UI_PORT)
const root = process.cwd(), procs = []
const start = (cmd, args, env = {}) => { const p=spawn(cmd,args,{cwd:root,env:{...process.env,...env},stdio:'ignore',detached:true}); procs.push(p); return p }
const cleanup = () => { for (const p of procs.reverse()) { try { process.kill(-p.pid,'SIGTERM') } catch {} } }
process.on('exit',cleanup)
async function wait(url) { for(let i=0;i<150;i++){try{if((await fetch(url)).status<500)return}catch{} await new Promise(r=>setTimeout(r,100))} throw Error('timeout '+url) }
const calls=[]
let browser
try {
  start('node',['mock/mock_server.mjs',String(mockPort)])
  await wait(`http://127.0.0.1:${mockPort}/api/teams`)
  start('npx',['vite','preview','--host','127.0.0.1','--port',String(uiPort),'--strictPort'],{GLACIER_API:`http://127.0.0.1:${mockPort}`})
  await wait(`http://127.0.0.1:${uiPort}/`)
  const exe=process.env.CHROMIUM_PATH || (existsSync('/opt/pw-browsers/chromium')?'/opt/pw-browsers/chromium':undefined)
  browser=await chromium.launch(exe?{executablePath:exe}:{})
  const page=await browser.newPage({viewport:{width:1280,height:800}})
  page.on('request', async req=>{if(req.url().includes('/api/build/')) calls.push({url:new URL(req.url()).pathname,body:req.postDataJSON?.() ?? null})})
  await page.goto(`http://127.0.0.1:${uiPort}/#/build`,{waitUntil:'networkidle'})
  if(await page.getByTestId('splash').count()) await page.keyboard.press('Enter')
  await page.getByTestId('build-interview').waitFor()
  await page.getByTestId('build-message').fill('Build an orchard lot tracker for small cold-storage operators. It must preserve reviewed lot locations.')
  await page.getByTestId('build-send').click()
  await page.getByText(/Who will use it/).waitFor()
  await page.getByTestId('build-understood').getByRole('button',{name:'Review spec'}).click()
  const spec=page.getByTestId('build-spec'); await spec.waitFor()
  const labels=spec.locator('label')
  await labels.filter({hasText:'project vision'}).locator('textarea').fill(process.env.REVIEWED_GOAL)
  await labels.filter({hasText:'requirements (EARS lines)'}).locator('textarea').fill(process.env.REVIEWED_REQUIREMENT)
  await labels.filter({hasText:'acceptance checks'}).locator('textarea').fill(process.env.REVIEWED_CHECK)
  await labels.filter({hasText:'out of scope'}).locator('textarea').fill('No supplier accounts')
  await spec.getByRole('button',{name:'keep talking'}).click()
  await page.getByTestId('build-interview').waitFor()
  await page.locator('.bt-step-panel .g-menu-item').filter({hasText:'approve spec'}).click()
  await page.getByTestId('build-spec').waitFor()
  if(await page.getByTestId('build-spec').locator('label').filter({hasText:'acceptance checks'}).locator('textarea').inputValue()!==process.env.REVIEWED_CHECK) throw Error('returning to the interview discarded the edited spec')
  const reviewedSpec=page.getByTestId('build-spec')
  await reviewedSpec.getByRole('button',{name:'approve spec'}).click()
  const proposed=page.getByTestId('build-plan'); await proposed.waitFor()
  const callOrder=calls.map(c=>c.url)
  const specCall=calls.find(c=>c.url==='/api/build/spec')
  const visionCall=calls.find(c=>c.url==='/api/build/vision')
  const planCall=calls.find(c=>c.url==='/api/build/plan')
  const planText=await proposed.innerText()
  console.log(JSON.stringify({callOrder,specBody:specCall?.body,visionBody:visionCall?.body,planBody:planCall?.body,planText},null,2))
  if(callOrder.join('|')!=='/api/build/interview|/api/build/draft-spec|/api/build/spec|/api/build/vision|/api/build/plan') throw Error('approval did not save the edited spec and vision before planning')
  if(specCall?.body?.spec?.acceptance?.[0]!==process.env.REVIEWED_CHECK) throw Error('approved checks differ from reviewed check')
  if(visionCall?.body?.vision?.goal!==process.env.REVIEWED_GOAL || visionCall?.body?.vision?.spec?.acceptance?.[0]!==process.env.REVIEWED_CHECK) throw Error('saved vision differs from reviewed goal/spec')
  if(!planText.includes(process.env.REVIEWED_GOAL) || !planText.includes(process.env.REVIEWED_CHECK)) throw Error('proposed plan does not visibly show the exact reviewed goal and acceptance check before start')
  if(planText.includes(process.env.MODEL_CHECK)) throw Error('proposed plan exposed a model-generated replacement check')
  await proposed.getByRole('button',{name:'edit with feedback'}).click()
  await page.getByTestId('build-interview').waitFor()
  if(!await page.getByTestId('build-message').inputValue().includes('please revise the plan')) throw Error('plan edit-feedback path is unavailable')
  console.log('[reviewed-plan-fidelity] PASS mock UI exact reviewed version, order, and edit path')
} finally { await browser?.close(); cleanup() }
"""
    env = {
        **os.environ,
        "TEST_MOCK_PORT": str(mock_port),
        "TEST_UI_PORT": str(ui_port),
        "REVIEWED_GOAL": REVIEWED_GOAL,
        "REVIEWED_CHECK": REVIEWED_CHECK,
        "REVIEWED_REQUIREMENT": REVIEWED_REQUIREMENT,
        "MODEL_CHECK": MODEL_CHECK,
    }
    result = subprocess.run(
        [node, "--input-type=module", "-e", script], cwd=WEB, env=env,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120,
    )
    (evidence_dir / "mock-ui.log").write_text(result.stdout, encoding="utf-8")
    assert result.returncode == 0, result.stdout
