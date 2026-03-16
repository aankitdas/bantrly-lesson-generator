"""
src/guardrails/checks.py
------------------------
All guardrail logic. Runs before the prompt is built and after
the lesson is generated.

PRE-GENERATION checks (validate the inputs):
    - validate_grade_band()     : Is the grade band one of our four valid options?
    - validate_ela_domain()     : Is the domain one of Speaking/Listening/Reading/Writing?
    - validate_theme()          : Is the theme non-empty and within length limits?
    - check_deduplication()     : Has this theme x skill x grade combo been used before?

POST-GENERATION checks (validate the output):
    - check_single_skill()      : Does the lesson teach exactly one primary skill?
    - check_cognitive_load()    : Is complexity appropriate for the grade band?
    - check_vocabulary_ceiling(): Are prompts within word count limits per grade band?
    - check_cultural_bias()     : Does the lesson contain any flagged terms or patterns?

Design note:
    Each check returns a CheckResult object with:
        - status: "pass" or "flag"
        - message: explanation of why it passed or was flagged
    This makes guardrail results human-readable in the output JSON.

Research grounding:
    Cognitive load checks are derived from Sweller (1988) grade-band rules
    defined in src/prompts/grade_specs.py.
"""

from dataclasses import dataclass
from src.utils.file_handler import combo_exists


# =============================================================================
# SHARED RESULT TYPE
# Every check returns a CheckResult — never raises an exception.
# The generator collects all results and embeds them in the lesson JSON.
# =============================================================================

@dataclass
class CheckResult:
    """
    The output of a single guardrail check.

    status:  "pass" → no issues found
             "flag" → issue detected; see message
    message: Human-readable explanation of the outcome.
             Always written as if a teacher might read it.
    """
    status:  str   # "pass" or "flag"
    message: str

    def passed(self) -> bool:
        return self.status == "pass"

    def __repr__(self):
        icon = "✅" if self.passed() else "⚠️"
        return f"{icon } [{self.status.upper()}] {self.message}"


# =============================================================================
# VALID VALUES
# Single source of truth for accepted input values.
# Mirrors the enums in schema.py but kept as plain sets here so
# checks.py has no dependency on pydantic.
# =============================================================================

VALID_GRADE_BANDS = {"K-2", "3-5", "6-8", "9-12"}

VALID_ELA_DOMAINS = {
    "Speaking",
    "Listening",
    "Reading",
    "Writing",
    "Reading → Speaking",
}

# Vocabulary ceiling: max words allowed in a single speaking prompt per grade band.
# Grounded in Sweller (1988) — working memory limits by developmental stage.
VOCAB_CEILING = {
    "K-2":  30,
    "3-5":  60,
    "6-8":  100,
    "9-12": 150,
}

# Words that suggest a lesson may be teaching more than one skill.
# A primary_skill containing these is a signal to flag.
MULTI_SKILL_SIGNALS = [" and ", " & ", " plus ", " as well as ", " while also "]

# Terms that may indicate cultural specificity without context.
# This is a minimal starter list — a production system would use a
# more sophisticated classifier. Flagging is not blocking.
CULTURAL_BIAS_TERMS = [
    "thanksgiving", "christmas", "halloween", "fourth of july",
    "american", "our country", "the founding fathers",
    "as an american", "in america",
]


# =============================================================================
# PRE-GENERATION CHECKS
# Run before the prompt is built, on the raw user inputs.
# =============================================================================

def validate_grade_band(grade_band: str) -> CheckResult:
    """
    Confirm the grade band is one of our four valid options.

    Args:
        grade_band: The raw string input from the user.

    Returns:
        CheckResult with status "pass" or "flag".
    """
    if grade_band in VALID_GRADE_BANDS:
        return CheckResult(
            status="pass",
            message=f"Grade band '{grade_band}' is valid."
        )
    return CheckResult(
        status="flag",
        message=(
            f"'{grade_band}' is not a valid grade band. "
            f"Must be one of: {sorted(VALID_GRADE_BANDS)}"
        )
    )


def validate_ela_domain(ela_domain: str) -> CheckResult:
    """
    Confirm the ELA domain is one of our valid options.

    Args:
        ela_domain: The raw string input from the user.

    Returns:
        CheckResult with status "pass" or "flag".
    """
    if ela_domain in VALID_ELA_DOMAINS:
        return CheckResult(
            status="pass",
            message=f"ELA domain '{ela_domain}' is valid."
        )
    return CheckResult(
        status="flag",
        message=(
            f"'{ela_domain}' is not a valid ELA domain. "
            f"Must be one of: {sorted(VALID_ELA_DOMAINS)}"
        )
    )


