"""Optional fast pre-scan of a CSV file using the Go `fastscan` binary.

This is a pure speed/UX enhancement: if the binary isn't found (e.g. a
plain `pip install` without the Go toolchain, or a dev machine that hasn't
built it), analysis still works fine without it.
"""
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

_BUNDLED_BIN = Path(__file__).resolve().parent.parent / "bin" / "fastscan"


def _find_binary() -> Optional[str]:
    from_path = shutil.which("fastscan")
    if from_path:
        return from_path
    if _BUNDLED_BIN.exists():
        return str(_BUNDLED_BIN)
    return None


def quick_scan(csv_path: str) -> Optional[dict]:
    """Runs fastscan against csv_path, returning its JSON result or None."""
    binary = _find_binary()
    if not binary:
        return None

    try:
        proc = subprocess.run(
            [binary, csv_path],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return json.loads(proc.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return None
