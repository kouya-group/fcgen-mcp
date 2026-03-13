# MCP Tools Reference

fcgen exposes 11 MCP tools for parametric CAD part generation and assembly.
All tools are registered on the `fcgen` FastMCP server.

---

## 1. check_freecad

Check if FreeCAD is available and return version information.
Use this to verify the environment before attempting part generation.

### Parameters

None.

### Return Value

| Key                    | Type           | Description                                      |
|------------------------|----------------|--------------------------------------------------|
| `available`            | `bool`         | Whether freecadcmd was found on the system       |
| `version`              | `str \| null`  | Detected FreeCAD version (e.g. `"1.0.0"`)        |
| `path`                 | `str \| null`  | Absolute path to the freecadcmd executable        |
| `compatible`           | `bool \| null` | Whether the detected version meets the minimum    |
| `min_version`          | `str`          | Minimum supported version (e.g. `"0.19.0"`)       |
| `recommended_version`  | `str`          | Recommended version (e.g. `"1.0.0"`)              |
| `tested_versions`      | `list[str]`    | Versions the tool has been tested against          |

### Example

**Call:**
```json
{"tool": "check_freecad"}
```

**Response:**
```json
{
  "available": true,
  "version": "1.0.0",
  "path": "C:\\Program Files\\FreeCAD 1.0\\bin\\freecadcmd.exe",
  "compatible": true,
  "min_version": "0.19.0",
  "recommended_version": "1.0.0",
  "tested_versions": ["0.21", "1.0"]
}
```

---

## 2. list_templates

List all available verified templates. Returns each template's purpose, tags,
parameter count, top-level schema keys, and whether an example is available.

### Parameters

None.

### Return Value

| Key         | Type   | Description                             |
|-------------|--------|-----------------------------------------|
| `templates` | `dict` | Map of template name to template info   |

Each template info object:

| Key              | Type        | Description                                        |
|------------------|-------------|----------------------------------------------------|
| `purpose`        | `str`       | Human-readable description of what the template makes |
| `tags`           | `list[str]` | Categorization tags                                 |
| `param_count`    | `int`       | Number of leaf parameters (excluding units/output)   |
| `top_level_keys` | `list[str]` | Top-level JSON Schema property names                 |
| `has_example`    | `bool`      | Whether `examples/basic.json` exists                 |

### Example

**Call:**
```json
{"tool": "list_templates"}
```

**Response:**
```json
{
  "templates": {
    "adapter_plate": {
      "purpose": "Flat plate with two bolt circle patterns",
      "tags": ["structural", "mounting", "plate"],
      "param_count": 12,
      "top_level_keys": ["units", "material_hint", "adapter_plate", "output"],
      "has_example": true
    },
    "bracket": {
      "purpose": "L-bracket with configurable holes",
      "tags": ["structural", "mounting"],
      "param_count": 10,
      "top_level_keys": ["units", "material_hint", "bracket", "output"],
      "has_example": true
    },
    "bolt": {
      "purpose": "Simple cylindrical bolt with head",
      "tags": ["fastener", "bolt"],
      "param_count": 4,
      "top_level_keys": ["units", "material_hint", "bolt", "output"],
      "has_example": true
    },
    "table_top": {
      "purpose": "Flat table top plate with optional edge fillet",
      "tags": ["furniture", "table"],
      "param_count": 4,
      "top_level_keys": ["units", "material_hint", "table_top", "output"],
      "has_example": true
    },
    "simple_leg": {
      "purpose": "Rectangular leg with chamfer and mounting hole",
      "tags": ["furniture", "leg"],
      "param_count": 5,
      "top_level_keys": ["units", "material_hint", "simple_leg", "output"],
      "has_example": true
    }
  }
}
```

---

## 3. get_template_schema

Return the full JSON Schema for a given template. Use this to inspect all
available parameters, types, defaults, and constraints before generating a part.

### Parameters

| Name       | Type  | Required | Description                   |
|------------|-------|----------|-------------------------------|
| `template` | `str` | Yes      | Name of the template          |

### Return Value

