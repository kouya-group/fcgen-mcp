import hashlib
import json
from pathlib import Path

from fcgen import TEMPLATES_DIR
from fcgen.core.freecadcmd import run_script
from fcgen.core.logging import write_log
from fcgen.core.runner import run_template


def run_assembly(spec: dict, out_dir: Path, dry_run: bool = False) -> dict:
    """複数の検証済みテンプレートを合成してアセンブリを生成する。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    parts_dir = out_dir / "_parts"

    parts = spec.get("parts", [])
    if not parts:
        raise RuntimeError("Assembly spec must contain at least one part")

    ids = [p["id"] for p in parts]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate part id in assembly spec")

    spec_bytes = json.dumps(spec, ensure_ascii=True, sort_keys=True).encode("utf-8")
    artifact_hash = hashlib.sha256(spec_bytes).hexdigest()

    part_results = []
    for part in parts:
        part_id = part["id"]
        template = part["template"]
        params = part["params"]
        placement = part.get("placement", {})

        part_out = parts_dir / part_id
        result = run_template(
            template=template,
            params=params,
            out_dir=part_out,
            dry_run=dry_run,
        )
        part_results.append({
            "id": part_id,
            "template": template,
            "artifact_hash": result["artifact_hash"],
            "placement": {
                "position": placement.get("position", [0, 0, 0]),
                "rotation": placement.get("rotation", [0, 0, 0]),
            },
            "outputs": result["outputs"],
        })

    step_path = out_dir / "assembly.step"
    stl_path = out_dir / "assembly.stl"
    log_path = out_dir / "log.txt"

    log_lines = [
        f"mode=assembly",
        f"dry_run={dry_run}",
        f"artifact_hash={artifact_hash}",
        f"part_count={len(parts)}",
    ]

    if not dry_run:
        manifest = {
            "parts": [
                {
                    "step_path": r["outputs"]["step"],
                    "position": r["placement"]["position"],
                    "rotation": r["placement"]["rotation"],
                }
                for r in part_results
            ],
            "output": spec.get("output", {"step": True, "stl": True}),
        }
        manifest_path = out_dir / "_assembly_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        script_path = Path(__file__).resolve().parent / "freecad_assemble.py"
        run_script(
            script_path=script_path,
            params_path=manifest_path,
            step_path=step_path,
            stl_path=stl_path,
            output_flags=spec.get("output", {"step": True, "stl": True}),
        )
        log_lines.append("assembly=ok")
    else:
        log_lines.append("assembly=skipped")

    write_log(log_path, log_lines)

    return {
        "mode": "assembly",
        "artifact_hash": artifact_hash,
        "parts": part_results,
        "outputs": {
            "step": str(step_path),
            "stl": str(stl_path),
            "log": str(log_path),
        },
    }
