from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from quasar.core.normalization import extract_alive_urls, extract_scoped_hostnames, in_scope, sorted_unique_hostnames
from quasar.core.targets import TargetValidationError, load_targets, normalize_domain
from quasar.core.process_runner import prepare_command, run_process
from quasar.core.reporting import create_assessment_dir
from quasar.modules import httpx as httpx_adapter, knockpy as knockpy_adapter, subfinder
from quasar.modules.registry import BY_KEY


class TargetValidationTests(unittest.TestCase):
    def test_normalizes_case_and_trailing_dot(self):
        self.assertEqual(normalize_domain("  Example.COM. "), "example.com")

    def test_idna_normalization(self):
        self.assertEqual(normalize_domain("bücher.example"), "xn--bcher-kva.example")

    def test_rejects_url_and_port(self):
        for value in ("https://example.com", "example.com:443", "*.example.com", "example.com/path", "bad domain.com"):
            with self.subTest(value=value):
                with self.assertRaises(TargetValidationError):
                    normalize_domain(value)

    def test_list_deduplicates_and_tracks_invalid_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "domains.txt"
            path.write_text("# comment\nExample.com\nexample.com.\nbad target\nexample.org\n", encoding="utf-8")
            targets, rejected = load_targets(list_path=path)
        self.assertEqual(targets, ["example.com", "example.org"])
        self.assertEqual(len(rejected), 1)


class NormalizationTests(unittest.TestCase):
    def test_scope_uses_label_boundary(self):
        self.assertTrue(in_scope("api.example.com", "example.com"))
        self.assertFalse(in_scope("notexample.com", "example.com"))
        self.assertFalse(in_scope("example.org", "example.com"))

    def test_extracts_only_scoped_candidates(self):
        text = "api.example.com\nhttps://WWW.Example.com/path [200]\nnotexample.com\nexample.org\n*.wild.example.com\nexample.com"
        self.assertEqual(
            extract_scoped_hostnames(text, "example.com"),
            {"api.example.com", "www.example.com", "wild.example.com"},
        )
        self.assertIn("example.com", extract_scoped_hostnames(text, "example.com", include_apex=True))

    def test_sorted_unique_is_deterministic(self):
        self.assertEqual(sorted_unique_hostnames(["z.example.com", "a.example.com", "a.example.com"]),
                         ["a.example.com", "z.example.com"])

    def test_httpx_url_parser_strips_status_decorations_and_scope_filters(self):
        output = "https://api.example.com [200]\nhttp://www.example.com\nhttps://notexample.com [200]\ninvalid output"
        self.assertEqual(extract_alive_urls(output, "example.com"),
                         ["http://www.example.com", "https://api.example.com"])


class ProcessAndAdapterTests(unittest.TestCase):
    def test_assessment_results_directory_is_absolute_even_when_root_is_relative(self):
        import os
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                _, assessment_dir = create_assessment_dir("results")
                self.assertTrue(assessment_dir.is_absolute())
                self.assertTrue((assessment_dir / "sample.txt").parent.is_absolute())
            finally:
                os.chdir(original_cwd)

    def test_runner_uses_argument_list_and_captures_output(self):
        import sys
        result = run_process([sys.executable, "-c", "print('safe')"], timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "safe")
        self.assertFalse(result.timed_out)

    def test_windows_python_launcher_is_invoked_without_shell(self):
        command = prepare_command(
            [r"C:\Quasar\bin\sublist3r.py", "-d", "example.com"],
            system_name="Windows", python_executable=r"C:\Python311\python.exe",
        )
        self.assertEqual(command, [r"C:\Python311\python.exe", r"C:\Quasar\bin\sublist3r.py", "-d", "example.com"])

    def test_subfinder_command_keeps_domain_as_single_argument(self):
        cmd = subfinder.build_command("/bin/subfinder", "example.com", Path("raw"), Path("out"), {})
        self.assertEqual(cmd[0], "/bin/subfinder")
        self.assertIn("example.com", cmd)
        self.assertNotIn("shell=True", cmd)

    def test_httpx_command_targets_input_file_and_writes_explicit_output(self):
        cmd = httpx_adapter.build_command("/go/bin/httpx", Path("hosts.txt"), {}, Path("httpx-results.txt"))
        self.assertIn("-l", cmd)
        self.assertIn("hosts.txt", cmd)
        self.assertIn("-no-fallback", cmd)
        self.assertIn("-o", cmd)
        self.assertIn("httpx-results.txt", cmd)
        self.assertIn("-disable-update-check", cmd)
        self.assertEqual(cmd[0], "/go/bin/httpx")

    def test_knockpy_uses_official_recon_json_cli(self):
        cmd = knockpy_adapter.build_command("/user/bin/knockpy", "example.com", Path("raw"), Path("artifacts"), {})
        self.assertEqual(cmd, ["/user/bin/knockpy", "-d", "example.com", "--recon", "--json"])

    def test_knockpy_install_recipe_uses_official_repository_not_pypi_name(self):
        spec = BY_KEY["knockpy"]
        self.assertEqual(spec.installer_kind, "pipx-git")
        self.assertIn("github.com/guelfoweb/knockpy.git", spec.installer_command[0])

    def test_httpx_registry_uses_projectdiscovery_source(self):
        spec = BY_KEY["httpx"]
        self.assertEqual(spec.installer_kind, "go")
        self.assertIn("github.com/projectdiscovery/httpx/cmd/httpx", spec.installer_command[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
