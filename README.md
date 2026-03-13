# fcgen-mcp

**An MCP server that lets LLMs safely generate parametric CAD parts through verified templates and FreeCAD.**

*LLM が検証済みテンプレートを通じて安全にパラメトリック CAD パーツを生成する MCP サーバー*

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)
![FreeCAD 0.19+](https://img.shields.io/badge/FreeCAD-0.19%2B-orange)

---

## What is this?

Large Language Models can describe mechanical parts in natural language, but giving them unconstrained access to a CAD kernel is a recipe for broken geometry, invalid dimensions, and non-manufacturable output. **fcgen-mcp** solves this by placing a structured safety layer between the LLM and FreeCAD.

Instead of generating raw CAD scripts, the LLM selects from **verified parametric templates**, fills in parameters validated against JSON Schema and semantic rules, and receives deterministic STEP/STL output.

```
                    ┌─────────────────────────────────┐
                    │         LLM (Claude, etc.)       │
                    └────────────┬──────────────────────┘
                                 │ MCP protocol
                    ┌────────────▼──────────────────────┐
                    │       fcgen MCP Server             │
                    │  ┌───────────┐  ┌──────────────┐  │
                    │  │  JSON     │  │  Semantic     │  │
                    │  │  Schema   │  │  Validation   │  │
                    │  └─────┬─────┘  └──────┬───────┘  │
                    │        └────────┬──────┘          │
                    │       ┌────────▼─────────┐       │
                    │       │ Template Registry │       │
                    │       │ (verified only)   │       │
                    │       └────────┬─────────┘       │
                    └────────────────┼─────────────────┘
                                     │ headless execution
                    ┌────────────────▼─────────────────┐
                    │     FreeCAD (freecadcmd)          │
                    │     → STEP / STL output           │
                    └──────────────────────────────────┘
```

## Key Features

- **11 MCP tools** -- complete workflow from discovery to generation, including assembly
- **Template registry** with candidate → verified lifecycle for quality control
- **JSON Schema + semantic validation** -- catches invalid geometry before it reaches FreeCAD
- **Multi-part assembly** with explicit placement (position + rotation)
- **FreeCAD headless generation** -- produces industry-standard STEP and STL files
- **Deterministic artifact hashing** -- identical parameters always produce identical output

## Quick Start

### Installation

```bash
pip install -e ".[mcp]"
```

### Launch the MCP server

```bash
python -m fcgen.mcp.server
```

### Claude Desktop configuration

Add to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fcgen": {
      "command": "python",
      "args": ["-m", "fcgen.mcp.server"]
    }
  }
}
```

### FreeCAD setup

If `freecadcmd` is not on your PATH, set the environment variable:

```bash
export FCGEN_FREECADCMD="/path/to/freecadcmd"
```

Windows:

```cmd
set FCGEN_FREECADCMD=C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe
```

## MCP Tools Reference

| Tool | Description |
|------|-------------|
| `check_freecad` | Verify FreeCAD is available and return version info |
| `list_templates` | List all verified templates with purpose, tags, and parameter count |
| `get_template_schema` | Return the full JSON Schema for a template |
| `get_template_example` | Return example parameters for a template |
| `validate_params` | Dry-run validation (schema + semantic) without generating output |
| `find_template` | Search templates by purpose description, ranked by simplicity |
| `generate_part` | Generate a single CAD part (STEP/STL) from a verified template |
| `generate_assembly` | Generate a multi-part assembly with placement |
| `list_candidates` | List unverified candidate templates |
| `propose_template` | Register a new template as a candidate |
| `verify_template` | Run verification checks and promote candidate to verified |

## Usage Examples

### Example 1: Discover and generate a bracket

A typical MCP tool call flow follows five steps -- discover, inspect, preview, validate, generate:

```
1. list_templates          → see what's available
2. get_template_schema     → inspect full parameter schema
3. get_template_example    → get working sample parameters
4. validate_params         → dry-run safety check
5. generate_part           → produce STEP/STL files
```

**Step 1 -- `list_templates`** returns all verified templates:

```json
{
  "templates": {
    "bracket": {
      "purpose": "L-bracket with configurable holes",
      "tags": ["structural", "mounting"],
      "param_count": 10,
      "top_level_keys": ["units", "material_hint", "bracket", "output"],
      "has_example": true
    },
    "adapter_plate": {
      "purpose": "Flat plate with two bolt circle patterns",
      "tags": ["structural", "mounting", "plate"],
      "param_count": 12,
      "top_level_keys": ["units", "material_hint", "adapter_plate", "output"],
      "has_example": true
    }
  }
}
```

**Step 3 -- `get_template_example("bracket")`** returns ready-to-use parameters:

```json
{
  "units": "mm",
  "material_hint": "al6061",
  "bracket": {
    "thickness": 3.0,
    "leg_a": 40.0,
    "leg_b": 60.0,
    "width": 25.0,
    "fillet": 1.0,
    "chamfer": 0.5,
    "holes": {
      "pattern": "line",
      "diameter": 5.5,
      "count": 2,
      "edge_offset": 8.0
    }
  },
  "output": { "step": true, "stl": true, "tolerance": 0.1 }
}
```

**Step 4 -- `validate_params("bracket", params)`** confirms validity before generation:

```json
{ "valid": true }
```

**Step 5 -- `generate_part("bracket", params)`** produces the CAD files:

```json
{
  "ok": true,
  "result": {
    "template": "bracket",
    "artifact_hash": "77bd1e4cb686862707a2977db293aaed...",
    "freecad_version": "1.0.0",
    "outputs": {
      "step": "output/bracket/model.step",
      "stl": "output/bracket/model.stl",
      "report_json": "output/bracket/report.json",
      "report_md": "output/bracket/report.md"
    }
  }
}
```

### Example 2: Multi-part bolted assembly

The `generate_assembly` tool composes multiple parts with explicit placement. Here is a 7-part assembly: an adapter plate, two L-brackets, and four bolts.

```json
{
  "units": "mm",
  "parts": [
    {
      "id": "base",
      "template": "adapter_plate",
      "params": { "...adapter_plate params..." },
      "placement": { "position": [0, 0, 0], "rotation": [0, 0, 0] }
    },
    {
      "id": "bracket_upper",
      "template": "bracket",
      "params": { "...bracket params..." },
      "placement": { "position": [67.622, 17.417, 6.0], "rotation": [135, 0, 0] }
    },
    {
      "id": "bracket_lower",
      "template": "bracket",
      "params": { "...bracket params..." },
      "placement": { "position": [-67.622, -17.417, 6.0], "rotation": [-45, 0, 0] }
    },
    {
      "id": "bolt_1",
      "template": "bolt",
      "params": { "...bolt params..." },
      "placement": { "position": [53.126, 14.235, 9.0], "rotation": [0, 0, 0] }
    }
  ],
  "output": { "step": true, "stl": true }
}
```

Each part is generated independently with full validation, then placed in a combined STEP/STL assembly. The remaining three bolts follow the same pattern at their respective positions.

## Template Lifecycle

Templates go through a quality gate before they can be used for generation:

```
[Create files]  →  propose_template  →  candidate  →  verify_template  →  verified
                                           │                                  │
                                           ▼                                  ▼
                                   templates_candidate/                 templates/
