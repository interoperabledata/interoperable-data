import json
from typing import Any, Dict
from urllib.parse import urlparse

import requests  # type: ignore

from .errors import RunnerError
from .paths import SCHEMAS_ROOT

_jsonschema_module = None


def _ensure_jsonschema_import() -> Any:
    global _jsonschema_module
    if _jsonschema_module is not None:
        return _jsonschema_module

    try:
        import jsonschema  # type: ignore
    except ImportError:
        raise RunnerError(
            "jsonschema is required for schema validation but is not installed. "
            "Ensure it is listed in requirements.txt and installed."
        )
    _jsonschema_module = jsonschema
    return jsonschema


def _local_path_for_schema_id(schema_id: str):
    """
    Map a schema ID/URL to a local file path under SCHEMAS_ROOT.

    Examples:
      https://interoperabledata.org/schemas/values/Number.simple.1_0.json
        -> <root>/schemas/values/Number.simple.1_0.json
    """
    parsed = urlparse(schema_id)

    if parsed.scheme and parsed.netloc:
        path_part = parsed.path.lstrip("/")  # e.g. "schemas/values/Number.simple.1_0.json"
    else:
        # Treat as plain path-ish string
        path_part = schema_id.lstrip("/")

    # Strip leading "schemas/" if present to avoid schemas/schemas/...
    if path_part.startswith("schemas/"):
        path_part = path_part[len("schemas/") :]

    return SCHEMAS_ROOT / path_part


def _download_schema(schema_id: str, dest_path) -> None:
    """
    Download schema JSON from schema_id URL and store it at dest_path.
    """
    parsed = urlparse(schema_id)
    if not (parsed.scheme and parsed.netloc):
        raise RunnerError(
            f"Schema file not found locally for schema ID '{schema_id}', and "
            f"it is not a valid URL that can be downloaded."
        )

    try:
        resp = requests.get(schema_id, timeout=10)
    except Exception as e:
        raise RunnerError(
            f"Failed to download schema from '{schema_id}': {e}"
        ) from e

    if resp.status_code != 200:
        raise RunnerError(
            f"Failed to download schema from '{schema_id}': HTTP {resp.status_code}"
        )

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        dest_path.write_text(resp.text, encoding="utf-8")
    except Exception as e:
        raise RunnerError(
            f"Downloaded schema from '{schema_id}' but failed to write to '{dest_path}': {e}"
        ) from e


def load_schema_for_id(schema_id: str) -> Dict[str, Any]:
    """
    Resolve a schema ID/URL to a local file.

    Strategy:
      1. Map ID to SCHEMAS_ROOT-relative path.
      2. If file exists -> load.
      3. If not, try to download from the schema_id URL, then load.
    """
    schema_path = _local_path_for_schema_id(schema_id)

    if not schema_path.is_file():
        # Attempt to download and cache
        _download_schema(schema_id, schema_path)

    if not schema_path.is_file():
        # Still missing after download attempt
        raise RunnerError(
            f"Schema file not found for schema ID '{schema_id}': {schema_path}"
        )

    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RunnerError(f"Failed to load schema JSON from {schema_path}: {e}") from e


def validate_json_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> None:
    jsonschema = _ensure_jsonschema_import()
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise RunnerError(f"JSON does not conform to schema: {e.message}") from e
