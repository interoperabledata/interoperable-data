#!/usr/bin/env python
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multiply two numbers.")
    parser.add_argument("--function-name", required=True)
    parser.add_argument("--node-name", required=True)
    parser.add_argument("--inputs-dir", required=True)
    parser.add_argument("--outputs-dir", required=True)
    return parser.parse_args()


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    if not manifest_path.is_file():
        raise RuntimeError(f"Manifest not found for function: {manifest_path}")
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"Failed to parse manifest JSON: {e}") from e


def get_port_names(manifest: Dict[str, Any]) -> (List[str], List[str]):
    inputs_raw = manifest.get("in")
    outputs_raw = manifest.get("out")

    if not isinstance(inputs_raw, list) or not isinstance(outputs_raw, list):
        raise RuntimeError("Manifest 'in' and 'out' must both be arrays.")

    input_names = []
    for p in inputs_raw:
        if not isinstance(p, dict) or "name" not in p:
            raise RuntimeError("Each input port in manifest must be an object with 'name'.")
        input_names.append(p["name"])

    output_names = []
    for p in outputs_raw:
        if not isinstance(p, dict) or "name" not in p:
            raise RuntimeError("Each output port in manifest must be an object with 'name'.")
        output_names.append(p["name"])

    if len(input_names) < 2:
        raise RuntimeError(
            f"Multiply function expects at least 2 input ports; found {len(input_names)}."
        )
    if len(output_names) < 1:
        raise RuntimeError("Multiply function expects at least 1 output port.")

    return input_names, output_names


def _load_single_number_from_port(port_dir: Path) -> float:
    """
    Load a single number from the first .json file in port_dir.
    The JSON document must be a top-level number.
    """
    if not port_dir.is_dir():
        raise RuntimeError(f"Input port directory does not exist: {port_dir}")

    json_files = sorted(
        f for f in port_dir.iterdir()
        if f.is_file() and f.suffix.lower() == ".json"
    )
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


def main() -> int:
    args = parse_args()

    inputs_dir = Path(args.inputs_dir)
    outputs_dir = Path(args.outputs_dir)

    # Load manifest next to this script
    manifest_path = Path(__file__).resolve().parent / "manifest.json"
    manifest = load_manifest(manifest_path)

    input_names, output_names = get_port_names(manifest)

    # For this multiply function, use the first two inputs and the first output.
    in1_name, in2_name = input_names[0], input_names[1]
    out_name = output_names[0]

    in1_dir = inputs_dir / in1_name
    in2_dir = inputs_dir / in2_name

    value1 = _load_single_number_from_port(in1_dir)
    value2 = _load_single_number_from_port(in2_dir)

    result = value1 * value2

    out_dir = outputs_dir / out_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "result.json"

    out_file.write_text(json.dumps(result), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
