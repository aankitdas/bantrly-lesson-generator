"""
src/utils/validator.py
----------------------
Validates the raw JSON string returned by the LLM before
it is parsed into a Lesson object.

Why this exists:
    LLMs sometimes return malformed JSON, add markdown code fences
    (```json ... ```), or omit required fields. This module catches
    all of that before it causes an error downstream.

What will be defined here:
    - strip_code_fences(raw)        : Remove ```json and ``` wrappers
                                      if the LLM added them
    - parse_json_safely(raw)        : Try to parse JSON, return None
                                      and log error if it fails
    - validate_required_fields(data): Check all required lesson fields
                                      are present in the parsed dict
    - validate_against_schema(data) : Use Pydantic to validate the full
                                      lesson structure against our schema
    - validate_llm_output(raw)      : Master function — runs all of the
                                      above in sequence, returns a
                                      validated Lesson object or raises
                                      a descriptive ValidationError

Design note:
    This is the safety net between the LLM and our data layer.
    Nothing touches data/generated/ without passing through here first.
"""

import json
import re
from src.guardrails.checks import run_post_checks


# =============================================================================
# CUSTOM EXCEPTION
# Raised when validation fails at any step.
# Always includes a descriptive message so the generator knows
# exactly what went wrong and can log it clearly.
# =============================================================================

class ValidationError(Exception):
    """
    Raised when the LLM output fails any validation step.
    The message describes exactly which step failed and why.
    """
    pass


# =============================================================================
# REQUIRED FIELDS
# The top-level fields every lesson must have.
# Nested field validation is handled by run_post_checks().
# =============================================================================

REQUIRED_TOP_LEVEL_FIELDS = [
    "lesson_id",
    "metadata",
    "lesson_flow",
    "guardrail_flags",
]

REQUIRED_METADATA_FIELDS = [
    "grade_band",
    "ela_domain",
    "lesson_type",
    "theme",
    "primary_skill",
    "voice_markers",
    "estimated_duration_minutes",
    "ccss_anchor",
]

REQUIRED_FLOW_FIELDS = [
    "hook",
    "model",
    "practice",
    "reflect",
]


# =============================================================================
# STEP 1: STRIP CODE FENCES
# LLMs frequently wrap JSON in markdown code fences even when told not to.
# This strips them before attempting to parse.
# =============================================================================

def strip_code_fences(raw: str) -> str:
    """
    Remove markdown code fences from a raw LLM response string.

    Handles all common fence patterns:
        ```json ... ```
        ```      ... ```
        `        ... `

    Args:
        raw: The raw string returned by the LLM.

    Returns:
        The cleaned string with fences removed and whitespace stripped.
    """
    # Remove ```json or ``` fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$",          "", cleaned.strip(), flags=re.MULTILINE)

    # Remove single backtick wrapping (less common but possible)
    if cleaned.startswith("`") and cleaned.endswith("`"):
        cleaned = cleaned[1:-1]

    return cleaned.strip()


# =============================================================================
# STEP 2: PARSE JSON SAFELY
# Attempt json.loads() and raise a descriptive ValidationError if it fails.
# =============================================================================

