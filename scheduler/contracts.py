"""Strict, side-effect-free canonical plan validation.

Schema is normative for shape; semantic checks here enforce the DAG and verified
capability boundary. Validation never imports a project or launches execution.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import re
from typing import Any

import yaml

SCHEMA_PATH = Path(__file__).resolve().parent / 'schemas' / 'plan-1.0.schema.json'


def _finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _check(value: Any, schema: dict, path: str = '$') -> None:
    kind = schema.get('type')
    matches = {
        'object': lambda: isinstance(value, dict),
        'array': lambda: isinstance(value, list),
        'string': lambda: isinstance(value, str),
        'integer': lambda: isinstance(value, int) and not isinstance(value, bool),
        'number': lambda: _finite_number(value),
    }
    if kind and not matches[kind]():
        raise ValueError(f'{path}: expected {kind}')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(f"{path}: expected one of {schema['enum']!r}")
    if kind == 'object':
        for key in schema.get('required', []):
            if key not in value:
                raise ValueError(f'{path}.{key}: required field missing')
        properties = schema.get('properties', {})
        for key, child in value.items():
            if key not in properties and schema.get('additionalProperties') is False:
                raise ValueError(f'{path}.{key}: unknown field')
            if key in properties:
                _check(child, properties[key], f'{path}.{key}')
        if 'oneOf' in schema:
            count = sum(all(key in value for key in option.get('required', [])) for option in schema['oneOf'])
            if count != 1:
                raise ValueError(f'{path}: specify exactly one repository locator, path or url')
    elif kind == 'array':
        if len(value) < schema.get('minItems', 0):
            raise ValueError(f'{path}: requires at least {schema["minItems"]} items')
        for index, child in enumerate(value):
            _check(child, schema['items'], f'{path}[{index}]')
        if schema.get('uniqueItems') and len(value) != len(set(value)):
            raise ValueError(f'{path}: duplicate items')
    elif kind == 'string':
        if len(value.strip()) < schema.get('minLength', 0):
            raise ValueError(f'{path}: must be nonempty')
        if 'pattern' in schema and not re.search(schema['pattern'], value):
            raise ValueError(f'{path}: invalid identifier')
    elif kind in ('integer', 'number'):
        for key, comparison in [('minimum', lambda a,b:a < b), ('maximum', lambda a,b:a > b), ('exclusiveMinimum', lambda a,b:a <= b)]:
            if key in schema and comparison(value, schema[key]):
                raise ValueError(f'{path}: violates {key} {schema[key]}')


def validate_plan(data: dict) -> dict:
    """Return an independent validated plan, or raise ValueError with field path.

    Structural validity is not a claim that every runtime option is implemented.
    Memory reservations, token budgets, skill requirements, due dates, merge and
    regression schedules remain declarative contracts in the simulation MVP.
    Execution admission must expose its supported subset and gate real adapters.
    """
    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    _check(data, schema)
    policy = data['policy']
    maximum = policy['max_workers']
    minimum = policy.get('min_workers', 0)
    target = policy.get('target_workers', maximum)
    if not minimum <= target <= maximum or policy.get('reserved_slots', 0) > maximum:
        raise ValueError('$.policy: require min_workers <= target_workers <= max_workers and reserved_slots <= max_workers')
    ids = [task['task_id'] for task in data['tasks']]
    if len(ids) != len(set(ids)):
        raise ValueError('$.tasks: duplicate immutable task_id')
    graph = {task['task_id']:task['depends_on'] for task in data['tasks']}
    for index, task in enumerate(data['tasks']):
        prefix = f'$.tasks[{index}]'
        for dependency in task['depends_on']:
            if dependency not in graph:
                raise ValueError(f'{prefix}.depends_on: unresolved dependency {dependency!r}')
        if task['resources']['slots'] > maximum:
            raise ValueError(f'{prefix}.resources.slots: exceeds project max_workers')
        timeout = task['timeout_policy']
        if timeout['warning_multiplier'] >= timeout['escalation_multiplier']:
            raise ValueError(f'{prefix}.timeout_policy: warning_multiplier must precede escalation_multiplier')
        if task['executor'] != 'simulation' and 'simulation' in task:
            raise ValueError(f'{prefix}.simulation: incompatible with executor')
        if 'override' in task['model'] or 'reasoning_effort' in task['model']:
            raise ValueError(f'{prefix}.model: override/reasoning capability is unverified and unsupported; use preference: default')
    # Iterative topological traversal supports large plans without recursion limits.
    unresolved = {key:len(edges) for key, edges in graph.items()}
    successors = {key:[] for key in graph}
    for key, dependencies in graph.items():
        for dependency in dependencies:
            successors[dependency].append(key)
    ready = [key for key,count in unresolved.items() if count == 0]
    visited = 0
    while ready:
        key = ready.pop()
        visited += 1
        for successor in successors[key]:
            unresolved[successor] -= 1
            if unresolved[successor] == 0:
                ready.append(successor)
    if visited != len(graph):
        raise ValueError('$.tasks: dependency cycle detected')
    return copy.deepcopy(data)


class _StrictLoader(yaml.SafeLoader):
    pass


def _mapping(loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ValueError(f'line {key_node.start_mark.line + 1}: mapping keys must be strings')
        if key in result:
            raise ValueError(f'line {key_node.start_mark.line + 1}: duplicate field {key!r}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _locations(node: yaml.Node, prefix: str = '$', result: dict | None = None) -> dict:
    result = {} if result is None else result
    result[prefix] = node.start_mark.line + 1
    if isinstance(node, yaml.MappingNode):
        for key, child in node.value:
            _locations(child, f'{prefix}.{key.value}', result)
    elif isinstance(node, yaml.SequenceNode):
        for index, child in enumerate(node.value):
            _locations(child, f'{prefix}[{index}]', result)
    return result


def load_plan(path: str | Path) -> dict:
    """Load YAML/JSON safely, reject duplicate fields, annotate errors with lines."""
    source = Path(path)
    text = source.read_text(encoding='utf-8-sig')
    try:
        if len(text.encode('utf-8')) > 2 * 1024 * 1024:
            raise ValueError('plan exceeds 2 MiB input limit')
        depth = 0
        for event in yaml.parse(text):
            if isinstance(event, yaml.AliasEvent):
                raise ValueError(f'line {event.start_mark.line + 1}: YAML aliases are unsupported; use explicit plan fields')
            if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
                depth += 1
                if depth > 32:
                    raise ValueError(f'line {event.start_mark.line + 1}: nesting exceeds 32 levels')
            elif isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
                depth -= 1
        node = yaml.compose(text, Loader=_StrictLoader)
        locations = _locations(node) if node else {'$':1}
        return validate_plan(yaml.load(text, Loader=_StrictLoader))
    except yaml.YAMLError as exc:
        mark = getattr(exc, 'problem_mark', None)
        line = mark.line + 1 if mark else 1
        raise ValueError(f'{source}:line {line}: invalid YAML: {exc}') from exc
    except ValueError as exc:
        match = re.match(r'(\$[^:]*):', str(exc))
        location = match.group(1) if match else '$'
        locations = locals().get('locations', {'$':1})
        while location not in locations and location != '$':
            location = re.sub(r'(\.[^.\[]+|\[\d+\])$', '', location) or '$'
        raise ValueError(f'{source}:line {locations.get(location, 1)}: {exc}') from exc
