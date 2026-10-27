from __future__ import annotations

import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from quasar.banner import BANNER, show_banner

ROOT = Path(__file__).resolve().parents[1]


class BannerTests(unittest.TestCase):
    def test_banner_contains_requested_branding_and_links(self):
        self.assertIn("Quasar v1.2.1 | Developed by Th3BlackHol3", BANNER)
        self.assertIn("https://github.com/Th3BlackHol3", BANNER)
        self.assertIn("https://twitter.com/Th3BlackHol3_", BANNER)
        self.assertIn("https://www.linkedin.com/in/th3blackhol3/", BANNER)
        self.assertIn("https://www.facebook.com/Th3BlackHol3", BANNER)

    def test_banner_is_suppressed_for_internal_subprocess_checks(self):
        output = StringIO()
        with patch.dict(os.environ, {"QUASAR_SUPPRESS_BANNER": "1"}), redirect_stdout(output):
            show_banner()
        self.assertEqual(output.getvalue(), "")

    def test_cli_prints_banner_for_version_and_help(self):
        for argument in ("--version", "--help"):
            with self.subTest(argument=argument):
                env = os.environ.copy()
                env.pop("QUASAR_SUPPRESS_BANNER", None)
                result = subprocess.run(
                    [sys.executable, str(ROOT / "quasar.py"), argument],
                    cwd=ROOT, text=True, capture_output=True, check=False, env=env, timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Quasar v1.2.1 | Developed by Th3BlackHol3", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
