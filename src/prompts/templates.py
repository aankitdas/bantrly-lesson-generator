"""
src/prompts/templates.py
------------------------
Constructs the full prompt sent to the Anthropic API.

A complete prompt has three parts:
    1. SYSTEM PROMPT    : Blueprint rules + output format instructions
    2. FEW-SHOT EXAMPLE : One hand-crafted lesson loaded from data/examples/
                          (this is our lightweight RAG substitute)
    3. USER PROMPT      : The specific grade band + domain + theme request

What will be defined here:
    - build_system_prompt(grade_band)   : Returns the system prompt string,
                                          injecting the correct grade spec
    - load_few_shot_example(grade_band) : Loads the most relevant example
                                          lesson from data/examples/
    - build_user_prompt(grade_band, ela_domain, theme) : Returns the user
                                          prompt string
    - build_full_prompt(...)            : Assembles all three parts into the
                                          messages list for the API call

Design note:
    The few-shot example is selected by matching grade band — K-2 requests
    get the K-2 example lesson as context, 9-12 requests get the 9-12 example.
    This reduces hallucination risk by showing the model a lesson at the
    appropriate complexity level.
"""

import json
from src.prompts.grade_specs import format_spec_for_prompt
from src.utils.file_handler import load_example_by_grade


# =============================================================================
# LESSON SCHEMA DESCRIPTION
# A plain-English description of the JSON schema we expect back.
# Injected into the system prompt so the model knows exactly what
# fields to produce and what each one means.
# =============================================================================

SCHEMA_DESCRIPTION = """
You must return a single valid JSON object with this exact structure:

{
  "lesson_id": "",
  "metadata": {
    "grade_band": "one of: K-2 | 3-5 | 6-8 | 9-12",
    "ela_domain": "one of: Speaking | Listening | Reading | Writing | Reading → Speaking",
    "lesson_type": "one of: Story Retell | Mission Brief | Debate Drop | Text Explorer | Listen & Judge",
    "theme": "the theme you were given",
    "primary_skill": "use the exact skill string you were given — do not modify it",
    "voice_markers": ["1 or 2 from: Pronunciation & Articulation | Prosody | Speaking Rate | Fluency & Fillers | Volume Control | Task Adherence"],
    "estimated_duration_minutes": integer between 4 and 10,
    "ccss_anchor": "the CCSS standard this lesson maps to",
    "design_notes": "brief note on your design decisions"
  },
  "lesson_flow": {
    "hook": {
      "duration_seconds": integer,
      "content": "the narrative scene-setting text"
    },
    "model": {
      "duration_seconds": integer,
      "content": "the worked example showing what the skill sounds like",
      "skill_named_explicitly": "Today we are practicing: ..."
    },
    "practice": [
      {
        "prompt_id": "P1",
        "type": "supported or independent",
        "text": "what the student is asked to say aloud",
        "scaffold": "sentence starter if supported, or null if independent"
      },
      {
        "prompt_id": "P2",
        "type": "independent",
        "text": "a second speaking prompt, more challenging than P1",
        "scaffold": null
      }
    ],
    "IMPORTANT — practice MUST be a JSON array [ ] not an object { }. Always use square brackets."
    "reflect": {
      "duration_seconds": integer,
      "voice_marker_focus": "one voice marker from the list above",
      "positive_signal": "what strong performance sounds like",
      "growth_signal": "one concrete thing to try next time"
    }
  },
  "guardrail_flags": {
    "cognitive_load_check":     {"status": "pass or flag", "message": "explanation"},
    "vocabulary_ceiling_check": {"status": "pass or flag", "message": "explanation"},
    "cultural_bias_check":      {"status": "pass or flag", "message": "explanation"},
    "single_skill_check":       {"status": "pass or flag", "message": "explanation"}
  }
}

CRITICAL RULES:
- Return ONLY the JSON object. No markdown, no code fences, no explanation.
- primary_skill must describe exactly ONE skill. Never use 'and', '&', or 'plus'.
- practice MUST be a JSON array using square brackets [ ]. NEVER use curly braces { } for practice.
- practice must contain 2 to 3 prompt objects inside the array.
- Every field listed above is required. Do not omit any field.
- guardrail_flags must be self-assessed honestly — flag anything that may be an issue.
""".strip()


# =============================================================================
# SYSTEM PROMPT BUILDER
# =============================================================================

