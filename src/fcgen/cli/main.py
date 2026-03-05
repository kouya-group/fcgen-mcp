import argparse
import copy
import csv
import json
from pathlib import Path

from fcgen import TEMPLATES_DIR
from fcgen.core.runner import run_template


def _load_params(path: Path) -> dict:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError("YAML input requires PyYAML. Use JSON or install pyyaml.") from exc
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    raise RuntimeError(f"Unsupported input format: {path.suffix}")


def run_demo(out_root: Path, dry_run: bool = False) -> dict:
    demo_cases = [
        ("bracket", TEMPLATES_DIR / "bracket" / "examples" / "basic.json"),
        ("enclosure", TEMPLATES_DIR / "enclosure" / "examples" / "basic.json"),
        ("adapter_plate", TEMPLATES_DIR / "adapter_plate" / "examples" / "basic.json"),
    ]
    runs: list[dict] = []
    out_root.mkdir(parents=True, exist_ok=True)

    for template, input_path in demo_cases:
        params = _load_params(input_path)
        case_out = out_root / template
        result = run_template(template, params, case_out, dry_run=dry_run)
        runs.append(
            {
                "template": template,
                "input": str(input_path),
                "output_dir": str(case_out),
                "result": result,
            }
        )

    summary = {
        "mode": "dry-run" if dry_run else "generate",
        "out_root": str(out_root),
        "runs": runs,
    }
    summary_path = out_root / "demo_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _parse_cell(cell: str):
    raw = cell.strip()
    if raw == "":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _set_path_value(target: dict, path: str, value) -> None:
    parts = [p for p in path.split(".") if p]
    if not parts:
        raise RuntimeError(f"Invalid path: '{path}'")
    cur = target
    for key in parts[:-1]:
        if key not in cur:
            cur[key] = {}
        if not isinstance(cur[key], dict):
            raise RuntimeError(f"Cannot set '{path}': '{key}' is not an object")
        cur = cur[key]
    cur[parts[-1]] = value


def run_batch(template: str, input_path: Path, csv_path: Path, out_root: Path, dry_run: bool = False) -> dict:
    base = _load_params(input_path)
    rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8-sig").splitlines()))
    if not rows:
        raise RuntimeError(f"Batch CSV is empty: {csv_path}")
    if "variant_id" not in (rows[0].keys() if rows else []):
        raise RuntimeError("Batch CSV must include 'variant_id' column")

    runs: list[dict] = []
    out_root.mkdir(parents=True, exist_ok=True)
    for idx, row in enumerate(rows, start=1):
        variant_id = (row.get("variant_id") or f"row_{idx}").strip() or f"row_{idx}"
        params = copy.deepcopy(base)

        for key, cell in row.items():
            if key == "variant_id":
                continue
            if cell is None or cell.strip() == "":
                continue
            _set_path_value(params, key, _parse_cell(cell))

        out_dir = out_root / variant_id
        result = run_template(template=template, params=params, out_dir=out_dir, dry_run=dry_run)
        runs.append(
            {
                "variant_id": variant_id,
                "output_dir": str(out_dir),
                "result": result,
            }
        )

    summary = {
        "template": template,
        "mode": "dry-run" if dry_run else "generate",
        "input": str(input_path),
        "csv": str(csv_path),
        "out_root": str(out_root),
        "runs": runs,
    }
    summary_path = out_root / "batch_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fcgen")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run a template with input params")
    run.add_argument("template", help="Template name, e.g. bracket")
    run.add_argument("--in", dest="input_path", required=True, help="Input JSON/YAML path")
    run.add_argument("--out", dest="out_dir", required=True, help="Output directory")
    run.add_argument("--dry-run", action="store_true", help="Validate and report only")

    demo = sub.add_parser("demo", help="Run all built-in template examples")
    demo.add_argument("--out", dest="out_dir", default="dist_demo", help="Demo output root directory")
    demo.add_argument("--dry-run", action="store_true", help="Validate and report only")

    batch = sub.add_parser("batch", help="Run one template for multiple variants from CSV")
    batch.add_argument("template", help="Template name, e.g. bracket")
    batch.add_argument("--in", dest="input_path", required=True, help="Base input JSON/YAML path")
    batch.add_argument("--csv", dest="csv_path", required=True, help="CSV with variant_id and dot-path columns")
    batch.add_argument("--out", dest="out_dir", required=True, help="Batch output root directory")
    batch.add_argument("--dry-run", action="store_true", help="Validate and report only")

    asm = sub.add_parser("assembly", help="Generate a multi-part assembly from spec JSON")
    asm.add_argument("--in", dest="input_path", required=True, help="Assembly spec JSON path")
    asm.add_argument("--out", dest="out_dir", required=True, help="Output directory")
    asm.add_argument("--dry-run", action="store_true", help="Validate and report only")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        input_path = Path(args.input_path).resolve()
        out_dir = Path(args.out_dir).resolve()
        params = _load_params(input_path)
        result = run_template(args.template, params, out_dir, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "demo":
        out_dir = Path(args.out_dir).resolve()
        summary = run_demo(out_dir, dry_run=args.dry_run)
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "assembly":
        from fcgen.assembly.engine import run_assembly
        input_path = Path(args.input_path).resolve()
        out_dir = Path(args.out_dir).resolve()
        spec = _load_params(input_path)
        result = run_assembly(spec, out_dir, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "batch":
        input_path = Path(args.input_path).resolve()
        csv_path = Path(args.csv_path).resolve()
        out_dir = Path(args.out_dir).resolve()
        summary = run_batch(
            template=args.template,
            input_path=input_path,
            csv_path=csv_path,
            out_root=out_dir,
            dry_run=args.dry_run,
        )
        print(json.dumps(summary, indent=2))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
