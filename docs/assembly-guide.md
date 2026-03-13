# Assembly Guide

This guide explains how to create multi-part assemblies in fcgen. An assembly
combines multiple individually generated parts into a single CAD model with
precise spatial placement.

---

## Assembly Spec Format

An assembly is defined by a JSON specification with the following top-level
structure:

```json
{
  "units": "mm",
  "parts": [ ... ],
  "output": {
    "step": true,
    "stl": true
  }
}
```

| Key      | Type         | Required | Description                                   |
|----------|--------------|----------|-----------------------------------------------|
| `units`  | `str`        | No       | Unit system (currently only `"mm"`)           |
| `parts`  | `list[dict]` | Yes      | Array of part definitions (at least one)      |
| `output` | `dict`       | No       | Output flags (`step`, `stl`); defaults to both true |

### Part Definition

Each entry in the `parts` array defines one part:

```json
{
  "id": "bolt_1",
  "template": "bolt",
  "params": { ... },
  "placement": {
    "position": [x, y, z],
    "rotation": [yaw, pitch, roll]
  }
}
```

| Key         | Type   | Required | Description                                    |
|-------------|--------|----------|------------------------------------------------|
| `id`        | `str`  | Yes      | Unique identifier for the part within the assembly |
| `template`  | `str`  | Yes      | Name of a verified template                    |
| `params`    | `dict` | Yes      | Full parameter dict matching the template's schema |
| `placement` | `dict` | No       | Position and rotation; defaults to origin      |

**Important:** Each `id` must be unique across all parts in the assembly.
Duplicate IDs will cause an error.

---

## Placement

Placement defines where and how a part is positioned in the assembly coordinate
system.

### Position

`position` is an array of three numbers `[x, y, z]` representing the
translation in millimeters from the assembly origin.

```json
"position": [53.126, 14.235, 9.0]
```

### Rotation

`rotation` is an array of three numbers `[yaw, pitch, roll]` representing
Euler angles **in degrees**.

```json
"rotation": [135.0, 0, 0]
```

FreeCAD internally uses `App.Rotation(yaw, pitch, roll)` to construct the
rotation. The angles follow the intrinsic ZY'X'' convention:

| Component | Axis | Description                        |
|-----------|------|------------------------------------|
| Yaw       | Z    | Rotation around the vertical axis  |
| Pitch     | Y'   | Rotation around the new Y axis     |
| Roll      | X''  | Rotation around the new X axis     |

All angles are in degrees. A rotation of `[0, 0, 0]` means no rotation
(identity orientation).

**Examples:**

| Rotation          | Effect                                   |
|-------------------|------------------------------------------|
| `[0, 0, 0]`      | No rotation (default orientation)        |
| `[90, 0, 0]`     | 90 degrees yaw around Z axis             |
| `[0, 90, 0]`     | 90 degrees pitch around Y axis           |
| `[0, 0, 90]`     | 90 degrees roll around X axis            |
| `[135, 0, 0]`    | 135 degrees yaw (used for angled brackets) |
| `[-45, 0, 0]`    | -45 degrees yaw                          |

---

## Step-by-Step Workflow

1. **Design the assembly** -- Decide which templates and parameters to use for
   each part. Determine the spatial layout (positions and rotations).

2. **Validate parameters** -- Use the `validate_params` tool to check each
   part's parameters individually before assembling.

3. **Write the assembly spec** -- Create the JSON specification with all parts,
   their parameters, and placements.

4. **Generate the assembly** -- Call `generate_assembly` with the spec:
   ```json
   {
     "tool": "generate_assembly",
     "spec": { ... },
     "out_name": "my_assembly"
   }
   ```

5. **Check the outputs** -- The tool generates:
   - Individual part files under `output/{out_name}/_parts/{part_id}/`
     - `model.step` -- STEP file for the individual part
     - `model.stl` -- STL mesh for the individual part
     - `report.json` / `report.md` -- Geometry reports
   - Combined assembly files under `output/{out_name}/`
     - `assembly.step` -- Combined STEP file with all parts placed
     - `assembly.stl` -- Combined STL mesh
     - `log.txt` -- Assembly generation log
     - `_assembly_manifest.json` -- Internal manifest used by FreeCAD

---

## Real Example: Simple Desk Assembly

This assembly creates a basic desk using `table_top` and `simple_leg` templates:
one flat top plate and four rectangular legs.

### Assembly JSON

