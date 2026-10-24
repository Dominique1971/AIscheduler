"""Authenticated loopback API. Remote publication requires a separate MFA gateway."""
from __future__ import annotations

import hmac
import hashlib
import json
import os
import re
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .contracts import validate_plan
from .core import Conflict, Store, stamp
from .intake import MARKDOWN_INTAKE_VERSION, TRANSFORM_VERSION, build_intake, load_intake, parse_markdown_intake, plan_summary


def create_app(store: Store, read_token=None, control_token=None):
    read_token = read_token or os.environ.get("SCHEDULER_READ_TOKEN")
    control_token = control_token or os.environ.get("SCHEDULER_CONTROL_TOKEN")
    if not control_token or len(control_token) < 32:
        raise ValueError("SCHEDULER_CONTROL_TOKEN of at least 32 characters is required")
    if read_token and (len(read_token) < 32 or hmac.compare_digest(read_token, control_token)):
        raise ValueError("read token must be distinct and at least 32 characters")
    app = FastAPI(title="Autonomous Project Scheduler", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)
    buckets = defaultdict(deque)
    expires = float(os.environ.get("SCHEDULER_TOKEN_EXPIRES_AT", "0"))

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        host = request.headers.get("host", "").split(":")[0]
        if host not in {"127.0.0.1", "localhost", "testserver"}:
            return JSONResponse({"error": "untrusted_host"}, status_code=400)
        if request.headers.get("origin") and request.headers["origin"] != f"{request.url.scheme}://{request.headers.get('host')}":
            return JSONResponse({"error": "cross_origin_forbidden"}, status_code=403)
        if request.url.path.startswith("/api/"):
            client = request.client.host if request.client else "unknown"
            now = time.monotonic()
            bucket = buckets[client]
            while bucket and bucket[0] < now-60:
                bucket.popleft()
            if len(bucket) >= 240:
                return JSONResponse({"error": "rate_limited"}, status_code=429, headers={"Retry-After": "60"})
            bucket.append(now)
            try:
                content_length = int(request.headers.get("content-length", "0"))
                if content_length < 0:
                    raise ValueError()
            except ValueError:
                return JSONResponse({"error": "invalid_content_length"}, status_code=400)
            if content_length > 1048576:
                return JSONResponse({"error": "request_too_large"}, status_code=413)
            if request.method == "POST":
                body = await request.body()
                if len(body) > 1048576:
                    return JSONResponse({"error": "request_too_large"}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'"
        return response

    def identity(request: Request):
        header = request.headers.get("authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        if expires and time.time() >= expires:
            raise HTTPException(401, "token expired")
        if hmac.compare_digest(token, control_token):
            return "controller"
        if read_token and hmac.compare_digest(token, read_token):
            return "reader"
        raise HTTPException(401, "valid bearer token required")

    def controller(request: Request, role=Depends(identity)):
        if role != "controller":
            raise HTTPException(403, "control permission required")
        key = request.headers.get("idempotency-key")
        if not key or len(key) > 128:
            raise HTTPException(400, "Idempotency-Key required (1..128 characters)")
        return role

    async def object_body(request):
        value = await request.json()
        if not isinstance(value, dict):
            raise ValueError("JSON request body must be an object")
        return value

    @app.exception_handler(Conflict)
    async def conflict(request, exc):
        return JSONResponse({"error": "conflict", "message": str(exc)}, status_code=409)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"error": "invalid_input", "message": str(exc)}, status_code=422)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"error": "not_found", "message": str(exc)}, status_code=404)

    @app.get("/api/v1/snapshot")
    def snapshot(role=Depends(identity)):
        return {**store.snapshot(), "role": role}

    @app.get("/api/v1/system/health")
    def health(role=Depends(identity)):
        s = store.snapshot()
        return {"updated_at": s["updated_at"], "daemon": s["daemon"], "executor": "simulation-only", "remote_access": "not-configured"}

    @app.get("/api/v1/projects")
    def projects(offset: int = 0, limit: int = 50, role=Depends(identity)):
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("invalid pagination")
        s = store.snapshot()
        return {"items": s["projects"][offset:offset+limit], "updated_at": s["updated_at"]}

    @app.get("/api/v1/projects/{project}/tasks/{task}/trace")
    def trace(project: str, task: str, role=Depends(identity)):
        return store.trace(project, task)

    @app.get("/api/v1/projects/{project}/plans/history")
    def history(project: str, offset: int = 0, limit: int = 50, role=Depends(identity)):
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("invalid pagination")
        with store.connect() as db:
            return {"items": [dict(r) for r in db.execute("SELECT * FROM revisions WHERE project=? ORDER BY revision DESC LIMIT ? OFFSET ?", (project, limit, offset))], "updated_at": stamp()}

    @app.get("/api/v1/projects/{project}/plan")
    def current_plan(project: str, role=Depends(identity)):
        result = store.current_plan(project)
        return {"summary": plan_summary(result["plan"]), "revision": result["plan"]["revision"],
                "plan_sha256": result["plan_sha256"], "source": result["source"]}

    @app.get("/api/v1/examples")
    def examples(role=Depends(identity)):
        root = Path(__file__).parent / "examples"
        items = []
        for name in ("demo-weather.yaml", "demo-inventory.yaml"):
            intake, source_hash = load_intake(root / name)
            draft = build_intake(intake, source_hash)
            items.append({"id": name.removesuffix(".yaml"), "intake": intake,
                          "summary": draft["summary"], "example_file_sha256": source_hash})
        return {"items": items}

    @app.post("/api/v1/intake/preview")
    async def intake_preview(request: Request, role=Depends(controller)):
        raw = await request.body()
        data = await object_body(request)
        if set(data) != {"intake"}:
            raise ValueError("intake preview requires only the intake object")
        source_text = json.dumps(data["intake"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        draft = build_intake(data["intake"], hashlib.sha256(source_text.encode()).hexdigest(),
                             source_kind="canonical-json-intake/1")
        return {**draft, "source_text": source_text, "request_sha256": hashlib.sha256(raw).hexdigest()}

    def markdown_draft(data):
        if set(data) != {"filename", "source_text"} or not isinstance(data["filename"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,124}\.md", data["filename"]):
            raise ValueError("upload one .md file with a simple filename")
        source_text = data["source_text"]
        intake = parse_markdown_intake(source_text)
        source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
        draft = build_intake(intake, source_hash, source_kind=MARKDOWN_INTAKE_VERSION)
        return draft, intake

    def guard_dummy_plan(plan):
        path = plan["repository"]["path"].replace("\\", "/")
        if not plan["project_id"].startswith(("demo-", "dummy-")) or not path.startswith(("./runtime/", "runtime/")) or ".." in path.split("/") or not all(t["executor"] == "simulation" for t in plan["tasks"]):
            raise ValueError("dashboard import is limited to disposable simulation projects under ./runtime/")

    @app.post("/api/v1/intake/file/preview")
    async def intake_file_preview(request: Request, role=Depends(controller)):
        raw = await request.body()
        data = await object_body(request)
        draft, intake = markdown_draft(data)
        return {**draft, "intake": intake, "source_text": data["source_text"],
                "filename": data["filename"], "request_sha256": hashlib.sha256(raw).hexdigest()}

    @app.post("/api/v1/intake/file/import")
    async def intake_file_import(request: Request, role=Depends(controller)):
        data = await object_body(request)
        if set(data) != {"filename", "source_text", "expected_source_sha256", "expected_preview", "approved"}:
            raise ValueError("file import requires filename, source_text, expected_source_sha256, expected_preview and approved")
        if data["approved"] is not True or not isinstance(data["expected_preview"], dict):
            raise ValueError("reviewed preview and explicit approval required")
        draft, _ = markdown_draft({"filename": data["filename"], "source_text": data["source_text"]})
        if draft["source_sha256"] != data["expected_source_sha256"]:
            raise Conflict("Markdown source changed; preview again")
        guard_dummy_plan(draft["plan"])
        return store.apply(draft["plan"], approved=True, key=request.headers["idempotency-key"],
                           expected_preview=data["expected_preview"],
                           source_receipt={"source": data["source_text"], "source_hash": draft["source_sha256"],
                                           "transform_version": MARKDOWN_INTAKE_VERSION + "+" + TRANSFORM_VERSION,
                                           "defaults": draft["defaults_applied"]})

    @app.post("/api/v1/intake/import")
    async def intake_import(request: Request, role=Depends(controller)):
        data = await object_body(request)
        if set(data) != {"intake", "expected_source_sha256", "expected_preview", "approved"}:
            raise ValueError("intake import requires intake, expected_source_sha256, expected_preview and approved")
        if data["approved"] is not True or not isinstance(data["expected_preview"], dict):
            raise ValueError("reviewed preview and explicit approval required")
        source_text = json.dumps(data["intake"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        source_hash = hashlib.sha256(source_text.encode()).hexdigest()
        if source_hash != data["expected_source_sha256"]:
            raise Conflict("intake changed; preview again")
        draft = build_intake(data["intake"], source_hash, source_kind="canonical-json-intake/1")
        guard_dummy_plan(draft["plan"])
        return store.apply(draft["plan"], approved=True, key=request.headers["idempotency-key"],
                           expected_preview=data["expected_preview"],
                           source_receipt={"source": source_text, "source_hash": source_hash,
                                           "transform_version": TRANSFORM_VERSION, "defaults": draft["defaults_applied"]})

    @app.post("/api/v1/plans/{operation}")
    async def plan(operation: str, request: Request, role=Depends(controller)):
        data = await object_body(request)
        if data.keys() - {"plan", "approved", "expected_preview"}:
            raise ValueError("unknown plan request fields")
        if "expected_preview" in data and not isinstance(data["expected_preview"], dict):
            raise ValueError("expected_preview must be an object")
        value = validate_plan(data.get("plan"))
        if operation == "validate":
            return {"valid": True, "project_id": value["project_id"]}
        if operation == "preview":
            return store.preview(value)
        if operation == "apply":
            return store.apply(value, approved=data.get("approved") is True,
                               key=request.headers["idempotency-key"],
                               expected_preview=data.get("expected_preview"))
        raise HTTPException(404, "unknown plan operation")

    @app.post("/api/v1/projects/{project}/{action}")
    async def project_control(project: str, action: str, request: Request, role=Depends(controller)):
        if action not in {"pause", "resume", "allocate"}:
            raise HTTPException(404)
        body = await object_body(request)
        allowed = {"max_workers", "min_workers", "target_workers", "reserved_slots"} if action == "allocate" else set()
        if body.keys() - allowed:
            raise ValueError("unknown project control fields")
        allocation = {k: body[k] for k in ("max_workers", "min_workers", "target_workers", "reserved_slots") if k in body}
        # Preserve convenient cap-only controls while supporting the full allocation contract.
        value = allocation if len(allocation) > 1 or "max_workers" not in allocation else allocation["max_workers"]
        return store.control(action, project, value=value if action == "allocate" else None,
                             key=request.headers["idempotency-key"], actor=role)

    @app.post("/api/v1/projects/{project}/tasks/{task}/{action}")
    def task_control(project: str, task: str, action: str, request: Request, role=Depends(controller)):
        if action not in {"retry", "hold", "unhold"}:
            raise HTTPException(404)
        return store.control(action, project, task, key=request.headers["idempotency-key"], actor=role)

    @app.post("/api/v1/system/{action}")
    async def system_control(action: str, request: Request, role=Depends(controller)):
        if action not in {"emergency-stop", "start", "workers"}:
            raise HTTPException(404)
        data = await object_body(request)
        allowed = {"confirmed"} if action == "emergency-stop" else {"max_workers"} if action == "workers" else set()
        if data.keys() - allowed:
            raise ValueError("unknown system control fields")
        if action == "emergency-stop" and data.get("confirmed") is not True:
            raise HTTPException(400, "emergency stop requires confirmed: true")
        return store.control(action, value=data.get("max_workers") if action == "workers" else None,
                             key=request.headers["idempotency-key"], actor=role)

    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="dashboard")
    return app
