import json
import traceback

import FreeCAD as App
import Mesh
import Part
import sys


def _screw_positions(length: float, width: float, offset: float, count: int) -> list[tuple[float, float]]:
    if count <= 0:
        return []
    if count == 2:
        return [(offset, width / 2.0), (length - offset, width / 2.0)]
    return [
        (offset, offset),
        (length - offset, offset),
        (length - offset, width - offset),
        (offset, width - offset),
    ]


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

    e = params["enclosure"]
    size = e["size"]
    length = float(size["length"])
    width = float(size["width"])
    height = float(size["height"])
    wall = float(e["wall_thickness"])
    lid_t = float(e["lid_thickness"])
    screws = e["screws"]
    screw_count = int(screws["count"])
    hole_d = float(screws["hole_diameter"])
    boss_d = float(screws["boss_diameter"])
    edge = float(screws["edge_offset"])

    if length <= 2.0 * wall or width <= 2.0 * wall or height <= wall:
        raise RuntimeError("Invalid enclosure dimensions: cavity would be non-positive")

    # Base shell: outer box minus inner cavity opened from top.
    outer = Part.makeBox(length, width, height)
    inner = Part.makeBox(length - 2.0 * wall, width - 2.0 * wall, height - wall, App.Vector(wall, wall, wall))
    base = outer.cut(inner)

    for px, py in _screw_positions(length, width, edge, screw_count):
        boss = Part.makeCylinder(boss_d / 2.0, height - wall, App.Vector(px, py, wall), App.Vector(0, 0, 1))
        hole = Part.makeCylinder(hole_d / 2.0, height + lid_t + 2.0, App.Vector(px, py, -1.0), App.Vector(0, 0, 1))
        base = base.fuse(boss).cut(hole)

    # Lid is exported in the same model, translated above the base for visual separation.
    lid_z = height + 2.0
    lid = Part.makeBox(length, width, lid_t, App.Vector(0, 0, lid_z))
    for px, py in _screw_positions(length, width, edge, screw_count):
        hole = Part.makeCylinder(hole_d / 2.0, lid_t + 2.0, App.Vector(px, py, lid_z - 1.0), App.Vector(0, 0, 1))
        lid = lid.cut(hole)

    compound = Part.makeCompound([base, lid])
    doc = App.ActiveDocument or App.newDocument("fcgen")
    obj = doc.addObject("Part::Feature", "Enclosure")
    obj.Shape = compound
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
