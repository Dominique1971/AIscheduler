"""Diagnostic backup and integrity tests; not generator acceptance."""
import json
from pathlib import Path
import tempfile

import pytest

from scheduler.contracts import load_plan
from scheduler.core import Conflict, Store
from scheduler.maintenance import backup, restore, verify


def test_backup_restore_and_corruption_rejection():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        store = Store(root/"live.db")
        store.apply(load_plan("examples/demo-weather.yaml"))
        store.tick("test")
        receipt = backup(store, root/"backup.db")
        assert receipt["valid"]
        assert restore(root/"backup.db", root/"new.db")["valid"]
        assert verify(Store(root/"new.db"))["revisions"] == 1
        with pytest.raises(Conflict):
            restore(root/"backup.db", root/"new.db")
        with (root/"backup.db").open("ab") as target:
            target.write(b"fault injection, never consumable")
        with pytest.raises(Conflict, match="integrity"):
            restore(root/"backup.db", root/"rejected.db")
        assert not (root/"rejected.db").exists()
