from __future__ import annotations


def validate_semantics(template: str, params: dict) -> None:
    _validate_output_flags(params)
    if template == "bracket":
        _validate_bracket(params)
        return
    if template == "enclosure":
        _validate_enclosure(params)
        return
    if template == "adapter_plate":
        _validate_adapter_plate(params)
        return
    # Unknown template: skip semantic validation (schema validation via jsonschema
    # is still enforced by runner.py).
    return


def _validate_output_flags(params: dict) -> None:
    output = params.get("output", {})
    if not output.get("step", True) and not output.get("stl", True):
        raise RuntimeError("At least one output format must be enabled: output.step or output.stl")


def _validate_bracket(params: dict) -> None:
    b = params["bracket"]
    holes = b["holes"]
    leg_a = float(b["leg_a"])
    width = float(b["width"])
    diameter = float(holes["diameter"])
    count = int(holes["count"])
    edge_offset = float(holes["edge_offset"])

    if count <= 0:
        return

    radius = diameter / 2.0
    if diameter >= width:
        raise RuntimeError(
            f"Invalid bracket.holes.diameter={diameter}: must be smaller than bracket.width={width}"
        )
    if edge_offset + radius > leg_a:
        raise RuntimeError(
            f"Invalid bracket holes placement: edge_offset({edge_offset}) + radius({radius}) exceeds leg_a({leg_a})"
        )
    if count >= 2 and (2.0 * edge_offset + diameter > leg_a):
        raise RuntimeError(
            f"Invalid bracket holes spacing: 2*edge_offset + diameter = {2.0 * edge_offset + diameter} exceeds leg_a={leg_a}"
        )


def _validate_enclosure(params: dict) -> None:
    e = params["enclosure"]
    size = e["size"]
    screws = e["screws"]
    length = float(size["length"])
    width = float(size["width"])
    hole_d = float(screws["hole_diameter"])
    boss_d = float(screws["boss_diameter"])
    edge = float(screws["edge_offset"])
    count = int(screws["count"])

    if count <= 0:
        return

    boss_r = boss_d / 2.0
    if hole_d >= boss_d:
        raise RuntimeError(
            f"Invalid enclosure screws: hole_diameter({hole_d}) must be smaller than boss_diameter({boss_d})"
        )
    if edge < boss_r:
        raise RuntimeError(
            f"Invalid enclosure screws edge_offset={edge}: must be >= boss radius {boss_r}"
        )
    if edge + boss_r > length or edge + boss_r > width:
        raise RuntimeError(
            "Invalid enclosure screws placement: edge_offset + boss radius must fit within length and width"
        )


def _validate_adapter_plate(params: dict) -> None:
    a = params["adapter_plate"]
    length = float(a["size"]["length"])
    width = float(a["size"]["width"])
    for name in ("pattern_a", "pattern_b"):
        p = a[name]
        count = int(p["count"])
        dia = float(p["hole_diameter"])
        pcd = float(p["pcd"])
        if count <= 0:
            continue
        if dia <= 0.0:
            raise RuntimeError(f"Invalid {name}.hole_diameter={dia}: must be positive")
        if pcd <= 0.0:
            raise RuntimeError(f"Invalid {name}.pcd={pcd}: must be > 0 when {name}.count > 0")
        if pcd + dia > min(length, width):
            raise RuntimeError(
                f"Invalid {name}: pcd + hole_diameter = {pcd + dia} exceeds min plate size {min(length, width)}"
            )
