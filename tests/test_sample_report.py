import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import sample_report as sr


class SampleReportTests(unittest.TestCase):
    def test_removes_plans_but_preserves_observations_and_source(self):
        original = {"weeks": [{"start": "2026-10-05", "plan": 10, "leads": 2, "sessions": 20}, {"start": "2026-10-12", "plan": 20}], "rates": {"lead": 1}, "targetWeek": 3}
        before = copy.deepcopy(original)
        clean = sr.without_targets(original)
        self.assertEqual(clean["weeks"], [{"start": "2026-10-05", "leads": 2, "sessions": 20}])
        self.assertNotIn("rates", clean)
        self.assertNotIn("targetWeek", clean)
        self.assertEqual(original, before)

    def test_html_import_reads_state_without_running_document_scripts(self):
        with tempfile.TemporaryDirectory(dir=sr.ROOT) as folder:
            path = Path(folder) / "input.html"
            path.write_text('<script>throw new Error("must not run")</script><script id="state" type="application/json">{"weeks":[]}</script>', encoding="utf-8")
            self.assertEqual(sr.read_state(path), {"weeks": []})

    def test_json_embedding_cannot_end_the_script_or_inject_a_title(self):
        value = '</script><script>alert(1)</script>'
        output = sr.render({"weeks": [], "brand": value})
        self.assertNotIn('<script>alert(1)</script>', output)
        self.assertIn('\\u003c/script\\u003e', output)
        self.assertIn('&lt;/script&gt;', output)

    def test_example_is_fictional_self_contained_and_reproducible(self):
        source = sr.read_state(sr.ROOT / 'examples' / 'sample-report.json')
        self.assertTrue(source['sample'])
        generated = sr.render(sr.without_targets(source))
        saved = (sr.ROOT / 'examples' / 'sample-report.html').read_text(encoding='utf-8')
        self.assertEqual(generated, saved)
        for fragment in ('<link ', '<script src=', 'window.claude', 'targetWeek', 'planFor(', 'Target 10 a day', '100k', '11Prop'):
            self.assertNotIn(fragment, generated)
        self.assertIn('Recorded lead events over time', generated)

    def test_sample_totals_reconcile_and_targets_are_absent(self):
        state = sr.read_state(sr.ROOT / 'examples' / 'sample-report.json')
        slices, paid = state['slices'], state['visuals']['paid']
        organic = sum(row[3] for row in slices['sessions'] if row[2] == 'Organic Search')
        self.assertEqual(organic, state['visuals']['journey']['sessions'])
        self.assertEqual(organic, sum(row['n'] for row in state['visuals']['journey']['landing']))
        self.assertEqual(sum(row['clicks'] for row in paid['daily']), paid['totals']['clicks'])
        self.assertAlmostEqual(sum(row['cost'] for row in paid['daily']), paid['totals']['spend'])
        self.assertEqual(sum(row['clicks'] for row in paid['campaigns']), paid['totals']['clicks'])
        self.assertNotIn('targetWeek', state)
        self.assertTrue(all('plan' not in week for week in state['weeks']))


if __name__ == '__main__':
    unittest.main()
