import json
from dataclasses import dataclass
from typing import Dict

from .errors import RunnerError
from .paths import DATA_FUNCTIONS_ROOT


@dataclass
class FunctionManifest:
    function_name: str
    # Only schema-based ports are tracked here (ports that have a "schema")
    inputs: Dict[str, str]   # port_name -> schema_id
    outputs: Dict[str, str]  # port_name -> schema_id


_manifest_cache: Dict[str, FunctionManifest] = {}


def load_manifest_for_function(function_name: str) -> FunctionManifest:
    if function_name in _manifest_cache:
        return _manifest_cache[function_name]

    function_dir = DATA_FUNCTIONS_ROOT / function_name
    manifest_path = function_dir / "manifest.json"
    if not manifest_path.is_file():
        raise RunnerError(
            f"Manifest not found for function '{function_name}': {manifest_path}"
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RunnerError(
            f"Failed to parse manifest for function '{function_name}': {e}"
        ) from e

    if "in" not in manifest or "out" not in manifest:
        raise RunnerError(
            f"Manifest for function '{function_name}' must contain 'in' and 'out' arrays."
        )

    inputs: Dict[str, str] = {}
    outputs: Dict[str, str] = {}

    def _extract_ports(arr, target: Dict[str, str], which: str) -> None:
        """
        Populate 'target' with schema-based ports: port_name -> schema_id.

        Manifest schema (per your function_manifest.schema.json):

        inputDescriptor:
          oneOf:
            { "name": string, "schema": string }
            { "name": string, "files": [string, ...] }

        outputDescriptor:
          oneOf:
            { "name": string, "schema": string }
            { "name": string, "file": string }
        """
        if not isinstance(arr, list):
            raise RunnerError(
                f"Manifest for function '{function_name}': '{which}' must be an array."
            )

        for port in arr:
            if not isinstance(port, dict):
                raise RunnerError(
                    f"Manifest for function '{function_name}': each entry in '{which}' must be an object."
                )

            name = port.get("name")
            if not isinstance(name, str):
                raise RunnerError(
                    f"Manifest for function '{function_name}': each port in '{which}' "
                    f"must have a string 'name'."
                )

            has_schema = "schema" in port
            has_files = "files" in port
            has_file = "file" in port

            # Enforce the oneOf semantics at a basic level
            if which == "in":
                if has_schema:
                    schema = port["schema"]
                    if not isinstance(schema, str):
                        raise RunnerError(
                            f"Manifest for function '{function_name}': port '{name}' in '{which}' "
                            f"must have 'schema' as a string."
                        )
                    # Only schema-based ports are put into the map
                    target[name] = schema
                elif has_files:
                    files = port["files"]
                    if not isinstance(files, list) or not files or not all(
                        isinstance(x, str) for x in files
                    ):
                        raise RunnerError(
                            f"Manifest for function '{function_name}': port '{name}' in '{which}' "
                            f"must have 'files' as a non-empty array of strings."
                        )
                    # No schema for this port; it's file-based. We don't add it to 'target'.
                else:
                    raise RunnerError(
                        f"Manifest for function '{function_name}': port '{name}' in '{which}' "
                        f"must have either 'schema' or 'files'."
                    )

            elif which == "out":
                if has_schema:
                    schema = port["schema"]
                    if not isinstance(schema, str):
                        raise RunnerError(
                            f"Manifest for function '{function_name}': port '{name}' in '{which}' "
                            f"must have 'schema' as a string."
                        )
                    target[name] = schema
                elif has_file:
                    file_path = port["file"]
                    if not isinstance(file_path, str):
                        raise RunnerError(
                            f"Manifest for function '{function_name}': port '{name}' in '{which}' "
                            f"must have 'file' as a string."
                        )
                    # File-based output; not added to 'target' (no schema).
                else:
                    raise RunnerError(
                        f"Manifest for function '{function_name}': port '{name}' in '{which}' "
                        f"must have either 'schema' or 'file'."
                    )
            else:
                # Should never happen; defensive
                raise RunnerError(
                    f"Internal error: unknown port list '{which}' in manifest loader."
                )

    _extract_ports(manifest["in"], inputs, "in")
    _extract_ports(manifest["out"], outputs, "out")

    fm = FunctionManifest(function_name=function_name, inputs=inputs, outputs=outputs)
    _manifest_cache[function_name] = fm
    return fm
