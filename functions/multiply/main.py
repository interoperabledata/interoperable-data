#!/usr/bin/env python
import argparse
import json
from pathlib import Path
from typing import Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multiply two numbers.")
    parser.add_argument("--function-name", required=True)
    parser.add_argument("--node-name", required=True)
    parser.add_argument("--inputs-dir", required=True)
    parser.add_argument("--outputs-dir", required=True)
    return parser.parse_args()


def _load_single_number_from_port(port_dir: Path) -> float:
    """
    Load a single number from the first .json file in port_dir.
    The JSON document must be a top-level number.
    """
    if not port_dir.is_dir():
        raise RuntimeError(f"Input port directory does not exist: {port_dir}")

    json_files = sorted(f for f in port_dir.iterdir() if f.is_file() and f.suffix.lower() == ".json")
    if not json_files:
        raise RuntimeError(f"No JSON files found in input port directory: {port_dir}")

    src = json_files[0]
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"Failed to parse JSON from {src}: {e}") from e

    if not isinstance(data, (int, float)):
        raise RuntimeError(
            f"Expected a top-level number in {src}, got {type(data).__name__}."
        )

    return float(data)


def _ensure_output_port_dir(outputs_dir: Path, port_name: str) -> Path:
    port_dir = outputs_dir / port_name
    port_dir.mkdir(parents=True, exist_ok=True)
    return port_dir


def main() -> int:
    args = parse_args()

    inputs_dir = Path(args.inputs_dir)
    outputs_dir = Path(args.outputs_dir)

    # We expect two input ports: 'a' and 'b'
    a_dir = inputs_dir / "a"
    b_dir = inputs_dir / "b"

    a_value = _load_single_number_from_port(a_dir)
    b_value = _load_single_number_from_port(b_dir)

    result = a_value * b_value

    # Single output port: 'result'
    result_dir = _ensure_output_port_dir(outputs_dir, "result")
    result_file = result_dir / "result.json"

    # Write result as a top-level number
    result_file.write_text(json.dumps(result), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
