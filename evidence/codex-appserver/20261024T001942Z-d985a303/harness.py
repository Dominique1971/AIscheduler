"""Explicitly authorized, bounded real stdio probe against owned dummy CLI IDs.

Never enumerates threads, reads credentials, edits config or uses API key billing.
Not collected by pytest; run deliberately after reviewing the subscription gate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


class StdioClient:
    def __init__(self, argv, env, cwd, out, deadline):
        self.deadline = deadline
        self.next_id = 0
        self.messages = []
        self.incoming = queue.Queue()
        self.sent = (out / "outbound.jsonl").open("xb")
        self.raw = (out / "inbound.jsonl").open("xb")
        self.stderr = (out / "stderr.txt").open("xb")
        self.process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=self.stderr)
        self.reader = threading.Thread(target=self.read, daemon=True)
        self.reader.start()

    def read(self):
        for raw in iter(self.process.stdout.readline, b""):
            self.raw.write(raw)
            self.raw.flush()
            try:
                self.incoming.put(json.loads(raw))
            except Exception as error:
                self.incoming.put({"parse_error": str(error)})
        self.incoming.put({"eof": True})

    def send(self, value):
        raw = (json.dumps(value, ensure_ascii=False) + "\n").encode()
        self.sent.write(raw)
        self.sent.flush()
        self.process.stdin.write(raw)
        self.process.stdin.flush()

    def receive(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("120-second probe deadline reached")
        message = self.incoming.get(timeout=remaining)
        self.messages.append(message)
        if message.get("eof") or message.get("parse_error"):
            raise RuntimeError(message)
        # Never grant a server-initiated tool or approval request.
        if "method" in message and "id" in message:
            self.send({"id": message["id"], "error": {"code": -32601,
                       "message": "No tool or approval actions allowed by probe"}})
        return message

    def request(self, method, params):
        self.next_id += 1
        identity = self.next_id
        self.send({"id": identity, "method": method, "params": params})
        while True:
            message = self.receive()
            if message.get("id") == identity and "method" not in message:
                if "error" in message:
                    raise RuntimeError({"method": method, "error": message["error"]})
                return message["result"]

    def completed(self, thread, turn):
        def matches(message):
            params = message.get("params", {})
            return (message.get("method") == "turn/completed" and params.get("threadId") == thread
                    and params.get("turn", {}).get("id") == turn)
        for message in self.messages:
            if matches(message):
                return message["params"]["turn"]
        while True:
            message = self.receive()
            if matches(message):
                return message["params"]["turn"]

    def wait_started(self, thread, turn):
        while True:
            for message in self.messages:
                params = message.get("params", {})
                if (message.get("method") == "turn/started" and params.get("threadId") == thread
                        and params.get("turn", {}).get("id") == turn):
                    return
            self.receive()

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=5)
        self.reader.join(timeout=5)
        self.sent.close()
        self.raw.close()
        self.stderr.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args()
    source = args.source_report.resolve(strict=True)
    original = json.loads(source.read_text())
    manifest = json.loads((source.parent / "manifest.json").read_text())
    for relative, expected in manifest.items():
        if hashlib.sha256((source.parent / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Source CLI evidence integrity failed")
    if not original["passed"]:
        raise RuntimeError("Source CLI probes did not pass")
    owned = {run["label"]: run for run in original["runs"]}
    exe = Path(owned["B"]["argv"][0])
    if hashlib.sha256(exe.read_bytes()).hexdigest() != original["native_cli_sha256"]:
        raise RuntimeError("Native CLI changed since source probe")
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
    out = args.evidence or ROOT / "evidence" / "codex-appserver" / run_id
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if (out / "report.json").exists():
        raise RuntimeError("Refusing to overwrite probe evidence")
    (out / "harness.py").write_bytes(Path(__file__).read_bytes())
    env = os.environ.copy()
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL"):
        env.pop(key, None)
    auth = subprocess.run([str(exe), "login", "status"], env=env, capture_output=True, timeout=15)
    (out / "login-stdout.txt").write_bytes(auth.stdout)
    (out / "login-stderr.txt").write_bytes(auth.stderr)
    if auth.returncode or b"Logged in using ChatGPT" not in auth.stdout + auth.stderr:
        raise RuntimeError("ChatGPT authentication not confirmed; no app-server launched")
    cwd = owned["B"]["cwd"]
    argv = [str(exe), "app-server", "--listen", "stdio://", "-c", 'sandbox_mode="read-only"',
            "-c", 'approval_policy="never"']
    report = {"run_id": out.name, "kind": "real owned dummy app-server runtime capability probe",
              "source_report": str(source), "argv": argv, "cwd": cwd,
              "started_at_epoch": time.time(), "cost": None, "checks": {},
              "native_cli_sha256": original["native_cli_sha256"],
              "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    client = None
    try:
        client = StdioClient(argv, env, cwd, out, time.monotonic() + 120)
        report["pid"] = client.process.pid
        initialized = client.request("initialize", {"clientInfo": {
            "name": "scheduler_dummy_capability_probe", "version": "0.1.0"}})
        report["checks"]["initialize"] = initialized
        client.send({"method": "initialized", "params": {}})
        models = client.request("model/list", {"limit": 100, "includeHidden": False})
        report["checks"]["model_list_count"] = len(models["data"])
        canary = Path(cwd) / ("sandbox-canary-" + out.name + ".txt")
        if canary.exists():
            raise RuntimeError("Refusing to reuse canary output")
        try:
            result = client.request("command/exec", {"command": [sys.executable, "-c",
                "from pathlib import Path; Path(" + repr(str(canary)) + ").write_text('diagnostic-canary'); print('CANARY_WRITE_SUCCEEDED')"],
                "cwd": cwd, "timeoutMs": 10000,
                "sandboxPolicy": {"type": "readOnly", "networkAccess": False}})
            report["checks"]["sandbox_canary"] = {"response": result, "canary_exists": canary.exists(),
                "path": str(canary), "classification": "diagnostic fault injection; never adopted as deliverable"}
        except RuntimeError as error:
            report["checks"]["sandbox_canary"] = {"rpc_error": str(error), "canary_exists": canary.exists(),
                "path": str(canary), "classification": "diagnostic fault injection; enforcement unconfirmed on setup error"}
        selected = next((model for model in models["data"] if model.get("isDefault")), models["data"][0])
        efforts = [entry["reasoningEffort"] for entry in selected["supportedReasoningEfforts"]]
        effort = "low" if "low" in efforts else selected["defaultReasoningEffort"]
        report["selected_model"] = selected["model"]
        report["selected_effort"] = effort
        for label, run in owned.items():
            result = client.request("thread/read", {"threadId": run["execution_id"], "includeTurns": True})
            report["checks"]["read_" + label] = {
                "id_matches": result["thread"]["id"] == run["execution_id"],
                "status": result["thread"].get("status"),
                "turn_count": len(result["thread"].get("turns", []))}
        thread = owned["B"]["execution_id"]
        resumed = client.request("thread/resume", {"threadId": thread, "cwd": cwd,
            "approvalPolicy": "never", "sandbox": "read-only", "excludeTurns": True})
        report["checks"]["resume_id_matches"] = resumed["thread"]["id"] == thread
        turn_params = {"threadId": thread, "cwd": cwd, "approvalPolicy": "never",
                       "sandboxPolicy": {"type": "readOnly", "networkAccess": False},
                       "model": selected["model"], "effort": effort}
        if not args.control_only:
            started = client.request("turn/start", {**turn_params, "input": [{"type": "text",
                "text": "Authorized disposable follow-up. Do not use tools, read files, make network requests or modify files. Reply exactly APP_SERVER_RESUME_OK."}]})
            turn = started["turn"]["id"]
            finished = client.completed(thread, turn)
            report["checks"]["followup"] = {"turn_id": turn, "status": finished["status"],
                "exact_response": any(item.get("type") == "agentMessage" and item.get("text") == "APP_SERVER_RESUME_OK"
                                      for item in finished.get("items", []))}
        else:
            report["checks"]["followup"] = {"skipped": "control-only; prior exact followup remains separate evidence"}
            created = client.request("thread/start", {"cwd": cwd, "approvalPolicy": "never", "sandbox": "read-only",
                "model": selected["model"]})
            thread = created["thread"]["id"]
            turn_params["threadId"] = thread
            report["created_thread_id"] = thread
        started = client.request("turn/start", {**turn_params, "input": [{"type": "text",
            "text": "Authorized disposable interruption probe. Do not use tools, read files, access network or modify files. Count integers from 1 through 100, separated by spaces."}]})
        turn = started["turn"]["id"]
        client.wait_started(thread, turn)
        steered = client.request("turn/steer", {"threadId": thread, "expectedTurnId": turn,
             "input": [{"type": "text", "text": "Do not use tools. Reply only APP_SERVER_STEER_OK."}]})
        report["checks"]["steer"] = {"expected_turn_id": turn, "returned": steered}
        interrupted = client.request("turn/interrupt", {"threadId": thread, "turnId": turn})
        completed = client.completed(thread, turn)
        report["checks"]["interrupt"] = {"result": interrupted, "turn_id": turn, "status": completed["status"]}
        result = client.request("thread/read", {"threadId": thread, "includeTurns": True})
        report["checks"]["read_after_interrupt"] = {"status": result["thread"].get("status"),
            "latest_turn_status": result["thread"]["turns"][-1]["status"] if result["thread"].get("turns") else None}
        report["passed"] = ((args.control_only or (report["checks"]["followup"]["exact_response"] and finished["status"] == "completed"))
            and completed["status"] == "interrupted" and steered.get("turnId") == turn
            and all(report["checks"]["read_" + label]["id_matches"] for label in owned))
    except Exception as error:
        report["passed"] = False
        report["error"] = repr(error)
    finally:
        if client is not None:
            client.close()
            report["process_exit_code"] = client.process.returncode
            report["notification_count"] = len(client.messages)
        report["finished_at_epoch"] = time.time()
        report["limitations"] = ["not scheduler executor acceptance", "canary tests one write denial only; broad tool parity unrun",
            "no desktop UI parity", "no Dot connectivity test", "steer acceptance does not establish semantic adoption",
            "dollar cost unavailable; ChatGPT login gate passed; API key environment removed"]
        (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        files = {str(path.relative_to(out)): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in out.rglob("*") if path.is_file() and path.name != "manifest.json"}
        (out / "manifest.json").write_text(json.dumps(files, indent=2), encoding="utf-8")
    print(json.dumps({"evidence": str(out), **report}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
