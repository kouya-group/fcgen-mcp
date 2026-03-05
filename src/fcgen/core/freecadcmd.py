import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from fcgen import FREECAD_MIN_VERSION, FREECAD_RECOMMENDED_VERSION, FREECAD_TESTED_VERSIONS

# バージョン情報キャッシュ（セッション中1回だけ取得）
_cached_version: dict | None = None
_version_fetched: bool = False


def find_freecadcmd() -> str:
    env_cmd = os.environ.get("FCGEN_FREECADCMD")
    if env_cmd:
        return env_cmd

    for name in ("freecadcmd.exe", "FreeCADCmd.exe", "freecadcmd", "FreeCADCmd"):
        cmd = shutil.which(name)
        if cmd:
            return cmd

    # Program Files 配下の FreeCAD * ディレクトリを新しい順に探索
    program_files = Path(r"C:\Program Files")
    if program_files.exists():
        for match in sorted(program_files.glob("FreeCAD */bin/freecadcmd.exe"), reverse=True):
            return str(match)

    raise RuntimeError(
        "freecadcmd was not found. Set FCGEN_FREECADCMD or install FreeCAD command-line tools."
    )


def get_freecad_version() -> dict | None:
    """FreeCAD のバージョン情報を取得する。結果はキャッシュされる。

    Returns a dict with keys: major, minor, patch, full.
    Returns None if freecadcmd is not found or the subprocess fails.
    """
    global _cached_version, _version_fetched
    if _version_fetched:
        return _cached_version

    _version_fetched = True

    try:
        cmd_path = find_freecadcmd()
    except RuntimeError:
        _cached_version = None
        return None

    script = (
        'import FreeCAD; v = FreeCAD.Version(); import json; '
        'print(json.dumps({"major": int(v[0]), "minor": int(v[1]), '
        '"patch": int(v[2]), "full": ".".join(v[:3])}))'
    )

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            user_cfg = tmp_path / "_freecad_user.cfg"
            system_cfg = tmp_path / "_freecad_system.cfg"
            script_file = tmp_path / "_version_check.py"
            script_file.write_text(script, encoding="utf-8")

            proc = subprocess.run(
                [cmd_path, "-u", str(user_cfg), "-s", str(system_cfg), str(script_file)],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            if proc.returncode != 0:
                _cached_version = None
                return None

            # stdout から JSON 行を探す
            for line in proc.stdout.strip().splitlines():
                line = line.strip()
                if line.startswith("{"):
                    _cached_version = json.loads(line)
                    return _cached_version

            _cached_version = None
            return None
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
        _cached_version = None
        return None


def check_freecad_available() -> dict:
    """FreeCAD 環境の状態を返す。

    Returns a dict: {"available": bool, "version": str or None, "path": str or None}
    """
    min_ver_str = ".".join(str(v) for v in FREECAD_MIN_VERSION)
    rec_ver_str = ".".join(str(v) for v in FREECAD_RECOMMENDED_VERSION)

    try:
        cmd_path = find_freecadcmd()
    except RuntimeError:
        return {
            "available": False,
            "version": None,
            "path": None,
            "compatible": None,
            "min_version": min_ver_str,
            "recommended_version": rec_ver_str,
            "tested_versions": FREECAD_TESTED_VERSIONS,
        }

    ver = get_freecad_version()

    if ver is not None:
        detected = (ver["major"], ver["minor"], ver["patch"])
        compatible = detected >= FREECAD_MIN_VERSION
    else:
        compatible = None

    return {
        "available": True,
        "version": ver["full"] if ver else None,
        "path": cmd_path,
        "compatible": compatible,
        "min_version": min_ver_str,
        "recommended_version": rec_ver_str,
        "tested_versions": FREECAD_TESTED_VERSIONS,
    }


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
