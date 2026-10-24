"""Outbound-only bridge to the normal loopback API. No shell or repository access.

Run separately from dispatcher/API: python remote/bridge.py --origin HTTPS_ORIGIN
The bridge does not infer, repair output, bypass auth or start an executor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_):
        return None


def project_snapshot(source):
    """Versioned allowlist, preserving source timestamps and local raw-output hash."""
    return {"schema_version": "remote-snapshot/2", "updated_at": source["updated_at"],
            "max_workers": source["max_workers"], "workers": source["workers"], "stopped": source["stopped"],
            "daemon": {"healthy": source["daemon"]["healthy"]}, "projects": [
                {"project_id": p["project_id"], "display_name": p["display_name"], "goal": p.get("goal", "")[:500], "paused": p["paused"], "max_workers": p["max_workers"],
                 "tasks": [{**{k: t[k] for k in ("task_id", "title", "state", "depends_on", "estimate_minutes", "started_at", "ended_at", "attempt_count")},
                            "description": t.get("description", "")[:500], "acceptance_criteria": [str(c)[:300] for c in t.get("acceptance_criteria", [])[:8]]}
                           for t in p["tasks"]]} for p in source["projects"]]}


def control_route(payload):
    """Validate the typed contract again at the local boundary; never accept URLs."""
    if not isinstance(payload, dict) or payload.keys() - {"action", "project", "task", "value", "confirmed"}:
        raise ValueError("invalid control")
    action = payload.get("action")
    if action in {"emergency-stop", "start"}:
        if payload.keys() - {"action", "confirmed"} or (action == "emergency-stop" and payload.get("confirmed") is not True):
            raise ValueError("confirmation required")
        return "/api/v1/system/"+action, {"confirmed": True} if action == "emergency-stop" else {}
    if action not in {"pause", "resume", "allocate", "hold", "unhold", "retry"}:
        raise ValueError("unsupported action")
    import re
    for key in ["project"] + (["task"] if action in {"hold", "unhold", "retry"} else []):
        if not isinstance(payload.get(key), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", payload[key]):
            raise ValueError("invalid identity")
    path = "/api/v1/projects/"+urllib.parse.quote(payload["project"], safe="")
    if action in {"hold", "unhold", "retry"}:
        path += "/tasks/"+urllib.parse.quote(payload["task"], safe="")
    if action == "allocate" and (type(payload.get("value")) is not int or not 0 <= payload["value"] <= 128):
        raise ValueError("invalid allocation")
    allowed = {"action", "project"} | ({"value"} if action == "allocate" else {"task"} if action in {"hold", "unhold", "retry"} else set())
    if payload.keys() - allowed:
        raise ValueError("unexpected control fields")
    return path+"/"+action, {"max_workers": payload["value"]} if action == "allocate" else {}


def request(url, secret, payload=None, key=None, site_access=None):
    headers = {"Authorization": "Bearer "+secret, "Content-Type": "application/json"}
    if site_access:
        headers["OAI-Sites-Authorization"] = "Bearer "+site_access
    if key:
        headers["Idempotency-Key"] = key
    req = urllib.request.Request(url, data=None if payload is None else json.dumps(payload).encode(), headers=headers)
    opener = urllib.request.build_opener(NoRedirect)
    try:
        response = opener.open(req, timeout=10)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        raw = response.read(1048577)
        if len(raw) > 1048576:
            raise ValueError("oversized response")
        return response.status, raw, json.loads(raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", required=True)
    parser.add_argument("--local-api", default="http://127.0.0.1:8765")
    parser.add_argument("--interval", type=float, default=5)
    parser.add_argument("--journal", default="runtime/remote-bridge/journal.jsonl")
    parser.add_argument("--run-seconds", type=float, default=0)
    parser.add_argument("--local-development", action="store_true")
    parser.add_argument("--site", action="store_true", help="use owner-private OpenAI Sites service access")
    args = parser.parse_args()
    cloud = urllib.parse.urlsplit(args.origin)
    local = urllib.parse.urlsplit(args.local_api)
    if cloud.username or cloud.password or cloud.query or cloud.fragment or cloud.path not in {"", "/"}:
        parser.error("origin must be a bare HTTPS origin")
    if cloud.scheme != "https" and not (args.local_development and cloud.scheme == "http" and cloud.hostname == "127.0.0.1"):
        parser.error("HTTPS required outside explicit loopback development")
    if local.scheme != "http" or local.hostname != "127.0.0.1" or local.username or local.password or local.path or local.query or local.fragment:
        parser.error("local API must be an exact http://127.0.0.1:PORT origin")
    if not 1 <= args.interval <= 30 or args.run_seconds < 0:
        parser.error("interval must be 1..30s; run duration must be nonnegative")
    cloud_key = os.environ.get("SCHEDULER_REMOTE_AGENT_TOKEN", "")
    site_access = os.environ.get("SCHEDULER_SITE_ACCESS_TOKEN", "") if args.site else None
    local_key = os.environ.get("SCHEDULER_CONTROL_TOKEN", "")
    if len(cloud_key) < 43 or len(local_key) < 32 or cloud_key == local_key:
        parser.error("distinct remote-agent and local control environment tokens required")
    if args.site and (not site_access or len(site_access) < 32 or site_access in {cloud_key, local_key}):
        parser.error("distinct Sites service access token required")
    journal = Path(args.journal)
    journal.parent.mkdir(parents=True, exist_ok=True)

    def record(kind, **data):
        with journal.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"at": time.time(), "kind": kind, **data})+"\n")

    def preserve(raw):
        digest = hashlib.sha256(raw).hexdigest()
        folder = journal.parent/"receipts"
        folder.mkdir(exist_ok=True)
        path = folder/(digest+".json")
        if not path.exists():
            path.write_bytes(raw)
        elif path.read_bytes() != raw:
            raise ValueError("receipt integrity mismatch")
        return digest

    started = time.monotonic()
    record("started", protocol="outbound-bridge/1", source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    while not args.run_seconds or time.monotonic()-started < args.run_seconds:
        try:
            status, raw, source = request(args.local_api+"/api/v1/snapshot", local_key)
            if status != 200:
                raise ValueError("local snapshot unavailable")
            projection = project_snapshot(source)
            projected_raw = json.dumps(projection, sort_keys=True).encode()
            record("snapshot.read", raw_sha256=preserve(raw), projection_sha256=preserve(projected_raw), transformation="remote-snapshot/2")
            status, remote_raw, response = request(args.origin.rstrip("/")+"/agent/poll", cloud_key, {"snapshot": projection}, site_access=site_access)
            record("site.poll", http_status=status, raw_sha256=preserve(remote_raw))
            if status != 200:
                raise ValueError("remote poll denied")
            job = response.get("command")
            if job:
                job_id, fence = job["id"], job["fence"]
                import re
                if not isinstance(job_id,str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,128}",job_id) or type(fence) is not int:
                    raise ValueError("invalid command identity")
                ack = {"id": job_id, "fence": fence, "status": "rejected"}
                try:
                    if type(job.get("expires")) is not int or job["expires"] <= time.time():
                        raise ValueError("expired control")
                    path, body = control_route(job["payload"])
                except ValueError:
                    record("control.rejected", id=job_id, fence=fence)
                else:
                    try:
                        code, output, _ = request(args.local_api+path, local_key, body, key="remote:"+job_id)
                        ack.update(status="succeeded" if code == 200 else "failed", http_status=code)
                        record("control.response", id=job_id, fence=fence, http_status=code, output_sha256=preserve(output))
                    except (OSError, TimeoutError, ValueError, urllib.error.URLError):
                        ack["status"] = "uncertain"
                        record("control.uncertain", id=job_id, fence=fence)
                ack_status, ack_raw, _ = request(args.origin.rstrip("/")+"/agent/ack", cloud_key, ack, site_access=site_access)
                record("control.ack", id=job_id, fence=fence, http_status=ack_status, status=ack["status"], raw_sha256=preserve(ack_raw))
        except (OSError, ValueError, TimeoutError, urllib.error.URLError):
            record("bridge.unavailable")
        time.sleep(args.interval)
    record("stopped")


if __name__ == "__main__":
    main()