```json
{
  "units": "mm",
  "parts": [
    {
      "id": "top",
      "template": "table_top",
      "params": {
        "units": "mm",
        "material_hint": "plywood",
        "table_top": { "width": 1200.0, "depth": 600.0, "thickness": 25.0, "edge_fillet": 3.0 },
        "output": { "step": true, "stl": true, "tolerance": 0.1 }
      },
      "placement": { "position": [0, 0, 700.0], "rotation": [0, 0, 0] }
    },
    {
      "id": "leg_front_left",
      "template": "simple_leg",
      "params": {
        "units": "mm",
        "material_hint": "wood",
        "simple_leg": { "width": 60.0, "depth": 60.0, "height": 700.0, "chamfer": 2.0, "hole_diameter": 8.0 },
        "output": { "step": true, "stl": true, "tolerance": 0.1 }
      },
      "placement": { "position": [30.0, 30.0, 0], "rotation": [0, 0, 0] }
    },
    {
      "id": "leg_front_right",
      "template": "simple_leg",
      "params": {
        "units": "mm",
        "material_hint": "wood",
        "simple_leg": { "width": 60.0, "depth": 60.0, "height": 700.0, "chamfer": 2.0, "hole_diameter": 8.0 },
        "output": { "step": true, "stl": true, "tolerance": 0.1 }
      },
      "placement": { "position": [1110.0, 30.0, 0], "rotation": [0, 0, 0] }
    },
    {
      "id": "leg_rear_left",
      "template": "simple_leg",
      "params": {
        "units": "mm",
        "material_hint": "wood",
        "simple_leg": { "width": 60.0, "depth": 60.0, "height": 700.0, "chamfer": 2.0, "hole_diameter": 8.0 },
        "output": { "step": true, "stl": true, "tolerance": 0.1 }
      },
      "placement": { "position": [30.0, 510.0, 0], "rotation": [0, 0, 0] }
    },
    {
      "id": "leg_rear_right",
      "template": "simple_leg",
      "params": {
        "units": "mm",
        "material_hint": "wood",
        "simple_leg": { "width": 60.0, "depth": 60.0, "height": 700.0, "chamfer": 2.0, "hole_diameter": 8.0 },
        "output": { "step": true, "stl": true, "tolerance": 0.1 }
      },
      "placement": { "position": [1110.0, 510.0, 0], "rotation": [0, 0, 0] }
    }
  ],
  "output": { "step": true, "stl": true }
}
```

### Part Layout

```
        ┌──────────────────────┐  ← table_top (1200x600x25mm, Z=700)
        │                      │
   ┌──┐ │                      │ ┌──┐
   │  │ │                      │ │  │
   │  │ │                      │ │  │  ← simple_leg x4 (60x60x700mm)
   │  │ │                      │ │  │
   └──┘ └──────────────────────┘ └──┘
```

| Part ID          | Template    | Position (mm)          | Description       |
|------------------|-------------|------------------------|-------------------|
| `top`            | table_top   | `[0, 0, 700]`         | Desk surface      |
| `leg_front_left` | simple_leg  | `[30, 30, 0]`         | Front-left leg    |
| `leg_front_right`| simple_leg  | `[1110, 30, 0]`       | Front-right leg   |
| `leg_rear_left`  | simple_leg  | `[30, 510, 0]`        | Rear-left leg     |
| `leg_rear_right` | simple_leg  | `[1110, 510, 0]`      | Rear-right leg    |

### Design Notes

- The **table top** is placed at Z=700mm (the height of the legs).
- The **legs** are inset 30mm from the edges of the table top.
- Legs have an 8mm mounting hole and 2mm chamfer on the bottom edges.
- Total desk height: 700mm (legs) + 25mm (top thickness) = 725mm.

### Desk Variations

See `templates/assembly_examples/` for more desk configurations:

| File                | Description                            | Dimensions            |
|---------------------|----------------------------------------|-----------------------|
| `simple_desk.json`  | Standard 4-leg desk                    | 1200 x 600 x 725mm   |
| `compact_desk.json` | Compact desk for small rooms           | 800 x 500 x 700mm    |
| `standing_desk.json`| Standing desk for stand-up work        | 1400 x 700 x 1050mm  |
| `desk_with_shelf.json` | Desk with under-shelf for storage  | 1200 x 600 x 725mm   |

---

## Real Example: plate_brackets_bolts Assembly

This assembly combines 7 parts: one adapter plate base, two L-brackets mounted
at opposing corners, and four bolts.

### Assembly JSON

