# fcgen

LLMが検証済み標準形状を安全に合成するためのMCPサーバー。

## コンセプト

MCP + 自然言語で FreeCAD を直接操作するアプローチは自由度が高すぎて破綻する。
fcgen は**検証済みテンプレートの組み合わせ**でこの問題を解決する。

- テンプレートごとに JSON Schema でパラメータを定義
- 意味検証（寸法整合性など）を生成前に実施
- candidate -> verified のライフサイクルで品質を担保

## クイックスタート

```bash
pip install -e .            # 基本インストール
pip install -e ".[mcp]"     # MCP サーバーを使う場合
```

MCP サーバー起動:

```bash
python -m fcgen.mcp.server
```

CLI 実行:

```bash
python -m fcgen.cli.main run bracket \
  --in templates/bracket/examples/basic.json \
  --out output/test --dry-run
```

## MCP ツール一覧

| ツール | 説明 |
|--------|------|
| `list_templates` | 利用可能なテンプレート一覧を返す |
| `get_template_schema` | 指定テンプレートの完全な JSON Schema を返す |
| `get_template_example` | 指定テンプレートのサンプルパラメータを返す |
| `validate_params` | パラメータをスキーマ + 意味検証する（生成なし） |
| `find_template` | 目的に合うテンプレートを検索 |
| `generate_part` | 単一パーツを生成する |
| `generate_assembly` | 複数パーツのアセンブリを生成する |
| `list_candidates` | 候補（未検証）テンプレート一覧を返す |
| `propose_template` | 新しいテンプレートを候補として登録する |
| `verify_template` | 候補テンプレートを検証し verified に昇格する |

## テンプレートライフサイクル

```
[LLM/人間が作成] --> candidate --> テスト実行+検証 --> verified
                        |                                |
                        v                                v
                  templates_candidate/            templates/
```

`candidate` はテスト生成と検証に合格して初めて `verified` に昇格する。
LLM は verified テンプレートのみを `generate_part` で使用できる。

## Claude Desktop 設定例

```json
{
  "mcpServers": {
    "fcgen": {
      "command": "python",
      "args": ["-m", "fcgen.mcp.server"]
    }
  }
}
```

## FreeCAD 互換性

| 項目 | バージョン |
|------|-----------|
| 最小（必須） | FreeCAD 0.19+ |
| 推奨 | FreeCAD 1.0 |
| テスト済み | 0.21, 1.0 |

使用している FreeCAD API: Part（プリミティブ、ブーリアン）、Mesh（STL エクスポート）、基本 Placement。

## FreeCAD 設定

`freecadcmd` が PATH にない場合、環境変数で指定する:

```bash
export FCGEN_FREECADCMD="/path/to/freecadcmd"
```

Windows の場合:

```cmd
set FCGEN_FREECADCMD=C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe
```

## テスト

```bash
python -m pytest tests/ -v
```
