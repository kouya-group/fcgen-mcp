import json
from pathlib import Path

from fcgen.core.freecadcmd import run_script


def generate(params: dict, step_path: Path, stl_path: Path) -> None:
    step_path.parent.mkdir(parents=True, exist_ok=True)
    params_path = step_path.parent / "_fcgen_params.json"
    params_path.write_text(json.dumps(params, indent=2), encoding="utf-8")

    script_path = Path(__file__).resolve().parent / "freecad_generate.py"
    run_script(
        script_path=script_path,
        params_path=params_path,
        step_path=step_path,
        stl_path=stl_path,
        output_flags=params.get("output", {}),
    )
