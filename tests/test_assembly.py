import pytest

from fcgen.assembly.engine import run_assembly


def test_assembly_dry_run(tmp_path):
    spec = {
        "units": "mm",
        "parts": [
            {
                "id": "plate",
                "template": "adapter_plate",
                "params": {
                    "units": "mm",
                    "adapter_plate": {
                        "size": {"length": 140.0, "width": 140.0},
                        "thickness": 6.0,
                        "pattern_a": {"count": 4, "hole_diameter": 6.6, "pcd": 90.0, "angle_deg": 0.0},
                        "pattern_b": {"count": 6, "hole_diameter": 5.5, "pcd": 110.0, "angle_deg": 15.0},
                    },
                    "output": {"step": True, "stl": True},
                },
                "placement": {"position": [0, 0, 0], "rotation": [0, 0, 0]},
            },
            {
                "id": "bracket_a",
                "template": "bracket",
                "params": {
                    "units": "mm",
                    "bracket": {
                        "thickness": 3.0,
                        "leg_a": 40.0,
                        "leg_b": 60.0,
                        "width": 25.0,
                        "holes": {"pattern": "line", "diameter": 5.5, "count": 2, "edge_offset": 8.0},
                    },
                    "output": {"step": True, "stl": True},
                },
                "placement": {"position": [10, 20, 6], "rotation": [0, 0, 0]},
            },
        ],
        "output": {"step": True, "stl": True},
    }
    result = run_assembly(spec, tmp_path / "asm", dry_run=True)
    assert result["mode"] == "assembly"
    assert "artifact_hash" in result
    assert len(result["parts"]) == 2
    assert result["parts"][0]["id"] == "plate"
    assert result["parts"][1]["id"] == "bracket_a"


def test_assembly_rejects_empty_parts(tmp_path):
    spec = {"units": "mm", "parts": [], "output": {"step": True, "stl": True}}
    with pytest.raises(RuntimeError, match="at least one part"):
        run_assembly(spec, tmp_path / "empty", dry_run=True)


def test_assembly_rejects_duplicate_ids(tmp_path):
    part = {
        "id": "same",
        "template": "bracket",
        "params": {
            "units": "mm",
            "bracket": {
                "thickness": 3.0, "leg_a": 40.0, "leg_b": 60.0, "width": 25.0,
                "holes": {"pattern": "line", "diameter": 5.5, "count": 2, "edge_offset": 8.0},
            },
            "output": {"step": True, "stl": True},
        },
    }
    spec = {"units": "mm", "parts": [part, part], "output": {"step": True, "stl": True}}
    with pytest.raises(RuntimeError, match="Duplicate part id"):
        run_assembly(spec, tmp_path / "dup", dry_run=True)
