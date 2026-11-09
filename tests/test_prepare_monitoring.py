import tempfile
import unittest
from pathlib import Path
from scripts.prepare_monitoring import prepare


class MonitoringPreparationTests(unittest.TestCase):
    def test_preserves_existing_application_configuration_and_monitor_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = root / '.env'
            original = 'METRICS_BEARER_TOKEN=' + 'a' * 64 + '\nSECRET_KEY=preserve-me\n'
            env.write_text(original, encoding='utf-8')
            extra = prepare(env, root / 'monitor')
            password_file = extra.read_bytes()
            prepare(env, root / 'monitor')
            self.assertEqual(env.read_text(encoding='utf-8'), original)
            self.assertEqual(extra.read_bytes(), password_file)
            self.assertEqual((root / 'monitor/secrets/metrics.token').read_text().strip(), 'a' * 64)

    def test_rejects_a_mismatched_existing_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = root / '.env'
            env.write_text('METRICS_BEARER_TOKEN=' + 'a' * 64, encoding='utf-8')
            prepare(env, root)
            (root / 'secrets/metrics.token').write_text('b' * 64, encoding='utf-8')
            with self.assertRaises(ValueError):
                prepare(env, root)
            self.assertEqual((root / 'secrets/metrics.token').read_text(), 'b' * 64)
