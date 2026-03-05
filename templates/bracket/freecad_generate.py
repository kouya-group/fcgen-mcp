import json
import sys
import traceback

import FreeCAD as App
import Mesh
import Part


def _hole_positions_line(count: int, start: float, end: float) -> list[float]:
    if count <= 0:
        return []
    if count == 1:
        return [(start + end) / 2.0]
    step = (end - start) / (count - 1)
    return [start + i * step for i in range(count)]


def main() -> int:
    if "--pass" in sys.argv:
        idx = sys.argv.index("--pass")
        args = sys.argv[idx + 1 :]
    else:
        # Fallback: treat trailing argv entries as payload args.
        args = sys.argv[-3:]

    if len(args) < 3:
        raise RuntimeError("Usage: freecad_generate.py <params.json> <model.step> <model.stl>")

    params_path = args[0]
    step_path = args[1]
    stl_path = args[2]
    with open(params_path, "r", encoding="utf-8") as f:
        params = json.load(f)

    b = params["bracket"]
    holes = b["holes"]
    t = float(b["thickness"])
    leg_a = float(b["leg_a"])
    leg_b = float(b["leg_b"])
    width = float(b["width"])
    hole_d = float(holes["diameter"])
    hole_count = int(holes["count"])
    edge_offset = float(holes["edge_offset"])

    # L-bracket from two orthogonal plates.
    base_plate = Part.makeBox(leg_a, width, t)
    side_plate = Part.makeBox(t, width, leg_b)
    shape = base_plate.fuse(side_plate)

    if hole_count > 0 and hole_d > 0.0:
        radius = hole_d / 2.0
        x_start = max(edge_offset, radius + 0.5)
        x_end = max(x_start, leg_a - edge_offset)
        x_positions = _hole_positions_line(hole_count, x_start, x_end)
        y = width / 2.0
        for x in x_positions:
            cyl = Part.makeCylinder(radius, t + 2.0, App.Vector(x, y, -1.0), App.Vector(0, 0, 1))
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
