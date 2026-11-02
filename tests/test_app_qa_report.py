"""El resumen no puede dar por aprobada una batería vacía, parcial o fallida."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts.summarize_app_qa import summarize


class AppQAReportTests(unittest.TestCase):
    def run_report(self, data):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'results.json').write_text(json.dumps(data), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                result = summarize(root)
            self.assertTrue((root / 'REVISION_VISUAL.html').exists())
            return result

    def test_empty_and_partial_runs_cannot_pass(self):
        for expected in (0, 1, 50):
            with self.subTest(expected=expected):
                self.assertFalse(self.run_report({'stats': {'expected': expected}})['functional_passed'])

    def test_failure_skip_and_runner_error_cannot_pass(self):
        for detail in ({'stats': {'expected': 51, 'unexpected': 1}},
                       {'stats': {'expected': 51, 'skipped': 1}},
                       {'stats': {'expected': 51}, 'errors': [{'message': 'runner detenido'}]}):
            self.assertFalse(self.run_report(detail)['functional_passed'])

    def test_full_success_keeps_visual_acceptance_pending(self):
        result = self.run_report({'stats': {'expected': 51, 'unexpected': 0, 'skipped': 0, 'flaky': 0}})
        self.assertTrue(result['functional_passed'])
        self.assertEqual(result['visual_acceptance'], 'PENDIENTE_REVISION_HUMANA')
