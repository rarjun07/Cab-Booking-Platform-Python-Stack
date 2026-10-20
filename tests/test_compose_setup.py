"""Safety regressions for the standalone local credential generator."""
import contextlib
import importlib.util
import io
from pathlib import Path
import stat
import tempfile
import unittest
from urllib.parse import urlsplit

SPEC = importlib.util.spec_from_file_location("setup_compose", Path(__file__).resolve().parents[1] / "scripts/setup_compose.py")
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


class ComposeConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous_root = setup.ROOT
        setup.ROOT = Path(self.temp.name)

    def tearDown(self):
        setup.ROOT = self.previous_root
        self.temp.cleanup()

    def generate(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            setup.main()
        return output.getvalue()

    def test_private_matching_credentials_safe_defaults_no_secret_output(self):
        output = self.generate()
        database = dict(line.split("=", 1) for line in (setup.ROOT / ".env.database").read_text().splitlines())
        app = dict(line.split("=", 1) for line in (setup.ROOT / ".env.compose").read_text().splitlines())
        parsed = urlsplit(app["DATABASE_URL"])
        self.assertEqual(parsed.password, database["APP_DB_PASSWORD"])
        self.assertEqual((parsed.username, parsed.hostname, parsed.path), ("cab_app", "database", "/cab_booking"))
        self.assertNotEqual(database["POSTGRES_PASSWORD"], database["APP_DB_PASSWORD"])
        for secret in [app["JWT_SECRET"], database["POSTGRES_PASSWORD"], database["APP_DB_PASSWORD"]]:
            self.assertGreaterEqual(len(secret), 48)
            self.assertNotIn(secret, output)
        for filename in [".env.database", ".env.compose"]:
            self.assertEqual(stat.S_IMODE((setup.ROOT / filename).stat().st_mode), 0o600)
        self.assertEqual(app["RECEIPT_EMAIL_ENABLED"], "false")
        self.assertEqual(app["COOKIE_SECURE"], "false")

    def test_rerun_preserves_existing_credentials(self):
        self.generate()
        before = {path.name: path.read_bytes() for path in setup.ROOT.iterdir()}
        with self.assertRaises(SystemExit):
            self.generate()
        self.assertEqual(before, {path.name: path.read_bytes() for path in setup.ROOT.iterdir()})

    def test_partial_configuration_and_symlinks_are_never_overwritten(self):
        target = setup.ROOT / "private-existing-file"
        target.write_text("existing private configuration")
        (setup.ROOT / ".env.compose").symlink_to(target)
        with self.assertRaises(SystemExit):
            self.generate()
        self.assertEqual(target.read_text(), "existing private configuration")
        self.assertFalse((setup.ROOT / ".env.database").exists())


if __name__ == "__main__":
    unittest.main()
