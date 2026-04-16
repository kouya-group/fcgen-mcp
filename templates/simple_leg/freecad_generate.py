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

    leg = params["simple_leg"]
    width = float(leg["width"])
    depth = float(leg["depth"])
    height = float(leg["height"])
    chamfer = float(leg.get("chamfer", 0.0))
    hole_d = float(leg.get("hole_diameter", 0.0))

    # 脚: 直方体
    shape = Part.makeBox(width, depth, height)

    # 底面の面取り（Z=0側の4辺）
    if chamfer > 0.0:
        bottom_edges = [e for e in shape.Edges if abs(e.CenterOfMass.z) < 0.01]
        if bottom_edges:
            shape = shape.makeChamfer(chamfer, bottom_edges)

    # 天板固定用の穴（上面中央、貫通）
    if hole_d > 0.0:
        radius = hole_d / 2.0
        cx = width / 2.0
        cy = depth / 2.0
        cyl = Part.makeCylinder(radius, height + 2.0, App.Vector(cx, cy, -1.0), App.Vector(0, 0, 1))
        shape = shape.cut(cyl)

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
