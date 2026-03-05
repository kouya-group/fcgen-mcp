def build_report(template: str, params: dict, artifact_hash: str, generated: bool) -> dict:
    if template == "bracket":
        return _report_bracket(params, artifact_hash, generated)
    if template == "enclosure":
        return _report_enclosure(params, artifact_hash, generated)
    if template == "adapter_plate":
        return _report_adapter_plate(params, artifact_hash, generated)
    return _report_generic(template, params, artifact_hash, generated)


def _report_generic(template: str, params: dict, artifact_hash: str, generated: bool) -> dict:
    return {
        "template": template,
        "artifact_hash": artifact_hash,
        "generated": generated,
        "geometry": {
            "bbox_mm": "unknown",
            "volume_mm3": "unknown",
        },
    }


def _report_bracket(params: dict, artifact_hash: str, generated: bool) -> dict:
    b = params["bracket"]
    holes = b["holes"]
    thickness = float(b["thickness"])
    leg_a = float(b["leg_a"])
    leg_b = float(b["leg_b"])
    width = float(b["width"])
    hole_d = float(holes["diameter"])
    hole_count = int(holes["count"])

    bbox = [max(leg_a, thickness), max(leg_b, thickness), width]
    solid_volume = thickness * width * (leg_a + leg_b - thickness)
    hole_volume = hole_count * (3.141592653589793 * (hole_d / 2.0) ** 2 * thickness)
    volume = max(0.0, solid_volume - hole_volume)

    return {
        "template": "bracket",
        "artifact_hash": artifact_hash,
        "generated": generated,
        "geometry": {
            "bbox_mm": [round(x, 3) for x in bbox],
            "volume_mm3": round(volume, 3),
            "approx_min_thickness_mm": round(thickness, 3),
            "hole_count": hole_count,
        },
    }


def _report_enclosure(params: dict, artifact_hash: str, generated: bool) -> dict:
    e = params["enclosure"]
    size = e["size"]
    length = float(size["length"])
    width = float(size["width"])
    height = float(size["height"])
    wall = float(e["wall_thickness"])
    lid = float(e["lid_thickness"])
    screw_count = int(e["screws"]["count"])

    outer = length * width * height
    inner_l = max(0.0, length - 2.0 * wall)
    inner_w = max(0.0, width - 2.0 * wall)
    inner_h = max(0.0, height - wall)
    cavity = inner_l * inner_w * inner_h
    lid_volume = length * width * lid
    volume = max(0.0, (outer - cavity) + lid_volume)

    return {
        "template": "enclosure",
        "artifact_hash": artifact_hash,
        "generated": generated,
        "geometry": {
            "bbox_mm": [round(length, 3), round(width, 3), round(height + lid + 2.0, 3)],
            "volume_mm3": round(volume, 3),
            "approx_min_thickness_mm": round(min(wall, lid), 3),
            "screw_count": screw_count,
        },
    }


def _report_adapter_plate(params: dict, artifact_hash: str, generated: bool) -> dict:
    a = params["adapter_plate"]
    t = float(a["thickness"])
    l = float(a["size"]["length"])
    w = float(a["size"]["width"])
    c1 = int(a["pattern_a"]["count"])
    c2 = int(a["pattern_b"]["count"])
    d1 = float(a["pattern_a"]["hole_diameter"])
    d2 = float(a["pattern_b"]["hole_diameter"])

    outer = l * w * t
    holes = (c1 * 3.141592653589793 * (d1 / 2.0) ** 2 + c2 * 3.141592653589793 * (d2 / 2.0) ** 2) * t
    volume = max(0.0, outer - holes)

    return {
        "template": "adapter_plate",
        "artifact_hash": artifact_hash,
        "generated": generated,
        "geometry": {
            "bbox_mm": [round(l, 3), round(w, 3), round(t, 3)],
            "volume_mm3": round(volume, 3),
            "approx_min_thickness_mm": round(t, 3),
            "hole_count": c1 + c2,
        },
    }
