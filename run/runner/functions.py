import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple

from .errors import RunnerError, print_info
from .manifests import load_manifest_for_function
from .paths import FUNCTIONS_ROOT, SCHEMAS_ROOT


def ensure_function_dependencies(function_name: str) -> None:
    function_dir = FUNCTIONS_ROOT / function_name
    if not function_dir.is_dir():
        raise RunnerError(
            f"Data function directory not found for '{function_name}': {function_dir}"
        )

    req_path = function_dir / "requirements.txt"
    sentinel = function_dir / ".deps_installed"

    if req_path.is_file() and not sentinel.exists():
        print_info(f"Installing dependencies for data function '{function_name}'...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req_path)],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RunnerError(
                f"Failed to install dependencies for data function '{function_name}': {e}"
            ) from e
        try:
            sentinel.write_text("ok", encoding="utf-8")
        except Exception:
            # Not fatal; deps are installed.
            pass


def ensure_node_io_dirs(node_name: str) -> Tuple[Path, Path]:
    node_dir = FUNCTIONS_ROOT / node_name
    inputs_dir = node_dir / "inputs"
    outputs_dir = node_dir / "outputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    return inputs_dir, outputs_dir


def run_function(function_name: str, node_name: str) -> None:
    function_dir = FUNCTIONS_ROOT / function_name
    main_py = function_dir / "main.py"
    if not main_py.is_file():
        raise RunnerError(
            f"main.py not found for data function '{function_name}': {main_py}"
        )

    # Preload manifest to fail fast if it's malformed
    load_manifest_for_function(function_name)
    ensure_function_dependencies(function_name)
    inputs_dir, outputs_dir = ensure_node_io_dirs(node_name)

    env = os.environ.copy()
    env["IDM_FUNCTION_NAME"] = function_name
    env["IDM_NODE_NAME"] = node_name
    env["IDM_INPUTS_DIR"] = str(inputs_dir.resolve())
    env["IDM_OUTPUTS_DIR"] = str(outputs_dir.resolve())
    env["IDM_SCHEMA_ROOT"] = str(SCHEMAS_ROOT.resolve())

    cmd = [
        sys.executable,
        str(main_py),
        "--function-name",
        function_name,
        "--node-name",
        node_name,
        "--inputs-dir",
        str(inputs_dir),
        "--outputs-dir",
        str(outputs_dir),
    ]

    print_info(f"Running data function '{function_name}' as node '{node_name}'...")
    try:
        result = subprocess.run(cmd, env=env)
    except Exception as e:
        raise RunnerError(
            f"Error running data function '{function_name}' as node '{node_name}': {e}"
        ) from e

    if result.returncode != 0:
        raise RunnerError(
            f"Error running data function '{function_name}': "
            f"exit code {result.returncode}."
        )
