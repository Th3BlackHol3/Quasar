"""Quasar terminal branding banner."""
from __future__ import annotations

import os
import sys
from typing import TextIO

BANNER = r"""
_░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░ ░▒▓███████▓▒░░▒▓██████▓▒░░▒▓███████▓▒░  
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░░▒▓██████▓▒░░▒▓████████▓▒░▒▓███████▓▒░  
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
 ░▒▓██████▓▒░ ░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
   ░▒▓█▓▒░                                                                      
    ░▒▓██▓▒░ Quasar v1.2.1 | Developed by Th3BlackHol3
    
https://github.com/Th3BlackHol3
https://twitter.com/Th3BlackHol3_
https://www.linkedin.com/in/th3blackhol3/
https://www.facebook.com/Th3BlackHol3
"""


def show_banner(stream: TextIO | None = None) -> None:
    """Print the branding banner once per user-facing program startup.

    Set QUASAR_SUPPRESS_BANNER=1 only for internal subprocess smoke checks.
    Unsupported console encodings are handled with replacement characters so
    older Windows terminals do not crash before the CLI starts.
    """
    if os.environ.get("QUASAR_SUPPRESS_BANNER", "").strip().lower() in {"1", "true", "yes"}:
        return

    target = stream or sys.stdout
    rendered = BANNER + "\n"
    try:
        target.write(rendered)
    except UnicodeEncodeError:
        encoding = getattr(target, "encoding", None) or "utf-8"
        target.write(rendered.encode(encoding, errors="replace").decode(encoding, errors="replace"))
    target.flush()