The full JSON Schema dictionary for the template, or an error dict if the
template is not found.

**On success:** JSON Schema dict (see JSON Schema Draft 2020-12).

**On error:**
```json
{"error": "Unknown template: foo"}
```

### Example

**Call:**
```json
{"tool": "get_template_schema", "template": "bolt"}
```

**Response:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["units", "bolt", "output"],
  "properties": {
    "units": {"type": "string", "const": "mm"},
    "material_hint": {"type": "string"},
    "bolt": {
      "type": "object",
      "additionalProperties": false,
      "required": ["diameter", "length", "head_diameter", "head_height"],
      "properties": {
        "diameter": {"type": "number", "exclusiveMinimum": 0.0},
        "length": {"type": "number", "exclusiveMinimum": 0.0},
        "head_diameter": {"type": "number", "exclusiveMinimum": 0.0},
        "head_height": {"type": "number", "exclusiveMinimum": 0.0}
      }
    },
    "output": {
      "type": "object",
      "additionalProperties": false,
      "required": ["step", "stl"],
      "properties": {
        "step": {"type": "boolean"},
        "stl": {"type": "boolean"},
        "tolerance": {"type": "number", "exclusiveMinimum": 0.0}
      }
    }
  }
}
```

---

## 4. get_template_example

Return an example parameter JSON for a given template. Use this as a starting
point to understand the expected input format and typical values.

### Parameters

| Name       | Type  | Required | Description                   |
|------------|-------|----------|-------------------------------|
| `template` | `str` | Yes      | Name of the template          |

### Return Value

The example parameters dictionary, or an error dict.

**On error:**
```json
{"error": "No example found for template: foo"}
```

### Example

**Call:**
```json
{"tool": "get_template_example", "template": "bolt"}
```

**Response:**
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

## 5. validate_params

Validate parameters against the template's JSON Schema and semantic rules
without generating any output. Use this as a dry-run safety check before
calling `generate_part`.

### Parameters

| Name       | Type   | Required | Description                          |
|------------|--------|----------|--------------------------------------|
| `template` | `str`  | Yes      | Name of the template                 |
| `params`   | `dict` | Yes      | Parameter dictionary to validate     |

### Return Value

| Key     | Type   | Description                                   |
|---------|--------|-----------------------------------------------|
| `valid` | `bool` | Whether the parameters passed all checks       |
| `error` | `str`  | Error message (only present when `valid=false`) |

### Example

**Call (valid):**
```json
{
  "tool": "validate_params",
  "template": "bolt",
  "params": {
    "units": "mm",
    "bolt": {"diameter": 5.0, "length": 20.0, "head_diameter": 8.0, "head_height": 3.5},
    "output": {"step": true, "stl": true}
  }
}
```

**Response:**
```json
{"valid": true}
```

**Call (invalid):**
```json
{
  "tool": "validate_params",
  "template": "bolt",
  "params": {
    "units": "mm",
    "bolt": {"diameter": -1, "length": 20.0, "head_diameter": 8.0, "head_height": 3.5},
    "output": {"step": true, "stl": true}
  }
}
```

**Response:**
```json
{"valid": false, "error": "Schema validation failed at 'bolt.diameter': -1 is less than or equal to the minimum of 0"}
```

---

## 6. find_template

Search for templates matching a given purpose description. Returns results
ranked by simplicity, preferring templates with fewer parameters.

### Parameters

| Name      | Type  | Required | Description                                |
|-----------|-------|----------|--------------------------------------------|
| `purpose` | `str` | Yes      | Purpose description to search for          |

### Return Value

| Key       | Type         | Description                            |
|-----------|--------------|----------------------------------------|
| `ok`      | `bool`       | Whether the search succeeded           |
| `results` | `list[dict]` | Matching templates sorted by param_count (ascending) |

Each result contains:

| Key           | Type        | Description                                |
|---------------|-------------|--------------------------------------------|
| `name`        | `str`       | Template name                              |
| `purpose`     | `str`       | Purpose description                        |
| `tags`        | `list[str]` | Tags                                       |
| `param_count` | `int`       | Number of leaf parameters                  |
| `status`      | `str`       | Template status (`"verified"`)             |
| `source`      | `str`       | Origin (`"builtin"` or `"generated"`)      |

### Example

**Call:**
```json
{"tool": "find_template", "purpose": "bolt"}
```

**Response:**
```json
{
  "ok": true,
  "results": [
    {
      "name": "bolt",
      "status": "verified",
      "source": "generated",
      "content_hash": "6e892b3c...",
      "param_count": 4,
      "purpose": "Simple cylindrical bolt with head",
      "tags": ["fastener", "bolt"],
      "added_at": "2026-03-05T05:41:46.588385+00:00",
      "verified_at": "2026-03-05T05:41:50.085304+00:00"
    }
  ]
}
```

---

## 7. generate_part

Generate a single CAD part from a verified template and parameters. The part
is generated by invoking FreeCAD headlessly via `freecadcmd`.

### Parameters

| Name       | Type   | Required | Default        | Description                                      |
|------------|--------|----------|----------------|--------------------------------------------------|
| `template` | `str`  | Yes      |                | Name of a verified template                      |
| `params`   | `dict` | Yes      |                | Parameters matching the template's JSON Schema   |
| `out_name` | `str`  | No       | `""` (uses template name) | Output subfolder name under `output/`  |

### Return Value

**On success:**

| Key      | Type   | Description                        |
|----------|--------|------------------------------------|
| `ok`     | `bool` | `true`                             |
| `result` | `dict` | Generation result (see below)      |

Result object:

| Key              | Type   | Description                                      |
|------------------|--------|--------------------------------------------------|
| `template`       | `str`  | Template name used                               |
| `artifact_hash`  | `str`  | SHA-256 hash of the canonicalized parameters     |
| `freecad_version`| `str`  | FreeCAD version used for generation              |
| `outputs`        | `dict` | Map of output file paths                         |

Outputs object:

| Key           | Type  | Description                        |
|---------------|-------|------------------------------------|
| `step`        | `str` | Path to generated STEP file        |
| `stl`         | `str` | Path to generated STL file         |
| `report_json` | `str` | Path to JSON geometry report       |
| `report_md`   | `str` | Path to Markdown geometry report   |
| `log`         | `str` | Path to generation log             |

**On error:**
```json
{"ok": false, "error": "error message"}
```

### Example

**Call:**
```json
{
  "tool": "generate_part",
  "template": "bolt",
  "params": {
    "units": "mm",
    "material_hint": "steel",
    "bolt": {"diameter": 5.0, "length": 20.0, "head_diameter": 8.0, "head_height": 3.5},
    "output": {"step": true, "stl": true, "tolerance": 0.1}
  },
  "out_name": "bolt_m5"
}
```

**Response:**
```json
{
  "ok": true,
  "result": {
    "template": "bolt",
    "artifact_hash": "e6e0dc054496065a0bdb530d2a1204e165cd86ed9b1da75701a18dec6e98fd01",
    "freecad_version": "1.0.0",
    "outputs": {
      "step": "C:\\Users\\chibi\\Project\\fcgen\\output\\bolt_m5\\model.step",
      "stl": "C:\\Users\\chibi\\Project\\fcgen\\output\\bolt_m5\\model.stl",
      "report_json": "C:\\Users\\chibi\\Project\\fcgen\\output\\bolt_m5\\report.json",
      "report_md": "C:\\Users\\chibi\\Project\\fcgen\\output\\bolt_m5\\report.md",
      "log": "C:\\Users\\chibi\\Project\\fcgen\\output\\bolt_m5\\log.txt"
    }
  }
}
```

---

## 8. generate_assembly

Generate a multi-part assembly. Each part is generated individually from its
template, then all parts are combined into a single assembly STEP/STL file
using FreeCAD placement transforms.

### Parameters

| Name       | Type   | Required | Default      | Description                                  |
|------------|--------|----------|--------------|----------------------------------------------|
| `spec`     | `dict` | Yes      |              | Assembly specification (see Assembly Guide)  |
| `out_name` | `str`  | No       | `"assembly"` | Output subfolder name under `output/`        |

### Return Value

**On success:**

| Key      | Type   | Description                        |
|----------|--------|------------------------------------|
| `ok`     | `bool` | `true`                             |
| `result` | `dict` | Assembly result (see below)        |

Result object:

| Key             | Type         | Description                              |
|-----------------|--------------|------------------------------------------|
| `mode`          | `str`        | Always `"assembly"`                      |
| `artifact_hash` | `str`        | SHA-256 hash of the full assembly spec   |
| `parts`         | `list[dict]` | Per-part generation results              |
| `outputs`       | `dict`       | Assembly-level output file paths         |

Each part result:

| Key             | Type   | Description                                    |
|-----------------|--------|------------------------------------------------|
| `id`            | `str`  | Part identifier from the spec                  |
| `template`      | `str`  | Template used                                  |
| `artifact_hash` | `str`  | Hash of this part's parameters                 |
| `placement`     | `dict` | `{position: [x,y,z], rotation: [yaw,pitch,roll]}` |
| `outputs`       | `dict` | Part-level output file paths                   |

Assembly-level outputs:

| Key    | Type  | Description                          |
|--------|-------|--------------------------------------|
| `step` | `str` | Path to combined assembly STEP file  |
| `stl`  | `str` | Path to combined assembly STL file   |
| `log`  | `str` | Path to assembly log                 |

**On error:**
```json
{"ok": false, "error": "error message"}
```

### Example

**Call:**
```json
{
  "tool": "generate_assembly",
  "spec": {
    "units": "mm",
    "parts": [
      {
        "id": "base",
        "template": "adapter_plate",
        "params": {"units": "mm", "adapter_plate": {"size": {"length": 140, "width": 140}, "thickness": 6, "corner_radius": 0, "pattern_a": {"count": 4, "hole_diameter": 6.6, "pcd": 90, "angle_deg": 0}, "pattern_b": {"count": 6, "hole_diameter": 5.5, "pcd": 110, "angle_deg": 15}}, "output": {"step": true, "stl": true}},
        "placement": {"position": [0, 0, 0], "rotation": [0, 0, 0]}
      },
      {
        "id": "bolt_1",
        "template": "bolt",
        "params": {"units": "mm", "bolt": {"diameter": 5, "length": 20, "head_diameter": 8, "head_height": 3.5}, "output": {"step": true, "stl": true}},
        "placement": {"position": [53.126, 14.235, 9.0], "rotation": [0, 0, 0]}
      }
    ],
    "output": {"step": true, "stl": true}
  },
  "out_name": "my_assembly"
}
```

**Response:**
```json
{
  "ok": true,
  "result": {
    "mode": "assembly",
    "artifact_hash": "abc123...",
    "parts": [
      {
        "id": "base",
        "template": "adapter_plate",
        "artifact_hash": "def456...",
        "placement": {"position": [0, 0, 0], "rotation": [0, 0, 0]},
        "outputs": {"step": "...", "stl": "...", "report_json": "...", "report_md": "...", "log": "..."}
      },
      {
        "id": "bolt_1",
        "template": "bolt",
        "artifact_hash": "ghi789...",
        "placement": {"position": [53.126, 14.235, 9.0], "rotation": [0, 0, 0]},
        "outputs": {"step": "...", "stl": "...", "report_json": "...", "report_md": "...", "log": "..."}
      }
    ],
    "outputs": {
      "step": "C:\\...\\output\\my_assembly\\assembly.step",
      "stl": "C:\\...\\output\\my_assembly\\assembly.stl",
      "log": "C:\\...\\output\\my_assembly\\log.txt"
    }
  }
}
```

---

## 9. list_candidates

List all candidate (unverified) templates. These templates have been proposed
but not yet passed verification.

### Parameters

None.

### Return Value

| Key          | Type   | Description                                    |
|--------------|--------|------------------------------------------------|
| `ok`         | `bool` | Whether the operation succeeded                |
| `candidates` | `dict` | Map of candidate template name to entry dict   |

Each entry contains the same fields as a registry entry: `status`, `source`,
`content_hash`, `param_count`, `purpose`, `tags`, `added_at`, `verified_at`.

### Example

**Call:**
```json
{"tool": "list_candidates"}
```

**Response (no candidates):**
```json
{"ok": true, "candidates": {}}
```

**Response (with candidates):**
```json
{
  "ok": true,
  "candidates": {
    "washer": {
      "status": "candidate",
      "source": "generated",
      "content_hash": "abc123...",
      "param_count": 3,
      "purpose": "Flat washer with inner and outer diameter",
      "tags": ["fastener"],
      "added_at": "2026-03-05T06:00:00+00:00",
      "verified_at": null
    }
  }
}
```

---

## 10. propose_template

Register a new template as a candidate. The template files (`generator.py`,
`schema.json`, `freecad_generate.py`, etc.) must already exist under
`templates_candidate/{name}/` before calling this tool.

### Parameters

| Name      | Type              | Required | Default       | Description                          |
|-----------|-------------------|----------|---------------|--------------------------------------|
| `name`    | `str`             | Yes      |               | Template name (directory name)       |
| `purpose` | `str`             | Yes      |               | Human-readable purpose description   |
| `tags`    | `list[str] \| None` | No     | `None`        | Categorization tags                  |
| `source`  | `str`             | No       | `"generated"` | Origin of the template               |

### Return Value

**On success:**

| Key     | Type   | Description                              |
|---------|--------|------------------------------------------|
| `ok`    | `bool` | `true`                                   |
| `entry` | `dict` | The new registry entry for this candidate |

Entry fields: `status` (`"candidate"`), `source`, `content_hash`, `param_count`,
`purpose`, `tags`, `added_at`, `verified_at` (`null`).

**On error:**
```json
{"ok": false, "error": "error message"}
```

### Example

**Call:**
```json
{
  "tool": "propose_template",
  "name": "washer",
  "purpose": "Flat washer with inner and outer diameter",
  "tags": ["fastener"],
  "source": "generated"
}
```

**Response:**
```json
{
  "ok": true,
  "entry": {
    "status": "candidate",
    "source": "generated",
    "content_hash": "abc123...",
    "param_count": 3,
    "purpose": "Flat washer with inner and outer diameter",
    "tags": ["fastener"],
    "added_at": "2026-03-05T06:00:00+00:00",
    "verified_at": null
  }
}
```

---

## 11. verify_template

Run verification checks on a candidate template. If all checks pass, promote
it to verified status so it becomes available for part generation.

Verification performs the following checks:
1. `schema.json` exists and is valid JSON
2. `generator.py` exists and defines a `generate()` function
3. If `examples/basic.json` exists, it validates against the schema
4. The template directory is moved from `templates_candidate/` to `templates/`
5. The registry entry is updated to `status: "verified"`

### Parameters

| Name   | Type  | Required | Description                                |
|--------|-------|----------|--------------------------------------------|
| `name` | `str` | Yes      | Name of the candidate template to verify   |

### Return Value

**On success:**

| Key     | Type   | Description                                |
|---------|--------|--------------------------------------------|
| `ok`    | `bool` | `true`                                     |
| `entry` | `dict` | The updated registry entry (now verified)  |

Entry fields: `status` (`"verified"`), `source`, `content_hash`, `param_count`,
`purpose`, `tags`, `added_at`, `verified_at`.

**On error:**
```json
{"ok": false, "error": "error message"}
```

### Example

**Call:**
```json
{"tool": "verify_template", "name": "washer"}
```

**Response:**
```json
{
  "ok": true,
  "entry": {
    "status": "verified",
    "source": "generated",
    "content_hash": "def456...",
    "param_count": 3,
    "purpose": "Flat washer with inner and outer diameter",
    "tags": ["fastener"],
    "added_at": "2026-03-05T06:00:00+00:00",
    "verified_at": "2026-03-05T06:05:00+00:00"
  }
}
```
