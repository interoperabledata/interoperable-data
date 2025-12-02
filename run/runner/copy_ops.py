import json
import os
from pathlib import Path
from typing import Any, Dict, List

from .functions import ensure_node_io_dirs
from .errors import RunnerError, print_info
from .exporters import export_csv, export_json, export_xlsx
from .fs_utils import clear_directory_contents, list_files_in_dir
from .manifests import load_manifest_for_function
from .paths import FUNCTIONS_ROOT, WORKFLOW_ROOT
from .schema_utils import load_schema_for_id, validate_json_against_schema
from .workflow import CopyCommand, Endpoint, parse_endpoint


def convert_file_to_schema(
    source_path: Path,
    schema_id: str,
    dest_path: Path,
) -> None:
    """
    Delegate conversion to converters.convert_to_schema, as per contract.
    """
    if "OPENAI_API_KEY" not in os.environ or not os.environ["OPENAI_API_KEY"]:
        raise RunnerError(
            "OPENAI_API_KEY is required for file→schema conversion but is not set."
        )

    try:
        from converters import convert_to_schema  # type: ignore
    except ImportError:
        raise RunnerError(
            "Conversion helper module 'converters' not found. "
            "It must provide convert_to_schema(source_path, schema_id, dest_path, env)."
        )

    env = os.environ.copy()

    try:
        convert_to_schema(
            source_path=source_path,
            schema_id=schema_id,
            dest_path=dest_path,
            env=env,
        )
    except Exception as e:
        raise RunnerError(
            f"Conversion failed for file '{source_path.name}': {e}"
        ) from e

    try:
        schema = load_schema_for_id(schema_id)
        data = json.loads(dest_path.read_text(encoding="utf-8"))
        validate_json_against_schema(data, schema)
    except RunnerError:
        raise
    except Exception as e:
        raise RunnerError(
            f"Converted file '{dest_path.name}' is not valid JSON or failed schema validation: {e}"
        ) from e


def _ensure_node_registered(
    cmd: CopyCommand,
    node_name: str,
    node_to_function: Dict[str, str],
) -> None:
    """
    Ensure node_name is known in node_to_function.
    If not, try to infer function_name == node_name and validate by checking manifest.
    """
    if node_name in node_to_function:
        return

    function_name = node_name
    function_dir = FUNCTIONS_ROOT / function_name
    manifest_path = function_dir / "manifest.json"

    if not manifest_path.is_file():
        # No matching function folder/manifest → real unknown node
        raise RunnerError(
            f"Error on line {cmd.line_no}: unknown node '{node_name}' in '{cmd.raw}'."
        )

    # Will raise RunnerError if manifest is malformed
    load_manifest_for_function(function_name)

    node_to_function[node_name] = function_name


def _resolve_src_dir_for_endpoint(
    cmd: CopyCommand,
    endpoint: Endpoint,
    node_to_function: Dict[str, str],
) -> Path:
    if endpoint.kind == "folder":
        return WORKFLOW_ROOT / "inputs" / endpoint.folder_name  # type: ignore

    src_node = endpoint.node_name  # type: ignore
    src_port = endpoint.port_name  # type: ignore

    _ensure_node_registered(cmd, src_node, node_to_function)

    return FUNCTIONS_ROOT / src_node / "outputs" / src_port


def copy_to_function_input(
    cmd: CopyCommand,
    src_endpoint: Endpoint,
    dest_endpoint: Endpoint,
    node_to_function: Dict[str, str],
) -> None:
    assert dest_endpoint.kind == "port"
    node_name = dest_endpoint.node_name  # type: ignore
    port_name = dest_endpoint.port_name  # type: ignore

    _ensure_node_registered(cmd, node_name, node_to_function)

    function_name = node_to_function[node_name]
    manifest = load_manifest_for_function(function_name)

    if port_name not in manifest.inputs:
        raise RunnerError(
            f"Error on line {cmd.line_no}: port '{node_name}.{port_name}' does not exist."
        )

    schema_id = manifest.inputs[port_name]
    src_dir = _resolve_src_dir_for_endpoint(cmd, src_endpoint, node_to_function)
    files = list_files_in_dir(src_dir)

    node_inputs_base, _ = ensure_node_io_dirs(node_name)
    dest_dir = node_inputs_base / port_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    clear_directory_contents(dest_dir)

    if not files:
        print_info(
            f"Copy (schema-aware) produced empty input for {node_name}.{port_name} "
            f"from {src_dir}."
        )
        return

    schema = load_schema_for_id(schema_id)

    for src_file in files:
        dest_file = dest_dir / src_file.name
        needs_conversion = True

        if src_file.suffix.lower() == ".json":
            try:
                raw = src_file.read_text(encoding="utf-8")
                data: Any = json.loads(raw)
                validate_json_against_schema(data, schema)
                dest_file.write_text(raw, encoding="utf-8")
                needs_conversion = False
            except RunnerError:
                needs_conversion = True
            except Exception:
                needs_conversion = True

        if needs_conversion:
            convert_file_to_schema(src_file, schema_id, dest_file)


def copy_to_folder(
    cmd: CopyCommand,
    src_endpoint: Endpoint,
    dest_endpoint: Endpoint,
    node_to_function: Dict[str, str],
) -> None:
    assert dest_endpoint.kind == "folder"
    folder_name = dest_endpoint.folder_name  # type: ignore

    src_dir = _resolve_src_dir_for_endpoint(cmd, src_endpoint, node_to_function)
    files = list_files_in_dir(src_dir)

    formats = ["json"] if cmd.formats is None else cmd.formats

    for fmt in formats:
        if fmt == "json":
            export_json(cmd.line_no, src_dir, files, folder_name)
        elif fmt == "csv":
            export_csv(cmd.line_no, src_dir, files, folder_name)
        elif fmt == "xlsx":
            export_xlsx(cmd.line_no, src_dir, files, folder_name)
        else:
            raise RunnerError(
                f"Error on line {cmd.line_no}: unsupported export format '{fmt}'."
            )


def execute_copy(
    cmd: CopyCommand,
    node_to_function: Dict[str, str],
) -> None:
    src_endpoint = parse_endpoint(cmd.src)
    dest_endpoint = parse_endpoint(cmd.dest)

    if dest_endpoint.kind == "port":
        if cmd.formats is not None:
            raise RunnerError(
                f"Error on line {cmd.line_no}: cannot use 'as <format>' "
                f"when destination is a function input: '{cmd.raw}'."
            )
        copy_to_function_input(cmd, src_endpoint, dest_endpoint, node_to_function)
    else:
        copy_to_folder(cmd, src_endpoint, dest_endpoint, node_to_function)
