"""fcgen MCP server — Tools for safely generating and assembling verified parametric CAD parts via LLM."""
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from fcgen import OUTPUT_DIR
from fcgen.core.runner import run_template, _load_schema, _validate_params
from fcgen.validators.semantic import validate_semantics
from fcgen.assembly.engine import run_assembly
from fcgen.registry import get_default_registry

mcp = FastMCP("fcgen")


def _get_registry():
    """レジストリを取得し、必要ならブートストラップする。"""
    reg = get_default_registry()
    if not reg.list_templates():
        reg.bootstrap()
    return reg


@mcp.tool()
def check_freecad() -> dict:
    """Check if FreeCAD is available and return version information. Use this to verify the environment before attempting part generation."""
    from fcgen.core.freecadcmd import check_freecad_available
    return check_freecad_available()


@mcp.tool()
def list_templates() -> dict:
    """List all available verified templates. Returns each template's purpose, tags, parameter count, top-level schema keys, and whether an example is available."""
    reg = _get_registry()
    entries = reg.list_templates(status="verified")
    result = {}
    for name, entry in entries.items():
        template_dir = reg.resolve_path(name)
        schema_path = template_dir / "schema.json"
        if not schema_path.exists():
            continue
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        props = list(schema.get("properties", {}).keys())
        result[name] = {
            "purpose": entry.get("purpose", ""),
            "tags": entry.get("tags", []),
            "param_count": entry.get("param_count", 0),
            "top_level_keys": props,
            "has_example": (template_dir / "examples" / "basic.json").exists(),
        }
    return {"templates": result}


@mcp.tool()
def get_template_schema(template: str) -> dict:
    """Return the full JSON Schema for a given template. Use this to inspect all available parameters, types, defaults, and constraints before generating a part."""
    reg = _get_registry()
    schema_path = reg.resolve_path(template) / "schema.json"
    if not schema_path.exists():
        return {"error": f"Unknown template: {template}"}
    return json.loads(schema_path.read_text(encoding="utf-8"))


@mcp.tool()
def get_template_example(template: str) -> dict:
    """Return an example parameter JSON for a given template. Use this as a starting point to understand the expected input format and typical values."""
    reg = _get_registry()
    example_path = reg.resolve_path(template) / "examples" / "basic.json"
    if not example_path.exists():
        return {"error": f"No example found for template: {template}"}
    return json.loads(example_path.read_text(encoding="utf-8"))


@mcp.tool()
def validate_params(template: str, params: dict) -> dict:
    """Validate parameters against the template's JSON Schema, semantic rules, and constraints. Returns warnings for canonical value deviations."""
    try:
        reg = _get_registry()
        schema_path = reg.resolve_path(template) / "schema.json"
        if not schema_path.exists():
            return {"valid": False, "error": f"Unknown template: {template}"}
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        _validate_params(params, schema)
        validate_semantics(template=template, params=params)

        # Canonical constraint warnings
        warnings = []
        constraints_path = reg.resolve_path(template) / "constraints.json"
        if constraints_path.exists():
            constraints = json.loads(constraints_path.read_text(encoding="utf-8"))
            for dotkey, canon in constraints.get("canonical", {}).items():
                if not isinstance(canon, dict) or dotkey.startswith("_"):
                    continue
                expected = canon.get("value")
                if expected is None:
                    continue
                # Navigate params by dotkey
                parts = dotkey.split(".")
                val = params
                for p in parts:
                    if isinstance(val, dict):
                        val = val.get(p)
                    else:
                        val = None
                        break
                if val is not None and val != expected:
                    warnings.append(
                        f"Canonical value deviation: {dotkey}={val} (expected {expected}, source: {canon.get('source', 'spec')})"
                    )

        result = {"valid": True}
        if warnings:
            result["warnings"] = warnings
        return result
    except RuntimeError as exc:
        return {"valid": False, "error": str(exc)}


@mcp.tool()
def list_candidates() -> dict:
    """List all candidate (unverified) templates. These templates have been proposed but not yet passed verification."""
    try:
        reg = _get_registry()
        entries = reg.list_templates(status="candidate")
        return {"ok": True, "candidates": entries}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def propose_template(name: str, purpose: str, tags: list[str] | None = None, source: str = "generated") -> dict:
    """Register a new template as a candidate. The template files (generator.py, schema.json, freecad_generate.py, etc.) must already exist under templates_candidate/{name}/. Provide a purpose description and optional tags."""
    try:
        reg = _get_registry()
        entry = reg.add_candidate(name=name, source=source, purpose=purpose, tags=tags)
        return {"ok": True, "entry": entry}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def verify_template(name: str) -> dict:
    """Run verification checks on a candidate template. If all checks pass, promote it to verified status so it becomes available for part generation."""
    try:
        reg = _get_registry()
        entry = reg.verify(name)
        return {"ok": True, "entry": entry}
    except (RuntimeError, KeyError, ValueError, FileNotFoundError, FileExistsError) as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_template_constraints(template: str) -> dict:
    """Return the constraints for a template: canonical values, variant presets, linked parameter sets, and configurable params. Use this to understand which parameters are fixed by specification, which have standard presets, and which are freely adjustable."""
    reg = _get_registry()
    constraints_path = reg.resolve_path(template) / "constraints.json"
    if not constraints_path.exists():
        return {"error": f"No constraints found for template: {template}"}
    return json.loads(constraints_path.read_text(encoding="utf-8"))


@mcp.tool()
def find_template(purpose: str) -> dict:
    """Search for templates by name, purpose, tags, or constraint presets (e.g. 'M5 bolt', 'soccer ball', 'LEGO 2x4'). Returns results ranked by simplicity with resolved parameters when a preset matches."""
    try:
        reg = _get_registry()
        results = reg.find_with_constraints(purpose)
        return {"ok": True, "results": results}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def generate_part(template: str, params: dict, out_name: str = "") -> dict:
    """Generate a single CAD part from a verified template and parameters. Optionally specify out_name to set the output subfolder name; defaults to the template name."""
    name = out_name.strip() or template
    out_dir = OUTPUT_DIR / name
    try:
        result = run_template(template=template, params=params, out_dir=out_dir, dry_run=False)
        return {"ok": True, "result": result}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def generate_assembly(spec: dict, out_name: str = "assembly") -> dict:
    """Generate a multi-part assembly. The spec dict must contain a 'parts' array defining each part's template and parameters, and a 'placement' section describing how parts are positioned relative to each other."""
    out_dir = OUTPUT_DIR / out_name.strip()
    try:
        result = run_assembly(spec=spec, out_dir=out_dir, dry_run=False)
        return {"ok": True, "result": result}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def main():
    mcp.run()


if __name__ == "__main__":
    main()
