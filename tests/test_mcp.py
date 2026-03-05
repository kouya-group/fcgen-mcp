"""MCP ツールの単体テスト — 各ツール関数を直接呼び出して検証する。"""
import json
from pathlib import Path

import pytest

from fcgen.mcp.server import (
    list_templates,
    get_template_schema,
    get_template_example,
    validate_params,
    generate_part,
    list_candidates,
    find_template,
)


class TestListTemplates:
    def test_returns_known_templates(self):
        result = list_templates()
        templates = result["templates"]
        assert "bracket" in templates
        assert "enclosure" in templates
        assert "adapter_plate" in templates

    def test_each_template_has_example(self):
        result = list_templates()
        for name, info in result["templates"].items():
            assert info["has_example"] is True, f"{name} missing example"


class TestGetTemplateSchema:
    def test_bracket_schema(self):
        schema = get_template_schema("bracket")
        assert "properties" in schema
        assert "bracket" in schema["properties"]

    def test_unknown_template(self):
        result = get_template_schema("nonexistent")
        assert "error" in result


class TestGetTemplateExample:
    def test_bracket_example(self):
        example = get_template_example("bracket")
        assert "units" in example
        assert "bracket" in example

    def test_unknown_template(self):
        result = get_template_example("nonexistent")
        assert "error" in result


class TestValidateParams:
    def test_valid_bracket(self):
        params = {
            "units": "mm",
            "bracket": {
                "thickness": 3.0,
                "leg_a": 40.0,
                "leg_b": 60.0,
                "width": 25.0,
                "holes": {"pattern": "line", "diameter": 5.5, "count": 2, "edge_offset": 8.0},
            },
            "output": {"step": True, "stl": True},
        }
        result = validate_params("bracket", params)
        assert result["valid"] is True

    def test_invalid_schema(self):
        params = {"units": "mm", "output": {"step": True, "stl": "bad"}}
        result = validate_params("bracket", params)
        assert result["valid"] is False
        assert "error" in result

    def test_invalid_semantic(self):
        params = {
            "units": "mm",
            "bracket": {
                "thickness": 3.0,
                "leg_a": 40.0,
                "leg_b": 60.0,
                "width": 5.0,
                "holes": {"pattern": "line", "diameter": 10.0, "count": 2, "edge_offset": 8.0},
            },
            "output": {"step": True, "stl": True},
        }
        result = validate_params("bracket", params)
        assert result["valid"] is False
        assert "diameter" in result["error"]

    def test_unknown_template(self):
        result = validate_params("nonexistent", {"units": "mm"})
        assert result["valid"] is False


class TestListCandidates:
    def test_list_candidates_initially_empty(self):
        result = list_candidates()
        assert result["ok"] is True
        assert result["candidates"] == {}


class TestFindTemplate:
    def test_find_template_returns_sorted(self):
        result = find_template("")
        assert result["ok"] is True
        results = result["results"]
        # ブートストラップ済みなので少なくとも3件ある
        assert len(results) >= 3
        param_counts = [r["param_count"] for r in results]
        assert param_counts == sorted(param_counts)
