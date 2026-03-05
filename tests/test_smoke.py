from pathlib import Path

from fcgen.core.runner import run_template


def test_bracket_smoke(tmp_path: Path) -> None:
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
        "output": {"step": True, "stl": True},
    }
    result = run_template("bracket", params, tmp_path, dry_run=False)
    assert "artifact_hash" in result
    assert (tmp_path / "report.json").exists()


def test_enclosure_smoke(tmp_path: Path) -> None:
    params = {
        "units": "mm",
        "enclosure": {
            "size": {"length": 120.0, "width": 80.0, "height": 40.0},
            "wall_thickness": 2.5,
            "lid_thickness": 2.0,
            "screws": {"count": 4, "hole_diameter": 3.2, "boss_diameter": 8.0, "edge_offset": 10.0},
        },
        "output": {"step": True, "stl": True},
    }
    result = run_template("enclosure", params, tmp_path / "enc", dry_run=False)
    assert "artifact_hash" in result
    assert (tmp_path / "enc" / "report.json").exists()


def test_adapter_plate_smoke(tmp_path: Path) -> None:
    params = {
        "units": "mm",
        "adapter_plate": {
            "size": {"length": 140.0, "width": 140.0},
            "thickness": 6.0,
            "pattern_a": {"count": 4, "hole_diameter": 6.6, "pcd": 90.0, "angle_deg": 0.0},
            "pattern_b": {"count": 6, "hole_diameter": 5.5, "pcd": 110.0, "angle_deg": 15.0},
        },
        "output": {"step": True, "stl": True},
    }
    result = run_template("adapter_plate", params, tmp_path / "adp", dry_run=False)
    assert "artifact_hash" in result
    assert (tmp_path / "adp" / "report.json").exists()
