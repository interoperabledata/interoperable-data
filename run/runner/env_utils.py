import os
import subprocess
import sys
from pathlib import Path

from .errors import RunnerError, print_error, print_info
from .paths import CORE_REQUIREMENTS, WORKFLOW_ROOT


def load_dotenv_if_present() -> None:
    """
    Minimal .env loader:
    - Ignores blank lines and lines starting with '#'
    - Parses KEY=VALUE (first '=' only)
    - Does not try to be fully compatible with all dotenv edge cases.
    """
    env_path: Path = WORKFLOW_ROOT / ".env"
    if not env_path.is_file():
        return

    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception as e:
        raise RunnerError(f"Failed to load .env: {e}") from e


def ensure_core_dependencies() -> None:
    """
    Ensure workflow-level dependencies are installed via requirements.txt.
    This is intentionally simple: it runs pip install if requirements.txt exists.
    """
    if not CORE_REQUIREMENTS.is_file():
        return

    print_info("Ensuring core dependencies from requirements.txt...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(CORE_REQUIREMENTS)],
            check=False,
        )
    except Exception as e:
        print_error(f"Warning: failed to install core requirements: {e}")
