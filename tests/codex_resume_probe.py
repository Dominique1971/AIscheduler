"""Resume only a previously hash-verified scheduler-owned dummy execution."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scheduler.codex_adapter import parse_jsonl


def main():
    original=ROOT/"evidence/codex-runtime/20261024T001621Z-05ccade5"
    for name,expected in json.loads((original/"manifest.json").read_text()).items():
        if hashlib.sha256((original/name).read_bytes()).hexdigest()!=expected:
            raise RuntimeError("Original probe evidence changed; refusing resume")
    source=json.loads((original/"report.json").read_text())["runs"][0]
    run_id=time.strftime("%Y%m%dT%H%M%SZ",time.gmtime())+"-resume-"+uuid.uuid4().hex[:8]
    out=ROOT/"evidence/codex-runtime"/run_id
    out.mkdir(parents=True)
    exe=source["argv"][0]
    env=os.environ.copy()
    for key in ["OPENAI_API_KEY","CODEX_API_KEY","OPENAI_BASE_URL"]:
        env.pop(key,None)
    status=subprocess.run([exe,"login","status"],env=env,capture_output=True,timeout=15)
    (out/"login-stdout.txt").write_bytes(status.stdout)
    (out/"login-stderr.txt").write_bytes(status.stderr)
    if status.returncode or b"Logged in using ChatGPT" not in status.stdout+status.stderr:
        raise RuntimeError("ChatGPT login not confirmed")
    prompt="Authorized disposable scheduler resume probe. Without tools or file access, reply with the exact sentinel from your previous assistant message, and nothing else."
    (out/"prompt.txt").write_text(prompt)
    argv=[exe,"--ask-for-approval","never","exec","--json","--ignore-user-config","--sandbox","read-only","--cd",source["cwd"],"resume",source["execution_id"],"-"]
    started=time.time()
    process=subprocess.run(argv,env=env,input=prompt.encode(),capture_output=True,timeout=90,cwd=source["cwd"])
    (out/"stdout.jsonl").write_bytes(process.stdout)
    (out/"stderr.txt").write_bytes(process.stderr)
    parsed=parse_jsonl(process.stdout)
    exact=any(e.get("type")=="item.completed" and e.get("item",{}).get("text")=="SCHEDULER_PROBE_A" for e in parsed["events"])
    passed=process.returncode==0 and exact and parsed["stream_completed"] and parsed["execution_id"]==source["execution_id"]
    receipt={"run_id":run_id,"passed":passed,"argv":argv,"started_epoch":started,"finished_epoch":time.time(),
        "original_execution_id":source["execution_id"],"returned_execution_id":parsed["execution_id"],"usage":parsed["usage"],
        "stdout_sha256":hashlib.sha256(process.stdout).hexdigest(),"stderr_sha256":hashlib.sha256(process.stderr).hexdigest(),
        "harness_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"exit_code":process.returncode,
        "auth":"ChatGPT status confirmed; API key environment removed","cost":None,"exact_previous_response":exact,
        "limitations":["no artifact generation or filesystem enforcement tested","model metadata not exposed by exec JSONL","not scheduled-task acceptance"]}
    (out/"report.json").write_text(json.dumps(receipt,indent=2))
    (out/"manifest.json").write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},indent=2))
    print(json.dumps({"directory":str(out),**receipt},indent=2))
    return 0 if passed else 1


if __name__=="__main__":
    raise SystemExit(main())
