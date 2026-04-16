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

    c = params["cup"]
    outer_d = float(c["outer_diameter"])
    height = float(c["height"])
    wall = float(c["wall_thickness"])
    bottom = float(c["bottom_thickness"])
    handle_w = float(c.get("handle_width", 0))
    handle_h = float(c.get("handle_height", 0))
    handle_t = float(c.get("handle_thickness", 0))

    outer_r = outer_d / 2.0
    inner_r = outer_r - wall

    # Outer cylinder (full body)
    outer = Part.makeCylinder(outer_r, height, App.Vector(0, 0, 0), App.Vector(0, 0, 1))

    # Inner cavity (hollow out from top, leaving bottom_thickness)
    cavity_h = height - bottom
    if cavity_h > 0 and inner_r > 0:
        cavity = Part.makeCylinder(
            inner_r, cavity_h + 1.0,  # +1 to ensure clean cut at top
            App.Vector(0, 0, bottom), App.Vector(0, 0, 1),
        )
        shape = outer.cut(cavity)
    else:
        shape = outer

    # Handle (torus section on the side)
    if handle_w > 0 and handle_h > 0 and handle_t > 0:
        # Handle as a box bent around the cup - approximate with a torus slice
        handle_center_z = bottom + cavity_h / 2.0
        torus_r1 = handle_h / 2.0  # major radius (how far handle sticks out)
        torus_r2 = handle_t / 2.0  # minor radius (cross section)

        # Create torus centered at cup surface
        torus = Part.makeTorus(
            torus_r1, torus_r2,
            App.Vector(outer_r, 0, handle_center_z),
            App.Vector(0, 1, 0),  # torus axis along Y
        )

        # Cut away the half inside the cup - keep only the outside half
        cut_box = Part.makeBox(
            outer_d + handle_h * 2, handle_h * 2 + handle_t * 2, height + 10,
            App.Vector(-outer_r - handle_h, -handle_h - handle_t, -5),
        )
        # We want only the part of the torus that's outside the cup radius
        # Keep only x > 0 side of the torus (the part sticking out)
        half_cut = Part.makeBox(
            outer_r + handle_h, handle_h * 2 + handle_t * 2, height + 10,
            App.Vector(-outer_r - handle_h, -handle_h - handle_t, -5),
        )
        handle_shape = torus.cut(half_cut)

        shape = shape.fuse(handle_shape)

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
