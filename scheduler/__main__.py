from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
import time
import uuid

from .contracts import load_plan
from .core import Store


def main():
    parser = argparse.ArgumentParser(description="Standalone dummy-first scheduler")
    parser.add_argument("--db", default="runtime/scheduler.sqlite")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("validate")
    p.add_argument("plan")
    p = sub.add_parser("intake")
    p.add_argument("source")
    p.add_argument("--output", help="write a new canonical JSON plan and provenance sidecar; never overwrite")
    for name in ["import", "preview"]:
        p = sub.add_parser(name)
        p.add_argument("plan")
        p.add_argument("--approve", action="store_true")
    p = sub.add_parser("daemon")
    p.add_argument("--workers", type=int)
    p.add_argument("--interval", type=float, default=0.25)
    p.add_argument("--run-seconds", type=float, default=0)
    p = sub.add_parser("serve")
    p.add_argument("--port", type=int, default=8765)
    sub.add_parser("snapshot")
    sub.add_parser("verify")
    p = sub.add_parser("backup")
    p.add_argument("destination")
    p = sub.add_parser("restore")
    p.add_argument("source")
    p = sub.add_parser("trace")
    p.add_argument("project")
    p.add_argument("task")
    p = sub.add_parser("control")
    p.add_argument("action", choices=["pause", "resume", "allocate", "hold", "unhold", "retry", "emergency-stop", "start", "workers"])
    p.add_argument("--project")
    p.add_argument("--task")
    p.add_argument("--value", type=int)
    p.add_argument("--confirmed", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "validate":
            plan = load_plan(args.plan)
            print(json.dumps({"valid": True, "project_id": plan["project_id"]}))
            return
        if args.command == "intake":
            from .intake import build_intake, load_intake

            value, source_hash = load_intake(args.source)
            draft = build_intake(value, source_hash)
            if args.output:
                destination = Path(args.output)
                receipt = destination.with_name(destination.name + ".provenance.json")
                if destination.exists() or receipt.exists():
                    raise ValueError("intake output or provenance already exists; choose a new path")
                if not destination.parent.is_dir():
                    raise ValueError("intake output parent directory does not exist")
                with destination.open("x", encoding="utf-8", newline="\n") as stream:
                    json.dump(draft["plan"], stream, indent=2, ensure_ascii=False)
                    stream.write("\n")
                with receipt.open("x", encoding="utf-8", newline="\n") as stream:
                    json.dump({key: draft[key] for key in ("transform_version", "source_sha256", "source_kind",
                                                              "plan_sha256", "defaults_applied", "summary", "status")},
                              stream, indent=2, ensure_ascii=False)
                    stream.write("\n")
                print(json.dumps({"plan_path": str(destination), "provenance_path": str(receipt),
                                  "summary": draft["summary"], "status": draft["status"]}, indent=2))
            else:
                print(json.dumps(draft, indent=2, ensure_ascii=False))
            return
        if args.command == "restore":
            from .maintenance import restore
            print(json.dumps(restore(args.source, args.db), indent=2))
            return
        store = Store(args.db, getattr(args, "workers", None) or 6)
        if args.command == "import":
            result = store.apply(load_plan(args.plan), approved=args.approve)
        elif args.command == "preview":
            result = store.preview(load_plan(args.plan))
        elif args.command == "snapshot":
            result = store.snapshot()
        elif args.command == "verify":
            from .maintenance import verify
            result = verify(store)
        elif args.command == "backup":
            from .maintenance import backup
            result = backup(store, args.destination)
        elif args.command == "trace":
            result = store.trace(args.project, args.task)
        elif args.command == "control":
            if args.action == "emergency-stop" and not args.confirmed:
                raise ValueError("emergency-stop requires --confirmed")
            result = store.control(args.action, args.project, args.task, args.value)
        elif args.command == "serve":
            import uvicorn
            from .api import create_app
            uvicorn.run(create_app(store), host="127.0.0.1", port=args.port, access_log=False)
            return
        elif args.command == "daemon":
            if not 0.02 <= args.interval <= 5 or args.run_seconds < 0:
                raise ValueError("interval must be .02..5 seconds; run-seconds must be nonnegative")
            if args.workers is not None:
                store.control("workers", value=args.workers)
            owner = str(uuid.uuid4())
            running = True

            def stop(*_):
                nonlocal running
                running = False

            signal.signal(signal.SIGINT, stop)
            signal.signal(signal.SIGTERM, stop)
            start = time.monotonic()
            print(json.dumps({"daemon": owner, "state": "started", "executor": "simulation-only"}), flush=True)
            try:
                while running and (not args.run_seconds or time.monotonic()-start < args.run_seconds):
                    store.tick(owner)
                    time.sleep(args.interval)
            finally:
                store.release(owner)
                print(json.dumps({"daemon": owner, "state": "stopped"}), flush=True)
            return
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError) as exc:
        parser.exit(2, json.dumps({"error": type(exc).__name__, "message": str(exc)})+"\n")


if __name__ == "__main__":
    main()
