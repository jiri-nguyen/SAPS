import shutil
import subprocess
from pathlib import Path


def test_import_contracts_hold() -> None:
    """ADR-0001: domain and application must not import adapters or frameworks."""
    executable = shutil.which("lint-imports")
    assert executable is not None, "import-linter is not installed"
    result = subprocess.run(  # noqa: S603
        [executable], cwd=Path(__file__).parents[2], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
