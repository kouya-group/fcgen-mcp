import json
import math
import traceback

import FreeCAD as App
import Mesh
import Part
import sys


def _holes_for_pattern(count: int, pcd: float, angle_deg: float) -> list[tuple[float, float]]:
    if count <= 0 or pcd <= 0.0:
        return []
    r = pcd / 2.0
    a0 = math.radians(angle_deg)
    pts = []
    for i in range(count):
        a = a0 + 2.0 * math.pi * i / count
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def main() -> int:
    if "--pass" in sys.argv:
        idx = sys.argv.index("--pass")
        args = sys.argv[idx + 1 :]
    else:
        args = sys.argv[-3:]
    if len(args) < 3:
        raise RuntimeError("Usage: freecad_generate.py <params.json> <model.step> <model.stl>")

    params_path, step_path, stl_path = args[0], args[1], args[2]
    with open(params_path, "r", encoding="utf-8") as f:
        params = json.load(f)

    a = params["adapter_plate"]
    l = float(a["size"]["length"])
    w = float(a["size"]["width"])
    t = float(a["thickness"])
    p1 = a["pattern_a"]
    p2 = a["pattern_b"]
    c1, d1, pcd1 = int(p1["count"]), float(p1["hole_diameter"]), float(p1["pcd"])
    c2, d2, pcd2 = int(p2["count"]), float(p2["hole_diameter"]), float(p2["pcd"])
    a1 = float(p1.get("angle_deg", 0.0))
    a2 = float(p2.get("angle_deg", 0.0))

    if l <= 0.0 or w <= 0.0 or t <= 0.0:
        raise RuntimeError("Adapter plate dimensions must be positive")

    plate = Part.makeBox(l, w, t, App.Vector(-l / 2.0, -w / 2.0, 0.0))
    hole_specs = [
        (c1, d1, pcd1, a1),
        (c2, d2, pcd2, a2),
    ]
    for count, dia, pcd, ang in hole_specs:
        if count <= 0:
            continue
        if dia <= 0.0:
            raise RuntimeError("hole_diameter must be positive")
        for x, y in _holes_for_pattern(count, pcd, ang):
            cyl = Part.makeCylinder(dia / 2.0, t + 2.0, App.Vector(x, y, -1.0), App.Vector(0, 0, 1))
            plate = plate.cut(cyl)

    doc = App.ActiveDocument or App.newDocument("fcgen")
    obj = doc.addObject("Part::Feature", "AdapterPlate")
    obj.Shape = plate
    doc.recompute()

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
