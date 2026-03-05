import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from fcgen.core.logging import write_log
from fcgen.validators.geometry import build_report
from fcgen.validators.semantic import validate_semantics


def _resolve_template_dir(template: str) -> Path:
    """レジストリ経由でテンプレートディレクトリを解決する。verified のみ許可。"""
    from fcgen.registry import get_default_registry
    reg = get_default_registry()
    entry = reg.get_entry(template)
    if entry is None:
        # フォールバック: レジストリ未登録でも TEMPLATES_DIR に存在すれば使用
        from fcgen import TEMPLATES_DIR
        fallback = TEMPLATES_DIR / template
        if fallback.exists() and (fallback / "schema.json").exists():
            return fallback
        raise RuntimeError(f"Template not found: {template}")
    if entry["status"] != "verified":
        raise RuntimeError(
            f"Template '{template}' is a candidate (not verified). "
            "Use verify_template to approve it first."
        )
    return reg.resolve_path(template)


def _load_template_module(template: str) -> Any:
    mod_path = _resolve_template_dir(template) / "generator.py"
    if not mod_path.exists():
        raise RuntimeError(f"Template generator not found: {mod_path}")
    spec = importlib.util.spec_from_file_location(f"templates.{template}.generator", mod_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec for: {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_schema(template: str) -> dict:
    schema_path = _resolve_template_dir(template) / "schema.json"
    if not schema_path.exists():
        raise RuntimeError(f"Template schema not found: {schema_path}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def run_template(template: str, params: dict, out_dir: Path, dry_run: bool = False) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    schema = _load_schema(template)
    _validate_params(params, schema)
    validate_semantics(template=template, params=params)

    params_bytes = json.dumps(params, ensure_ascii=True, sort_keys=True).encode("utf-8")
    artifact_hash = hashlib.sha256(params_bytes).hexdigest()

    step_path = out_dir / "model.step"
    stl_path = out_dir / "model.stl"
    log_path = out_dir / "log.txt"

    log_lines = [f"template={template}", f"dry_run={dry_run}", f"artifact_hash={artifact_hash}"]
    if not dry_run:
        mod = _load_template_module(template)
        if not hasattr(mod, "generate"):
            raise RuntimeError(f"Template module must define generate(params, step_path, stl_path): {template}")
        mod.generate(params=params, step_path=step_path, stl_path=stl_path)
        log_lines.append("generation=ok")
    else:
        log_lines.append("generation=skipped")

    # FreeCAD バージョン情報を取得
    from fcgen.core.freecadcmd import get_freecad_version
    fc_version = get_freecad_version()
    fc_version_str = fc_version["full"] if fc_version else "unknown"
    log_lines.append(f"freecad_version={fc_version_str}")

    report = build_report(template=template, params=params, artifact_hash=artifact_hash, generated=not dry_run)
    report["freecad_version"] = fc_version_str
    report_json = out_dir / "report.json"
    report_md = out_dir / "report.md"
    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md.write_text(_to_markdown(report), encoding="utf-8")

    write_log(log_path, log_lines)
    return {
        "template": template,
        "artifact_hash": artifact_hash,
        "freecad_version": fc_version_str,
        "outputs": {
            "step": str(step_path),
            "stl": str(stl_path),
            "report_json": str(report_json),
            "report_md": str(report_md),
            "log": str(log_path),
        },
    }


def _validate_params(params: dict, schema: dict) -> None:
    try:
        from jsonschema import validate  # type: ignore
        from jsonschema.exceptions import ValidationError  # type: ignore
    except ImportError:
        _minimal_validate(params)
        return
    try:
        validate(instance=params, schema=schema)
    except ValidationError as exc:
        path = ".".join(str(x) for x in exc.path)
        loc = f" at '{path}'" if path else ""
        raise RuntimeError(f"Schema validation failed{loc}: {exc.message}") from exc


def _minimal_validate(params: dict) -> None:
    for key in ("units", "output"):
        if key not in params:
            raise RuntimeError(f"Missing required key: {key}")
    if params["units"] != "mm":
        raise RuntimeError("Only 'mm' is supported for units")


def _to_markdown(report: dict) -> str:
    lines = [
        "# fcgen report",
        "",
        f"- template: `{report['template']}`",
        f"- artifact_hash: `{report['artifact_hash']}`",
        f"- generated: `{report['generated']}`",
        "",
        "## Geometry",
    ]
    geom = report["geometry"]
    lines.append(f"- bbox_mm: `{geom['bbox_mm']}`")
    lines.append(f"- volume_mm3: `{geom['volume_mm3']}`")
    for key, value in geom.items():
        if key in {"bbox_mm", "volume_mm3"}:
            continue
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"
