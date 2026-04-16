---
name: fcgen
description: Generate parametric CAD parts and assemblies via the fcgen MCP server. Use when user asks to "create a CAD part", "generate a bracket", "build a desk", "make an assembly", "design a bolt", "M5 bolt", "soccer ball", "LEGO brick", "Minecraft block", "3D model", "STEP file", "STL file", mentions template names like "bracket", "adapter_plate", "enclosure", "bolt", "table_top", "simple_leg", "sphere", "cup", "lego_brick", "minecraft_block", or asks about FreeCAD generation. Do NOT use for general 3D modeling questions unrelated to fcgen templates.
---

# fcgen -- Parametric CAD Generation via MCP

Generate verified parametric CAD parts (STEP/STL) through the fcgen MCP server and FreeCAD.

## Critical Rules

- ALWAYS call `find_template` first to resolve constraints and presets
- NEVER change canonical parameter values without explicit user confirmation
- NEVER skip `validate_params` before `generate_part` or `generate_assembly`
- If `validate_params` returns warnings, inform the user before proceeding
- ALL dimensions are in millimeters (mm)
- Each part `id` in an assembly MUST be unique
- Only verified templates can be used for generation

## Documentation

This skill uses the project's docs/ as its single source of truth.
Read these files for detailed reference:

- `docs/mcp-tools.md` -- Full MCP tools reference (parameters, return values, examples)
- `docs/assembly-guide.md` -- Assembly spec format, placement rules, examples
- `docs/template-guide.md` -- Custom template creation guide
- `docs/quickstart.md` -- Quick start guide and available templates

## Available MCP Tools

| Tool | Purpose |
|------|---------|
| `check_freecad` | Verify FreeCAD is installed and compatible |
| `list_templates` | List all verified templates |
| `get_template_schema` | Get full JSON Schema for a template |
| `get_template_example` | Get working example parameters |
| `get_template_constraints` | Get canonical/variant/linked/configurable constraints |
| `validate_params` | Dry-run validation with canonical deviation warnings |
| `find_template` | Search by name, purpose, tags, or presets (e.g. "M5 bolt 20mm") |
| `generate_part` | Generate single part (STEP/STL) |
| `generate_assembly` | Generate multi-part assembly with interference check |
| `list_candidates` | List unverified candidate templates |
| `propose_template` | Register new template as candidate |
| `verify_template` | Verify and promote candidate to verified |

## Workflow: Generate a Single Part

### Step 1: Find template with constraints

Call `find_template(purpose)` with the user's description. This searches templates, constraints, and presets. Example queries: "M5 bolt 20mm", "soccer ball", "LEGO 2x4".

If the result includes `matched_preset`, use the resolved parameters directly.

### Step 2: Check constraints

If Step 1 did not resolve a preset, call `get_template_constraints(template)` to understand:
- **canonical**: Fixed by specification. Do NOT change without user confirmation.
- **linked**: One key determines others (e.g. "M5" sets diameter/head_d/head_h). Use presets.
- **variant**: Pick from predefined options (e.g. soccer ball sizes).
- **configurable**: Freely adjustable by the user.

### Step 3: Build parameters

- Start from `get_template_example` as a base
- Apply resolved preset values (canonical/linked/variant)
- Set configurable params from user's requirements

### Step 4: Validate

Call `validate_params(template, params)`.
- If `valid: false`, fix the error and re-validate.
- If `warnings` are present (canonical deviations), inform the user.

### Step 5: Generate

Call `generate_part(template, params, out_name)` to produce STEP/STL files.

## Parameter Constraints

### 4 Constraint Types

| Type | Meaning | Action |
|------|---------|--------|
| **canonical** | Fixed by specification | Do NOT change. Ask user if override needed. |
| **linked** | One key determines others | Use preset. If no match, suggest closest. |
| **variant** | Choose from options | Pick best fit for user's intent. |
| **configurable** | Free to set | Adjust to user's requirements. |

### Examples

- "M5 bolt 20mm" → `linked:M5` resolves diameter=5, head_d=8, head_h=3.5. Only length=20 is free.
- "Minecraft block" → `canonical:size=1000mm`. Do not set to 50mm.
- "Soccer ball" → `variant:soccer_size_5` resolves radius=110mm.
- "Table 800mm wide" → `configurable:width=800`. All params are free.

## Workflow: Generate an Assembly

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
2. For each part: resolve constraints via `find_template` or `get_template_constraints`
3. Validate each part's params individually with `validate_params`
4. Build the assembly spec JSON with unique `id` per part
5. Call `generate_assembly(spec, out_name)`
6. Check the `interference` field in the result for part collisions

### Interference Check

`generate_assembly` automatically checks all part pairs for physical overlap. The result includes:

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
- A detailed report is saved as `interference_report.json` in the output directory

## Available Templates Quick Reference

| Template | Purpose | Key Params |
|----------|---------|------------|
| `bracket` | L-bracket with holes | thickness, leg_a, leg_b, width, holes |
| `adapter_plate` | Flat plate with bolt circle patterns | size, thickness, pattern_a, pattern_b |
| `enclosure` | Box with lid and screw bosses | width, depth, height, wall, corner_radius |
| `bolt` | Cylindrical bolt with head | diameter, length, head_d, head_h (linked: M3-M20) |
| `table_top` | Flat plate with edge fillet | width, depth, thickness, edge_fillet |
| `simple_leg` | Rectangular leg with chamfer | width, depth, height, chamfer, hole_diameter |
| `sphere` | Solid sphere | radius (variants: soccer/tennis/baseball/golf/etc.) |
| `cup` | Hollow cup with handle | outer_d, height, wall, bottom (variants: espresso/mug/large) |
| `lego_brick` | LEGO-compatible brick | studs_x, studs_y, height_plates (canonical: pitch=8mm) |
| `minecraft_block` | Minecraft-style cube | size (canonical: 1000mm), chamfer, grooves |

## Parameter Structure Convention

Every template follows this structure:

```json
{
  "units": "mm",
  "material_hint": "optional_material_string",
  "TEMPLATE_NAME": { "param1": value, "param2": value },
  "output": { "step": true, "stl": true, "tolerance": 0.1 }
}
```

## Creating Custom Templates

Create files under `templates_candidate/{name}/`:

| File | Purpose |
|------|---------|
| `schema.json` | JSON Schema (Draft 2020-12) with parameter constraints |
| `constraints.json` | Canonical/variant/linked/configurable definitions |
| `generator.py` | Python entry point: calls FreeCAD subprocess |
| `freecad_generate.py` | FreeCAD script: builds geometry using Part API |
| `examples/basic.json` | Valid example parameter set |

Then: `propose_template(name, purpose, tags)` → `verify_template(name)`.

For detailed guide, read `docs/template-guide.md`.

## Common Issues

### "Unknown template" error
The template is not verified. Check with `list_templates`. If it is a candidate, run `verify_template` first.

### Validation fails with schema error
Use `get_template_schema` to check required fields. Common mistakes:
- Missing required fields (`units`, `output`, template section)
- Wrong nesting level (params must be inside the template-named section)
- Negative dimensions (all dimensions require `exclusiveMinimum: 0`)

### Canonical deviation warning
`validate_params` warns when a canonical value differs from specification. Inform the user and ask for confirmation before proceeding.

### FreeCAD not found
Run `check_freecad` to diagnose. Set `FCGEN_FREECADCMD` environment variable.

### Assembly part ID conflict
Each part `id` must be unique. Use descriptive names like `bolt_1`, `bracket_upper`.
