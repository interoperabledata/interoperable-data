import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .errors import RunnerError, print_info
from .fs_utils import clear_directory_contents, list_files_in_dir
from .paths import WORKFLOW_ROOT


def ensure_outputs_subdir(folder_name: str, fmt: str) -> Path:
    base = WORKFLOW_ROOT / "outputs" / folder_name / fmt
    base.mkdir(parents=True, exist_ok=True)
    clear_directory_contents(base)
    return base


def iter_tabular_rows(src_dir: Path, files: List[Path]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Load all .json files as tabular data (flattened) and return (columns, rows).
    - Accepts top-level array or single object.
    - Uses dot-notation for nested keys.
    """
    rows: List[Dict[str, Any]] = []

    def flatten(prefix: str, obj: Any, out: Dict[str, Any]) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = f"{prefix}.{k}" if prefix else k
                flatten(key, v, out)
        else:
            out[prefix] = obj

    for f in files:
        if f.suffix.lower() != ".json":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            raise RunnerError(
                f"File '{f}' is not valid JSON for tabular export: {e}"
            ) from e

        iterable = data if isinstance(data, list) else [data]

        for obj in iterable:
            if not isinstance(obj, dict):
                raise RunnerError(
                    f"File '{f}' contains a non-object row during tabular export."
                )
            flat: Dict[str, Any] = {}
            flatten("", obj, flat)
            rows.append(flat)

    cols_set = set()
    for r in rows:
        cols_set.update(r.keys())
    columns = sorted(cols_set)
    return columns, rows


def export_json(line_no: int, src_dir: Path, files: List[Path], folder_name: str) -> None:
    import shutil

    dest_dir = ensure_outputs_subdir(folder_name, "json")
    if not files:
        print_info(
            f"Copy (json) created empty outputs/{folder_name}/json/ from {src_dir}."
        )
        return

    for f in files:
        dest_file = dest_dir / f.name
        try:
            shutil.copy2(f, dest_file)
        except Exception as e:
            raise RunnerError(
                f"Error on line {line_no}: failed to copy '{f}' to '{dest_file}': {e}"
            ) from e


def export_csv(line_no: int, src_dir: Path, files: List[Path], folder_name: str) -> None:
    import csv

    dest_dir = ensure_outputs_subdir(folder_name, "csv")
    dest_file = dest_dir / "data.csv"

    columns, rows = iter_tabular_rows(src_dir, files)
    if not columns:
        dest_file.write_text("", encoding="utf-8")
        print_info(
            f"Copy (csv) produced empty table for outputs/{folder_name}/csv/data.csv."
        )
        return

    try:
        with dest_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                writer.writerow({col: row.get(col, "") for col in columns})
    except Exception as e:
        raise RunnerError(
            f"Error on line {line_no}: failed to write CSV '{dest_file}': {e}"
        ) from e


def export_xlsx(line_no: int, src_dir: Path, files: List[Path], folder_name: str) -> None:
    try:
        import openpyxl  # type: ignore
    except ImportError:
        raise RunnerError(
            "openpyxl is required for xlsx export but is not installed. "
            "Ensure it is listed in requirements.txt and installed."
        )

    dest_dir = ensure_outputs_subdir(folder_name, "xlsx")
    dest_file = dest_dir / "data.xlsx"

    columns, rows = iter_tabular_rows(src_dir, files)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "data"

    if columns:
        ws.append(columns)
        for row in rows:
            ws.append([row.get(col, "") for col in columns])

    try:
        wb.save(dest_file)
    except Exception as e:
        raise RunnerError(
            f"Error on line {line_no}: failed to write Excel '{dest_file}': {e}"
        ) from e