def validate_theme(theme: str) -> CheckResult:
    """
    Confirm the theme is non-empty and a reasonable length.

    Args:
        theme: The raw theme string from the user.

    Returns:
        CheckResult with status "pass" or "flag".
    """
    theme = theme.strip()

    if not theme:
        return CheckResult(
            status="flag",
            message="Theme cannot be empty."
        )
    if len(theme.split()) < 2:
        return CheckResult(
            status="flag",
            message=f"Theme '{theme}' is too short. Please provide a descriptive theme."
        )
    if len(theme) > 80:
        return CheckResult(
            status="flag",
            message=f"Theme is too long ({len(theme)} chars). Keep it under 80 characters."
        )

    return CheckResult(
        status="pass",
        message=f"Theme '{theme}' is valid."
    )


def check_deduplication(theme: str, skill: str, grade_band: str, ela_domain: str) -> CheckResult:
    """
    Check if this theme x skill x grade_band x ela_domain combination
    has already been generated.

    Args:
        theme:      e.g. "Space Exploration"
        skill:      e.g. "Present a main idea with two supporting details"
        grade_band: e.g. "3-5"
        ela_domain: e.g. "Speaking"

    Returns:
        CheckResult — flagged if the combo already exists.
    """
    if combo_exists(theme, skill, grade_band, ela_domain):
        return CheckResult(
            status="flag",
            message=(
                f"Combination already used: '{theme}' × '{skill}' × '{grade_band}' × '{ela_domain}'. "
                f"Try a different theme to avoid repetition."
            )
        )
    return CheckResult(
        status="pass",
        message="Combination is new — no duplication detected."
    )


def run_pre_checks(grade_band: str, ela_domain: str, theme: str) -> dict:
    """
    Run all pre-generation checks at once.
    Returns a dict of CheckResults keyed by check name.

    Args:
        grade_band: User-provided grade band string
        ela_domain: User-provided ELA domain string
        theme:      User-provided theme string

    Returns:
        Dict mapping check name → CheckResult

    Raises:
        ValueError: If any check fails (status="flag"). The generator
                    should not proceed if pre-checks fail.
    """
    results = {
        "grade_band": validate_grade_band(grade_band),
        "ela_domain": validate_ela_domain(ela_domain),
        "theme":      validate_theme(theme),
    }

    failures = [name for name, r in results.items() if not r.passed()]

    if failures:
        messages = "\n".join(f"  {results[f]}" for f in failures)
        raise ValueError(
            f"[checks] Pre-generation checks failed:\n{messages}"
        )

    print("[checks] All pre-generation checks passed ✅")
    return results


# =============================================================================
# POST-GENERATION CHECKS
# Run on the lesson dict returned by the LLM, before saving to disk.
# These never raise — they flag and let the lesson be saved with warnings.
# =============================================================================

def check_single_skill(lesson_dict: dict) -> CheckResult:
    """
    Verify that primary_skill describes exactly one skill.
    Flags if the skill text contains conjunctions suggesting multiple skills.

    Grounding: Instructional clarity principle — one lesson, one measurable
    target. Multi-skill lessons produce unfocused voice marker feedback.

    Args:
        lesson_dict: The raw lesson dict from the LLM.

    Returns:
        CheckResult
    """
    skill = lesson_dict.get("metadata", {}).get("primary_skill", "")

    if not skill:
        return CheckResult(
            status="flag",
            message="primary_skill is missing or empty."
        )

    skill_lower = skill.lower()
    for signal in MULTI_SKILL_SIGNALS:
        if signal in skill_lower:
            return CheckResult(
                status="flag",
                message=(
                    f"primary_skill may describe more than one skill "
                    f"(contains '{signal.strip()}'): '{skill}'"
                )
            )

    return CheckResult(
        status="pass",
        message=f"Single skill confirmed: '{skill}'"
    )


