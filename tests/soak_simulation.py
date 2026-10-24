"""Bounded standalone soak controller using only normal scheduler CLI operations.

Default: 24 hours, one 12-task dummy batch/hour, synthetic failure and restart.
This tests idle and burst operation, not sustained maximum inference throughput.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=24)
    parser.add_argument("--period-seconds", type=float, default=3600)
    parser.add_argument("--task-duration", type=float, default=5)
    args = parser.parse_args()
    if not 0 < args.hours <= 24 or args.period_seconds < 2 or not 0 <= args.task_duration <= 60:
        parser.error("hours must be 0..24, period>=2s, duration 0..60s")
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())+"-"+uuid.uuid4().hex[:8]
    out = ROOT/"evidence"/"soak"/run_id
    out.mkdir(parents=True)
    db = out/"scheduler.db"
    started = time.time()
    deadline = started+args.hours*3600
    counter = 0
    batches = 0
    daemon = None
    handles = []
    hashes = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (ROOT/"scheduler").rglob("*") if p.is_file() and "__pycache__" not in p.parts}

    def event(kind, **data):
        with (out/"journal.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"kind":kind,"at":time.time(),**data})+"\n")

    def command(*argv):
        nonlocal counter
        counter += 1
        cmd = [sys.executable,"-m","scheduler","--db",str(db),*argv]
        result = subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=30)
        prefix = out/f"{counter:04}"
        prefix.with_suffix(".stdout").write_bytes(result.stdout)
        prefix.with_suffix(".stderr").write_bytes(result.stderr)
        event("cli",argv=cmd,exit_code=result.returncode,stdout_sha256=hashlib.sha256(result.stdout).hexdigest())
        if result.returncode:
            raise RuntimeError(f"CLI failed: {argv}; see {prefix}")
        return json.loads(result.stdout)

    def launch():
        nonlocal daemon
        a=(out/f"daemon-{batches:03}.stdout").open("wb")
        b=(out/f"daemon-{batches:03}.stderr").open("wb")
        handles.extend([a,b])
        daemon=subprocess.Popen([sys.executable,"-m","scheduler","--db",str(db),"daemon","--interval",".25",
            "--run-seconds",str(max(1,deadline-time.time()))],cwd=ROOT,stdout=a,stderr=b)
        event("daemon.started",pid=daemon.pid)

    (out/"launch.json").write_text(json.dumps({"run_id":run_id,"pid":os.getpid(),"entry_point":sys.argv,
        "started_at_epoch":started,"deadline_epoch":deadline,"source_sha256":hashes,"configuration":vars(args),
        "executor":"simulation-only","model":None,"cost":0,"acceptance":"RUNNING; not passed",
        "host_reboot":"UNRUN","load":"hourly bursts with idle monitoring; no inference"},indent=2),encoding="utf-8")
    print(json.dumps({"run_id":run_id,"directory":str(out),"pid":os.getpid(),"deadline_epoch":deadline}),flush=True)
    passed = False
    error = None
    try:
        next_batch = started
        launch()
        while time.time() < deadline:
            if daemon.poll() is not None:
                if time.time() >= deadline-1:
                    break
                raise RuntimeError("daemon exited before deadline")
            if time.time() < next_batch:
                event("heartbeat",daemon_pid=daemon.pid,batches=batches)
                time.sleep(min(30,max(.1,min(next_batch,deadline)-time.time())))
                continue
            if batches and batches%4 == 0:
                daemon.kill()
                daemon.wait(timeout=10)
                event("daemon.forced_restart",pid=daemon.pid,exit_code=daemon.returncode)
                time.sleep(3.2)
                launch()
            project_ids=[]
            for filename in ["demo-weather.yaml","demo-inventory.yaml"]:
                plan=yaml.safe_load((ROOT/"examples"/filename).read_text())
                plan["project_id"] += f"-soak-{batches:03}"
                project_ids.append(plan["project_id"])
                for task in plan["tasks"]:
                    task["simulation"]["duration_seconds"]=args.task_duration
                    task["timeout_policy"]["execution_seconds"]=max(10,args.task_duration*3)
                path=out/f"batch-{batches:03}-{filename}"
                path.write_text(yaml.safe_dump(plan,sort_keys=False),encoding="utf-8")
                command("import",str(path))
            end=min(deadline,time.time()+max(60,args.task_duration*20))
            while True:
                snapshot=command("snapshot")
                tasks=[t for p in snapshot["projects"] if p["project_id"] in project_ids for t in p["tasks"]]
                if len(tasks)==12 and all(t["state"]=="completed" for t in tasks):
                    break
                if time.time()>=end:
                    raise RuntimeError("dummy batch unfinished before its bound")
                time.sleep(min(5,max(.1,args.task_duration)))
            for pid in project_ids:
                trace=command("trace",pid,"transform")
                if len(trace["attempts"])!=2 or [a["state"] for a in trace["attempts"]] != ["failed","completed"]:
                    raise RuntimeError("bounded recovery did not match configured synthetic failure")
            event("batch.completed",batch=batches,projects=project_ids)
            batches+=1
            next_batch=started+batches*args.period_seconds
        passed=True
    except BaseException as exc:
        error=repr(exc)
        event("failed",error=error)
    finally:
        if daemon and daemon.poll() is None:
            daemon.terminate()
            daemon.wait(timeout=10)
        for stream in handles:
            stream.close()
        unchanged=all((ROOT/path).exists() and hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected for path,expected in hashes.items())
        passed=passed and unchanged and time.time()-started >= args.hours*3600-.5
        report={"run_id":run_id,"passed":passed,"requested_hours":args.hours,"elapsed_seconds":time.time()-started,
            "batches_completed":batches,"error":error,"source_unchanged":unchanged,"cost":0,"model":None,
            "soak_24h_passed":bool(passed and args.hours==24),"host_reboot":"UNRUN","real_Codex":"UNRUN"}
        (out/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        manifest={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob("*") if p.is_file()}
        (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        print(json.dumps(report),flush=True)
    return 0 if passed else 1


if __name__=="__main__":
    raise SystemExit(main())
