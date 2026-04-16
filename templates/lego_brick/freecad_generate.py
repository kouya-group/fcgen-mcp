"""LEGO-compatible brick generator.

Standard LEGO dimensions:
- Pitch: 8.0 mm (center-to-center stud distance)
- Stud diameter: 4.8 mm
- Stud height: 1.8 mm
- Plate height: 3.2 mm (1 plate unit)
- Brick height: 9.6 mm (3 plates)
- Wall thickness: 1.6 mm (outer wall)
- Body width: studs_x * 8.0 mm
- Body depth: studs_y * 8.0 mm
"""
import json
import sys
import traceback

import FreeCAD as App
import Mesh
import Part

# LEGO standard dimensions (mm)
PITCH = 8.0
STUD_D = 4.8
STUD_H = 1.8
PLATE_H = 3.2
WALL = 1.6


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

    b = params["lego_brick"]
    nx = int(b["studs_x"])
    ny = int(b["studs_y"])
    n_plates = int(b.get("height_plates", 3))

    body_w = nx * PITCH
    body_d = ny * PITCH
    body_h = n_plates * PLATE_H

    # Outer shell
    outer = Part.makeBox(body_w, body_d, body_h)

    # Hollow interior (subtract inner box from bottom, leaving walls and top)
    inner_w = body_w - 2 * WALL
    inner_d = body_d - 2 * WALL
    inner_h = body_h - WALL  # leave top plate
    if inner_w > 0 and inner_d > 0 and inner_h > 0:
        inner = Part.makeBox(
            inner_w, inner_d, inner_h,
            App.Vector(WALL, WALL, 0),
        )
        shape = outer.cut(inner)
    else:
        shape = outer

    # Add studs on top
    stud_r = STUD_D / 2.0
    for ix in range(nx):
        for iy in range(ny):
            cx = PITCH / 2.0 + ix * PITCH
            cy = PITCH / 2.0 + iy * PITCH
            stud = Part.makeCylinder(
                stud_r, STUD_H,
                App.Vector(cx, cy, body_h),
                App.Vector(0, 0, 1),
            )
            shape = shape.fuse(stud)

    # Refine shape to clean up Boolean artifacts
    shape = shape.removeSplitter()

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
