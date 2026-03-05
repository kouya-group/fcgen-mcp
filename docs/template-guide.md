# Template Creation Guide

This guide explains how to create a new parametric CAD template for fcgen.
Templates follow a two-stage lifecycle: **candidate** (proposed, unverified)
then **verified** (approved, available for part generation).

---

## Required Files

Every template must contain the following files in its directory:

```
templates_candidate/{name}/
  schema.json            # JSON Schema defining all parameters
  generator.py           # Python entry point called by the runner
  freecad_generate.py    # FreeCAD script that builds the geometry
  examples/
    basic.json           # Example parameter set for testing
```

| File                   | Purpose                                                  |
|------------------------|----------------------------------------------------------|
| `schema.json`          | Defines parameter types, constraints, and required fields |
| `generator.py`         | Bridges between fcgen runner and FreeCAD subprocess       |
| `freecad_generate.py`  | FreeCAD script that creates the 3D geometry               |
| `examples/basic.json`  | A complete, valid example parameter set                   |

---

## schema.json Format

The schema uses **JSON Schema Draft 2020-12**. It defines the full parameter
dictionary structure that users pass to `generate_part` or `validate_params`.

### Conventions

- The root object must require `"units"` and `"output"` at minimum.
- `units` is always `{"type": "string", "const": "mm"}`.
- `material_hint` is an optional string for informational purposes (not used
  in geometry generation).
- The main geometry parameters go under a key matching the template name
  (e.g. `"bolt"`, `"bracket"`, `"adapter_plate"`).
- `output` controls STEP/STL export and optional tolerance.
- Use `"additionalProperties": false` at each object level to catch typos.
- Use `"exclusiveMinimum": 0.0` for dimensions that must be positive.

### Bolt Schema (Complete Example)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["units", "bolt", "output"],
  "properties": {
    "units": { "type": "string", "const": "mm" },
    "material_hint": { "type": "string" },
    "bolt": {
      "type": "object",
      "additionalProperties": false,
      "required": ["diameter", "length", "head_diameter", "head_height"],
      "properties": {
        "diameter": { "type": "number", "exclusiveMinimum": 0.0 },
        "length": { "type": "number", "exclusiveMinimum": 0.0 },
        "head_diameter": { "type": "number", "exclusiveMinimum": 0.0 },
        "head_height": { "type": "number", "exclusiveMinimum": 0.0 }
      }
    },
    "output": {
      "type": "object",
      "additionalProperties": false,
      "required": ["step", "stl"],
      "properties": {
        "step": { "type": "boolean" },
        "stl": { "type": "boolean" },
        "tolerance": { "type": "number", "exclusiveMinimum": 0.0 }
      }
    }
  }
}
```

### Parameter Counting

fcgen counts "leaf parameters" for complexity ranking, excluding `units`,
`output`, and `material_hint`. In the bolt schema above, the leaf parameters
are: `diameter`, `length`, `head_diameter`, `head_height` -- so `param_count`
is 4.

---

## generator.py

This file is the Python entry point loaded by the fcgen runner. It must define
a `generate` function with the following signature:

```python
def generate(params: dict, step_path: Path, stl_path: Path) -> None:
```

| Parameter   | Type   | Description                               |
|-------------|--------|-------------------------------------------|
| `params`    | `dict` | Validated parameter dictionary             |
| `step_path` | `Path` | Target path for the STEP output file       |
| `stl_path`  | `Path` | Target path for the STL output file        |

The function must:
1. Create the output directory if it does not exist.
2. Write the parameters to a JSON file for the FreeCAD subprocess.
3. Call `run_script()` from `fcgen.core.freecadcmd` to invoke the FreeCAD
   script.

### Bolt generator.py (Complete Example)

```python
import json
from pathlib import Path

from fcgen.core.freecadcmd import run_script

def generate(params: dict, step_path: Path, stl_path: Path) -> None:
    step_path.parent.mkdir(parents=True, exist_ok=True)
    params_path = step_path.parent / "_fcgen_params.json"
    params_path.write_text(json.dumps(params, indent=2), encoding="utf-8")
    script_path = Path(__file__).resolve().parent / "freecad_generate.py"
    run_script(
        script_path=script_path,
        params_path=params_path,
        step_path=step_path,
        stl_path=stl_path,
        output_flags=params.get("output", {}),
    )
```

This pattern is the same across all templates. The only template-specific logic
lives in `freecad_generate.py`.

---

## freecad_generate.py

This is a FreeCAD script executed via `freecadcmd` as a subprocess. It has
access to the full FreeCAD Python API (`FreeCAD`, `Part`, `Mesh`, etc.).

### Structure

The script receives three arguments via `--pass`:
1. Path to the parameters JSON file
2. Path for the STEP output
3. Path for the STL output

Standard boilerplate:

```python
import json
import sys
import traceback

import FreeCAD as App
import Mesh
import Part


def main() -> int:
    if "--pass" in sys.argv:
        idx = sys.argv.index("--pass")
        args = sys.argv[idx + 1:]
    else:
        args = sys.argv[-3:]

    if len(args) < 3:
        raise RuntimeError("Usage: freecad_generate.py <params.json> <model.step> <model.stl>")

    params_path = args[0]
    step_path = args[1]
    stl_path = args[2]
    with open(params_path, "r", encoding="utf-8") as f:
        params = json.load(f)

    # --- Build geometry here ---
    # ... create Part shapes using FreeCAD API ...

    # --- Export ---
    doc = App.ActiveDocument or App.newDocument("fcgen")
    Part.show(shape)
    doc = App.ActiveDocument
    doc.recompute()
    obj = doc.Objects[-1]

    if params.get("output", {}).get("step", True):
        Part.export([obj], step_path)
    if params.get("output", {}).get("stl", True):
        Mesh.export([obj], stl_path)
    return 0


