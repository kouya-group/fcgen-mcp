import pytest

from fcgen.core.runner import run_template


def test_schema_error_message_includes_path(tmp_path) -> None:
    params = {
        "units": "mm",
        "bracket": {
            "thickness": 3.0,
            "leg_a": 40.0,
            "leg_b": 60.0,
            "width": 25.0,
            "holes": {
                "pattern": "line",
                "diameter": 5.5,
                "count": 2,
                "edge_offset": 8.0,
            },
        },
        "output": {"step": True, "stl": "yes"},
    }

    with pytest.raises(RuntimeError, match=r"Schema validation failed at 'output\.stl'"):
        run_template("bracket", params, tmp_path / "schema_err", dry_run=True)


def test_output_flags_require_one_enabled(tmp_path) -> None:
    params = {
        "units": "mm",
        "bracket": {
            "thickness": 3.0,
            "leg_a": 40.0,
            "leg_b": 60.0,
            "width": 25.0,
            "holes": {
                "pattern": "line",
                "diameter": 5.5,
                "count": 2,
                "edge_offset": 8.0,
            },
        },
        "output": {"step": False, "stl": False},
    }

    with pytest.raises(RuntimeError, match=r"At least one output format"):
        run_template("bracket", params, tmp_path / "no_output", dry_run=True)


def test_enclosure_rejects_hole_not_smaller_than_boss(tmp_path) -> None:
    params = {
        "units": "mm",
        "enclosure": {
            "size": {"length": 120.0, "width": 80.0, "height": 40.0},
            "wall_thickness": 2.5,
            "lid_thickness": 2.0,
            "screws": {
                "count": 4,
                "hole_diameter": 8.0,
                "boss_diameter": 8.0,
                "edge_offset": 10.0,
            },
        },
        "output": {"step": True, "stl": True},
    }

    with pytest.raises(RuntimeError, match=r"hole_diameter\(8.0\) must be smaller than boss_diameter\(8.0\)"):
        run_template("enclosure", params, tmp_path / "enclosure_err", dry_run=True)


def test_adapter_plate_rejects_pcd_that_does_not_fit(tmp_path) -> None:
    params = {
        "units": "mm",
        "adapter_plate": {
            "size": {"length": 100.0, "width": 90.0},
            "thickness": 6.0,
            "pattern_a": {"count": 4, "hole_diameter": 10.0, "pcd": 85.0, "angle_deg": 0.0},
            "pattern_b": {"count": 0, "hole_diameter": 5.0, "pcd": 0.0, "angle_deg": 0.0},
        },
        "output": {"step": True, "stl": True},
    }

    with pytest.raises(RuntimeError, match=r"pcd \+ hole_diameter = 95.0 exceeds min plate size 90.0"):
        run_template("adapter_plate", params, tmp_path / "adapter_err", dry_run=True)
