import tempfile
import unittest
from pathlib import Path
import copy
import json
import shutil
import subprocess
from scripts.prepare_deploy import prepare
from scripts.check_deploy_layout import validate


class PrepareDeploymentTests(unittest.TestCase):
    def test_generated_credentials_are_distinct_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = prepare(Path(directory), 'http://localhost:8080', 'aeroguard-test', 8080)
            original = path.read_bytes()
            values = dict(line.split('=', 1) for line in original.decode().splitlines())
            self.assertGreaterEqual(len(values['SECRET_KEY']), 32)
            self.assertNotEqual(values['POSTGRES_PASSWORD'], values['RABBITMQ_DEFAULT_PASS'])
            with self.assertRaises(FileExistsError):
                prepare(Path(directory), 'http://localhost:8080', 'aeroguard-test', 8080)
            self.assertEqual(original, path.read_bytes())

    def test_remote_plaintext_and_credential_urls_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for url in ('http://example.org', 'https://example.org:8080', 'https://user:password@example.org', 'https://example.org/?token=secret'):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    prepare(Path(directory), url, 'aeroguard-test', 8080)
            self.assertFalse((Path(directory) / '.env').exists())

    def test_project_name_and_port_are_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            for project, port in (('../other', 8080), ('valid', 0), ('valid', 65536)):
                with self.subTest(project=project, port=port), self.assertRaises(ValueError):
                    prepare(Path(directory), 'http://localhost:8080', project, port)

    def test_port_must_match_the_private_origin(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            prepare(Path(directory), 'http://localhost:8080', 'aeroguard-test', 18081)


@unittest.skipUnless(shutil.which('docker'), 'Requiere la CLI de Docker Compose, sin arrancar el motor.')
class PrivateLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        env = prepare(Path(cls.directory.name), 'http://localhost:8080', 'aeroguard-test', 8080)
        root = Path(__file__).resolve().parents[1]
        response = subprocess.run(['docker', 'compose', '--env-file', str(env), '-f', str(root / 'deploy/compose.yml'), 'config', '--format', 'json'],
                                  capture_output=True, text=True, check=True)
        cls.config = json.loads(response.stdout)
        cls.release = json.loads((root / 'deploy/release.json').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_rendered_configuration_is_private(self):
        self.assertTrue(validate(self.config, self.release)['private_loopback_only'])

    def test_public_interface_is_rejected(self):
        config = copy.deepcopy(self.config)
        config['services']['frontend']['ports'][0]['host_ip'] = '0.0.0.0'
        with self.assertRaises(ValueError):
            validate(config, self.release)

    def test_published_database_is_rejected(self):
        config = copy.deepcopy(self.config)
        config['services']['postgres']['ports'] = [{'host_ip': '127.0.0.1', 'target': 5432}]
        with self.assertRaises(ValueError):
            validate(config, self.release)

    def test_docker_socket_mount_is_rejected(self):
        config = copy.deepcopy(self.config)
        config['services']['backend']['volumes'].append({'type': 'bind', 'source': '/var/run/docker.sock', 'target': '/var/run/docker.sock'})
        with self.assertRaises(ValueError):
            validate(config, self.release)

    def test_replacing_bootstrap_with_another_host_file_is_rejected(self):
        config = copy.deepcopy(self.config)
        mount = next(item for item in config['services']['postgres']['volumes'] if item['type'] == 'bind')
        mount['source'] = str(Path(self.directory.name) / 'private-key')
        with self.assertRaises(ValueError):
            validate(config, self.release)

    def test_privileged_container_is_rejected(self):
        config = copy.deepcopy(self.config)
        config['services']['backend']['privileged'] = True
        with self.assertRaises(ValueError):
            validate(config, self.release)

    def test_external_data_network_is_rejected(self):
        config = copy.deepcopy(self.config)
        config['networks']['default']['internal'] = False
        with self.assertRaises(ValueError):
            validate(config, self.release)


if __name__ == '__main__':
    unittest.main()
