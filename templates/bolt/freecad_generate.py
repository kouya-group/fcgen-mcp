import json
import sys
import traceback

import FreeCAD as App
import Mesh
import Part


def main() -> int:
    if "--pass" in sys.argv:
        idx = sys.argv.index("--pass")
        args = sys.argv[idx + 1 :]
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
    shaft = Part.makeCylinder(diameter / 2.0, length, App.Vector(0, 0, -length), App.Vector(0, 0, 1))

    # Head: cylinder from Z=0 upward
    head = Part.makeCylinder(head_diameter / 2.0, head_height, App.Vector(0, 0, 0), App.Vector(0, 0, 1))

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
