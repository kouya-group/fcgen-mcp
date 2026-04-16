"""Minecraft-style block: cube with edge chamfers and face grooves.

The grooves create a cross pattern on each face, giving the pixelated
texture feel of a Minecraft block.
"""
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

    m = params["minecraft_block"]
    size = float(m["size"])
    chamfer = float(m.get("edge_chamfer", 0))
    groove_d = float(m.get("groove_depth", 0))
    groove_w = float(m.get("groove_width", 0))

    # Base cube
    shape = Part.makeBox(size, size, size)

    # Edge chamfer
    if chamfer > 0:
        shape = shape.makeChamfer(chamfer, shape.Edges)

    # Face grooves — carve cross pattern on each face to look like pixel grid
    if groove_d > 0 and groove_w > 0:
        half = size / 2.0

        # Grooves along X (cuts through Y-Z faces)
        groove_x = Part.makeBox(
            size + 2, groove_w, groove_d,
            App.Vector(-1, half - groove_w / 2.0, size - groove_d),
        )
        shape = shape.cut(groove_x)

        groove_x2 = Part.makeBox(
            size + 2, groove_w, groove_d,
            App.Vector(-1, half - groove_w / 2.0, -0.001),
        )
        shape = shape.cut(groove_x2)

        # Grooves along Y
        groove_y = Part.makeBox(
            groove_w, size + 2, groove_d,
            App.Vector(half - groove_w / 2.0, -1, size - groove_d),
        )
        shape = shape.cut(groove_y)

        groove_y2 = Part.makeBox(
            groove_w, size + 2, groove_d,
            App.Vector(half - groove_w / 2.0, -1, -0.001),
        )
        shape = shape.cut(groove_y2)

        # Grooves along Z (on side faces)
        groove_z1 = Part.makeBox(
            groove_d, groove_w, size + 2,
            App.Vector(size - groove_d, half - groove_w / 2.0, -1),
        )
        shape = shape.cut(groove_z1)

        groove_z2 = Part.makeBox(
            groove_d, groove_w, size + 2,
            App.Vector(-0.001, half - groove_w / 2.0, -1),
        )
        shape = shape.cut(groove_z2)

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