def parse_json_safely(raw: str) -> dict:
    """
    Parse a JSON string into a Python dict.
    Raises ValidationError with a clear message if parsing fails.

    Args:
        raw: A (hopefully) valid JSON string.

    Returns:
        A Python dict.

    Raises:
        ValidationError: If the string is not valid JSON.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        # Show the first 300 chars of the raw string to help debugging
        preview = raw[:300] + "..." if len(raw) > 300 else raw
        raise ValidationError(
            f"[validator] LLM returned invalid JSON.\n"
            f"JSON error: {e}\n"
            f"Raw output preview:\n{preview}"
        )


# =============================================================================
# STEP 3: VALIDATE REQUIRED FIELDS
# Check that the parsed dict contains all required top-level,
# metadata, and lesson_flow fields.
# =============================================================================

def autocorrect_practice(data: dict) -> dict:
    """
    Auto-correct the common LLM mistake of returning practice as a dict
    instead of a list.

    The model sometimes returns:
        "practice": { "P1": { ... }, "P2": { ... } }

    When we need:
        "practice": [ { "prompt_id": "P1", ... }, { "prompt_id": "P2", ... } ]

    This corrects that silently before field validation runs.
    """
    try:
        practice = data["lesson_flow"]["practice"]
        if isinstance(practice, dict):
            print("[validator] ⚠️  practice was a dict — auto-correcting to list...")
            corrected = []
            for key, value in practice.items():
                if isinstance(value, dict):
                    if "prompt_id" not in value:
                        value["prompt_id"] = key
                    corrected.append(value)
            data["lesson_flow"]["practice"] = corrected
            print(f"[validator] Auto-corrected practice → {len(corrected)} prompts ")
    except (KeyError, TypeError):
        pass
    return data


def validate_required_fields(data: dict) -> None:
    """
    Check that all required fields are present in the parsed lesson dict.
    Checks top-level, metadata, and lesson_flow fields.

    Args:
        data: The parsed lesson dict.

    Raises:
        ValidationError: If any required field is missing.
    """
    # Check top-level fields
    missing_top = [f for f in REQUIRED_TOP_LEVEL_FIELDS if f not in data]
    if missing_top:
        raise ValidationError(
            f"[validator] Missing top-level fields: {missing_top}"
        )

    # Check metadata fields
    metadata = data.get("metadata", {})
    missing_meta = [f for f in REQUIRED_METADATA_FIELDS if f not in metadata]
    if missing_meta:
        raise ValidationError(
            f"[validator] Missing metadata fields: {missing_meta}"
        )

    # Check lesson_flow fields
    flow = data.get("lesson_flow", {})
    missing_flow = [f for f in REQUIRED_FLOW_FIELDS if f not in flow]
    if missing_flow:
        raise ValidationError(
            f"[validator] Missing lesson_flow fields: {missing_flow}"
        )

    # Check practice is a non-empty list
    practice = flow.get("practice", [])
    if not isinstance(practice, list) or len(practice) == 0:
        raise ValidationError(
            f"[validator] lesson_flow.practice must be a non-empty list. "
            f"Got: {type(practice).__name__}"
        )

    # Check practice has no more than 3 prompts
    if len(practice) > 3:
        raise ValidationError(
            f"[validator] lesson_flow.practice has {len(practice)} prompts. "
            f"Maximum allowed is 3."
        )


# =============================================================================
# STEP 4: RUN POST-GENERATION GUARDRAIL CHECKS
# Runs all checks from checks.py and embeds the results back
# into the lesson dict. Flags are recorded but do not block saving.
# =============================================================================

def validate_against_schema(data: dict) -> dict:
    """
    Run post-generation guardrail checks and embed results
    into the guardrail_flags section of the lesson dict.

    This does NOT raise on flag — it records the flag so the
    lesson is self-documenting about any issues found.

    Args:
        data: The parsed and field-validated lesson dict.

    Returns:
        The lesson dict with guardrail_flags updated from checks.
    """
    check_results = run_post_checks(data)

    # Overwrite the LLM's self-assessed guardrail flags with
    # our programmatic checks — our checks are more reliable
    data["guardrail_flags"] = {
        name: {
            "status":  result.status,
            "message": result.message,
        }
        for name, result in check_results.items()
    }

    return data


# =============================================================================
# MASTER VALIDATION FUNCTION
# Runs all four steps in sequence.
# This is the only function the generator needs to call.
# =============================================================================

def validate_llm_output(raw: str) -> dict:
    """
    Master validation function. Runs the full pipeline:
        1. Strip code fences
        2. Parse JSON
        3. Validate required fields
        4. Run guardrail checks and embed results

    Args:
        raw: The raw string returned by the Groq API.

    Returns:
        A clean, validated lesson dict ready to be saved.

    Raises:
        ValidationError: If steps 1-3 fail (structural problems).
        Step 4 never raises — it flags and records issues.
    """
    print("[validator] Starting validation pipeline...")

    # Step 1
    cleaned = strip_code_fences(raw)
    print("[validator] Step 1 — Code fences stripped ✅")

    # Step 2
    data = parse_json_safely(cleaned)
    print("[validator] Step 2 — JSON parsed successfully ✅")

    # Step 2.5: Auto-correct known LLM formatting mistakes
    data = autocorrect_practice(data)

    # Step 3
    validate_required_fields(data)
    print("[validator] Step 3 — Required fields present ✅")

    # Step 4
    data = validate_against_schema(data)
    print("[validator] Step 4 — Guardrail checks complete ✅")

    print(f"[validator] Validation passed for lesson: {data.get('lesson_id', 'UNKNOWN')}")
    return data