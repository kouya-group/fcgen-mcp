"""FreeCAD headless script: load STEP files, apply placement, compound, export."""
import json
import math
import traceback
import sys

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
        raise RuntimeError("Usage: freecad_assemble.py <manifest.json> <assembly.step> <assembly.stl>")

    manifest_path, step_path, stl_path = args[0], args[1], args[2]
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    shapes = []
    for entry in manifest["parts"]:
        part_step = entry["step_path"]
        pos = entry.get("position", [0, 0, 0])
        rot = entry.get("rotation", [0, 0, 0])

        shape = Part.read(part_step)

        placement = App.Placement(
            App.Vector(pos[0], pos[1], pos[2]),
            App.Rotation(rot[0], rot[1], rot[2]),
        )
        shape = shape.copy()
        shape.Placement = placement
        shapes.append(shape)

    if not shapes:
        raise RuntimeError("No parts to assemble")

    compound = Part.makeCompound(shapes)

    doc = App.ActiveDocument or App.newDocument("fcgen_assembly")
    obj = doc.addObject("Part::Feature", "Assembly")
    obj.Shape = compound
    doc.recompute()

    output = manifest.get("output", {})
    if output.get("step", True):
        Part.export([obj], step_path)
    if output.get("stl", True):
        Mesh.export([obj], stl_path)
    return 0


try:
    raise SystemExit(main())
except SystemExit:
    raise
except Exception:
    traceback.print_exc()
    raise SystemExit(1)
