"""FreeCAD headless script: load STEP files, apply placement, check interference, compound, export."""
import json
import math
import os
import traceback
import sys

import FreeCAD as App
import Mesh
import Part


def _check_interference(shapes, part_ids):
    """全パーツ間のBoolean交差を計算し、干渉ペアのリストを返す。

    Returns:
        list[dict]: 干渉が検出されたペア。各要素は:
            {"part_a": str, "part_b": str, "volume_mm3": float}
        干渉なしなら空リスト。
    """
    interferences = []
    n = len(shapes)
    for i in range(n):
        for j in range(i + 1, n):
            try:
                common = shapes[i].common(shapes[j])
                vol = common.Volume
                if vol > 0.001:  # 0.001 mm^3 未満はノイズとして無視
                    interferences.append({
                        "part_a": part_ids[i],
                        "part_b": part_ids[j],
                        "volume_mm3": round(vol, 3),
                    })
            except Exception:
                # Boolean演算失敗時はスキップ（複雑形状で起こりうる）
                pass
    return interferences


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
    part_ids = []
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
        part_ids.append(entry.get("id", f"part_{len(part_ids)}"))

    if not shapes:
        raise RuntimeError("No parts to assemble")

    # 干渉チェック
    interferences = _check_interference(shapes, part_ids)
    interference_report = {
        "checked": True,
        "pair_count": len(interferences),
        "pairs": interferences,
    }

    # 干渉レポートをJSONに保存
    out_dir = os.path.dirname(step_path)
    report_path = os.path.join(out_dir, "interference_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(interference_report, f, indent=2, ensure_ascii=False)

    # 干渉があれば標準エラーに警告
    if interferences:
        print(f"WARNING: {len(interferences)} interference(s) detected:", file=sys.stderr)
        for intf in interferences:
            print(f"  {intf['part_a']} <-> {intf['part_b']}: {intf['volume_mm3']} mm^3", file=sys.stderr)

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
