import json
from typing import Any, Dict

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


def load_schema_for_id(schema_id: str) -> Dict[str, Any]:
    """
    Resolve a schema ID/URL to ./schemas/<path-from-url>.
    """
    if "://" in schema_id:
        _, after_scheme = schema_id.split("://", 1)
        if "/" in after_scheme:
            _, path_part = after_scheme.split("/", 1)
        else:
            path_part = ""
    else:
        path_part = schema_id.lstrip("/")

    schema_path = SCHEMAS_ROOT / path_part
    if not schema_path.is_file():
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
