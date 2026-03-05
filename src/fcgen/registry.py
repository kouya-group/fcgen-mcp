"""テンプレートレジストリ — candidate → verified の2段階管理."""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Registry class
# ---------------------------------------------------------------------------

class Registry:
    """registry.json を介してテンプレートの状態を管理する."""

    def __init__(
        self,
        registry_path: Path,
        templates_dir: Path,
        candidates_dir: Path,
    ) -> None:
        self.registry_path = Path(registry_path)
        self.templates_dir = Path(templates_dir)
        self.candidates_dir = Path(candidates_dir)
        self._data: dict = {"version": 1, "templates": {}}

    # -- 永続化 ---------------------------------------------------------------

    def load(self) -> dict:
        """registry.json を読み込む。存在しなければ空レジストリを返す."""
        if self.registry_path.exists():
            text = self.registry_path.read_text(encoding="utf-8")
            self._data = json.loads(text)
        else:
            self._data = {"version": 1, "templates": {}}
        return self._data

    def save(self) -> None:
        """registry.json に書き出す."""
        self.registry_path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # -- クエリ ---------------------------------------------------------------

    def list_templates(self, status: str | None = None) -> dict[str, dict]:
        """テンプレート一覧を返す。status を指定すればフィルタする."""
        templates = self._data.get("templates", {})
        if status is None:
            return dict(templates)
        return {k: v for k, v in templates.items() if v.get("status") == status}

    def get_entry(self, name: str) -> dict | None:
        """指定名のエントリを返す。存在しなければ None."""
        return self._data.get("templates", {}).get(name)

    def resolve_path(self, name: str) -> Path:
        """テンプレートの実ディレクトリを返す (verified→templates/, candidate→templates_candidate/)."""
        entry = self.get_entry(name)
        if entry is not None and entry.get("status") == "candidate":
            return self.candidates_dir / name
        return self.templates_dir / name

    # -- ハッシュ / 複雑度 ----------------------------------------------------

    @staticmethod
    def compute_content_hash(template_dir: Path) -> str:
        """schema.json, generator.py, freecad_generate.py の SHA-256 を算出する."""
        canonical_files = sorted(["freecad_generate.py", "generator.py", "schema.json"])
        h = hashlib.sha256()
        for fname in canonical_files:
            fpath = template_dir / fname
            if fpath.exists():
                h.update(fpath.read_bytes())
        return h.hexdigest()

    @staticmethod
    def count_params(schema: dict) -> int:
        """JSON Schema のリーフプロパティ数を返す (units, output, material_hint は除外)."""
        skip_keys = {"units", "output", "material_hint"}

        def _walk(node: dict, key: str | None = None) -> int:
            if key in skip_keys:
                return 0
            # object で properties を持つ → 中間ノード
            if node.get("type") == "object" and "properties" in node:
                return sum(
                    _walk(v, k) for k, v in node["properties"].items()
                )
            # それ以外 → リーフ
            return 1

        props = schema.get("properties", {})
        return sum(_walk(v, k) for k, v in props.items())

    # -- 登録 -----------------------------------------------------------------

    def add_candidate(
        self,
        name: str,
        source: str,
        purpose: str,
        tags: list[str] | None = None,
    ) -> dict:
        """候補テンプレートをレジストリに追加する."""
        now = datetime.now(timezone.utc).isoformat()
        template_dir = self.candidates_dir / name
        content_hash = ""
        param_count = 0

        if template_dir.exists():
            content_hash = self.compute_content_hash(template_dir)
            schema_path = template_dir / "schema.json"
            if schema_path.exists():
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                param_count = self.count_params(schema)

        entry: dict = {
            "status": "candidate",
            "source": source,
            "content_hash": content_hash,
            "param_count": param_count,
            "purpose": purpose,
            "tags": tags or [],
            "added_at": now,
            "verified_at": None,
        }
        self._data.setdefault("templates", {})[name] = entry
        self.save()
        return entry

    # -- 検証・昇格 -----------------------------------------------------------

    def verify(self, name: str) -> dict:
        """candidate を verified に昇格させる。検証に失敗すれば例外を送出する."""
        entry = self.get_entry(name)
        if entry is None:
            raise KeyError(f"テンプレート '{name}' が見つかりません")
        if entry.get("status") != "candidate":
            raise ValueError(f"'{name}' は candidate ではありません (status={entry.get('status')})")

        src_dir = self.candidates_dir / name

        # --- 検証チェック ---
        # 1. schema.json がパース可能
        schema_path = src_dir / "schema.json"
        if not schema_path.exists():
            raise FileNotFoundError(f"{schema_path} が見つかりません")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        # 2. generator.py に generate 関数がある
        gen_path = src_dir / "generator.py"
        if not gen_path.exists():
            raise FileNotFoundError(f"{gen_path} が見つかりません")
        tree = ast.parse(gen_path.read_text(encoding="utf-8"), filename=str(gen_path))
        func_names = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        }
        if "generate" not in func_names:
            raise ValueError(f"{gen_path} に generate 関数が定義されていません")

        # 3. examples/basic.json がスキーマで検証可能
        example_path = src_dir / "examples" / "basic.json"
        if example_path.exists():
            try:
                import jsonschema
                example = json.loads(example_path.read_text(encoding="utf-8"))
                jsonschema.validate(example, schema)
            except ImportError:
                pass  # jsonschema 未インストール時はスキップ

        # --- ディレクトリ移動 ---
        dst_dir = self.templates_dir / name
        if dst_dir.exists():
            raise FileExistsError(f"移動先 {dst_dir} が既に存在します")
        shutil.move(str(src_dir), str(dst_dir))

        # --- エントリ更新 ---
        now = datetime.now(timezone.utc).isoformat()
        entry["status"] = "verified"
        entry["verified_at"] = now
        entry["content_hash"] = self.compute_content_hash(dst_dir)
        entry["param_count"] = self.count_params(schema)
        self.save()
        return entry

    # -- 検索 -----------------------------------------------------------------

    def find_simpler(self, purpose: str) -> list[dict]:
        """purpose に部分一致するテンプレートを param_count 昇順で返す."""
        results = []
        for name, entry in self._data.get("templates", {}).items():
            if purpose.lower() in (entry.get("purpose") or "").lower():
                results.append({"name": name, **entry})
        results.sort(key=lambda x: x.get("param_count", 0))
        return results

    # -- 整合性チェック -------------------------------------------------------

    def check_integrity(self, name: str) -> bool:
        """保存済みハッシュと実ファイルのハッシュが一致するか検証する."""
        entry = self.get_entry(name)
        if entry is None:
            return False
        template_dir = self.resolve_path(name)
        if not template_dir.exists():
            return False
        current_hash = self.compute_content_hash(template_dir)
        return current_hash == entry.get("content_hash", "")

    # -- ブートストラップ -----------------------------------------------------

    def bootstrap(self) -> None:
        """templates/ 内の既存ディレクトリを verified/builtin として登録する."""
        if not self.templates_dir.exists():
            return
        now = datetime.now(timezone.utc).isoformat()
        templates = self._data.setdefault("templates", {})

        for child in sorted(self.templates_dir.iterdir()):
            if not child.is_dir():
                continue
            name = child.name
            if name.startswith("_") or name.startswith("."):
                continue
            if name in templates:
                continue  # 既存エントリはスキップ

            schema_path = child / "schema.json"
            param_count = 0
            if schema_path.exists():
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                param_count = self.count_params(schema)

            templates[name] = {
                "status": "verified",
                "source": "builtin",
                "content_hash": self.compute_content_hash(child),
                "param_count": param_count,
                "purpose": "",
                "tags": [],
                "added_at": now,
                "verified_at": now,
            }

        self.save()


# ---------------------------------------------------------------------------
# シングルトンアクセス
# ---------------------------------------------------------------------------

_default_registry: Registry | None = None


def get_default_registry() -> Registry:
    """デフォルトレジストリのシングルトンを取得する."""
    global _default_registry
    if _default_registry is None:
        from fcgen import REGISTRY_PATH, TEMPLATES_DIR, CANDIDATES_DIR
        _default_registry = Registry(REGISTRY_PATH, TEMPLATES_DIR, CANDIDATES_DIR)
        _default_registry.load()
    return _default_registry
