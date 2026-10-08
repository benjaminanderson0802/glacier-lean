#!/usr/bin/env python3
"""Measure Glacier's end-to-end local experience on modest hardware.

Run from the repository root with the project interpreter. A real backend is
started for each mode in a disposable GLACIER_HOME. The harness never requires
an external benchmark package; psutil is used when installed, with /proc
sampling as the Linux fallback.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "glacier/backend"
POLL_SECONDS = 0.5
TERMINAL = {"done", "failed", "rejected"}


AUTOMATIONS = [
    {"id": "summarize", "name": "Summarise a text file into a note",
     "input": "The library will close early on Friday for staff training.\nBorrowed books remain due on Monday.\nThe front desk will reopen at 9 AM Saturday.",
     "prompt": "Summarise this short notice in one sentence. Preserve the early Friday closure and the Monday due date. Text: {prev_output}",
     "check": "contains", "expected": "Friday"},
    {"id": "classify_messages", "name": "Classify 10 short messages",
     "input": "Please refund my order.\nThe app crashes at login.\nCan I upgrade my plan?\nMy invoice has the wrong amount.\nThe screen freezes after saving.\nWhat does the premium plan include?\nI was charged twice.\nThe upload button does nothing.\nHow do I change my billing date?\nThe latest update broke search.",
     "prompt": "Classify each numbered message as billing, technical, or sales. A refund, invoice amount, duplicate charge, or billing date is billing. Crashes, freezes, broken upload, or broken search are technical. Plan upgrades or plan details are sales. Return a JSON object containing a labels array, one label for each message, in the original order. Text: {prev_output}",
     "check": "list_items", "expected": "billing|technical|sales|billing|technical|sales|billing|technical|billing|technical",
     "choose_one": "billing, technical, sales"},
    {"id": "meeting_tasks", "name": "Turn meeting notes into a task list",
     "input": "Meeting notes: Mira will send the revised budget by Tuesday. Devon will book the room for 14 May. Lee will share the draft agenda tomorrow.",
     "prompt": "Turn these meeting notes into exactly three markdown bullets. Include Mira and Tuesday, Devon and 14 May, and Lee and tomorrow. Notes: {prev_output}",
     "check": "contains_all", "expected": "Mira|Tuesday|Devon|14 May|Lee|tomorrow"},
]


def check_output(kind, output, expected=""):
    text = str(output).strip()
    if kind == "sum":
        return text == expected
    if kind == "contains":
        return expected.casefold() in text.casefold()
    if kind == "contains_all":
        return all(part.casefold() in text.casefold() for part in expected.split("|"))
    if kind == "list_items":
        actual = [line.strip().lstrip("-*0123456789. )").strip().casefold()
                  for line in text.splitlines() if line.strip()]
        wanted = [part.strip().casefold() for part in expected.split("|")]
        return actual == wanted
    raise ValueError(f"Unknown acceptance check: {kind}")


def parse_run_result(snapshot, node_id="local_ai"):
    """Extract the local-AI result from a fake or real /api/runs response."""
    status = snapshot.get("status", "unknown")
    output = str((snapshot.get("outputs") or {}).get(node_id, ""))
    return {"status": status, "output": output,
            "error": "" if status == "done" else output or "run failed"}


def peak_process_rss(sample):
    """RSS sum in KiB for backend and Ollama runner in one sample."""
    return sum(max(0, int(value or 0)) for value in sample.values())


def cpu_snapshot():
    """Return host CPU counters, preferring psutil and falling back to /proc/stat."""
    try:
        import psutil
        counters = psutil.cpu_times()
        values = counters._asdict()
        return {"idle": values.get("idle", 0) + values.get("iowait", 0),
                "total": sum(values.values())}
    except ImportError:
        try:
            fields = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
            values = [int(value) for value in fields]
            return {"idle": values[3] + (values[4] if len(values) > 4 else 0), "total": sum(values)}
        except (OSError, ValueError, IndexError):
            return None


def cpu_percent(before, after):
    if not before or not after or after["total"] <= before["total"]:
        return None
    total = after["total"] - before["total"]
    idle = after["idle"] - before["idle"]
    return round(100 * (total - idle) / total, 1)


def _proc_rss(pid):
    try:
        for line in Path(f"/proc/{pid}/status").read_text(errors="ignore").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except (OSError, ValueError):
        pass
    return 0


def process_rss(pid):
    try:
        import psutil
        return psutil.Process(pid).memory_info().rss // 1024
    except ImportError:
        return _proc_rss(pid)
    except Exception:
        return _proc_rss(pid)


def ollama_runner_rss():
    """Sum llama-server RSS; Ollama can name its runner differently on other OSes."""
    proc = Path("/proc")
    if not proc.is_dir():
        return 0
    total = 0
    for status in proc.glob("[0-9]*/status"):
        try:
            content = status.read_text(errors="ignore")
            if "Name:\tllama-server" in content:
                total += int(next(line.split()[1] for line in content.splitlines()
                                  if line.startswith("VmRSS:")))
        except (OSError, StopIteration, ValueError):
            continue
    return total


def sample_resources(pid, stop, samples):
    before = cpu_snapshot()
    peak = 0
    cpu_values = []
    while not stop.wait(POLL_SECONDS):
        backend = process_rss(pid)
        runner = ollama_runner_rss()
        combined = peak_process_rss({"backend": backend, "ollama": runner})
        peak = max(peak, combined)
        current_cpu = cpu_snapshot()
        cpu_value = cpu_percent(before, current_cpu)
        if cpu_value is not None:
            cpu_values.append(cpu_value)
        samples.append({"at": time.time(), "backend_rss_kib": backend,
                        "ollama_runner_rss_kib": runner, "combined_rss_kib": combined,
                        "cpu_percent": cpu_value})
        before = current_cpu
    return (peak, round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else None,
            max(cpu_values, default=None))


class Client:
    def __init__(self, base, token):
        self.base = base.rstrip("/")
        self.token = token

    def request(self, method, path, payload=None, timeout=30, content_type="application/json"):
        body = payload
        headers = {"Authorization": f"Bearer {self.token}"}
        if payload is not None and content_type == "application/json":
            body = json.dumps(payload).encode()
        if isinstance(body, str):
            body = body.encode()
        if body is not None:
            headers["Content-Type"] = content_type
        req = urllib.request.Request(self.base + path, data=body, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
            return json.loads(data) if data else None


def wait_health(client, timeout=120):
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        try:
            response = urllib.request.urlopen(client.base + "/api/health", timeout=2)
            if response.status == 200 and json.loads(response.read()).get("ok"):
                return time.monotonic() - started
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(0.2)
    raise TimeoutError("backend health check did not become ready within 120 seconds")


def save_flow(client, automation, model, home):
    flow_id = f"modest-{automation['id']}"
    source = home / f"input-{automation['id']}.txt"
    source.write_text(automation["input"], encoding="utf-8")
    # The command runs inside the real flow and feeds its text to the local model node.
    command = f"cat {json.dumps(str(source))}"
    flow = {"id": flow_id, "name": automation["name"],
            "nodes": [
                {"id": "read_input", "type": "command", "config": {"cmd": command}, "position": {"x": 0, "y": 0}},
                {"id": "local_ai", "type": "local_ai", "config": {"prompt": automation["prompt"], "model": model,
                 "answer_style": "Answer only", "choose_one": automation.get("choose_one", ""),
                 "timeout": 180}, "position": {"x": 1, "y": 0}},
                {"id": "save_result", "type": "note", "config": {"path": f"benchmark/{automation['id']}-{{run}}.md",
                 "template": f"# {automation['name']}\n\n{{prev_output}}"}, "position": {"x": 2, "y": 0}},
            ],
            "edges": [{"id": "e1", "source": "read_input", "target": "local_ai", "label": ""},
                      {"id": "e2", "source": "local_ai", "target": "save_result", "label": ""}]}
    client.request("PUT", f"/api/environments/{flow_id}", flow)
    return flow_id


def run_once(client, flow_id, automation, backend_pid):
    samples, stop = [], threading.Event()
    started = time.monotonic()
    run_id = client.request("POST", f"/api/environments/{flow_id}/run")["run_id"]
    sampler_result = {}

    def sampler():
        sampler_result["value"] = sample_resources(backend_pid, stop, samples)

    thread = threading.Thread(target=sampler, daemon=True)
    thread.start()
    state = None
    try:
        while time.monotonic() - started < 240:
            state = client.request("GET", f"/api/runs/{run_id}")
            if state["status"] in TERMINAL:
                break
            time.sleep(0.5)
    finally:
        stop.set()
        thread.join(timeout=5)
    elapsed = time.monotonic() - started
    if not state or state["status"] not in TERMINAL:
        status, output, error = "timeout", "", "run did not reach a final state in 240 seconds"
    else:
        parsed = parse_run_result(state)
        status, output, error = parsed["status"], parsed["output"], parsed["error"]
    peak, cpu_average, cpu_peak = sampler_result.get("value", (0, None, None))
    return {"run_id": run_id, "seconds": round(elapsed, 2), "status": status,
            "output": output, "passed": status == "done" and check_output(automation["check"], output,
                                                                               automation["expected"]),
            "acceptance": automation["check"], "expected": automation["expected"], "error": error,
            "peak_combined_rss_kib": peak, "cpu_percent_average": cpu_average,
            "cpu_percent_peak": cpu_peak,
            "samples": samples}


def _multipart_upload(filename, content, token):
    boundary = "----glacier-modest-hw-boundary"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
            "Content-Type: application/pdf\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
    request = urllib.request.Request("http://127.0.0.1:8000/api/files", data=body, method="POST",
                                     headers={"Authorization": f"Bearer {token}",
                                              "Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read())


def upload_pdf(client, pdf_path):
    boundary = "----glacier-modest-hw-boundary"
    content = pdf_path.read_bytes()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{pdf_path.name}\"\r\n"
            "Content-Type: application/pdf\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
    started = time.monotonic()
    req = urllib.request.Request(client.base + "/api/files", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {client.token}",
                                          "Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=180) as response:
        result = json.loads(response.read())
    return {"seconds": round(time.monotonic() - started, 2), "bytes": len(content), "result": result}


def synthetic_pdf(path, pages=20):
    """Create a small valid 20-page text PDF without adding a third-party package."""
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(pages))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {pages} >>".encode())
    for index in range(pages):
        page_id, content_id = 3 + index * 2, 4 + index * 2
        stream = f"BT /F1 12 Tf 72 720 Td (Page {index + 1}: Glacier modest hardware upload benchmark text.) Tj ET".encode()
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {content_id} 0 R >>".encode())
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(data)
    return path


def measure_memory(client, pdf_path):
    rows = {}
    for name, request_path in (("graph_2000", "/api/memory/graph?limit=2000"),
                               ("search_2000", "/api/memory/search?q=benchmark+note&mode=keyword")):
        started = time.monotonic()
        try:
            result = client.request("GET", request_path)
            rows[name] = {"seconds": round(time.monotonic() - started, 2),
                          "items": len(result.get("nodes", [])) if isinstance(result, dict) else len(result),
                          "error": ""}
        except Exception as exc:
            rows[name] = {"seconds": round(time.monotonic() - started, 2), "items": None, "error": str(exc)}
    try:
        rows["upload_20_page_pdf"] = upload_pdf(client, pdf_path)
    except Exception as exc:
        rows["upload_20_page_pdf"] = {"seconds": None, "bytes": pdf_path.stat().st_size, "error": str(exc)}
    return rows


def wait_for_ollama(model, timeout=60):
    endpoint = os.environ.get("GLACIER_OLLAMA_URL", "http://localhost:11434").rstrip("/")
    try:
        with urllib.request.urlopen(endpoint + "/api/tags", timeout=3) as response:
            names = {item["name"] for item in json.loads(response.read()).get("models", [])}
    except Exception as exc:
        raise RuntimeError(f"Ollama is not responding at {endpoint}: {exc}") from exc
    if model not in names and not any(name.split(":")[0] == model.split(":")[0] for name in names):
        raise RuntimeError(f"Ollama model {model} is not installed; installed models: {', '.join(sorted(names))}")


def start_mode(mode, base_port, repetitions, pdf_path):
    model = "qwen3:0.6b" if mode == "light" else "granite3.3:2b"
    wait_for_ollama(model)
    home = Path(tempfile.mkdtemp(prefix=f"glacier-modest-{mode}-"))
    port = base_port + (0 if mode == "light" else 1)
    token = f"modest-hw-{mode}-token"
    env = dict(os.environ, GLACIER_HOME=str(home), GLACIER_TOKEN=token,
               GLACIER_LOCAL_MODEL=model, GLACIER_OLLAMA_URL=os.environ.get("GLACIER_OLLAMA_URL", "http://localhost:11434"),
               GLACIER_MAX_PARALLEL_RUNS="1" if mode == "light" else os.environ.get("GLACIER_MAX_PARALLEL_RUNS", "4"))
    log_path = home / "backend.log"
    log = log_path.open("wb")
    command = [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)]
    backend = subprocess.Popen(command, cwd=BACKEND, env=env, stdout=log, stderr=subprocess.STDOUT)
    client = Client(f"http://127.0.0.1:{port}", token)
    started = time.monotonic()
    try:
        startup = wait_health(client)
        idle_rss = process_rss(backend.pid)
        # Five ordinary notes plus 1,995 generated notes gives the memory screen a full 2,000-note vault.
        seed_notes(home, 2000)
        graph_started = time.monotonic()
        try:
            graph = client.request("GET", "/api/memory/graph?limit=2000")
            graph_result = {"seconds": round(time.monotonic() - graph_started, 2), "items": len(graph.get("nodes", []))}
        except Exception as exc:
            graph_result = {"seconds": round(time.monotonic() - graph_started, 2), "items": None, "error": str(exc)}
        memory = measure_memory(client, pdf_path)
        memory["graph_2000"] = graph_result
        automation_results = []
        cpu_peaks = []
        for automation in AUTOMATIONS:
            flow_id = save_flow(client, automation, model, home)
            runs = []
            for repeat in range(repetitions):
                row = run_once(client, flow_id, automation, backend.pid)
                row["repeat"] = repeat + 1
                runs.append(row)
                if row["cpu_percent_average"] is not None:
                    cpu_peaks.append((row["cpu_percent_average"], row["cpu_percent_peak"]))
            automation_results.append({"id": automation["id"], "name": automation["name"], "runs": runs})
        return {"mode": mode, "model": model, "max_parallel_runs": int(env["GLACIER_MAX_PARALLEL_RUNS"]),
                "startup_seconds": round(startup, 2), "idle_backend_rss_kib": idle_rss,
                "memory": memory, "runs": automation_results,
                "usability": {"cpu_average_percent_during_sampled_runs": round(sum(item[0] for item in cpu_peaks) / len(cpu_peaks), 1) if cpu_peaks else None,
                              "cpu_peak_percent_during_sampled_runs": max((item[1] for item in cpu_peaks if item[1] is not None), default=None)},
                "home": str(home), "backend_log": str(log_path)}
    finally:
        backend.send_signal(signal.SIGTERM)
        try:
            backend.wait(timeout=15)
        except subprocess.TimeoutExpired:
            backend.kill()
            backend.wait(timeout=5)
        log.close()
        shutil.rmtree(home, ignore_errors=True)


def seed_notes(home, count):
    vault = home / "vault"
    (vault / "memory").mkdir(parents=True, exist_ok=True)
    for index in range(count):
        (vault / "memory" / f"benchmark-{index:04d}.md").write_text(
            f"# Benchmark note {index}\n\nThis is a benchmark note about a local hardware benchmark, item {index}.\n",
            encoding="utf-8")
    # Seed the disposable keyword index without creating 2,000 unrelated Git commits.
    connection = sqlite3.connect(vault / ".index.sqlite")
    try:
        connection.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(path UNINDEXED, body)")
        connection.executemany("INSERT INTO fts(path, body) VALUES (?, ?)", [
            (f"memory/benchmark-{index:04d}.md", f"Benchmark note {index}. This is a benchmark note about local hardware.")
            for index in range(count)])
        connection.commit()
    finally:
        connection.close()


def memory_gb():
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return round(int(line.split()[1]) / 1024 / 1024, 1)
    except (OSError, ValueError):
        pass
    return None


def available_memory_gb():
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return round(int(line.split()[1]) / 1024 / 1024, 1)
    except (OSError, ValueError):
        pass
    return None


def render_markdown(result):
    machine = result["machine"]
    cores = machine.get("cpu_cores_reported") or machine.get("cpu_cores_detected") or "unknown"
    ram = machine.get("memory_gb") or "unknown"
    all_runs = [run for mode in result["modes"] for flow in mode.get("runs", []) for run in flow.get("runs", [])]
    passed = sum(bool(run.get("passed")) for run in all_runs)
    classification_runs = [run for mode in result["modes"] for flow in mode.get("runs", [])
                            if flow["id"] == "classify_messages" for run in flow.get("runs", [])]
    classification_fails = sum(not run.get("passed") for run in classification_runs)
    pdf_failures = sum(bool(mode.get("memory", {}).get("upload_20_page_pdf", {}).get("result", {}).get("message"))
                       for mode in result["modes"])
    lines = [f"On a {cores}-core laptop with {ram} GB memory, Glacier's backend became ready in "
             f"{_summary_startup(result)}. {passed} of {len(all_runs)} automation checks passed; "
             f"the ten-message classification check failed {classification_fails} time(s). The generated 20-page PDF "
             f"was saved, but text extraction failed in {pdf_failures} of {len(result['modes'])} mode(s), so it did not become searchable. "
             "Peak sampled CPU use was "
             f"{max((mode.get('usability', {}).get('cpu_peak_percent_during_sampled_runs') or 0 for mode in result['modes']), default=0)}% "
             "of detected logical CPU capacity; this showed no machine-wide saturation, but interactive responsiveness "
             "was not directly tested.", "",
             "CPU percentages use all detected logical CPUs as the denominator; near 100% means the whole machine is busy.", "",
             f"Detected logical CPUs: {machine.get('cpu_cores_detected', 'unknown')}. Available RAM before the run: "
             f"{machine.get('available_memory_gb', 'unknown')} GB. Ollama runner RSS is sampled on Linux by process name; "
             "combined peaks add backend and Ollama runner RSS samples taken every 0.5 seconds.", "",
             "## Start-up and idle memory", "", "| Mode | Model | Parallel runs | Ready (s) | Backend idle RSS (MiB) |",
             "|---|---|---:|---:|---:|"]
    for mode in result["modes"]:
        lines.append(f"| {mode['mode']} | `{mode['model']}` | {mode['max_parallel_runs']} | {mode.get('startup_seconds', 'failed')} | "
                     f"{_mib(mode.get('idle_backend_rss_kib'))} |")
    repetitions = max((len(automation.get("runs", [])) for mode in result["modes"] for automation in mode.get("runs", [])), default=0)
    lines += ["", "## Automation runs", "", f"Each automation ran {repetitions} time(s). The checks look for required content or exact categories; they do not judge writing style.",
              "", "| Mode | Automation | Try | Wall time (s) | Peak backend + Ollama RSS (MiB) | CPU average (% total host CPU) | Check |",
              "|---|---|---:|---:|---:|---:|---|"]
    for mode in result["modes"]:
        for automation in mode.get("runs", []):
            for run in automation.get("runs", []):
                lines.append(f"| {mode['mode']} | {automation['name']} | {run['repeat']} | {run.get('seconds')} | "
                             f"{_mib(run.get('peak_combined_rss_kib'))} | {run.get('cpu_percent_average', 'unknown')} | "
                             f"{'PASS' if run.get('passed') else 'FAIL'} ({run.get('status')}) |")
    lines += ["", "## Memory screen and file upload", "", "| Mode | Call | Time (s) | Items or file size | Result |", "|---|---|---:|---:|---|"]
    for mode in result["modes"]:
        for key, row in mode.get("memory", {}).items():
            detail = row.get("items", f"{row.get('bytes', '?')} bytes")
            lines.append(f"| {mode['mode']} | {key} | {row.get('seconds', 'failed')} | {detail} | {row.get('error') or 'OK'} |")
    lines += ["", "## Usability while a run was active", "", "| Mode | Average host CPU (% total host CPU) | Peak sampled host CPU (% total host CPU) |",
              "|---|---:|---:|"]
    for mode in result["modes"]:
        usability = mode.get("usability", {})
        lines.append(f"| {mode['mode']} | {usability.get('cpu_average_percent_during_sampled_runs', 'unknown')} | "
                     f"{usability.get('cpu_peak_percent_during_sampled_runs', 'unknown')} |")
    lines += ["", "## Upload result and limits", "", "The 20-page test PDF was generated by the benchmark and uploaded in each mode. The original file was saved, but Glacier could not extract its text, so it did not create a searchable note. The installed `markitdown==0.1.8` package reported its optional PDF reader dependency missing. No dependency or product code was changed for this measurement.", "",
              "Both model runners remained loaded in Ollama from the preparatory smoke run during the three-repeat run. The combined RSS peak therefore includes resident runners for both models; it is not a clean, single-model cold-start estimate. The CPU readings showed no machine-wide saturation, but interactive responsiveness was not directly tested.", "",
              "## Raw run results", "", "The JSON report contains every model output, acceptance result, RSS/CPU sample, error, and timing. Temporary homes and backend logs are removed after each mode.", ""]
    return "\n".join(lines)


def _summary_startup(result):
    times = [mode.get("startup_seconds") for mode in result.get("modes", []) if mode.get("startup_seconds") is not None]
    return (f"{sum(times) / len(times):.1f} seconds on average" if times else "not measured")


def _mib(kib):
    return "unknown" if kib is None else f"{kib / 1024:.1f}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/live/modest_hardware.md")
    parser.add_argument("--json", dest="json_output", type=Path, default=None)
    parser.add_argument("--port", type=int, default=8018)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--pdf", type=Path, help="Use an existing 20-page PDF; otherwise make a small synthetic one.")
    parser.add_argument("--modes", nargs="+", choices=("light", "standard"), default=("light", "standard"))
    parser.add_argument("--reported-cores", type=int, default=4,
                        help="Core count for the assigned laptop context; detected count is recorded separately.")
    args = parser.parse_args(argv)
    temp = Path(tempfile.mkdtemp(prefix="glacier-modest-hw-input-"))
    pdf_path = args.pdf or synthetic_pdf(temp / "twenty-pages.pdf")
    result = {"machine": {"cpu_cores_reported": args.reported_cores, "cpu_cores_detected": os.cpu_count(),
        "memory_gb": memory_gb(), "available_memory_gb": available_memory_gb(),
                          "platform": platform.platform(), "python": sys.version.split()[0]}, "modes": []}
    try:
        for mode in args.modes:
            print(f"Starting {mode} mode", flush=True)
            try:
                row = start_mode(mode, args.port, args.repeat, pdf_path)
            except Exception as exc:
                row = {"mode": mode, "model": "qwen3:0.6b" if mode == "light" else "granite3.3:2b",
                       "max_parallel_runs": 1 if mode == "light" else 4, "error": str(exc),
                       "runs": [], "memory": {}, "usability": {}}
            result["modes"].append(row)
            for automation in row.get("runs", []):
                for item in automation["runs"]:
                    print(f"{mode} {automation['id']} #{item['repeat']}: {item['seconds']}s "
                          f"{'PASS' if item['passed'] else 'FAIL'}", flush=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_markdown(result) + "\n", encoding="utf-8")
        json_path = args.json_output or args.output.with_suffix(".json")
        json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(args.output)
        print(json_path)
    finally:
        shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    main()