try:
    raise SystemExit(main())
except SystemExit:
    raise
except Exception:
    traceback.print_exc()
    raise SystemExit(1)
```

### Bolt freecad_generate.py (Complete Example)

```python
import json
import sys
import traceback

import FreeCAD as App
import Mesh
import Part


def main() -> int:
    if "--pass" in sys.argv:
        idx = sys.argv.index("--pass")
        args = sys.argv[idx + 1:]
    else:
        args = sys.argv[-3:]

    if len(args) < 3:
        raise RuntimeError("Usage: freecad_generate.py <params.json> <model.step> <model.stl>")

    params_path = args[0]
    step_path = args[1]
    stl_path = args[2]
    with open(params_path, "r", encoding="utf-8") as f:
        params = json.load(f)

    b = params["bolt"]
    diameter = float(b["diameter"])
    length = float(b["length"])
    head_diameter = float(b["head_diameter"])
    head_height = float(b["head_height"])

    # Shaft: cylinder along -Z from Z=0 downward
    shaft = Part.makeCylinder(
        diameter / 2.0, length,
        App.Vector(0, 0, -length), App.Vector(0, 0, 1)
    )

    # Head: cylinder from Z=0 upward
    head = Part.makeCylinder(
        head_diameter / 2.0, head_height,
        App.Vector(0, 0, 0), App.Vector(0, 0, 1)
    )

    shape = head.fuse(shaft)

    doc = App.ActiveDocument or App.newDocument("fcgen")
    Part.show(shape)
    doc = App.ActiveDocument
    doc.recompute()
    obj = doc.Objects[-1]

    if params.get("output", {}).get("step", True):
        Part.export([obj], step_path)
    if params.get("output", {}).get("stl", True):
        Mesh.export([obj], stl_path)
    return 0


try:
    raise SystemExit(main())
except SystemExit:
    raise
except Exception:
    traceback.print_exc()
    raise SystemExit(1)
```

### Key Points

- The bolt head sits at Z=0 and extends upward by `head_height`.
- The shaft extends downward from Z=0 by `length`.
- `Part.makeCylinder(radius, height, base_point, direction)` creates a solid
  cylinder.
- `head.fuse(shaft)` performs a boolean union of the two cylinders.
- Always call `doc.recompute()` before exporting.
- Exit with code 0 on success, 1 on failure.

---

## examples/basic.json

A complete, valid parameter set that exercises the template. This file is used
during verification to ensure the schema and generator work correctly.

### Bolt Example

```json
{
  "units": "mm",
  "material_hint": "steel",
  "bolt": {
    "diameter": 5.0,
    "length": 20.0,
    "head_diameter": 8.0,
    "head_height": 3.5
  },
  "output": {
    "step": true,
    "stl": true,
    "tolerance": 0.1
  }
}
```

---

## Template Lifecycle

### 1. Create the Template Files

Create the directory and all required files:

```
templates_candidate/my_template/
  schema.json
  generator.py
  freecad_generate.py
  examples/
    basic.json
```

### 2. Propose the Template

Register the template as a candidate using the `propose_template` MCP tool:

```json
{
  "tool": "propose_template",
  "name": "my_template",
  "purpose": "Description of what this template creates",
  "tags": ["category1", "category2"],
  "source": "generated"
}
```

This adds an entry to `registry.json` with `status: "candidate"`. The template
is not yet available for part generation.

### 3. Verify the Template

Run verification using the `verify_template` MCP tool:

```json
{
  "tool": "verify_template",
  "name": "my_template"
}
```

Verification checks:
1. `schema.json` is present and parseable as valid JSON.
2. `generator.py` is present and defines a `generate()` function (checked via
   AST parsing -- the function is not executed).
3. If `examples/basic.json` exists and `jsonschema` is installed, the example
   is validated against the schema.

If all checks pass:
- The template directory is **moved** from `templates_candidate/my_template/`
  to `templates/my_template/`.
- The registry entry is updated to `status: "verified"` with a timestamp.
- A content hash (SHA-256 of `schema.json`, `generator.py`,
  `freecad_generate.py`) is computed and stored.

### 4. Use the Template

Once verified, the template is available through all generation tools:

```json
{"tool": "generate_part", "template": "my_template", "params": {...}}
```

---

## Content Hash and Integrity

Each template has a `content_hash` in the registry computed from the SHA-256
of three canonical files (sorted alphabetically):
- `freecad_generate.py`
- `generator.py`
- `schema.json`

The registry provides a `check_integrity(name)` method to verify that the
stored hash matches the current file contents. This detects unauthorized
modifications to verified templates.

---

## Checklist for New Templates

- [ ] `schema.json` uses JSON Schema Draft 2020-12 with `"additionalProperties": false`
- [ ] Root object requires `"units"` and `"output"` at minimum
- [ ] All dimensions use `"exclusiveMinimum": 0.0`
- [ ] `generator.py` defines `generate(params, step_path, stl_path)`
- [ ] `generator.py` calls `run_script()` from `fcgen.core.freecadcmd`
- [ ] `freecad_generate.py` handles `--pass` argument parsing
- [ ] `freecad_generate.py` exports both STEP and STL based on output flags
- [ ] `freecad_generate.py` exits with code 0 on success, 1 on failure
- [ ] `examples/basic.json` is a valid instance of the schema
- [ ] Template directory is placed under `templates_candidate/` before proposing
