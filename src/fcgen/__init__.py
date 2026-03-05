from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
CANDIDATES_DIR = PROJECT_ROOT / "templates_candidate"
REGISTRY_PATH = PROJECT_ROOT / "registry.json"
OUTPUT_DIR = PROJECT_ROOT / "output"
