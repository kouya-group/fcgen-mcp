from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
CANDIDATES_DIR = PROJECT_ROOT / "templates_candidate"
REGISTRY_PATH = PROJECT_ROOT / "registry.json"
OUTPUT_DIR = PROJECT_ROOT / "output"

# FreeCAD version compatibility
FREECAD_MIN_VERSION = (0, 19, 0)  # Minimum supported
FREECAD_RECOMMENDED_VERSION = (1, 0, 0)  # Recommended
FREECAD_TESTED_VERSIONS = ["0.21", "1.0"]  # Tested against
