import argparse
from typing import Dict, List, Optional

from .functions import run_function
from .env_utils import ensure_core_dependencies, load_dotenv_if_present
from .errors import RunnerError, print_error, print_info
from .fs_utils import clear_directory_contents
from .paths import FUNCTIONS_ROOT
from .copy_ops import execute_copy
from .workflow import WorkflowCommand, parse_workflow


def clean_generated() -> None:
    if not FUNCTIONS_ROOT.is_dir():
        print_info("No functions/ directory found; nothing to clean.")
        return

    print_info("Cleaning generated inputs/outputs under functions/...")

    for entry in FUNCTIONS_ROOT.iterdir():
        if not entry.is_dir():
            continue
        inputs_dir = entry / "inputs"
        outputs_dir = entry / "outputs"

        for d in (inputs_dir, outputs_dir):
            if d.is_dir():
                clear_directory_contents(d)

    print_info("Clean complete.")


def execute_workflow(commands: List[WorkflowCommand]) -> None:
    node_to_functions: Dict[str, str] = {}

    for kind, cmd in commands:
        if kind == "run":
            functions_name = cmd.function_name
            node_name = cmd.node_name
            node_to_functions[node_name] = functions_name
            run_function(functions_name, node_name)

        elif kind == "copy":
            execute_copy(cmd, node_to_functions)

        else:
            raise RunnerError(f"Internal error: unknown command kind '{kind}'.")

    print_info("Workflow completed successfully.")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Interoperable Data Runner (run.py)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove generated function inputs/outputs and exit.",
    )
    args = parser.parse_args(argv)

    try:
        load_dotenv_if_present()
    except RunnerError as e:
        print_error(str(e))
        return 1

    if args.clean:
        try:
            clean_generated()
            return 0
        except RunnerError as e:
            print_error(str(e))
            return 1

    try:
        ensure_core_dependencies()
        commands = parse_workflow()
        execute_workflow(commands)
    except RunnerError as e:
        print_error(str(e))
        return 1
    except KeyboardInterrupt:
        print_error("Interrupted by user.")
        return 1

    return 0
