"""
src/core/skill_selector.py
--------------------------
Selects the next uncovered skill from the taxonomy for a given
grade band and ELA domain.

Responsibilities:
    - get_next_skill(grade_band, ela_domain)
        Looks at the registry to find which skills have already been
        covered for this band + domain, then returns the next uncovered
        one. If all skills are covered, cycles back to the least
        recently used skill.

    - get_coverage_report(grade_band, ela_domain)
        Returns a dict showing covered and remaining skills.
        Used by notebooks and the HF Spaces UI.

Design note:
    "Reading → Speaking" draws from both Reading and Speaking skill
    lists, interleaving them so both domains get covered evenly.
"""

import json
from pathlib import Path
from src.utils.file_handler import load_registry
from datetime import datetime

# =============================================================================
# PATH
# =============================================================================

PROJECT_ROOT   = Path(__file__).resolve().parents[2]
TAXONOMY_FILE  = PROJECT_ROOT / "data" / "skills" / "skill_taxonomy.json"


# =============================================================================
# TAXONOMY LOADER
# =============================================================================

def load_taxonomy() -> dict:
    """
    Load the full skill taxonomy from data/skills/skill_taxonomy.json.

    Returns:
        The taxonomy as a nested dict:
        { grade_band: { domain: [skill, ...] } }

    Raises:
        FileNotFoundError: If the taxonomy file doesn't exist.
    """
    if not TAXONOMY_FILE.exists():
        raise FileNotFoundError(
            f"[skill_selector] Taxonomy file not found at {TAXONOMY_FILE}."
        )

    with open(TAXONOMY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_skills_for(grade_band: str, ela_domain: str) -> list[str]:
    """
    Return the ordered skill list for a grade band + domain combination.

    For "Reading → Speaking", interleaves the Reading and Speaking
    skill lists so both domains are covered evenly.

    Args:
        grade_band: One of "K-2", "3-5", "6-8", "9-12"
        ela_domain: One of the valid ELA domains

    Returns:
        An ordered list of skill strings.

    Raises:
        KeyError: If grade band or domain is not found in taxonomy.
    """
    taxonomy = load_taxonomy()

    if grade_band not in taxonomy:
        raise KeyError(
            f"[skill_selector] Grade band '{grade_band}' not in taxonomy. "
            f"Available: {list(taxonomy.keys())}"
        )

    band = taxonomy[grade_band]

    if ela_domain == "Reading → Speaking":
        reading  = band.get("Reading",  [])
        speaking = band.get("Speaking", [])
        # Interleave: Reading[0], Speaking[0], Reading[1], Speaking[1]...
        interleaved = []
        for r, s in zip(reading, speaking):
            interleaved.append(r)
            interleaved.append(s)
        # Append any remainder if lists are unequal length
        interleaved += reading[len(speaking):]
        interleaved += speaking[len(reading):]
        return interleaved

    if ela_domain not in band:
        raise KeyError(
            f"[skill_selector] Domain '{ela_domain}' not in taxonomy for '{grade_band}'. "
            f"Available: {list(band.keys())}"
        )

    return band[ela_domain]


# =============================================================================
# COVERAGE TRACKER
# =============================================================================

def get_covered_skills(grade_band: str, ela_domain: str) -> list[str]:
    """
    Return a list of skills already covered for this grade band + domain,
    in the order they were generated (oldest first).

    Reads from the deduplication registry.

    Args:
        grade_band: e.g. "K-2"
        ela_domain: e.g. "Speaking"

    Returns:
        Ordered list of skill strings already generated.
    """
    registry = load_registry()
    covered  = []

    # Normalise "Reading → Speaking" for comparison
    domain_key = ela_domain.lower()

    for entry in registry["used_combinations"]:
        if entry["grade_band"].lower() != grade_band.lower():
            continue

        entry_domain = entry.get("ela_domain", "").lower()

        # Match exact domain OR either component of Reading → Speaking
        if ela_domain == "Reading → Speaking":
            if entry_domain in ("reading → speaking", "reading", "speaking"):
                covered.append(entry["skill"])
        elif ela_domain in ("Reading", "Speaking"):
            # Also count Reading → Speaking lessons toward Reading and Speaking
            if entry_domain == domain_key or entry_domain == "reading → speaking":
                covered.append(entry["skill"])
        else:
            if entry_domain == domain_key:
                covered.append(entry["skill"])

    return covered


# =============================================================================
# SKILL SELECTOR
# =============================================================================

def get_next_skill(grade_band: str, ela_domain: str) -> str:
    """
    Select the next uncovered skill for this grade band + domain.

    Selection logic:
        1. Load the ordered skill list from the taxonomy
        2. Load covered skills from the registry
        3. Return the first skill in the taxonomy list not yet covered
        4. If all skills are covered, cycle deterministically using
           len(covered) % len(all_skills) — rotates through all skills
           in taxonomy order indefinitely

    Args:
        grade_band: One of "K-2", "3-5", "6-8", "9-12"
        ela_domain: One of the valid ELA domains

    Returns:
        A skill string from the taxonomy.
    """
    all_skills  = get_skills_for(grade_band, ela_domain)
    covered     = get_covered_skills(grade_band, ela_domain)
    covered_set = set(s.lower() for s in covered)

    # Find first uncovered skill
    for skill in all_skills:
        if skill.lower() not in covered_set:
            return skill

    # All skills covered — cycle deterministically
    # len(covered) grows with each generation, so modulo rotates
    # through all skills in order: 5%5=0, 6%5=1, 7%5=2, etc.
    cycle_index = len(covered) % len(all_skills)
    return all_skills[cycle_index]


# =============================================================================
# COVERAGE REPORT
# =============================================================================

def get_coverage_report(grade_band: str, ela_domain: str) -> dict:
    """
    Return a coverage report for a grade band + domain combination.

    Useful for notebooks and the HF Spaces UI to show progress.

    Args:
        grade_band: e.g. "6-8"
        ela_domain: e.g. "Speaking"

    Returns:
        A dict with keys:
            grade_band    : str
            ela_domain    : str
            total         : int — total skills in taxonomy
            covered_count : int — skills with at least one lesson
            remaining     : list[str] — skills not yet covered
            covered       : list[str] — skills already covered
            complete      : bool — True if all skills covered
    """
    all_skills  = get_skills_for(grade_band, ela_domain)
    covered     = get_covered_skills(grade_band, ela_domain)
    covered_set = set(s.lower() for s in covered)

    remaining = [s for s in all_skills if s.lower() not in covered_set]
    covered_in_taxonomy = [s for s in all_skills if s.lower() in covered_set]

    return {
        "grade_band":    grade_band,
        "ela_domain":    ela_domain,
        "total":         len(all_skills),
        "covered_count": len(covered_in_taxonomy),
        "covered":       covered_in_taxonomy,
        "remaining":     remaining,
        "complete":      len(remaining) == 0,
    }