#!/usr/bin/env python3
"""
Run

- Reads workflow.id
- Supports two commands: COPY and RUN
- Manages per-app virtualenvs under .envs/
- Loads global .env at repo root and passes env vars to all apps
- Channels are mapped to folders:
    root.in   -> ./inputs
    root.out  -> ./outputs
    App.in    -> ./apps/<App>/inputs
    App.out   -> ./apps/<App>/outputs
"""

import os
import sys
import re
import json
import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Optional


# ------------- config / constants -------------

CHANNEL_PATTERN = re.compile(r"^([A-Za-z0-9_-]+)\.(in|out)$")
COPY_PATTERN = re.compile(r"^COPY\s+([A-Za-z0-9_.-]+)\s*->\s*([A-Za-z0-9_.-]+)\s*$")
RUN_PATTERN = re.compile(r"^RUN\s+([A-Za-z0-9_-]+)\s*$")

ENV_DIR_NAME = ".envs"
WORKFLOW_FILE = "workflow.id"
GLOBAL_ENV_FILE = ".env"


# ------------- small helpers -------------

def log(msg: str) -> None:
    print(f"[RUN] {msg}")


def warn(msg: str) -> None:
    print(f"[RUN:WARN] {msg}", file=sys.stderr)


def error(msg: str) -> None:
    print(f"[RUN:ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def load_dotenv(env_path: Path) -> None:
    """Very simple .env loader: KEY=VALUE, ignores comments and blank lines."""
    if not env_path.is_file():
        return
    log(f"Loading environment from {env_path}")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ[key.strip()] = value.strip()


# ------------- channel mapping -------------

class Channel:
    """Logical channel -> backing directory mapping."""

    def __init__(self, owner: str, port: str):
        self.owner = owner
        self.port = port

    @classmethod
    def parse(cls, ref: str) -> "Channel":
        m = CHANNEL_PATTERN.match(ref)
        if not m:
            raise ValueError(f"Invalid channel reference: {ref!r}")
        owner, port = m.group(1), m.group(2)
        return cls(owner, port)

    def path(self, root: Path) -> Path:
        """Map logical channel to real directory path."""
        if self.owner == "root":
            if self.port == "in":
                return root / "inputs"
            else:
                return root / "outputs"
        else:
            app_dir = root / "apps" / self.owner
            if self.port == "in":
                return app_dir / "inputs"
            else:
                return app_dir / "outputs"

    def __repr__(self) -> str:
        return f"{self.owner}.{self.port}"


# ------------- workflow parsing -------------

class WorkflowStep:
    pass


class CopyStep(WorkflowStep):
    def __init__(self, src: Channel, dst: Channel):
        self.src = src
        self.dst = dst

    def __repr__(self) -> str:
        return f"COPY {self.src} -> {self.dst}"


class RunStep(WorkflowStep):
    def __init__(self, app_name: str):
        self.app_name = app_name

    def __repr__(self) -> str:
        return f"RUN {self.app_name}"


def parse_workflow(path: Path) -> List[WorkflowStep]:
    if not path.is_file():
        error(f"Workflow file not found: {path}")

    steps: List[WorkflowStep] = []
    lines = path.read_text(encoding="utf-8").splitlines()

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue

        copy_match = COPY_PATTERN.match(line)
        if copy_match:
            src_ref, dst_ref = copy_match.group(1), copy_match.group(2)
            try:
                src = Channel.parse(src_ref)
                dst = Channel.parse(dst_ref)
            except ValueError as e:
                error(f"{path}:{idx}: {e}")
            steps.append(CopyStep(src, dst))
            continue

        run_match = RUN_PATTERN.match(line)
        if run_match:
            app_name = run_match.group(1)
            steps.append(RunStep(app_name))
            continue

        error(f"{path}:{idx}: Unrecognised command: {raw_line!r}")

    return steps


# ------------- filesystem ops -------------

def safe_clear_dir(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_dir_contents(src: Path, dst: Path) -> None:
    """Copy contents of src into dst, replacing dst entirely."""
    # Treat missing src as empty
    if not src.exists():
        log(f"Source channel dir {src} does not exist; target {dst} will be empty.")
        safe_clear_dir(dst)
        return

    if not src.is_dir():
        error(f"Source channel path is not a directory: {src}")

    safe_clear_dir(dst)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


# ------------- per-app venv management -------------

def compute_requirements_hash(req_path: Path) -> Optional[str]:
    if not req_path.is_file():
        return None
    h = hashlib.sha256()
    h.update(req_path.read_bytes())
    return h.hexdigest()


def get_venv_paths(root: Path, app_name: str) -> Dict[str, Path]:
    env_root = root / ENV_DIR_NAME / app_name
    if os.name == "nt":
        python_path = env_root / "Scripts" / "python.exe"
        pip_path = env_root / "Scripts" / "pip.exe"
    else:
        python_path = env_root / "bin" / "python"
        pip_path = env_root / "bin" / "pip"
    return {
        "env_root": env_root,
        "python": python_path,
        "pip": pip_path,
        "hash_file": env_root / ".requirements.hash",
    }


def ensure_app_env(root: Path, app_name: str, app_dir: Path) -> Path:
    """Ensure virtualenv for app exists and requirements are installed. Returns python path."""
    req_path = app_dir / "requirements.txt"
    venv_paths = get_venv_paths(root, app_name)
    env_root = venv_paths["env_root"]
    python_exe = venv_paths["python"]
    pip_exe = venv_paths["pip"]
    hash_file = venv_paths["hash_file"]

    current_hash = compute_requirements_hash(req_path)
    existing_hash = hash_file.read_text(encoding="utf-8").strip() if hash_file.is_file() else None

    needs_rebuild = False

    if not env_root.is_dir():
        needs_rebuild = True
    elif current_hash != existing_hash:
        needs_rebuild = True

    if needs_rebuild:
        if env_root.is_dir():
            log(f"Rebuilding virtualenv for app {app_name} (requirements changed).")
            shutil.rmtree(env_root)
        else:
            log(f"Creating virtualenv for app {app_name}.")

        # Create venv
        subprocess.run(
            [sys.executable, "-m", "venv", str(env_root)],
            check=True,
        )

        # Install requirements if present
        if current_hash is not None:
            log(f"Installing requirements for app {app_name}.")
            subprocess.run(
                [str(pip_exe), "install", "-r", str(req_path)],
                check=True,
            )
            hash_file.write_text(current_hash, encoding="utf-8")
        else:
            # No requirements.txt; clear any previous hash
            if hash_file.exists():
                hash_file.unlink()

    if not python_exe.is_file():
        error(f"Python executable not found in virtualenv for app {app_name}: {python_exe}")

    return python_exe


# ------------- app execution -------------

def run_app(root: Path, app_name: str) -> None:
    app_dir = root / "apps" / app_name
    if not app_dir.is_dir():
        error(f"App directory not found: {app_dir}")

    main_py = app_dir / "main.py"
    manifest = app_dir / "manifest.json"

    if not main_py.is_file():
        error(f"App {app_name} missing main.py")
    if not manifest.is_file():
        warn(f"App {app_name} missing manifest.json (continuing, but this is not ideal).")
    else:
        # Basic sanity check manifest is valid JSON
        try:
            json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            error(f"Invalid manifest.json for app {app_name}: {e}")

    # Ensure inputs/outputs dirs exist
    (app_dir / "inputs").mkdir(parents=True, exist_ok=True)
    (app_dir / "outputs").mkdir(parents=True, exist_ok=True)

    python_exe = ensure_app_env(root, app_name, app_dir)

    # Inherit current env (including global .env vars)
    env = os.environ.copy()
    env["RUN_APP_NAME"] = app_name
    env["RUN_ROOT"] = str(root)

    log(f"Running app {app_name} with {python_exe}")
    result = subprocess.run(
        [str(python_exe), str(main_py)],
        cwd=str(app_dir),
        env=env,
    )

    if result.returncode != 0:
        error(f"App {app_name} failed with exit code {result.returncode}")


# ------------- main flow -------------

def execute_workflow(root: Path, steps: List[WorkflowStep]) -> None:
    # Ensure base input/output dirs exist
    (root / "inputs").mkdir(parents=True, exist_ok=True)
    (root / "outputs").mkdir(parents=True, exist_ok=True)

    for step in steps:
        if isinstance(step, CopyStep):
            src_path = step.src.path(root)
            dst_path = step.dst.path(root)
            log(f"{step}: {src_path} -> {dst_path}")
            copy_dir_contents(src_path, dst_path)
        elif isinstance(step, RunStep):
            log(f"{step}")
            run_app(root, step.app_name)
        else:
            error(f"Unknown workflow step type: {step}")


def main(argv: List[str]) -> None:
    # Root directory is where this script lives, unless overridden
    if len(argv) > 1:
        root = Path(argv[1]).resolve()
    else:
        root = Path(__file__).resolve().parent

    log(f"Run starting in root: {root}")

    # Load global .env if present
    load_dotenv(root / GLOBAL_ENV_FILE)

    # Parse workflow
    workflow_path = root / WORKFLOW_FILE
    steps = parse_workflow(workflow_path)

    # Execute
    execute_workflow(root, steps)

    log("Run completed.")


if __name__ == "__main__":
    main(sys.argv)
