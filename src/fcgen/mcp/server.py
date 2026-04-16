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
    """Validate parameters against the template's JSON Schema and semantic rules without generating any output. Use this as a dry-run safety check before calling generate_part."""
    try:
        reg = _get_registry()
        schema_path = reg.resolve_path(template) / "schema.json"
        if not schema_path.exists():
            return {"valid": False, "error": f"Unknown template: {template}"}
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        _validate_params(params, schema)
        validate_semantics(template=template, params=params)
        return {"valid": True}
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
def find_template(purpose: str) -> dict:
    """Search for templates matching a given purpose description. Returns results ranked by simplicity, preferring templates with fewer parameters."""
    try:
        reg = _get_registry()
        results = reg.find_simpler(purpose)
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