```

- **Candidate**: template files exist and are registered, but not yet validated
- **Verified**: passed schema checks, test generation, and semantic validation -- available to `generate_part`

LLMs can only generate parts from **verified** templates.

## Available Templates

| Template | Description | Param Count |
|----------|-------------|:-----------:|
| `bracket` | L-bracket with configurable holes, fillet, and chamfer | 10 |
| `adapter_plate` | Flat plate with two bolt circle patterns (PCD) | 12 |
| `enclosure` | Rectangular box with lid and screw bosses | 10 |
| `bolt` | Simple cylindrical bolt with head | 4 |
| `table_top` | Flat table top plate with optional edge fillet | 4 |
| `simple_leg` | Rectangular leg with chamfer and mounting hole | 5 |

## Creating Custom Templates

Each template is a directory containing four files:

```
templates_candidate/my_part/
├── schema.json            # JSON Schema defining all parameters
├── generator.py           # Python logic: params → FreeCAD script args
├── freecad_generate.py    # FreeCAD script: runs inside freecadcmd
└── examples/
    └── basic.json         # Working example parameters
```

Workflow:

1. Create the template directory and files under `templates_candidate/`
2. Call `propose_template("my_part", purpose="...", tags=[...])` to register it
3. Call `verify_template("my_part")` to run automated checks
4. On success, the template is promoted to `templates/` and becomes available for generation

## FreeCAD Compatibility

| | Version |
|---|---------|
| **Minimum** | FreeCAD 0.19+ |
| **Recommended** | FreeCAD 1.0 |
| **Tested** | 0.21, 1.0 |

The project uses FreeCAD's Part module (primitives, booleans), Mesh module (STL export), and basic Placement API.

## Project Structure

```
src/fcgen/
├── mcp/server.py          # MCP tools (primary interface for LLMs)
├── core/runner.py         # Generation engine
├── assembly/engine.py     # Multi-part assembly with placement
├── validators/
│   ├── semantic.py        # Dimensional & geometric validation
│   └── geometry.py        # Geometry constraint checks
├── registry.py            # Template lifecycle management
└── cli/main.py            # CLI interface (secondary)

templates/                 # Verified templates (ready for generation)
templates_candidate/       # Candidate templates (pending verification)
tests/                     # Test suite
```

## Documentation

| Document | Description |
|----------|-------------|
| [Quick Start](docs/quickstart.md) | Build a desk in 5 minutes |
| [MCP Tools Reference](docs/mcp-tools.md) | All 11 MCP tools with examples |
| [Template Guide](docs/template-guide.md) | How to create custom templates |
| [Assembly Guide](docs/assembly-guide.md) | Multi-part assembly creation |

## Assembly Examples

Pre-built assembly examples in `templates/assembly_examples/`:

| File | Description |
|------|-------------|
| `simple_desk.json` | Standard 4-leg desk (1200 x 600 x 725mm) |
| `compact_desk.json` | Compact desk for small rooms (800 x 500 x 700mm) |
| `standing_desk.json` | Standing desk (1400 x 700 x 1050mm) |
| `desk_with_shelf.json` | Desk with under-shelf storage |
| `plate_brackets_bolts.json` | Bolted plate assembly with L-brackets |
| `plate_with_brackets.json` | Plate with L-brackets |

## Development

Install in development mode with MCP support:

```bash
pip install -e ".[mcp]"
```

Run the test suite:

```bash
python -m pytest tests/ -v
```

There are currently 39 tests covering validation, generation, registry operations, and assembly logic.

## License

[MIT](LICENSE) -- Copyright (c) 2026 kouya-group
