from pathlib import Path
from datetime import datetime, timezone


def write_log(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    payload = [f"[{stamp}] {line}" for line in lines]
    path.write_text("\n".join(payload) + "\n", encoding="utf-8")
