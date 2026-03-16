"""
src/core/generator.py
---------------------
The main orchestrator. This is the module that ties everything together.

When you call generator.generate(), here is the sequence it runs:
    1. Validate inputs via guardrails/checks.py
    2. Load a relevant few-shot example from data/examples/
    3. Build the full prompt via prompts/templates.py
    4. Send the prompt to the Groq API
    5. Parse and validate the response via utils/validator.py
    6. Log the theme x skill x grade combo via utils/file_handler.py
    7. Save the lesson JSON to data/generated/
    8. Return the Lesson object

What will be defined here:
    - LessonGenerator     : Main class with a .generate() method

Usage:
    from src.core.generator import LessonGenerator

    gen = LessonGenerator()
    lesson = gen.generate(
        grade_band="6-8",
        ela_domain="Speaking",
        theme="Climate Change"
    )
"""

import os
import time
from dotenv import load_dotenv
from groq import Groq

from src.guardrails.checks import run_pre_checks, check_deduplication
from src.prompts.templates import build_full_prompt, inspect_prompt
from src.utils.validator    import validate_llm_output, ValidationError
from src.utils.file_handler import save_lesson, register_combo, DATA_GENERATED
from src.core.skill_selector import get_next_skill

# Load environment variables from .env
load_dotenv()

# =============================================================================
# CONSTANTS
# =============================================================================

# The Groq model we use for generation.
# llama-3.3-70b-versatile is currently the best free-tier model
# for instruction-following and structured JSON output on Groq.
GROQ_MODEL = "llama-3.1-8b-instant" # "llama-3.3-70b-versatile" # "llama-3.1-8b-instant"

# Generation parameters
MAX_TOKENS   = 4096   # Enough for a complete lesson JSON
TEMPERATURE  = 0.7    # Balance between creativity and consistency
MAX_RETRIES  = 3      # How many times to retry on validation failure
RETRY_DELAY  = 2      # Seconds to wait between retries


# =============================================================================
# LESSON GENERATOR
# =============================================================================

