"""テンプレートレジストリ (Registry) のユニットテスト."""

import json
from pathlib import Path

import pytest

from fcgen import TEMPLATES_DIR, CANDIDATES_DIR, REGISTRY_PATH
from fcgen.registry import Registry


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_registry(tmp_path: Path, *, templates_dir: Path | None = None) -> Registry:
    """tmp_path 内に隔離された Registry を作る."""
    reg = Registry(
        registry_path=tmp_path / "registry.json",
        templates_dir=templates_dir or (tmp_path / "templates"),
        candidates_dir=tmp_path / "templates_candidate",
    )
    reg.load()
    return reg


def _make_real_registry(tmp_path: Path) -> Registry:
    """実 templates/ ディレクトリを参照する Registry を作る."""
    return _make_registry(tmp_path, templates_dir=TEMPLATES_DIR)


def _create_candidate_files(
    candidate_dir: Path,
    *,
    generator_body: str = "def generate(params, step, stl): pass\n",
    include_freecad: bool = True,
    include_example: bool = True,
) -> None:
    """candidate テンプレートの最低限ファイルを生成する."""
    candidate_dir.mkdir(parents=True, exist_ok=True)

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "width": {"type": "number"},
            "height": {"type": "number"},
        },
    }
    (candidate_dir / "schema.json").write_text(
        json.dumps(schema, indent=2), encoding="utf-8"
    )

    (candidate_dir / "generator.py").write_text(generator_body, encoding="utf-8")

    if include_freecad:
        (candidate_dir / "freecad_generate.py").write_text(
            "def main(): pass\n", encoding="utf-8"
        )

    if include_example:
        examples_dir = candidate_dir / "examples"
        examples_dir.mkdir(parents=True, exist_ok=True)
        (examples_dir / "basic.json").write_text(
            json.dumps({"width": 10.0, "height": 20.0}, indent=2), encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

class TestBootstrap:
    def test_bootstrap_finds_builtin_templates(self, tmp_path: Path) -> None:
        reg = _make_real_registry(tmp_path)
        reg.bootstrap()

        for name in ("bracket", "enclosure", "adapter_plate"):
            entry = reg.get_entry(name)
            assert entry is not None, f"{name} should be registered"
            assert entry["status"] == "verified"
            assert entry["source"] == "builtin"


class TestCountParams:
    def test_count_params_bracket(self) -> None:
        schema_path = TEMPLATES_DIR / "bracket" / "schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        count = Registry.count_params(schema)
        # bracket: thickness, leg_a, leg_b, width, fillet, chamfer,
        #          holes.(pattern, diameter, count, edge_offset) = 10
        assert 8 <= count <= 12
        assert count == 10


class TestContentHash:
    def test_compute_content_hash_deterministic(self) -> None:
        template_dir = TEMPLATES_DIR / "bracket"
        h1 = Registry.compute_content_hash(template_dir)
        h2 = Registry.compute_content_hash(template_dir)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest


class TestAddCandidate:
    def test_add_candidate(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path)
        candidate_dir = reg.candidates_dir / "my_widget"
        _create_candidate_files(candidate_dir)

        entry = reg.add_candidate(
            name="my_widget",
            source="llm",
            purpose="test widget",
            tags=["test"],
        )
        assert entry["status"] == "candidate"
        assert entry["source"] == "llm"
        assert entry["purpose"] == "test widget"
        assert entry["param_count"] == 2  # width, height
        assert entry["content_hash"] != ""
        assert entry["verified_at"] is None

        # registry.json が書き出されている
        assert reg.registry_path.exists()

        # get_entry で取得可能
        fetched = reg.get_entry("my_widget")
        assert fetched is not None
        assert fetched["status"] == "candidate"


class TestVerify:
    def test_verify_promotes_to_verified(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path)
        reg.templates_dir.mkdir(parents=True, exist_ok=True)

        candidate_dir = reg.candidates_dir / "my_widget"
        _create_candidate_files(candidate_dir)

        reg.add_candidate(
            name="my_widget",
            source="llm",
            purpose="test widget",
        )
        entry = reg.verify("my_widget")

        assert entry["status"] == "verified"
        assert entry["verified_at"] is not None
        # ディレクトリが templates/ に移動されている
        assert (reg.templates_dir / "my_widget").exists()
        assert not (reg.candidates_dir / "my_widget").exists()

    def test_verify_rejects_missing_generate_function(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path)
        reg.templates_dir.mkdir(parents=True, exist_ok=True)

        candidate_dir = reg.candidates_dir / "bad_widget"
        _create_candidate_files(
            candidate_dir,
            generator_body="def helper(): pass\n",  # no generate()
        )

        reg.add_candidate(
            name="bad_widget",
            source="llm",
            purpose="broken widget",
        )
        with pytest.raises(ValueError, match="generate"):
            reg.verify("bad_widget")


class TestFindSimpler:
    def test_find_simpler_sorts_by_param_count(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path)

        # 手動で param_count が異なるエントリを登録
        templates = reg._data.setdefault("templates", {})
        templates["big"] = {
            "status": "verified",
            "source": "builtin",
            "content_hash": "",
            "param_count": 20,
            "purpose": "mounting bracket",
            "tags": [],
            "added_at": "",
            "verified_at": "",
        }
        templates["small"] = {
            "status": "verified",
            "source": "builtin",
            "content_hash": "",
            "param_count": 3,
            "purpose": "simple mounting bracket",
            "tags": [],
            "added_at": "",
            "verified_at": "",
        }
        templates["mid"] = {
            "status": "verified",
            "source": "builtin",
            "content_hash": "",
            "param_count": 10,
            "purpose": "mounting bracket with holes",
            "tags": [],
            "added_at": "",
            "verified_at": "",
        }

        results = reg.find_simpler("mounting bracket")
        assert len(results) >= 3
        param_counts = [r["param_count"] for r in results]
        assert param_counts == sorted(param_counts)
        assert results[0]["name"] == "small"

    def test_find_simpler_with_real_bootstrap(self, tmp_path: Path) -> None:
        reg = _make_real_registry(tmp_path)
        reg.bootstrap()

        # bracket の purpose は "" だが空文字は任意に部分一致するのでテスト可能
        # 代わりに全テンプレートにマッチする空文字で検索
        results = reg.find_simpler("")
        assert len(results) >= 3
        param_counts = [r["param_count"] for r in results]
        assert param_counts == sorted(param_counts)


class TestCheckIntegrity:
    def test_check_integrity(self, tmp_path: Path) -> None:
        reg = _make_real_registry(tmp_path)
        reg.bootstrap()

        for name in ("bracket", "enclosure", "adapter_plate"):
            assert reg.check_integrity(name), f"{name} integrity check failed"

    def test_check_integrity_fails_for_unknown(self, tmp_path: Path) -> None:
        reg = _make_real_registry(tmp_path)
        reg.bootstrap()
        assert not reg.check_integrity("nonexistent_template")


class TestResolvePath:
    def test_resolve_path_verified_vs_candidate(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path)

        # candidate エントリを手動追加
        reg._data["templates"]["cand"] = {"status": "candidate"}
        reg._data["templates"]["verf"] = {"status": "verified"}

        assert reg.resolve_path("cand") == reg.candidates_dir / "cand"
        assert reg.resolve_path("verf") == reg.templates_dir / "verf"

    def test_resolve_path_unknown_defaults_to_templates(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path)
        # 未登録名は templates/ にフォールバック
        assert reg.resolve_path("unknown") == reg.templates_dir / "unknown"
