"""
src/utils/file_handler.py
-------------------------
Handles all file reading and writing for the generator.

Responsibilities:
    - save_lesson(lesson)           : Save a generated lesson to data/generated/
                                      using lesson_id as the filename
    - load_lesson(lesson_id)        : Load a lesson JSON by ID
    - load_example(grade_band)      : Load a hand-crafted example lesson from
                                      data/examples/ by grade band
    - load_registry()               : Load the deduplication registry JSON
    - update_registry(entry)        : Add a new theme x skill x grade combo
                                      to the registry and save it
    - combo_exists(theme, skill, grade_band) : Check if a combo is already
                                      in the registry — returns True/False

Registry format (data/registry/registry.json):
    {
        "used_combinations": [
            {
                "theme": "Space Exploration",
                "skill": "retell a story in sequence",
                "grade_band": "K-2",
                "lesson_id": "L-K2-SPK-001",
                "generated_at": "2024-01-15T10:30:00"
            }
        ]
    }
"""

import json
from datetime import datetime
from pathlib import Path

# =============================================================================
# PATH CONSTANTS
# All paths are relative to the project root.
# Using pathlib.Path so this works on Windows, Mac, and Linux equally.
# =============================================================================

# Find the project root — two levels up from this file (src/utils/file_handler.py)
PROJECT_ROOT  = Path(__file__).resolve().parents[2]

DATA_EXAMPLES  = PROJECT_ROOT / "data" / "examples"
DATA_GENERATED = PROJECT_ROOT / "data" / "generated"
DATA_REGISTRY  = PROJECT_ROOT / "data" / "registry"
REGISTRY_FILE  = DATA_REGISTRY / "registry.json"

# The single examples file that holds all 5 hand-crafted lessons
EXAMPLES_FILE  = DATA_EXAMPLES / "bantrly_example_lessons.json"


# =============================================================================
# LESSON I/O
# =============================================================================

def save_lesson(lesson_dict: dict) -> Path:
    """
    Save a generated lesson to data/generated/<lesson_id>.json

    Args:
        lesson_dict: The lesson as a plain Python dict (call lesson.to_dict())

    Returns:
        The Path where the file was saved.

    Raises:
        KeyError: If lesson_dict doesn't contain a 'lesson_id' field.
    """
    lesson_id = lesson_dict["lesson_id"]
    filepath  = DATA_GENERATED / f"{lesson_id}.json"

    DATA_GENERATED.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(lesson_dict, f, indent=2, ensure_ascii=False)

    print(f"[file_handler] Saved lesson → {filepath}")
    return filepath


def load_lesson(lesson_id: str) -> dict:
    """
    Load a previously generated lesson from data/generated/<lesson_id>.json

    Args:
        lesson_id: e.g. "L-K2-SPK-001"

    Returns:
        The lesson as a plain Python dict.

    Raises:
        FileNotFoundError: If no lesson with that ID exists.
    """
    filepath = DATA_GENERATED / f"{lesson_id}.json"

    if not filepath.exists():
        raise FileNotFoundError(
            f"[file_handler] No lesson found with ID '{lesson_id}' at {filepath}"
        )

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# EXAMPLE LESSON LOADER
# Loads hand-crafted few-shot examples from data/examples/
# Selects the most relevant example by matching grade band.
# =============================================================================

# Maps each grade band string to the lesson_id of the matching example
GRADE_BAND_TO_EXAMPLE_ID = {
    "K-2":  "L-K2-SPK-001",
    "3-5":  "L-35-SPK-005",   # Mission Brief — good general 3-5 example
    "6-8":  "L-68-SPK-003",
    "9-12": "L-912-RDG-SPK-004",
}


