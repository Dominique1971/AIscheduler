"""Allocation fixture diagnostics; not end-to-end executor acceptance."""
from copy import deepcopy
from pathlib import Path
import json
import time

import pytest

from scheduler.contracts import load_plan
from scheduler.core import Conflict, Store


def plan(pid, slots=1, **policy):
    value = load_plan(Path(__file__).resolve().parents[1] / 'examples/demo-weather.yaml')
    value['project_id'] = pid
    value['policy'].update({'max_workers':6, 'target_workers':0, **policy})
    prototype = value['tasks'][0]
    value['tasks'] = []
    for index in range(8):
        task = deepcopy(prototype)
        task.update(task_id=f't{index}', depends_on=[], resources={'slots': slots},
                    simulation={'duration_seconds': 5}, priority=80)
        value['tasks'].append(task)
    return value


def projects(store):
    return {p['project_id']:p for p in store.snapshot()['projects']}


def test_minimum_and_target_dispatch_preferences_and_backfill(tmp_path):
    store = Store(tmp_path / 'allocation.db', max_workers=4)
    store.apply(plan('a', target_workers=0))
    store.apply(plan('z', min_workers=2, target_workers=3))
    store.tick('test', now=time.time())
    values = projects(store)
    assert values['z']['busy'] == 3
    assert values['a']['busy'] == 1
    # Min/target do not reserve idle capacity; another project uses all spare slots.
    second = Store(tmp_path / 'backfill.db', max_workers=4)
    second.apply(plan('a'))
    second.apply(plan('z', min_workers=2, target_workers=3))
    second.control('pause', 'z')
    second.tick('test', now=time.time())
    assert projects(second)['a']['busy'] == 4


def test_paused_reservation_holds_idle_and_release_backfills(tmp_path):
    store = Store(tmp_path / 'reserved.db', max_workers=6)
    store.apply(plan('a'))
    store.apply(plan('z', reserved_slots=2))
    store.control('pause', 'z')
    now = time.time()
    store.tick('test', now=now)
    values = projects(store)
    assert values['a']['busy'] == 4
    assert values['z']['allocated'] == values['z']['idle'] == 2
    assert values['z']['busy'] == 0
    assert values['z']['blocked'] == 8
    store.control('allocate', 'z', value={'reserved_slots':0})
    store.tick('test', now=now+.1)
    assert projects(store)['a']['busy'] == 6


def test_multislot_task_cannot_consume_reserved_capacity(tmp_path):
    store = Store(tmp_path / 'resources.db', max_workers=4)
    store.apply(plan('a', slots=2))
    store.apply(plan('z', reserved_slots=1))
    store.control('pause', 'z')
    store.tick('test', now=time.time())
    values = projects(store)
    assert values['a']['busy'] == 2
    assert values['a']['ready'] == 14
    assert store.snapshot()['metrics']['unallocated'] == 1


def test_reallocation_is_audited_without_mutating_canonical_plan(tmp_path):
    store = Store(tmp_path / 'live.db', max_workers=6)
    original = plan('a', min_workers=1, target_workers=4)
    store.apply(original)
    store.control('allocate', 'a', value=2)
    values = projects(store)['a']
    assert values['max_workers'] == 2
    assert values['target_workers'] == 2
    store.control('allocate', 'a', value={'max_workers':3,'target_workers':3,'reserved_slots':1})
    store = Store(store.path)
    assert projects(store)['a']['reserved_slots'] == 1
    with store.connect() as db:
        assert json.loads(db.execute('SELECT plan FROM revisions').fetchone()[0]) == original
        assert json.loads(db.execute('SELECT plan FROM projects').fetchone()[0]) == original
        assert db.execute("SELECT count(*) FROM events WHERE kind='control.allocate'").fetchone()[0] == 2


def test_infeasible_reservations_and_worker_reductions_are_atomic(tmp_path):
    store = Store(tmp_path / 'bounds.db', max_workers=4)
    store.apply(plan('a', reserved_slots=3))
    with pytest.raises(Conflict, match='reserved slots'):
        store.apply(plan('z', reserved_slots=2))
    assert len(projects(store)) == 1
    with pytest.raises(Conflict, match='reserved slots'):
        store.control('workers', value=2)
    assert store.snapshot()['max_workers'] == 4
    store.control('allocate', 'a', value={'reserved_slots':0})
    store.tick('test', now=time.time())
    with pytest.raises(Conflict, match='active work'):
        store.control('workers', value=3)
    with pytest.raises(ValueError):
        store.control('allocate', 'a', value={'target_workers':9})
    with pytest.raises(ValueError):
        store.control('allocate', 'a', value=True)


def test_legacy_database_migration_keeps_plan_history(tmp_path):
    store = Store(tmp_path / 'legacy.db')
    original = plan('a', min_workers=1, target_workers=3, reserved_slots=1)
    store.apply(original)
    with store.connect() as db:
        db.execute('DROP TABLE allocations')
    reopened = Store(store.path)
    value = projects(reopened)['a']
    assert (value['min_workers'],value['target_workers'],value['reserved_slots']) == (1,3,1)
    with reopened.connect() as db:
        assert json.loads(db.execute('SELECT plan FROM revisions').fetchone()[0]) == original



def test_three_project_live_reallocation_four_one_one_to_two_two_two(tmp_path):
    store = Store(tmp_path / 'three.db', max_workers=6)
    for pid, cap in [('a',4),('b',1),('c',1)]:
        store.apply(plan(pid, max_workers=cap, target_workers=cap))
    now = time.time()
    store.tick('test', now=now)
    assert {pid:p['busy'] for pid,p in projects(store).items()} == {'a':4,'b':1,'c':1}
    for pid in ('a','b','c'):
        store.control('allocate', pid, value={'max_workers':2,'target_workers':2})
    # Active work drains safely; updated allocations govern replacement dispatch.
    store.tick('test', now=now+5.1)
    assert {pid:p['busy'] for pid,p in projects(store).items()} == {'a':2,'b':2,'c':2}
