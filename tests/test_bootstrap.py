from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bootstrap import _requirements_have_packages, venv_python
from quasar.core.dependencies import DependencyManager, quasar_data_dir
from quasar.core.process_runner import ProcessResult
from quasar.modules.registry import BY_KEY


class BootstrapTests(unittest.TestCase):
    def test_venv_python_path_for_posix_platforms(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / ".venv"
            self.assertEqual(venv_python(root, "Linux"), root / "bin" / "python")
            self.assertEqual(venv_python(root, "Darwin"), root / "bin" / "python")

    def test_venv_python_path_for_windows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / ".venv"
            self.assertEqual(venv_python(root, "Windows"), root / "Scripts" / "python.exe")

    def test_empty_requirements_does_not_require_package_install(self):
        with tempfile.TemporaryDirectory() as temp:
            req = Path(temp) / "requirements.txt"
            req.write_text("# standard library only\n\n  # no packages\n", encoding="utf-8")
            self.assertFalse(_requirements_have_packages(req))
            req.write_text("requests>=2\n", encoding="utf-8")
            self.assertTrue(_requirements_have_packages(req))

    def test_quasar_data_directory_is_named_for_application(self):
        self.assertEqual(quasar_data_dir().name.lower(), "quasar")

    def test_httpx_probe_accepts_current_projectdiscovery_version_banner(self):
        manager = DependencyManager()
        def fake_run(command, timeout=10, cwd=None):
            return ProcessResult(list(command), 0, "[INF] Current httpx version v1.10.0 (latest)", "", 0.01)
        with patch("quasar.core.dependencies.run_process", side_effect=fake_run):
            okay, detail = manager._probe(Path("/fake/httpx"), BY_KEY["httpx"])
        self.assertTrue(okay)
        self.assertIn("httpx", detail.lower())

    def test_httpx_probe_rejects_python_httpx_cli(self):
        manager = DependencyManager()
        def fake_run(command, timeout=10, cwd=None):
            return ProcessResult(list(command), 0, "Usage: httpx [OPTIONS] URL\nPython HTTPX client", "", 0.01)
        with patch("quasar.core.dependencies.run_process", side_effect=fake_run):
            okay, _ = manager._probe(Path("/fake/httpx"), BY_KEY["httpx"])
        self.assertFalse(okay)

    def test_knockpy_probe_requires_security_tool_identity(self):
        manager = DependencyManager()
        def wrong_cli(command, timeout=10, cwd=None):
            return ProcessResult(list(command), 0, "knockpy variable selection package", "", 0.01)
        with patch("quasar.core.dependencies.run_process", side_effect=wrong_cli):
            okay, _ = manager._probe(Path("/fake/knockpy"), BY_KEY["knockpy"])
        self.assertFalse(okay)

    def test_knockpy_vcs_installer_force_replaces_unverified_same_name(self):
        manager = DependencyManager()
        from types import SimpleNamespace
        fake_result = ProcessResult(["pipx"], 0, "installed", "", 0.01)
        with patch.object(manager, "_pipx_prefix", return_value=(["pipx"], None)), \
             patch("quasar.core.dependencies.run_process", return_value=fake_result) as run, \
             patch.object(manager, "_refresh_paths"):
            result = manager._run_installer(BY_KEY["knockpy"])
        self.assertEqual(result["status"], "installer_completed")
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[:3], ["pipx", "install", "--force"])
        self.assertIn("github.com/guelfoweb/knockpy.git", cmd[-1])

    def test_knockpy_probe_accepts_official_help_flags(self):
        manager = DependencyManager()
        def official_cli(command, timeout=10, cwd=None):
            return ProcessResult(list(command), 0, "usage: knockpy [-h] [-d DOMAIN] [--recon] [--bruteforce]", "", 0.01)
        with patch("quasar.core.dependencies.run_process", side_effect=official_cli):
            okay, detail = manager._probe(Path("/fake/knockpy"), BY_KEY["knockpy"])
        self.assertTrue(okay)
        self.assertIn("knockpy", detail.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
