---
name: fcgen
description: Generate parametric CAD parts and assemblies via the fcgen MCP server. Use when user asks to "create a CAD part", "generate a bracket", "build a desk", "make an assembly", "design a bolt", "3D model", "STEP file", "STL file", mentions template names like "bracket", "adapter_plate", "enclosure", "bolt", "table_top", "simple_leg", or asks about FreeCAD generation. Do NOT use for general 3D modeling questions unrelated to fcgen templates.
---

# fcgen -- Parametric CAD Generation via MCP

Generate verified parametric CAD parts (STEP/STL) through the fcgen MCP server and FreeCAD.

## Critical Rules

- ALWAYS follow the 5-step workflow: discover, inspect, example, validate, generate
- NEVER skip `validate_params` before `generate_part` or `generate_assembly`
- ALL dimensions are in millimeters (mm)
- Each part `id` in an assembly MUST be unique
- Only verified templates can be used for generation

## Documentation

This skill uses the project's docs/ as its single source of truth.
Read these files for detailed reference:

- `docs/mcp-tools.md` -- Full MCP tools reference (11 tools, parameters, return values, examples)
- `docs/assembly-guide.md` -- Assembly spec format, placement rules, desk/bolted plate examples
- `docs/template-guide.md` -- Custom template creation (schema.json, generator.py, FreeCAD script)
- `docs/quickstart.md` -- Quick start guide and available templates

## Available MCP Tools

| Tool | Purpose |
|------|---------|
| `check_freecad` | Verify FreeCAD is installed and compatible |
| `list_templates` | List all verified templates |
| `get_template_schema` | Get full JSON Schema for a template |
| `get_template_example` | Get working example parameters |
| `validate_params` | Dry-run validation (schema + semantic) |
| `find_template` | Search templates by purpose description |
| `generate_part` | Generate single part (STEP/STL) |
| `generate_assembly` | Generate multi-part assembly |
| `list_candidates` | List unverified candidate templates |
| `propose_template` | Register new template as candidate |
| `verify_template` | Verify and promote candidate to verified |

## Workflow: Generate a Single Part

### Step 1: Discover templates

Call `list_templates` to see what is available.

### Step 2: Inspect the schema

Call `get_template_schema(template)` to understand parameters, types, and constraints.

### Step 3: Get an example

Call `get_template_example(template)` to get a working parameter set as a starting point.

### Step 4: Validate

Call `validate_params(template, params)` to dry-run check before generation.
If validation fails, fix the error and re-validate.

### Step 5: Generate

Call `generate_part(template, params, out_name)` to produce STEP/STL files.

## Workflow: Generate an Assembly

An assembly combines multiple parts with spatial placement.

### Assembly Spec Format

```json
{
  "units": "mm",
  "parts": [
    {
      "id": "unique_part_id",
      "template": "template_name",
      "params": { "...full parameter dict..." },
      "placement": {
        "position": [x, y, z],
        "rotation": [yaw, pitch, roll]
      }
    }
  ],
  "output": { "step": true, "stl": true }
}
```

### Placement Rules

- `position`: translation in mm from assembly origin `[x, y, z]`
- `rotation`: Euler angles in degrees `[yaw, pitch, roll]` (ZY'X'' convention)
- `[0, 0, 0]` = no rotation (default)

### Assembly Steps

1. Plan the assembly: decide templates, parameters, and spatial layout
2. Validate each part's params individually with `validate_params`
3. Build the assembly spec JSON with unique `id` per part
4. Call `generate_assembly(spec, out_name)`
5. Check the `interference` field in the result for part collisions

### Interference Check

`generate_assembly` automatically checks all part pairs for physical overlap using FreeCAD Boolean intersection. The result includes:

```json
{
  "interference": {
    "checked": true,
    "pair_count": 1,
    "pairs": [
      {"part_a": "top", "part_b": "leg_1", "volume_mm3": 88743.363}
    ]
  }
}
```

- `pair_count > 0` means parts are colliding — fix placement before using the output
- A detailed report is also saved as `interference_report.json` in the output directory
- Volumes below 0.001 mm^3 are ignored as numerical noise

### Desk Assembly Pattern

A standard desk uses `table_top` + 4x `simple_leg`:

- Table top at Z = leg_height (e.g. `[0, 0, 700]`)
- Legs at floor level, inset from edges:
  - Front-left: `[inset, inset, 0]`
  - Front-right: `[top_width - leg_width - inset, inset, 0]`
  - Rear-left: `[inset, top_depth - leg_depth - inset, 0]`
  - Rear-right: `[top_width - leg_width - inset, top_depth - leg_depth - inset, 0]`
- Total height = leg_height + top_thickness

For full assembly examples including bolted plate patterns, read `docs/assembly-guide.md`.

## Available Templates Quick Reference

| Template | Purpose | Key Params |
|----------|---------|------------|
| `bracket` | L-bracket with holes | thickness, leg_a, leg_b, width, holes |
| `adapter_plate` | Flat plate with bolt circle patterns | size, thickness, pattern_a, pattern_b |
| `enclosure` | Box with lid and screw bosses | width, depth, height, wall, corner_radius |
| `bolt` | Cylindrical bolt with head | diameter, length, head_diameter, head_height |
| `table_top` | Flat plate with edge fillet | width, depth, thickness, edge_fillet |
| `simple_leg` | Rectangular leg with chamfer | width, depth, height, chamfer, hole_diameter |

For full parameter schemas and examples, call `get_template_schema` and `get_template_example`, or read `docs/quickstart.md`.

## Parameter Structure Convention

Every template follows this structure:

```json
{
  "units": "mm",
  "material_hint": "optional_material_string",
  "TEMPLATE_NAME": {
    "param1": value,
    "param2": value
  },
  "output": {
    "step": true,
    "stl": true,
    "tolerance": 0.1
  }
}
```

- `units` is always `"mm"`
- `material_hint` is informational only (not used in geometry)
- The template-specific section key matches the template name exactly
- `output.tolerance` is optional (default varies by template)

## Creating Custom Templates

### Step 1: Create template files

Create these files under `templates_candidate/{name}/`:

| File | Purpose |
|------|---------|
| `schema.json` | JSON Schema (Draft 2020-12) with parameter constraints |
| `generator.py` | Python entry point: calls FreeCAD subprocess |
| `freecad_generate.py` | FreeCAD script: builds geometry using Part API |
| `examples/basic.json` | Valid example parameter set |

### Step 2: Register as candidate

```
propose_template(name, purpose, tags)
```

### Step 3: Verify and promote

```
verify_template(name)
```

On success, the template moves from `templates_candidate/` to `templates/` and becomes available for generation.

For detailed template creation guide with code examples, read `docs/template-guide.md`.

## Common Issues

### "Unknown template" error
The template is not verified. Check with `list_templates`. If it is a candidate, run `verify_template` first.

### Validation fails with schema error
Parameters do not match the template's JSON Schema. Use `get_template_schema` to check required fields, types, and constraints. Common mistakes:
- Missing required fields (`units`, `output`, template section)
- Wrong nesting level (params must be inside the template-named section)
- Negative dimensions (all dimensions require `exclusiveMinimum: 0`)

### FreeCAD not found
Run `check_freecad` to diagnose. Set the `FCGEN_FREECADCMD` environment variable to the full path of `freecadcmd`.

### Assembly part ID conflict
Each part `id` must be unique. Use descriptive names like `bolt_1`, `bracket_upper`, `leg_front_left`.

## Performance Notes

- Take your time to validate before generating
- Quality is more important than speed
- Do not skip the validate_params step