def build_system_prompt(grade_band: str) -> str:
    """
    Build the system prompt for a lesson generation request.

    Combines:
    - The role definition (who the model is)
    - The lesson blueprint rules
    - The grade band specification
    - The JSON schema the model must return

    Args:
        grade_band: One of "K-2", "3-5", "6-8", "9-12"

    Returns:
        The full system prompt as a string.
    """
    grade_spec_block = format_spec_for_prompt(grade_band)

    return f"""
You are an expert K-12 ELA lesson designer for Bantrly, a voice-based
language learning platform for students. Your job is to generate a single,
complete, structured lesson in JSON format.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LESSON DESIGN PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every lesson you generate must follow these principles:

1. SINGLE SKILL: Each lesson teaches exactly ONE primary skill.
   A lesson that teaches multiple skills teaches nothing measurable.

2. NARRATIVE FIRST: Every lesson wraps its skill practice in a narrative
   frame — a character, a problem, a mission, or a scenario.
   Students need something to say before they can practice saying it well.
   (Bruner, 1990 — narrative mode of cognition)

3. FOUR-STAGE FLOW: Hook → Model → Practice → Reflect.
   - Hook: Set the scene. Activate curiosity. No skill instruction yet.
   - Model: Show what the skill sounds like. Name it explicitly.
   - Practice: Student speaks. 1-3 prompts, scaffolded → independent.
   - Reflect: Close the feedback loop. One strength. One growth area.
   (Rosenshine, 2012 — Principles of Instruction)

4. FEEDBACK CLOSES THE LOOP: The reflect stage must connect directly
   to the voice marker being evaluated. Be specific — not 'speak clearly'
   but 'pause after each sequence word so your listener can follow.'
   (Hattie & Timperley, 2007 — feedback model)

5. GRADE-APPROPRIATE COMPLEXITY: Follow the grade band rules below exactly.
   Violating cognitive load rules is the most common lesson design failure.
   (Sweller, 1988 — Cognitive Load Theory)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GRADE BAND RULES — FOLLOW THESE EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{grade_spec_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{SCHEMA_DESCRIPTION}
""".strip()


# =============================================================================
# USER PROMPT BUILDER
# =============================================================================

def build_user_prompt(grade_band: str, ela_domain: str, theme: str, skill: str) -> str:
    """
    Build the user-turn prompt for a lesson generation request.

    Args:
        grade_band: One of "K-2", "3-5", "6-8", "9-12"
        ela_domain: One of the valid ELA domains
        theme:      The lesson theme e.g. "Climate Change"
        skill:      The exact skill from the taxonomy to target

    Returns:
        The user prompt string.
    """
    return (
        f"Generate a complete Bantrly lesson with the following parameters:\n\n"
        f"  Grade Band     : {grade_band}\n"
        f"  ELA Domain     : {ela_domain}\n"
        f"  Theme          : {theme}\n"
        f"  Primary Skill  : {skill}\n\n"
        f"IMPORTANT: You must use the exact Primary Skill string above as the "
        f"'primary_skill' field in your JSON. Do not modify, rephrase, or "
        f"replace it. Build the entire lesson around this specific skill.\n\n"
        f"Follow all grade band rules and design principles exactly. "
        f"Return only the JSON object."
    )


# =============================================================================
# FULL PROMPT ASSEMBLER
# Combines system prompt + few-shot example + user prompt
# into the messages list expected by the Groq API.
# =============================================================================

def build_full_prompt(
    grade_band: str,
    ela_domain: str,
    theme:      str,
    skill:      str,
) -> list[dict]:
    """
    Assemble the complete messages list for the Groq API call.

    Structure:
        [system]    → blueprint rules + grade spec + schema
        [user]      → "here is an example lesson at this grade band"
        [assistant] → "understood, I will follow this format exactly"
        [user]      → the actual generation request

    The middle user/assistant pair is the few-shot example.
    This pattern is the most reliable way to show an LLM the exact
    output format you want, grounded at the right complexity level.

    Args:
        grade_band: One of "K-2", "3-5", "6-8", "9-12"
        ela_domain: One of the valid ELA domains
        theme:      The lesson theme
        skill:      The exact skill from the taxonomy to target

    Returns:
        A list of message dicts ready to pass to the Groq API.
    """
    # Part 1: system prompt
    system_prompt = build_system_prompt(grade_band)

    # Part 2: few-shot example — load matching grade band example
    example_lesson = load_example_by_grade(grade_band)
    example_json   = json.dumps(example_lesson, indent=2)

    few_shot_user = (
        f"Here is a complete example of a well-designed Bantrly lesson "
        f"for grade band {grade_band}. Study its structure, depth, and "
        f"how it follows all the design principles:\n\n{example_json}"
    )

    few_shot_assistant = (
        "Understood. I have studied the example lesson carefully. "
        "I will follow the same structure, depth, narrative quality, "
        "and JSON format exactly. I will respect all grade band rules "
        "and return only a valid JSON object with no additional text."
    )

    # Part 3: the actual generation request
    user_prompt = build_user_prompt(grade_band, ela_domain, theme, skill)

    return [
        {"role": "system",    "content": system_prompt},
        {"role": "user",      "content": few_shot_user},
        {"role": "assistant", "content": few_shot_assistant},
        {"role": "user",      "content": user_prompt},
    ]


# =============================================================================
# PROMPT INSPECTOR
# Utility for notebooks — prints a readable summary of a prompt
# without dumping the full few-shot example JSON.
# =============================================================================

def inspect_prompt(messages: list[dict]) -> None:
    """
    Print a human-readable summary of a messages list.
    Useful in notebooks for verifying prompt structure before API calls.

    Args:
        messages: The messages list returned by build_full_prompt()
    """
    print(f"Total messages: {len(messages)}")
    print("=" * 60)
    for i, msg in enumerate(messages):
        role    = msg["role"].upper()
        content = msg["content"]
        preview = content[:300] + "..." if len(content) > 300 else content
        print(f"\n[{i+1}] {role}")
        print("-" * 40)
        print(preview)
    print("\n" + "=" * 60)
    total_chars = sum(len(m["content"]) for m in messages)
    print(f"Total prompt length: {total_chars:,} characters (~{total_chars // 4:,} tokens)")

  