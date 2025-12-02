import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from .errors import RunnerError
from .formats import FORMAT_ALIASES, SUPPORTED_FORMATS
from .paths import WORKFLOW_FILE


@dataclass
class RunCommand:
    line_no: int
    raw: str
    function_name: str
    node_name: str


@dataclass
class CopyCommand:
    line_no: int
    raw: str
    src: str
    dest: str
    formats: Optional[List[str]]  # None means "use default (json)"


WorkflowCommand = Tuple[str, Any]  # ("run", RunCommand) or ("copy", CopyCommand)


@dataclass
class Endpoint:
    kind: str  # "folder" or "port"
    folder_name: Optional[str] = None
    node_name: Optional[str] = None
    port_name: Optional[str] = None


def parse_workflow() -> List[WorkflowCommand]:
    if not WORKFLOW_FILE.is_file():
        raise RunnerError(f"workflow.id not found at: {WORKFLOW_FILE}")

    commands: List[WorkflowCommand] = []
    with WORKFLOW_FILE.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            raw_line = line.rstrip("\n")
            stripped = raw_line.strip()

            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            if stripped.startswith("@ui:"):
                break

            if stripped.startswith("run "):
                cmd = _parse_run_line(idx, raw_line)
                commands.append(("run", cmd))
            elif stripped.startswith("copy "):
                cmd = _parse_copy_line(idx, raw_line)
                commands.append(("copy", cmd))
            else:
                raise RunnerError(
                    f"Error on line {idx}: unrecognised command '{raw_line.strip()}'."
                )

    return commands


def _parse_run_line(line_no: int, raw: str) -> RunCommand:
    tokens = raw.strip().split()
    if len(tokens) not in (2, 4) or tokens[0] != "run":
        raise RunnerError(
            f"Error on line {line_no}: invalid run command syntax: '{raw.strip()}'."
        )

    function_name = tokens[1]
    if len(tokens) == 2:
        node_name = function_name
    else:
        if tokens[2] != "as" or len(tokens) != 4:
            raise RunnerError(
                f"Error on line {line_no}: invalid run command syntax: '{raw.strip()}'."
            )
        node_name = tokens[3]

    return RunCommand(
        line_no=line_no,
        raw=raw.strip(),
        function_name=function_name,
        node_name=node_name,
    )


def _parse_copy_line(line_no: int, raw: str) -> CopyCommand:
    stripped = raw.strip()
    if not stripped.startswith("copy "):
        raise RunnerError(
            f"Error on line {line_no}: invalid copy command syntax: '{stripped}'."
        )

    as_split = stripped.split(" as ", 1)
    left = as_split[0]
    formats: Optional[List[str]] = None

    if len(as_split) == 2:
        formats_part = as_split[1].strip()
        if not formats_part:
            raise RunnerError(
                f"Error on line {line_no}: empty format list in copy command."
            )
        raw_formats = [f.strip() for f in formats_part.split(",") if f.strip()]
        if not raw_formats:
            raise RunnerError(
                f"Error on line {line_no}: empty format list in copy command."
            )

        resolved_formats: List[str] = []
        for fmt in raw_formats:
            fmt_lower = fmt.lower()
            fmt_lower = FORMAT_ALIASES.get(fmt_lower, fmt_lower)
            if fmt_lower not in SUPPORTED_FORMATS:
                raise RunnerError(
                    f"Error on line {line_no}: unknown export format '{fmt}'."
                )
            resolved_formats.append(fmt_lower)
        formats = resolved_formats

    m = re.match(r"^copy\s+(.+?)\s+to\s+(.+)$", left)
    if not m:
        raise RunnerError(
            f"Error on line {line_no}: invalid copy command syntax: '{stripped}'."
        )

    src = m.group(1).strip()
    dest = m.group(2).strip()
    if not src or not dest:
        raise RunnerError(
            f"Error on line {line_no}: invalid copy command syntax: '{stripped}'."
        )

    return CopyCommand(
        line_no=line_no,
        raw=stripped,
        src=src,
        dest=dest,
        formats=formats,
    )


def parse_endpoint(endpoint: str) -> Endpoint:
    """
    Folder endpoint: "Z"
    Port endpoint: "Node.Port"
    """
    if "." in endpoint:
        node_name, port_name = endpoint.split(".", 1)
        node_name = node_name.strip()
        port_name = port_name.strip()
        if not node_name or not port_name:
            raise RunnerError(f"Invalid endpoint '{endpoint}'.")
        return Endpoint(kind="port", node_name=node_name, port_name=port_name)
    else:
        folder_name = endpoint.strip()
        if not folder_name:
            raise RunnerError(f"Invalid endpoint '{endpoint}'.")
        return Endpoint(kind="folder", folder_name=folder_name)