def check_vocabulary_ceiling(lesson_dict: dict) -> CheckResult:
    """
    Check that no speaking prompt exceeds the word count ceiling
    for the lesson's grade band.

    Grounding: Sweller (1988) — working memory capacity limits in children.
    Overly long prompts split attention between reading and speaking.

    Args:
        lesson_dict: The raw lesson dict from the LLM.

    Returns:
        CheckResult — flags which prompt(s) exceeded the ceiling.
    """
    grade_band = lesson_dict.get("metadata", {}).get("grade_band", "")
    ceiling    = VOCAB_CEILING.get(grade_band)

    if ceiling is None:
        return CheckResult(
            status="flag",
            message=f"Cannot check vocabulary — unknown grade band '{grade_band}'."
        )

    prompts   = lesson_dict.get("lesson_flow", {}).get("practice", [])
    violations = []

    for p in prompts:
        text       = p.get("text", "")
        word_count = len(text.split())
        if word_count > ceiling:
            violations.append(
                f"Prompt {p.get('prompt_id', '?')} has {word_count} words "
                f"(ceiling for {grade_band} is {ceiling})"
            )

    if violations:
        return CheckResult(
            status="flag",
            message="Vocabulary ceiling exceeded: " + "; ".join(violations)
        )

    return CheckResult(
        status="pass",
        message=f"All prompts within {grade_band} vocabulary ceiling ({ceiling} words)."
    )


def check_cognitive_load(lesson_dict: dict) -> CheckResult:
    """
    For K-2 lessons, flag if the hook introduces both a new theme AND
    new vocabulary terms simultaneously — a double extraneous load risk.

    Grounding: Sweller (1988) — for young learners, only one element
    should be novel at a time.

    This is a heuristic check: it looks for hook length as a proxy
    for complexity. A production system would use a readability scorer.

    Args:
        lesson_dict: The raw lesson dict from the LLM.

    Returns:
        CheckResult
    """
    grade_band  = lesson_dict.get("metadata", {}).get("grade_band", "")
    hook_content = lesson_dict.get("lesson_flow", {}).get("hook", {}).get("content", "")
    hook_words   = len(hook_content.split())

    # For K-2, flag if the hook is unusually long (proxy for over-complexity)
    if grade_band == "K-2" and hook_words > 80:
        return CheckResult(
            status="flag",
            message=(
                f"K-2 hook is {hook_words} words — may introduce too much novelty at once. "
                f"Consider simplifying to under 80 words (Sweller, 1988)."
            )
        )

    return CheckResult(
        status="pass",
        message=f"Cognitive load check passed for grade band '{grade_band}'."
    )


def check_cultural_bias(lesson_dict: dict) -> CheckResult:
    """
    Scan lesson text for terms that may indicate cultural specificity
    without sufficient context for non-Western or international students.

    Grounding: Brief requirement — "cultural bias in narratives" is a
    known limitation. Flagging does not block; it prompts human review.

    Args:
        lesson_dict: The raw lesson dict from the LLM.

    Returns:
        CheckResult
    """
    # Collect all text fields from the lesson into one string for scanning
    all_text = _extract_all_text(lesson_dict).lower()

    found = [term for term in CULTURAL_BIAS_TERMS if term in all_text]

    if found:
        return CheckResult(
            status="flag",
            message=(
                f"Potential cultural specificity detected: {found}. "
                f"Review whether non-US/non-Western students would have "
                f"sufficient context. Consider adding a brief explainer or "
                f"choosing a more globally neutral reference."
            )
        )

    return CheckResult(
        status="pass",
        message="No cultural bias terms detected."
    )


def run_post_checks(lesson_dict: dict) -> dict:
    """
    Run all post-generation checks on the lesson dict.
    Returns a dict of CheckResults — never raises.

    Args:
        lesson_dict: The raw lesson dict returned by the LLM.

    Returns:
        Dict mapping check name → CheckResult.
        Also prints a summary to the console.
    """
    results = {
        "single_skill_check":       check_single_skill(lesson_dict),
        "vocabulary_ceiling_check": check_vocabulary_ceiling(lesson_dict),
        "cognitive_load_check":     check_cognitive_load(lesson_dict),
        "cultural_bias_check":      check_cultural_bias(lesson_dict),
    }

    for name, result in results.items():
        print(f"[checks] {name}: {result}")

    return results


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _extract_all_text(lesson_dict: dict) -> str:
    """
    Recursively extract all string values from a nested dict.
    Used by the cultural bias check to scan the full lesson text.
    """
    parts = []
    if isinstance(lesson_dict, dict):
        for value in lesson_dict.values():
            parts.append(_extract_all_text(value))
    elif isinstance(lesson_dict, list):
        for item in lesson_dict:
            parts.append(_extract_all_text(item))
    elif isinstance(lesson_dict, str):
        parts.append(lesson_dict)
    return " ".join(parts)