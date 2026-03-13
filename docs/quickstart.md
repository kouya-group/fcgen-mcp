# Quick Start: Build a Desk in 5 Minutes

This guide walks you through generating a complete desk assembly using fcgen-mcp
and Claude (or any MCP-compatible LLM).

---

## Prerequisites

1. **Python 3.10+** installed
2. **FreeCAD 0.19+** installed (recommended: 1.0)
3. **fcgen-mcp** installed:
   ```bash
   pip install -e ".[mcp]"
   ```
4. FreeCAD path configured:
   ```bash
   # Linux/macOS
   export FCGEN_FREECADCMD="/path/to/freecadcmd"

   # Windows
   set FCGEN_FREECADCMD=C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe
   ```

---

## Step 1: Start the MCP Server

```bash
python -m fcgen.mcp.server
```

Or add to Claude Desktop's `claude_desktop_config.json`:

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

---

## Step 2: Ask Claude to Build a Desk

Simply tell Claude:

> "Build me a simple desk, 1200mm wide, 600mm deep, 725mm tall."

Claude will use the MCP tools to:
1. `list_templates` -- discover available templates
2. `get_template_example` -- see example parameters
3. `generate_assembly` -- build the desk

---

## Step 3: Manual Generation (Without Claude)

You can also call the tools directly via Python:

```python
from fcgen.mcp.server import generate_assembly

desk = {
    "units": "mm",
    "parts": [
        {
            "id": "top",
            "template": "table_top",
            "params": {
                "units": "mm",
                "table_top": {"width": 1200, "depth": 600, "thickness": 25, "edge_fillet": 3},
                "output": {"step": True, "stl": True, "tolerance": 0.1}
            },
            "placement": {"position": [0, 0, 700], "rotation": [0, 0, 0]}
        },
        {
            "id": "leg_fl",
            "template": "simple_leg",
            "params": {
                "units": "mm",
                "simple_leg": {"width": 60, "depth": 60, "height": 700, "chamfer": 2, "hole_diameter": 8},
                "output": {"step": True, "stl": True, "tolerance": 0.1}
            },
            "placement": {"position": [30, 30, 0], "rotation": [0, 0, 0]}
        },
        {
            "id": "leg_fr",
            "template": "simple_leg",
            "params": {
                "units": "mm",
                "simple_leg": {"width": 60, "depth": 60, "height": 700, "chamfer": 2, "hole_diameter": 8},
                "output": {"step": True, "stl": True, "tolerance": 0.1}
            },
            "placement": {"position": [1110, 30, 0], "rotation": [0, 0, 0]}
        },
        {
            "id": "leg_rl",
            "template": "simple_leg",
            "params": {
                "units": "mm",
                "simple_leg": {"width": 60, "depth": 60, "height": 700, "chamfer": 2, "hole_diameter": 8},
                "output": {"step": True, "stl": True, "tolerance": 0.1}
            },
            "placement": {"position": [30, 510, 0], "rotation": [0, 0, 0]}
        },
        {
            "id": "leg_rr",
            "template": "simple_leg",
            "params": {
                "units": "mm",
                "simple_leg": {"width": 60, "depth": 60, "height": 700, "chamfer": 2, "hole_diameter": 8},
                "output": {"step": True, "stl": True, "tolerance": 0.1}
            },
            "placement": {"position": [1110, 510, 0], "rotation": [0, 0, 0]}
        }
    ],
    "output": {"step": True, "stl": True}
}

result = generate_assembly(desk)
print(result["result"]["outputs"]["step"])  # Path to assembly.step
```

---

## Step 4: View the Result

Open the generated `assembly.step` in FreeCAD to see the 3D model:

```
output/assembly/
  assembly.step      ← Open this in FreeCAD
  assembly.stl       ← For 3D printing or mesh viewers
  _parts/
    top/model.step
    leg_fl/model.step
    ...
```

---

## Available Templates

| Template       | Purpose                                    | Params |
|----------------|--------------------------------------------|--------|
| `bracket`      | L-bracket with configurable holes          | 10     |
| `adapter_plate`| Flat plate with two bolt circle patterns   | 12     |
| `enclosure`    | Rectangular box with lid and screw bosses  | 10     |
| `bolt`         | Simple cylindrical bolt with head          | 4      |
| `table_top`    | Flat table top plate with edge fillet      | 4      |
| `simple_leg`   | Rectangular leg with chamfer and hole      | 5      |

---

## Assembly Examples

Pre-built assembly examples are available in `templates/assembly_examples/`:

| File                          | Description                    |
|-------------------------------|--------------------------------|
| `simple_desk.json`            | Standard 4-leg desk            |
| `compact_desk.json`           | Small room compact desk        |
| `standing_desk.json`          | Standing desk (1050mm height)  |
| `desk_with_shelf.json`        | Desk with storage shelf        |
| `plate_brackets_bolts.json`   | Bolted plate with brackets     |
| `plate_with_brackets.json`    | Plate with L-brackets          |

---

## MCP Tool Flow

The typical 5-step MCP workflow for generating parts:

```
1. list_templates       → See what's available
2. get_template_schema  → Inspect parameter schema
3. get_template_example → Get working sample params
4. validate_params      → Dry-run safety check
5. generate_part        → Produce STEP/STL files
   (or generate_assembly for multi-part models)
```

---

## Next Steps

- **Create custom templates**: See [Template Guide](template-guide.md)
- **Build complex assemblies**: See [Assembly Guide](assembly-guide.md)
- **MCP tools reference**: See [MCP Tools](mcp-tools.md)
