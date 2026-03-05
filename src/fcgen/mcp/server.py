"""fcgen MCP server — LLM が検証済み標準形状を安全に生成・合成するためのツール群。"""
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
def list_templates() -> dict:
    """利用可能なテンプレート一覧を返す。各テンプレートのスキーマ概要を含む。"""
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
    """指定テンプレートの完全なJSONスキーマを返す。"""
    reg = _get_registry()
    schema_path = reg.resolve_path(template) / "schema.json"
    if not schema_path.exists():
        return {"error": f"Unknown template: {template}"}
    return json.loads(schema_path.read_text(encoding="utf-8"))


@mcp.tool()
def get_template_example(template: str) -> dict:
    """指定テンプレートのサンプルパラメータJSONを返す。"""
    reg = _get_registry()
    example_path = reg.resolve_path(template) / "examples" / "basic.json"
    if not example_path.exists():
        return {"error": f"No example found for template: {template}"}
    return json.loads(example_path.read_text(encoding="utf-8"))


@mcp.tool()
def validate_params(template: str, params: dict) -> dict:
    """パラメータをスキーマ＋意味検証する。生成は行わない。安全確認用。"""
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
    """候補（未検証）テンプレート一覧を返す。"""
    try:
        reg = _get_registry()
        entries = reg.list_templates(status="candidate")
        return {"ok": True, "candidates": entries}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def propose_template(name: str, purpose: str, tags: list[str] | None = None, source: str = "generated") -> dict:
    """新しいテンプレートを候補として登録する。templates_candidate/{name}/ にファイルが必要。"""
    try:
        reg = _get_registry()
        entry = reg.add_candidate(name=name, source=source, purpose=purpose, tags=tags)
        return {"ok": True, "entry": entry}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def verify_template(name: str) -> dict:
    """候補テンプレートを検証し、合格なら verified に昇格する。"""
    try:
        reg = _get_registry()
        entry = reg.verify(name)
        return {"ok": True, "entry": entry}
    except (RuntimeError, KeyError, ValueError, FileNotFoundError, FileExistsError) as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def find_template(purpose: str) -> dict:
    """目的に合うテンプレートを検索。シンプルな方を優先。"""
    try:
        reg = _get_registry()
        results = reg.find_simpler(purpose)
        return {"ok": True, "results": results}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def generate_part(template: str, params: dict, out_name: str = "") -> dict:
    """単一パーツを生成する。out_name で出力サブフォルダ名を指定可能。"""
    name = out_name.strip() or template
    out_dir = OUTPUT_DIR / name
    try:
        result = run_template(template=template, params=params, out_dir=out_dir, dry_run=False)
        return {"ok": True, "result": result}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def generate_assembly(spec: dict, out_name: str = "assembly") -> dict:
    """複数パーツのアセンブリを生成する。spec は parts 配列と placement を含む。"""
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