def load_example_by_grade(grade_band: str) -> dict:
    """
    Load a hand-crafted example lesson matching the given grade band.
    Used as a few-shot example in the prompt to ground the LLM's output.

    Args:
        grade_band: One of "K-2", "3-5", "6-8", "9-12"

    Returns:
        The example lesson as a plain Python dict.

    Raises:
        ValueError: If the grade band is not one of the four valid options.
        FileNotFoundError: If the examples file doesn't exist.
    """
    if grade_band not in GRADE_BAND_TO_EXAMPLE_ID:
        raise ValueError(
            f"[file_handler] Invalid grade band '{grade_band}'. "
            f"Must be one of: {list(GRADE_BAND_TO_EXAMPLE_ID.keys())}"
        )

    if not EXAMPLES_FILE.exists():
        raise FileNotFoundError(
            f"[file_handler] Examples file not found at {EXAMPLES_FILE}. "
            f"Make sure bantrly_example_lessons.json is in data/examples/"
        )

    with open(EXAMPLES_FILE, "r", encoding="utf-8") as f:
        all_examples = json.load(f)

    lessons = all_examples["bantrly_example_lessons"]["lessons"]
    target_id = GRADE_BAND_TO_EXAMPLE_ID[grade_band]

    for lesson in lessons:
        if lesson["lesson_id"] == target_id:
            return lesson

    raise FileNotFoundError(
        f"[file_handler] Example lesson '{target_id}' not found in examples file."
    )


# =============================================================================
# DEDUPLICATION REGISTRY
# Tracks which theme x skill x grade_band combinations have been used.
# Prevents the generator from producing repetitive lessons.
# =============================================================================

def load_registry() -> dict:
    """
    Load the deduplication registry from data/registry/registry.json.
    If the file doesn't exist or is empty, returns an empty registry.

    Returns:
        A dict with a "used_combinations" list.
    """
    if not REGISTRY_FILE.exists():
        return {"used_combinations": []}

    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return {"used_combinations": []}
        return json.loads(content)


def save_registry(registry: dict) -> None:
    """
    Write the registry dict back to data/registry/registry.json.

    Args:
        registry: The full registry dict (with "used_combinations" list).
    """
    DATA_REGISTRY.mkdir(parents=True, exist_ok=True)

    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def combo_exists(theme: str, skill: str, grade_band: str, ela_domain: str) -> bool:
    """
    Check if a theme x skill x grade_band combination has already
    been used. Comparison is case-insensitive.

    Args:
        theme:      e.g. "Space Exploration"
        skill:      e.g. "retell a story in sequence"
        grade_band: e.g. "K-2"
        ela_domain: e.g. "Speaking"

    Returns:
        True if the combo already exists, False if it's new.
    """
    registry = load_registry()

    for entry in registry["used_combinations"]:
        if (
            entry["theme"].lower()      == theme.lower()      and
            entry["skill"].lower()      == skill.lower()      and
            entry["grade_band"].lower() == grade_band.lower() and
            entry.get("ela_domain", "").lower() == ela_domain.lower()
        ):
            return True

    return False


def register_combo(theme: str, skill: str, grade_band: str, ela_domain: str, lesson_id: str) -> None:
    """
    Add a new theme x skill x grade_band combo to the registry.
    Should be called immediately after a lesson is successfully generated.

    Args:
        theme:      e.g. "Space Exploration"
        skill:      e.g. "retell a story in sequence"
        grade_band: e.g. "K-2"
        ela_domain: e.g. "Speaking"
        lesson_id:  e.g. "L-K2-SPK-001"
    """
    registry = load_registry()

    entry = {
        "theme":        theme,
        "skill":        skill,
        "grade_band":   grade_band,
        "ela_domain":   ela_domain,
        "lesson_id":    lesson_id,
        "generated_at": datetime.utcnow().isoformat()
    }

    registry["used_combinations"].append(entry)
    save_registry(registry)

    print(f"[file_handler] Registered combo → {grade_band} | {theme} | {skill}")

def get_covered_skills(grade_band: str, ela_domain: str) -> list[str]:
    """
    Return skills already covered for a grade band + domain from the registry.
    Ordered oldest → newest (insertion order).

    Args:
        grade_band: e.g. "K-2"
        ela_domain: e.g. "Speaking"

    Returns:
        List of skill strings already generated for this band + domain.
    """
    registry   = load_registry()
    domain_key = ela_domain.lower()
    covered    = []

    for entry in registry["used_combinations"]:
        if entry["grade_band"].lower() != grade_band.lower():
            continue

        entry_domain = entry.get("ela_domain", "").lower()

        if ela_domain == "Reading → Speaking":
            if entry_domain in ("reading → speaking", "reading", "speaking"):
                covered.append(entry["skill"])
        else:
            if entry_domain == domain_key:
                covered.append(entry["skill"])

    return covered