import copy
import json
from pathlib import Path
import tempfile
import unittest

from scheduler.contracts import load_plan, validate_plan, SCHEMA_PATH

ROOT = Path(__file__).resolve().parent.parent


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.plan = load_plan(ROOT / 'examples/demo-weather.yaml')

    def reject(self, mutate, message):
        plan = copy.deepcopy(self.plan)
        mutate(plan)
        with self.assertRaisesRegex(ValueError, message):
            validate_plan(plan)

    def test_example_plans_are_independent_valid_dags(self):
        plans = [load_plan(path) for path in sorted((ROOT / 'examples').glob('demo-*.yaml'))]
        self.assertEqual(len(plans), 2)
        self.assertGreaterEqual(sum(len(plan['tasks']) for plan in plans), 12)
        self.assertEqual(len({plan['project_id'] for plan in plans}), 2)
        result = validate_plan(self.plan)
        result['tasks'][0]['title'] = 'changed'
        self.assertNotEqual(result, self.plan)

    def test_normative_schema_is_versioned(self):
        schema = json.loads(SCHEMA_PATH.read_text())
        self.assertEqual(schema['$schema'], 'https://json-schema.org/draft/2020-12/schema')
        self.assertFalse(schema['additionalProperties'])

    def test_missing_and_unknown_fields(self):
        self.reject(lambda p:p['tasks'][0].pop('acceptance_criteria'), 'required')
        self.reject(lambda p:p.update(typo=True), 'unknown field')
        self.reject(lambda p:p['tasks'][0].update(priority=True), 'expected integer')

    def test_duplicate_unknown_and_cyclic_edges(self):
        self.reject(lambda p:p['tasks'][1].update(task_id='source'), 'duplicate')
        self.reject(lambda p:p['tasks'][0].update(depends_on=['missing']), 'unresolved')
        self.reject(lambda p:p['tasks'][0].update(depends_on=['publish']), 'cycle')
        self.reject(lambda p:p['tasks'][1].update(depends_on=['source','source']), 'duplicate')

    def test_capabilities_and_capacity(self):
        self.reject(lambda p:p['tasks'][0]['model'].update(override='unverified-model'), 'unverified')
        self.reject(lambda p:p['tasks'][0]['model'].update(reasoning_effort='high'), 'unverified')
        self.reject(lambda p:p['tasks'][0].update(executor='desktop'), 'expected one of')
        self.reject(lambda p:p['tasks'][0]['resources'].update(slots=10), 'max_workers')
        self.reject(lambda p:p['policy'].update(min_workers=4,target_workers=1), 'min_workers')

    def test_limits_and_locators(self):
        self.reject(lambda p:p['tasks'][0].update(estimate_minutes=float('nan')), 'expected number')
        self.reject(lambda p:p['tasks'][0]['timeout_policy'].update(max_retries=-1), 'minimum')
        self.reject(lambda p:p['repository'].update(url='https://example.invalid/repo'), 'exactly one')

    def test_nonfinite_and_oversized_numbers_are_rejected_cleanly(self):
        self.reject(lambda p:p['tasks'][0].update(estimate_minutes=10**1000), 'expected number')
        self.reject(lambda p:p['tasks'][0].update(estimate_minutes=float('inf')), 'expected number')
        self.reject(lambda p:p.update(revision=2**63), 'maximum')
        self.reject(lambda p:p['tasks'][0]['timeout_policy'].update(max_retries=2**63), 'maximum')
        self.reject(lambda p:p['tasks'][0].update(depends_on=[{}]), 'expected string')

    def test_canonical_schema_packaging_and_reference(self):
        self.assertEqual(SCHEMA_PATH.parent.name, 'schemas')
        self.assertEqual(SCHEMA_PATH.parent.parent.name, 'scheduler')
        reference = json.loads((ROOT / 'schemas/plan-1.0.schema.json').read_text())
        self.assertEqual((ROOT / 'schemas' / reference['$ref']).resolve(), SCHEMA_PATH)
        self.assertIn('"schemas/*.json"', (ROOT / 'pyproject.toml').read_text())

    def test_recursive_alias_and_deep_input_fail_before_composition(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'malicious.yaml'
            for payload, message in [('a: &self [*self]', 'aliases'), ('['*40 + '0' + ']'*40, 'nesting')]:
                path.write_text(payload)
                with self.assertRaisesRegex(ValueError, message):
                    load_plan(path)

    def test_error_lines_duplicate_keys_and_aliases(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'plan.yaml'
            text = (ROOT / 'examples/demo-weather.yaml').read_text()
            path.write_text(text.replace('priority: 80', 'priority: wrong',1))
            with self.assertRaisesRegex(ValueError, r'line \d+: \$\.tasks\[0\].priority'):
                load_plan(path)
            path.write_text('schema_version: "1.0"\nschema_version: "1.0"\n')
            with self.assertRaisesRegex(ValueError, 'duplicate field'):
                load_plan(path)
            path.write_text('a: &anchor [1]\nb: *anchor\n')
            with self.assertRaisesRegex(ValueError, 'aliases'):
                load_plan(path)
            path.write_text('[')
            with self.assertRaisesRegex(ValueError, 'line.*invalid YAML'):
                load_plan(path)


if __name__ == '__main__':
    unittest.main()