```json
{
  "units": "mm",
  "parts": [
    {
      "id": "base",
      "template": "adapter_plate",
      "params": {
        "units": "mm",
        "material_hint": "al5052",
        "adapter_plate": {
          "size": {"length": 140.0, "width": 140.0},
          "thickness": 6.0,
          "corner_radius": 0.0,
          "pattern_a": {"count": 4, "hole_diameter": 6.6, "pcd": 90.0, "angle_deg": 0.0},
          "pattern_b": {"count": 6, "hole_diameter": 5.5, "pcd": 110.0, "angle_deg": 15.0}
        },
        "output": {"step": true, "stl": true, "tolerance": 0.1}
      },
      "placement": {"position": [0, 0, 0], "rotation": [0, 0, 0]}
    },
    {
      "id": "bracket_upper",
      "template": "bracket",
      "params": {
        "units": "mm",
        "material_hint": "al6061",
        "bracket": {
          "thickness": 3.0, "leg_a": 71.0, "leg_b": 60.0, "width": 25.0,
          "fillet": 1.0, "chamfer": 0.5,
          "holes": {"pattern": "line", "diameter": 5.5, "count": 2, "edge_offset": 8.0}
        },
        "output": {"step": true, "stl": true, "tolerance": 0.1}
      },
      "placement": {"position": [67.622, 17.417, 6.0], "rotation": [135.0, 0, 0]}
    },
    {
      "id": "bracket_lower",
      "template": "bracket",
      "params": {
        "units": "mm",
        "material_hint": "al6061",
        "bracket": {
          "thickness": 3.0, "leg_a": 71.0, "leg_b": 60.0, "width": 25.0,
          "fillet": 1.0, "chamfer": 0.5,
          "holes": {"pattern": "line", "diameter": 5.5, "count": 2, "edge_offset": 8.0}
        },
        "output": {"step": true, "stl": true, "tolerance": 0.1}
      },
      "placement": {"position": [-67.622, -17.417, 6.0], "rotation": [-45.0, 0, 0]}
    },
    {
      "id": "bolt_1",
      "template": "bolt",
      "params": {
        "units": "mm", "material_hint": "steel",
        "bolt": {"diameter": 5.0, "length": 20.0, "head_diameter": 8.0, "head_height": 3.5},
        "output": {"step": true, "stl": true, "tolerance": 0.1}
      },
      "placement": {"position": [53.1259, 14.2350, 9.0], "rotation": [0, 0, 0]}
    },
    {
      "id": "bolt_2",
      "template": "bolt",
      "params": {
        "units": "mm", "material_hint": "steel",
        "bolt": {"diameter": 5.0, "length": 20.0, "head_diameter": 8.0, "head_height": 3.5},
        "output": {"step": true, "stl": true, "tolerance": 0.1}
      },
      "placement": {"position": [14.2350, 53.1259, 9.0], "rotation": [0, 0, 0]}
    },
    {
      "id": "bolt_3",
      "template": "bolt",
      "params": {
        "units": "mm", "material_hint": "steel",
        "bolt": {"diameter": 5.0, "length": 20.0, "head_diameter": 8.0, "head_height": 3.5},
        "output": {"step": true, "stl": true, "tolerance": 0.1}
      },
      "placement": {"position": [-53.1259, -14.2350, 9.0], "rotation": [0, 0, 0]}
    },
    {
      "id": "bolt_4",
      "template": "bolt",
      "params": {
        "units": "mm", "material_hint": "steel",
        "bolt": {"diameter": 5.0, "length": 20.0, "head_diameter": 8.0, "head_height": 3.5},
        "output": {"step": true, "stl": true, "tolerance": 0.1}
      },
      "placement": {"position": [-14.2350, -53.1259, 9.0], "rotation": [0, 0, 0]}
    }
  ],
  "output": {
    "step": true,
    "stl": true
  }
}
```

### Part Layout

| Part ID          | Template       | Position (mm)               | Rotation (deg)    |
|------------------|----------------|-----------------------------|-------------------|
| `base`           | adapter_plate  | `[0, 0, 0]`                | `[0, 0, 0]`      |
| `bracket_upper`  | bracket        | `[67.622, 17.417, 6.0]`    | `[135, 0, 0]`    |
| `bracket_lower`  | bracket        | `[-67.622, -17.417, 6.0]`  | `[-45, 0, 0]`    |
| `bolt_1`         | bolt           | `[53.126, 14.235, 9.0]`    | `[0, 0, 0]`      |
| `bolt_2`         | bolt           | `[14.235, 53.126, 9.0]`    | `[0, 0, 0]`      |
| `bolt_3`         | bolt           | `[-53.126, -14.235, 9.0]`  | `[0, 0, 0]`      |
| `bolt_4`         | bolt           | `[-14.235, -53.126, 9.0]`  | `[0, 0, 0]`      |

### Design Notes

- The **base plate** sits at the origin with two bolt circle patterns (PCD 90mm
  and 110mm).
- The **brackets** are placed at opposite corners of the plate, offset in Z by
  the plate thickness (6mm). They use yaw rotations of 135 and -45 degrees to
  align with the bolt hole positions on the plate.
- The **bolts** are positioned at four of the inner bolt circle holes (PCD 90mm,
  at 45-degree intervals). Their Z position (9mm) places the bolt head flush
  above the plate surface plus the bracket thickness.

### Generating This Assembly

```json
{
  "tool": "generate_assembly",
  "spec": { "...the JSON above..." },
  "out_name": "assembly_bolted"
}
```

Output directory structure:
```
output/assembly_bolted/
  assembly.step
  assembly.stl
  log.txt
  _assembly_manifest.json
  _parts/
    base/
      model.step
      model.stl
      report.json
      report.md
    bracket_upper/
      model.step
      model.stl
      report.json
      report.md
    bracket_lower/
      ...
    bolt_1/
      ...
    bolt_2/
      ...
    bolt_3/
      ...
    bolt_4/
      ...
```
