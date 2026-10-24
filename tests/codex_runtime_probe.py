"""Bounded real CLI capability probes in disposable repositories, subscription only.

Never import API keys, use billing APIs, or touch unrelated sessions/projects.
The installed login must independently report ChatGPT before running this script.
"""
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
    exe=Path(r"C:\Users\domin\AppData\Roaming\npm\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe")
    if not exe.is_file():
        raise RuntimeError("Verified native CLI path unavailable; do not guess replacement")
    run_id=time.strftime("%Y%m%dT%H%M%SZ",time.gmtime())+"-"+uuid.uuid4().hex[:8]
    out=ROOT/"evidence"/"codex-runtime"/run_id
    out.mkdir(parents=True)
    env=os.environ.copy()
    for key in ["OPENAI_API_KEY","CODEX_API_KEY","OPENAI_BASE_URL"]:
        env.pop(key,None)
    auth=subprocess.run([str(exe),"login","status"],env=env,capture_output=True,timeout=15)
    (out/"login-stdout.txt").write_bytes(auth.stdout)
    (out/"login-stderr.txt").write_bytes(auth.stderr)
    if auth.returncode or b"Logged in using ChatGPT" not in auth.stdout+auth.stderr:
        raise RuntimeError("ChatGPT authentication not confirmed; no execution launched")
    runs=[]
    processes=[]
    for label in ["A","B"]:
        repo=ROOT/"runtime"/"codex-probes"/run_id/label
        repo.mkdir(parents=True)
        subprocess.run(["git","init",str(repo)],capture_output=True,check=True)
        prompt=f"Authorized disposable scheduler capability probe {label}. Do not use tools, read files, make network requests or change files. Reply exactly SCHEDULER_PROBE_{label}."
        (out/f"{label}-prompt.txt").write_text(prompt,encoding="utf-8")
        stdout=(out/f"{label}-stdout.jsonl").open("wb")
        stderr=(out/f"{label}-stderr.txt").open("wb")
        argv=[str(exe),"--ask-for-approval","never","exec","--json","--ignore-user-config","--sandbox","read-only","--color","never","--cd",str(repo),"-"]
        started=time.time()
        process=subprocess.Popen(argv,env=env,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,cwd=repo)
        process.stdin.write(prompt.encode())
        process.stdin.close()
        processes.append((process,stdout,stderr,started))
        runs.append({"label":label,"argv":argv,"cwd":str(repo),"pid":process.pid,"started_epoch":started,"auth":"ChatGPT status verified; API key vars removed","model":"CLI default; observed metadata if available","cost":None})
    deadline=time.time()+120
    timed_out=False
    while any(p.poll() is None for p,*_ in processes):
        if time.time()>deadline:
            timed_out=True
            for p,*_ in processes:
                if p.poll() is None:
                    p.terminate()
            break
        time.sleep(.2)
    for run,(process,stdout,stderr,started) in zip(runs,processes):
        process.wait(timeout=10)
        stdout.close();stderr.close()
        run.update(exit_code=process.returncode,finished_epoch=time.time(),timed_out=timed_out,
                   prompt_sha256=hashlib.sha256((out/f"{run['label']}-prompt.txt").read_bytes()).hexdigest())
        raw=(out/f"{run['label']}-stdout.jsonl").read_bytes()
        try:
            parsed=parse_jsonl(raw)
            run.update(execution_id=parsed["execution_id"],usage=parsed["usage"],stream_completed=parsed["stream_completed"],stdout_sha256=parsed["stdout_sha256"])
            run["exact_response"]=any(e.get("type")=="item.completed" and e.get("item",{}).get("text")=="SCHEDULER_PROBE_"+run["label"] for e in parsed["events"])
        except ValueError as exc:
            run["parse_error"]=str(exc)
    passed=all(r.get("exit_code")==0 and r.get("stream_completed") and r.get("exact_response") for r in runs)
    report={"run_id":run_id,"passed":passed,"kind":"real installed CLI subscription-backed dummy probes",
            "runs":runs,"native_cli_sha256":hashlib.sha256(exe.read_bytes()).hexdigest(),
            "harness_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "limitations":["not scheduled generator acceptance","no writes or tool parity tested","stop/cancel not confirmed","dollars unavailable; no API key supplied"]}
    (out/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    (out/"manifest.json").write_text(json.dumps({str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},indent=2),encoding="utf-8")
    print(json.dumps({"directory":str(out),"passed":passed,"runs":runs},indent=2))
    return 0 if passed else 1


if __name__=="__main__":
    raise SystemExit(main())
