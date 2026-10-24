"""Real local Worker/D1 -> outbound bridge -> normal scheduler API diagnostics.

Supabase Auth is an explicitly fake provider fixture. This is NOT hosted MFA or
fresh real-generator acceptance. All process inputs/outputs are preserved.
"""
from __future__ import annotations
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[2]
OWNER="a1234567-1234-4234-8234-123456789012"
FACTOR="f1234567-1234-4234-8234-123456789012"
CHALLENGE="c1234567-1234-4234-8234-123456789012"

def main():
    run_id=time.strftime("%Y%m%dT%H%M%SZ",time.gmtime())+"-"+uuid.uuid4().hex[:8]
    out=ROOT/"evidence/remote-local"/run_id;out.mkdir(parents=True)
    state=ROOT/"runtime/remote-local"/run_id;state.mkdir(parents=True)
    def port():
        with socket.socket() as s:s.bind(("127.0.0.1",0));return s.getsockname()[1]
    api_port,web_port,auth_port=port(),port(),port()
    origin=f"http://127.0.0.1:{web_port}";local=f"http://127.0.0.1:{api_port}"
    agent_token=secrets.token_hex(32);control_token=secrets.token_hex(32)
    env=os.environ.copy();env.update(SCHEDULER_CONTROL_TOKEN=control_token,SCHEDULER_REMOTE_AGENT_TOKEN=agent_token,WRANGLER_SEND_METRICS="false")
    env.pop("SCHEDULER_TOKEN_EXPIRES_AT",None);env.pop("SCHEDULER_READ_TOKEN",None)
    processes=[];streams=[];counter=0;checks={};error=None
    def write(name,raw):
        (out/name).write_bytes(raw)
    def cli(name,argv,cwd=ROOT):
        r=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,timeout=45)
        write(name+".stdout",r.stdout);write(name+".stderr",r.stderr)
        write(name+".receipt.json",json.dumps({"argv":argv,"exit_code":r.returncode}).encode())
        if r.returncode:raise RuntimeError(name+" failed; see raw stderr")
        return r
    def launch(name,argv,cwd=ROOT):
        a=(out/(name+".stdout")).open("wb");b=(out/(name+".stderr")).open("wb");streams.extend([a,b])
        p=subprocess.Popen(argv,cwd=cwd,env=env,stdout=a,stderr=b);processes.append(p)
        write(name+".receipt.json",json.dumps({"argv":argv,"pid":p.pid}).encode());return p
    def http(base,path,body=None,headers=None,expected=200):
        nonlocal counter
        counter+=1;h={"Content-Type":"application/json",**(headers or {})}
        req=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers=h)
        try:r=urllib.request.urlopen(req,timeout=5)
        except urllib.error.HTTPError as exc:r=exc
        with r:
            raw=r.read();status=r.status;cookie=r.headers.get("set-cookie")
            write(f"{counter:03}-http.body",raw)
            write(f"{counter:03}-http.receipt.json",json.dumps({"path":path,"status":status,"body":body,"response_sha256":hashlib.sha256(raw).hexdigest()}).encode())
        if status!=expected:raise RuntimeError(f"{path} expected {expected}, actual {status}: {raw[:100]!r}")
        return json.loads(raw),cookie
    def wait(action,condition,seconds=35):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            try:
                value=action()
                if condition(value):return value
            except (OSError,urllib.error.URLError,RuntimeError):pass
            time.sleep(.3)
        raise RuntimeError("local pipeline readiness/condition timeout")
    class AuthFixture(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_GET(self):self.reply()
        def do_POST(self):self.rfile.read(int(self.headers.get("content-length",0)));self.reply()
        def reply(self):
            path=self.path
            claims={"sub":OWNER,"aal":"aal2" if path.endswith("verify") else "aal1","exp":int(time.time())+3600}
            jwt="fixture."+base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")+".not-real"
            if path.startswith("/auth/v1/token"):value={"access_token":jwt}
            elif path=="/auth/v1/user":value={"id":OWNER,"is_anonymous":False,"email_confirmed_at":"2026-01-01T00:00:00Z","factors":[{"id":FACTOR,"status":"verified","factor_type":"totp"}]}
            elif path.endswith("challenge"):value={"id":CHALLENGE}
            elif path.endswith("verify"):value={"access_token":jwt}
            else:self.send_error(404);return
            raw=json.dumps(value).encode();self.send_response(200);self.send_header("content-type","application/json");self.send_header("content-length",str(len(raw)));self.end_headers();self.wfile.write(raw)
    fixture=ThreadingHTTPServer(("127.0.0.1",auth_port),AuthFixture);threading.Thread(target=fixture.serve_forever,daemon=True).start()
    passed=False
    try:
        config=json.loads((ROOT/"remote/wrangler.jsonc").read_text())
        config["main"]=str(ROOT/"remote/worker.mjs");config["assets"]["directory"]=str(ROOT/"remote/public")
        config["vars"].update(APP_ORIGIN=origin,SUPABASE_URL=f"http://127.0.0.1:{auth_port}",SUPABASE_PUBLISHABLE_KEY="sb_publishable_local_fixture_only",OWNER_ID=OWNER,AGENT_TOKEN=agent_token,DEV_MODE="local-only",REMOTE_CONTROL_ENABLED="true")
        config_path=state/"local-config.json";config_path.write_text(json.dumps(config,indent=2))
        wrangler=str(ROOT/"remote/node_modules/wrangler/bin/wrangler.js")
        shared=["--config",str(config_path),"--persist-to",str(state/"d1")]
        cli("d1-schema",["node",wrangler,"d1","execute","SCHEDULER_REMOTE","--local","--file",str(ROOT/"remote/schema.sql"),*shared],ROOT/"remote")
        db=state/"scheduler.db"
        for i,name in enumerate(["demo-weather.yaml","demo-inventory.yaml"]):cli(f"import-{i}",[sys.executable,"-m","scheduler","--db",str(db),"import",str(ROOT/"examples"/name)])
        launch("api",[sys.executable,"-m","scheduler","--db",str(db),"serve","--port",str(api_port)])
        launch("daemon",[sys.executable,"-m","scheduler","--db",str(db),"daemon","--run-seconds","180"])
        launch("worker",["node",wrangler,"dev","--local","--ip","127.0.0.1","--port",str(web_port),*shared],ROOT/"remote")
        local_headers={"Authorization":"Bearer "+control_token}
        wait(lambda:http(local,"/api/v1/snapshot",headers=local_headers)[0],lambda x:x["daemon"]["healthy"])
        wait(lambda:http(origin,"/api/snapshot",expected=401)[0],lambda x:x["error"]=="sign_in_required")
        auth,cookie=http(origin,"/auth/login",{"email":"fixture@example.invalid","password":"SYNTHETIC_NOT_REAL_PASSWORD","code":"123456"},headers={"Origin":origin})
        headers={"Cookie":cookie.split(";")[0],"Origin":origin,"X-CSRF-Token":auth["csrf"]}
        checks["mock_provider_mfa_login"]=True
        launch("bridge",[sys.executable,"remote/bridge.py","--origin",origin,"--local-api",local,"--local-development","--interval","1","--run-seconds","120","--journal",str(out/"bridge-journal.jsonl")])
        wait(lambda:http(origin,"/api/snapshot",headers=headers)[0],lambda x:x["agent_online"] and len(x["snapshot"]["projects"])==2)
        checks["outbound_projected_status"]=True
        for n,(action,extra) in enumerate([("pause",{}),("allocate",{"value":2}),("resume",{})]):
            key=f"local-command-{run_id}-{n}"
            payload={"action":action,"project":"demo-weather",**extra}
            http(origin,"/api/control",payload,headers={**headers,"Idempotency-Key":key},expected=202)
            result=wait(lambda:http(origin,"/api/commands",headers=headers)[0],lambda x:any(c["id"]==key and c["state"]=="succeeded" for c in x["items"]))
            native,_=http(local,"/api/v1/snapshot",headers=local_headers)
            p=next(p for p in native["projects"] if p["project_id"]=="demo-weather")
            if action=="pause":assert p["paused"]
            if action=="resume":assert not p["paused"]
            if action=="allocate":assert p["max_workers"]==2
            checks["normal_control_"+action]=True
        http(origin,"/api/control",{"action":"shell","command":"dir"},headers={**headers,"Idempotency-Key":"invalid-command-0000000"},expected=422)
        http(origin,"/auth/logout",{},headers=headers)
        http(origin,"/api/snapshot",headers=headers,expected=401)
        checks["logout_revoked_and_shell_rejected"]=True
        passed=True
    except BaseException as exc:error=repr(exc)
    finally:
        for p in reversed(processes):
            if p.poll() is None:
                if os.name=="nt":subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True,timeout=10)
                else:p.terminate();p.wait(timeout=10)
        for stream in streams:stream.close()
        fixture.shutdown();fixture.server_close()
        code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/"remote/worker.mjs",ROOT/"remote/contract.mjs",ROOT/"remote/bridge.py",Path(__file__)]}
        report={"run_id":run_id,"passed":passed,"error":error,"checks":checks,"source_sha256":code,"kind":"local pipeline diagnostics with mocked Auth provider, real Worker/D1/bridge/API/daemon","hosted_mfa":"UNRUN","cellular":"UNRUN","cloud_resources_created":False,"cost":0,"real_projects_connected":False}
        write("report.json",json.dumps(report,indent=2).encode())
        manifest={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob("*") if p.is_file()}
        write("manifest.json",json.dumps(manifest,indent=2).encode())
    print(json.dumps({"directory":str(out),**report},indent=2));return 0 if passed else 1

if __name__=="__main__":raise SystemExit(main())
