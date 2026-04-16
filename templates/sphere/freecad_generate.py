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

    s = params["sphere"]
    radius = float(s["radius"])

    shape = Part.makeSphere(radius)

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
