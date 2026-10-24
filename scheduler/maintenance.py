"""Explicit backup/restore transformations; never edits application results."""
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from contextlib import closing

from .core import Conflict, Connection, Store, digest


def read_only_store(path):
    # Construct a read-only view without running schema initialization/migrations
    # against preserved backup bytes.
    store = object.__new__(Store)
    store.path = str(path)

    def connect():
        db = sqlite3.connect(Path(path).as_uri()+"?mode=ro", uri=True, factory=Connection)
        db.row_factory = sqlite3.Row
        return db

    store.connect = connect
    return store


def verify(store):
    attempts = 0
    revisions = 0
    with store.connect() as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise Conflict("SQLite integrity check failed")
        for row in db.execute("SELECT plan,hash FROM revisions"):
            if digest(json.loads(row["plan"])) != row["hash"]:
                raise Conflict("revision integrity failure")
            revisions += 1
        keys = db.execute("SELECT DISTINCT project,task FROM attempts").fetchall()
    for row in keys:
        attempts += len(store.trace(row["project"], row["task"])["attempts"])
    return {"valid": True, "attempts": attempts, "revisions": revisions, "checked_at_epoch": time.time(),
            "limitation": "hashes establish byte consistency, not semantic correctness or tamper-proof storage"}


def backup(store, destination):
    path = Path(destination).resolve()
    receipt_path = path.with_suffix(path.suffix+".receipt.json")
    if path.exists() or receipt_path.exists():
        raise Conflict("backup destination or receipt already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    with store.connect() as source:
        with closing(sqlite3.connect(path)) as target:
            source.backup(target)
    result = verify(read_only_store(path))
    receipt = {"operation": "sqlite-online-backup-v1", "source": str(Path(store.path).resolve()),
               "destination": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), **result}
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


def restore(source, destination):
    path = Path(source).resolve(strict=True)
    receipt = json.loads(path.with_suffix(path.suffix+".receipt.json").read_text(encoding="utf-8"))
    if hashlib.sha256(path.read_bytes()).hexdigest() != receipt["sha256"]:
        raise Conflict("backup integrity failure")
    target_path = Path(destination).resolve()
    if target_path.exists():
        raise Conflict("restore target must be new; existing state is never overwritten")
    verify(read_only_store(path))
    # Use SQLite's backup operation, preserving the signed source byte-for-byte.
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path.as_uri()+"?mode=ro", uri=True)) as original:
        with closing(sqlite3.connect(target_path)) as target:
            original.backup(target)
    result = verify(Store(target_path))
    restored = Store(target_path)
    with restored.transaction() as db:
        db.execute("UPDATE leader SET expires=0")
        restored.event(db, "backup.restored", source_sha256=receipt["sha256"], transformation="sqlite-backup-v1")
    return {"destination": str(target_path), "source_sha256": receipt["sha256"], **result}
