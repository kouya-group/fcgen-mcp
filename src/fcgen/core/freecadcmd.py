import os
import shutil
import subprocess
from pathlib import Path


def find_freecadcmd() -> str:
    env_cmd = os.environ.get("FCGEN_FREECADCMD")
    if env_cmd:
        return env_cmd

    for name in ("freecadcmd.exe", "FreeCADCmd.exe", "freecadcmd", "FreeCADCmd"):
        cmd = shutil.which(name)
        if cmd:
            return cmd

    common = Path(r"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe")
    if common.exists():
        return str(common)
    raise RuntimeError(
        "freecadcmd was not found. Set FCGEN_FREECADCMD or install FreeCAD command-line tools."
    )


def run_script(script_path: Path, params_path: Path, step_path: Path, stl_path: Path, output_flags: dict) -> None:
    user_cfg = step_path.parent / "_freecad_user.cfg"
    system_cfg = step_path.parent / "_freecad_system.cfg"
    cmd = [
        find_freecadcmd(),
        "-u",
        str(user_cfg),
        "-s",
        str(system_cfg),
        str(script_path),
        "--pass",
        str(params_path),
        str(step_path),
        str(stl_path),
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            "FreeCAD generation failed.\n"
            f"command: {' '.join(cmd)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    if output_flags.get("step", True) and not step_path.exists():
        raise RuntimeError(
            "FreeCAD generation completed without STEP output.\n"
            f"command: {' '.join(cmd)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    if output_flags.get("stl", True) and not stl_path.exists():
        raise RuntimeError(
            "FreeCAD generation completed without STL output.\n"
            f"command: {' '.join(cmd)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
