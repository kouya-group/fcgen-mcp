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
        canonical_files = sorted(["constraints.json", "freecad_generate.py", "generator.py", "schema.json"])
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
        """purpose/name/tags に部分一致するテンプレートを param_count 昇順で返す.

        クエリを空白で分割し、全トークンが name・purpose・tags のいずれかに
        含まれる AND 検索を行う。
        """
        tokens = purpose.lower().split()
        if not tokens:
            return []
        results = []
        for name, entry in self._data.get("templates", {}).items():
            searchable = " ".join([
                name.lower(),
                (entry.get("purpose") or "").lower(),
                " ".join(t.lower() for t in entry.get("tags", [])),
            ])
            if all(tok in searchable for tok in tokens):
                results.append({"name": name, **entry})
        results.sort(key=lambda x: x.get("param_count", 0))
        return results

    # -- Constraints 付き検索 ------------------------------------------------

    def _load_constraints(self, name: str) -> dict | None:
        """テンプレートの constraints.json を読み込む。なければ None。"""
        cpath = self.resolve_path(name) / "constraints.json"
        if cpath.exists():
            return json.loads(cpath.read_text(encoding="utf-8"))
        return None

    def _build_constraint_index(self, name: str, constraints: dict) -> str:
        """constraints.json から検索用テキストを構築。"""
        parts = []
        # linked プリセット名
        for _key, linked in constraints.get("linked", {}).items():
            for preset_name in linked.get("presets", {}):
                parts.append(preset_name.lower())
        # variant プリセット名 + ラベル
        for _key, variant in constraints.get("variants", {}).items():
            for preset_name, info in variant.get("presets", {}).items():
                parts.append(preset_name.lower())
                if isinstance(info, dict) and "label" in info:
                    parts.append(info["label"].lower())
        # canonical の source
        for _key, canon in constraints.get("canonical", {}).items():
            if isinstance(canon, dict) and "source" in canon:
                parts.append(canon["source"].lower())
        return " ".join(parts)

    def _resolve_preset(self, query_tokens: list[str], constraints: dict) -> dict | None:
        """クエリトークンから linked/variant プリセットを解決する。"""
        # linked プリセット検索
        for _key, linked in constraints.get("linked", {}).items():
            presets = linked.get("presets", {})
            for preset_name, values in presets.items():
                if preset_name.lower() in query_tokens:
                    return {
                        "type": "linked",
                        "preset": preset_name,
                        "source": linked.get("source", ""),
                        "resolved_params": values,
                        "free_params": linked.get("free_params", []),
                    }
        # variant プリセット検索
        for param_key, variant in constraints.get("variants", {}).items():
            presets = variant.get("presets", {})
            for preset_name, info in presets.items():
                # プリセット名またはラベルの部分一致
                label = ""
                if isinstance(info, dict):
                    label = info.get("label", "").lower()
                check_texts = [preset_name.lower(), label]
                for tok in query_tokens:
                    for ct in check_texts:
                        if tok in ct:
                            if isinstance(info, dict) and "value" in info:
                                value = info["value"]
                                if isinstance(value, dict):
                                    resolved = value
                                else:
                                    resolved = {param_key: value}
                            else:
                                resolved = {param_key: info}
                            return {
                                "type": "variant",
                                "preset": preset_name,
                                "label": label,
                                "source": variant.get("source", ""),
                                "resolved_params": resolved,
                            }
        return None

    # テンプレート名の多言語エイリアス（日本語、略称など）
    _ALIASES: dict[str, list[str]] = {
        "bolt": ["ボルト", "ねじ"],
        "bracket": ["ブラケット", "l字金具"],
        "adapter_plate": ["アダプタープレート", "プレート", "plate"],
        "enclosure": ["エンクロージャー", "筐体", "ケース", "ボックス"],
        "table_top": ["天板", "テーブルトップ", "テーブル"],
        "simple_leg": ["脚", "レッグ"],
        "sphere": ["球", "ボール", "サッカーボール", "テニスボール", "野球ボール", "バスケットボール", "ゴルフボール", "卓球ボール"],
        "cup": ["カップ", "コップ", "マグカップ", "マグ", "コーヒーカップ", "コーヒーマグ", "エスプレッソ"],
        "lego_brick": ["レゴ", "lego", "ブロック"],
        "minecraft_block": ["マイクラブロック", "マイクラ", "マインクラフト", "minecraft"],
    }

    def find_with_constraints(self, purpose: str) -> list[dict]:
        """constraints.json も含めて横断検索し、プリセット解決済み結果を返す。"""
        import re
        tokens = purpose.lower().split()
        if not tokens:
            return []

        # トークン前処理: "2x4" → "2" "4", "20mm" → "20"
        preprocessed = []
        for tok in tokens:
            # "2x4" パターン
            m = re.match(r"^(\d+)x(\d+)$", tok, re.IGNORECASE)
            if m:
                preprocessed.extend([m.group(1), m.group(2)])
                continue
            preprocessed.append(tok)

        # 数値トークンを抽出（"20mm" → 20.0）
        numeric_values = []
        text_tokens = []
        for tok in preprocessed:
            m = re.match(r"^(\d+(?:\.\d+)?)\s*(?:mm)?$", tok)
            if m:
                numeric_values.append(float(m.group(1)))
            else:
                text_tokens.append(tok)

        # エイリアス展開: text_tokens にエイリアスが含まれていればテンプレート名に変換
        # 「M5ボルト」のように結合されたトークンも部分一致で分解する
        # 長いエイリアスを先にマッチさせる（「マイクラブロック」→「マイクラ」+「ブロック」ではなく一括マッチ）
        all_aliases: list[tuple[str, str]] = []  # (alias_lower, tmpl_name)
        for tmpl_name, aliases in self._ALIASES.items():
            for alias in aliases:
                all_aliases.append((alias.lower(), tmpl_name))
        all_aliases.sort(key=lambda x: len(x[0]), reverse=True)  # 長い順

        expanded_tokens = []
        for tok in text_tokens:
            matched_alias = False
            for al, tmpl_name in all_aliases:
                if tok == al:
                    expanded_tokens.append(tmpl_name)
                    matched_alias = True
                    break
                elif al in tok:
                    remainder = tok.replace(al, "", 1).strip()
                    expanded_tokens.append(tmpl_name)
                    if remainder:
                        # 残りも再帰的にエイリアス展開
                        remainder_resolved = False
                        for al2, tmpl2 in all_aliases:
                            if remainder == al2:
                                # 同じテンプレートなら冗長なので捨てる
                                if tmpl2 != tmpl_name:
                                    expanded_tokens.append(tmpl2)
                                remainder_resolved = True
                                break
                        if not remainder_resolved:
                            expanded_tokens.append(remainder)
                    matched_alias = True
                    break
            if not matched_alias:
                expanded_tokens.append(tok)
        text_tokens = expanded_tokens

        results = []
        for name, entry in self._data.get("templates", {}).items():
            if entry.get("status") != "verified":
                continue

            # 基本検索テキスト
            searchable = " ".join([
                name.lower(),
                (entry.get("purpose") or "").lower(),
                " ".join(t.lower() for t in entry.get("tags", [])),
            ])

            # constraints 検索テキスト追加
            constraints = self._load_constraints(name)
            if constraints:
                searchable += " " + self._build_constraint_index(name, constraints)

            # AND 検索（text_tokens のみ）
            if not text_tokens or all(tok in searchable for tok in text_tokens):
                result_entry = {"name": name, **entry}

                # プリセット解決
                if constraints:
                    preset = self._resolve_preset(text_tokens, constraints)
                    if preset:
                        result_entry["matched_preset"] = preset
                        # 数値をfree_paramsに割り当て
                        if numeric_values and "free_params" in preset:
                            assigned = {}
                            for i, fp in enumerate(preset.get("free_params", [])):
                                if i < len(numeric_values):
                                    assigned[fp] = numeric_values[i]
                            if assigned:
                                preset["assigned_free_params"] = assigned

                results.append(result_entry)

        results.sort(key=lambda x: (
            0 if "matched_preset" in x else 1,
            x.get("param_count", 0),
        ))
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
