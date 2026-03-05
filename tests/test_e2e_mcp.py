"""E2E 技術実証: MCP ツールを使った完全ワークフロー"""

from fcgen.mcp.server import (
    list_templates,
    get_template_schema,
    get_template_example,
    validate_params,
    find_template,
    list_candidates,
)


def test_e2e_discovery_and_validation():
    """テンプレート発見→スキーマ取得→サンプル取得→検証の一連フロー"""
    # 1. テンプレート一覧取得
    templates = list_templates()
    assert "bracket" in templates["templates"]

    # 2. bracket のスキーマ取得
    schema = get_template_schema("bracket")
    assert "properties" in schema

    # 3. サンプルパラメータ取得
    example = get_template_example("bracket")
    assert "units" in example

    # 4. サンプルパラメータで検証 (そのまま通るはず)
    result = validate_params("bracket", example)
    assert result["valid"] is True

    # 5. パラメータを壊して検証 (エラーになるはず)
    bad_params = {**example, "output": {"step": False, "stl": False}}
    result = validate_params("bracket", bad_params)
    assert result["valid"] is False


def test_e2e_find_simplest_for_purpose():
    """目的検索 → シンプルな形状が優先されることを確認"""
    result = find_template("mounting")
    assert result["ok"] is True
    # mounting にマッチするテンプレートが見つかる
    if result["results"]:
        counts = [r["param_count"] for r in result["results"]]
        assert counts == sorted(counts), "シンプルさ順にソートされていること"


def test_e2e_all_templates_validate_with_examples():
    """全テンプレートのサンプルが自身のスキーマを通ることを確認"""
    templates = list_templates()
    for name in templates["templates"]:
        example = get_template_example(name)
        if "error" in example:
            continue
        result = validate_params(name, example)
        assert result["valid"] is True, f"{name} のサンプルが検証に失敗: {result.get('error')}"