class LessonGenerator:
    """
    The main lesson generation orchestrator.

    Ties together all modules into a single .generate() call:
        checks → prompt → Groq API → validate → save → register

    Usage:
        gen    = LessonGenerator()
        lesson = gen.generate(
            grade_band = "6-8",
            ela_domain = "Speaking",
            theme      = "Climate Change"
        )

    The returned lesson is a validated dict saved to data/generated/.
    """

    def __init__(self, verbose: bool = True):
        """
        Initialise the generator and Groq client.

        Args:
            verbose: If True, print step-by-step progress logs.
                     Set to False for cleaner notebook output.

        Raises:
            EnvironmentError: If GROQ_API_KEY is not set in .env
        """
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise EnvironmentError(
                "[generator] GROQ_API_KEY not found. "
                "Make sure it is set in your .env file."
            )

        self.client  = Groq(api_key=api_key)
        self.verbose = verbose

        if self.verbose:
            print("[generator] LessonGenerator initialised ✅")
            print(f"[generator] Model: {GROQ_MODEL}")


    def _log(self, message: str) -> None:
        """Print a log message only if verbose mode is on."""
        if self.verbose:
            print(message)


    def generate(
        self,
        grade_band : str,
        ela_domain : str,
        theme      : str,
        skill      : str = None,
        skip_dedup : bool = False,
    ) -> dict:
        """
        Generate a complete, validated Bantrly lesson.

        Args:
            grade_band : One of "K-2", "3-5", "6-8", "9-12"
            ela_domain : One of "Speaking", "Listening", "Reading",
                         "Writing", "Reading → Speaking"
            theme      : The lesson theme e.g. "Climate Change"
            skill      : Optional. The exact skill from the taxonomy to target.
                         If None, the next skill in the domain will be selected.
            skip_dedup : If True, skip deduplication check.
                         Useful for testing. Default False.

        Returns:
            A validated lesson dict, saved to data/generated/.

        Raises:
            ValueError       : If pre-checks fail (bad grade band, domain, theme)
            RuntimeError     : If all retries are exhausted without a valid lesson
            EnvironmentError : If GROQ_API_KEY is missing
        """
        self._log("\n" + "="*60)
        self._log(f"[generator] Starting lesson generation")
        self._log(f"[generator] Grade: {grade_band} | Domain: {ela_domain} | Theme: {theme}")
        self._log("="*60)

        # ------------------------------------------------------------------
        # STEP 1: Pre-generation checks
        # Validates grade band, ELA domain, and theme format.
        # Raises ValueError immediately if any check fails.
        # ------------------------------------------------------------------
        self._log("\n[generator] Step 1 — Running pre-generation checks...")
        run_pre_checks(grade_band, ela_domain, theme)

        # ------------------------------------------------------------------
        # STEP 2: Deduplication check
        # We don't know the skill yet (the LLM picks it), so we check
        # theme + grade_band only here. Full combo is registered after.
        # ------------------------------------------------------------------
        if not skip_dedup:
            self._log("[generator] Step 2 — Checking deduplication...")
            dedup = check_deduplication(theme, theme, grade_band, ela_domain)
            if not dedup.passed():
                self._log(f"[generator] ⚠️  {dedup.message}")
                self._log("[generator] Proceeding anyway — skill may differ.")

        # ------------------------------------------------------------------
        # STEP 3: Select skill from taxonomy
        # If no skill is provided, auto-select the next uncovered skill
        # for this grade band + domain combination.
        # ------------------------------------------------------------------
        self._log("\n[generator] Step 3 — Selecting skill...")
        if skill is None:
            skill = get_next_skill(grade_band, ela_domain)
            self._log(f"[generator] Auto-selected skill: {skill}")
        else:
            self._log(f"[generator] Using provided skill: {skill}")

        # ------------------------------------------------------------------
        # STEP 4: Build the prompt
        # ------------------------------------------------------------------
        self._log("\n[generator] Step 4 — Building prompt...")
        messages = build_full_prompt(grade_band, ela_domain, theme, skill)

        # ------------------------------------------------------------------
        # STEP 5 + 6: Call Groq API + Validate output
        # Retries up to MAX_RETRIES times on ValidationError.
        # ------------------------------------------------------------------
        self._log(f"\n[generator] Step 5 — Calling Groq API ({GROQ_MODEL})...")

        lesson = None
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._log(f"[generator] Attempt {attempt}/{MAX_RETRIES}...")

                # Make the API call
                response = self.client.chat.completions.create(
                    model       = GROQ_MODEL,
                    messages    = messages,
                    max_tokens  = MAX_TOKENS,
                    temperature = TEMPERATURE,
                )

                raw_output = response.choices[0].message.content
                self._log(f"[generator] Received response — {len(raw_output):,} chars")

                # Step 6: Validate the response
                self._log("\n[generator] Step 6 — Validating output...")
                lesson = validate_llm_output(raw_output)

                # If we get here, validation passed
                break

            except ValidationError as e:
                last_error = e
                self._log(f"[generator] ⚠️  Validation failed on attempt {attempt}: {e}")
                if attempt < MAX_RETRIES:
                    self._log(f"[generator] Retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)

            except Exception as e:
                # Unexpected errors (network, API errors) — re-raise immediately
                raise RuntimeError(
                    f"[generator] Groq API call failed: {type(e).__name__}: {e}"
                )

        if lesson is None:
            raise RuntimeError(
                f"[generator] All {MAX_RETRIES} attempts failed. "
                f"Last error: {last_error}"
            )

        # ------------------------------------------------------------------
        # STEP 7: Assign a guaranteed unique lesson ID
        # We never trust the LLM to generate the ID — it reuses numbers.
        # We generate it ourselves based on what already exists on disk.
        # ------------------------------------------------------------------
        self._log("\n[generator] Step 7 — Assigning unique lesson ID...")
        lesson["lesson_id"] = self._generate_unique_id(grade_band, ela_domain)
        self._log(f"[generator] Assigned ID: {lesson['lesson_id']}")

        # ------------------------------------------------------------------
        # STEP 8: Save the lesson to data/generated/
        # ------------------------------------------------------------------
        self._log("[generator] Step 8 — Saving lesson...")
        save_lesson(lesson)

        # ------------------------------------------------------------------
        # STEP 9: Register the combo in the deduplication registry
        # ------------------------------------------------------------------
        self._log("[generator] Step 9 — Registering combo...")
        skill = lesson.get("metadata", {}).get("primary_skill", "unknown")
        register_combo(theme, skill, grade_band, ela_domain, lesson["lesson_id"])

        # ------------------------------------------------------------------
        # DONE
        # ------------------------------------------------------------------
        self._log("\n" + "="*60)
        self._log(f"[generator] ✅ Lesson generated successfully!")
        self._log(f"[generator] ID     : {lesson['lesson_id']}")
        self._log(f"[generator] Skill  : {skill}")
        self._log(f"[generator] Domain : {lesson['metadata']['ela_domain']}")
        self._log(f"[generator] Theme  : {lesson['metadata']['theme']}")
        self._log("="*60 + "\n")

        return lesson

    def _generate_unique_id(self, grade_band: str, ela_domain: str) -> str:
        """
        Generate a unique lesson ID that is guaranteed not to already
        exist in data/generated/.

        Format: L-{GRADEBAND}-{DOMAIN}-{3-digit number}
        Example: L-K2-SPK-001, L-912-RDG-004

        Args:
            grade_band: e.g. "K-2"
            ela_domain: e.g. "Speaking"

        Returns:
            A unique lesson ID string.
        """
        # Build the grade band slug: "K-2" → "K2", "9-12" → "912"
        grade_slug = grade_band.replace("-", "")

        # Build the domain slug: "Speaking" → "SPK", "Reading → Speaking" → "RDG"
        domain_slug_map = {
            "Speaking":           "SPK",
            "Listening":          "LST",
            "Reading":            "RDG",
            "Writing":            "WRT",
            "Reading → Speaking": "RDG",
        }
        domain_slug = domain_slug_map.get(ela_domain, "GEN")

        prefix = f"L-{grade_slug}-{domain_slug}"

        # Find all existing files with this prefix
        existing = list(DATA_GENERATED.glob(f"{prefix}-*.json"))
        existing_numbers = []

        for filepath in existing:
            # Extract the number from e.g. "L-K2-SPK-007.json"
            stem = filepath.stem  # "L-K2-SPK-007"
            parts = stem.split("-")
            if parts[-1].isdigit():
                existing_numbers.append(int(parts[-1]))

        # Next number is max existing + 1, or 1 if none exist
        next_number = max(existing_numbers) + 1 if existing_numbers else 1
        return f"{prefix}-{next_number:03d}"

    def preview_prompt(
        self,
        grade_band : str,
        ela_domain : str,
        theme      : str,
        skill      : str = None,
    ) -> None:
        """
        Build and display the prompt without making an API call.
        Useful in notebooks for inspecting the prompt before generation.

        If no skill is provided, auto-selects the next uncovered skill
        from the taxonomy — same behaviour as generate().

        Args:
            grade_band : One of "K-2", "3-5", "6-8", "9-12"
            ela_domain : ELA domain string
            theme      : Theme string
            skill      : Optional — skill string from taxonomy.
                         If None, auto-selected from taxonomy.
        """
        if skill is None:
            skill = get_next_skill(grade_band, ela_domain)
            print(f"[preview] Auto-selected skill: {skill}\n")
        else:
            print(f"[preview] Using provided skill: {skill}\n")

        messages = build_full_prompt(grade_band, ela_domain, theme, skill)
        inspect_prompt(messages)