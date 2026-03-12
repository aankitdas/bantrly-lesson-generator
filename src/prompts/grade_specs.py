"""
src/prompts/grade_specs.py
--------------------------
Grade band specifications injected into every prompt.

Each grade band has a fixed spec that controls:
    - cognitive_load_rule   : What can and cannot be new simultaneously
    - vocab_ceiling_words   : Max words per speaking prompt
    - narrative_types       : What story contexts work for this age
    - speaking_task_length  : How long a student response should be
    - scaffold_required     : Whether sentence starters must be provided
    - example_voice_markers : Which voice markers are most relevant

What will be defined here:
    - GRADE_SPECS           : A dict mapping each grade band to its spec

Research grounding:
    All specs derived from:
    - Sweller (1988) Cognitive Load Theory
    - CCSS ELA Speaking & Listening Standards by grade band
    - Developmental reading research (Chall, 1983 — Stages of Reading Development)

Usage:
    from src.prompts.grade_specs import GRADE_SPECS
    spec = GRADE_SPECS["K-2"]
"""

# =============================================================================
# GRADE BAND SPECIFICATIONS
#
# Research grounding:
#   - Sweller (1988, 1994): Cognitive Load Theory — working memory limits
#     differ by developmental stage. Younger learners need more scaffolding
#     and less simultaneous novelty.
#   - Chall (1983): Stages of Reading Development — language complexity
#     expectations by grade band.
#   - CCSS ELA Speaking & Listening Standards (corestandards.org)
#   - Bruner (1990): Narrative types appropriate for different ages —
#     young children need concrete, character-driven stories; older
#     students can handle abstract and morally complex narratives.
# =============================================================================

GRADE_SPECS = {

    "K-2": {
        # ----------------------------------------------------------------
        # WHO THESE STUDENTS ARE
        # Ages 5-8. Early readers and speakers. Limited working memory
        # capacity. Learn best through concrete, character-driven stories.
        # Chall (1983) Stage 1-2: decoding and fluency building.
        # ----------------------------------------------------------------
        "cognitive_load_rule": (
            "Introduce only ONE new element per lesson — either a new theme "
            "OR a new skill, never both simultaneously. "
            "Sweller (1988): young learners have limited working memory "
            "and cannot process multiple novel inputs at once."
        ),
        "vocab_ceiling": 30,
        "vocab_ceiling_note": (
            "Maximum 30 words per speaking prompt. "
            "Use simple, high-frequency vocabulary only. "
            "No idioms, figurative language, or multi-clause sentences."
        ),
        "narrative_types": [
            "Animal characters with clear motivations",
            "Fantasy settings (forests, magical worlds, talking objects)",
            "Simple cause-and-effect plots (X happened, so Y happened)",
            "Familiar community settings (school, home, playground)",
        ],
        "speaking_task_length": (
            "1-2 sentences maximum. "
            "Students at this level cannot sustain longer spoken responses "
            "without losing the thread of their own thought."
        ),
        "scaffold_required": True,
        "scaffold_note": (
            "ALL practice prompts must include a sentence starter. "
            "Example: 'Start with: First, the turtle...' "
            "Scaffolds reduce extraneous cognitive load so students can "
            "focus entirely on the target skill (Sweller, 1994)."
        ),
        "primary_voice_markers": [
            "Pronunciation & Articulation",
            "Speaking Rate",
            "Volume Control",
        ],
        "ccss_descriptor": (
            "CCSS.ELA-Literacy.SL.K-2: Participate in collaborative "
            "conversations. Describe familiar people, places, things, and "
            "events with prompting and support. Speak audibly and express "
            "thoughts, feelings, and ideas clearly."
        ),
        "forbidden_elements": [
            "Abstract or philosophical themes",
            "Multi-part instructions (more than one thing at a time)",
            "Vocabulary requiring prior content knowledge",
            "Idioms or figurative language without explanation",
            "Historical or current events content",
            "Any prompt requiring more than 2 sentences to answer",
        ],
        "lesson_tone": (
            "Warm, playful, encouraging. Use character names. "
            "Frame everything as an adventure or a game. "
            "Celebrate attempt over accuracy."
        ),
    },

    "3-5": {
        # ----------------------------------------------------------------
        # WHO THESE STUDENTS ARE
        # Ages 8-11. Developing readers and speakers. Can handle moderate
        # complexity if one element is scaffolded. Beginning to reason
        # causally and make inferences.
        # Chall (1983) Stage 2-3: reading to learn begins.
        # ----------------------------------------------------------------
        "cognitive_load_rule": (
            "Theme AND skill can both be new, but the FORMAT must be "
            "scaffolded — provide sentence starters for the first prompt "
            "only. The second prompt can be independent. "
            "Sweller (1994): scaffolds can be gradually faded as "
            "learners build schema."
        ),
        "vocab_ceiling": 60,
        "vocab_ceiling_note": (
            "Maximum 60 words per speaking prompt. "
            "Grade-appropriate vocabulary is fine. Avoid unexplained "
            "technical jargon. New content-area terms should be defined "
            "inline within the hook or model stage."
        ),
        "narrative_types": [
            "Adventure and mystery plots",
            "Science discovery scenarios (expeditions, experiments)",
            "Historical fiction (accessible, character-focused)",
            "Community and social problem-solving stories",
            "Animal and nature narratives with scientific grounding",
        ],
        "speaking_task_length": (
            "2-4 sentences. Students should be able to make a point "
            "and support it with one detail or reason."
        ),
        "scaffold_required": True,
        "scaffold_note": (
            "First practice prompt must include a sentence starter. "
            "Second prompt should be independent — this gradual release "
            "mirrors Vygotsky's Zone of Proximal Development."
        ),
        "primary_voice_markers": [
            "Fluency & Fillers",
            "Speaking Rate",
            "Task Adherence",
        ],
        "ccss_descriptor": (
            "CCSS.ELA-Literacy.SL.3-5: Report on topics using appropriate "
            "facts and relevant details, speaking clearly at an "
            "understandable pace. Identify reasons and evidence a speaker "
            "provides. Create engaging audio recordings of stories or poems."
        ),
        "forbidden_elements": [
            "Highly abstract philosophical questions without concrete grounding",
            "Politically charged content without clear balanced framing",
            "Technical vocabulary without inline definitions",
            "Speaking tasks requiring more than 4 sentences",
        ],
        "lesson_tone": (
            "Curious and energetic. Frame tasks as missions, discoveries, "
            "or problems to solve. Students are capable — treat them as "
            "junior experts. Encourage specificity over length."
        ),
    },

    "6-8": {
        # ----------------------------------------------------------------
        # WHO THESE STUDENTS ARE
        # Ages 11-14. Abstract reasoning developing. Can handle moral
        # complexity, multiple perspectives, and sustained argument.
        # Identity and peer perception are highly salient — speaking
        # tasks must feel purposeful, not performative.
        # Chall (1983) Stage 3-4: reading and speaking for analysis.
        # ----------------------------------------------------------------
        "cognitive_load_rule": (
            "All three dimensions — theme, skill, and format — can be "
            "new simultaneously. However, the model stage must provide "
            "a clear worked example showing the target skill in action. "
            "Sweller (1994): worked examples reduce cognitive load even "
            "when content complexity is high."
        ),
        "vocab_ceiling": 100,
        "vocab_ceiling_note": (
            "Maximum 100 words per speaking prompt. "
            "Domain-specific vocabulary is expected and appropriate. "
            "Avoid overly casual language — students this age respond "
            "better to being treated as intellectually capable."
        ),
        "narrative_types": [
            "Ethical dilemmas and moral decision-making",
            "Current events and social issues (balanced framing required)",
            "Historical turning points and counterfactual thinking",
            "Science and technology ethics",
            "Interpersonal conflict and perspective-taking",
        ],
        "speaking_task_length": (
            "4-6 sentences. Students should make a claim, support it "
            "with at least one piece of evidence, and acknowledge "
            "complexity or a counterpoint."
        ),
        "scaffold_required": False,
        "scaffold_note": (
            "Scaffolds are optional — offer a structural framework "
            "(e.g. 'claim → reason → counterargument') but do not "
            "provide sentence starters. Students at this level benefit "
            "from constructing their own language."
        ),
        "primary_voice_markers": [
            "Prosody",
            "Task Adherence",
            "Fluency & Fillers",
        ],
        "ccss_descriptor": (
            "CCSS.ELA-Literacy.SL.6-8: Present claims and findings in a "
            "focused, coherent manner with pertinent descriptions, facts, "
            "and examples. Use appropriate eye contact, adequate volume, "
            "and clear pronunciation. Delineate a speaker's argument."
        ),
        "forbidden_elements": [
            "One-sided political content without balanced framing",
            "Topics that require lived experience students may not have",
            "Overly simplified binary choices on complex issues",
        ],
        "lesson_tone": (
            "Direct and intellectually serious. Students this age can "
            "detect condescension immediately. Frame tasks as real stakes — "
            "'you are presenting to the school board', not 'pretend you are'. "
            "Acknowledge that reasonable people disagree on hard questions."
        ),
    },

    "9-12": {
        # ----------------------------------------------------------------
        # WHO THESE STUDENTS ARE
        # Ages 14-18. Full abstract reasoning. Can handle rhetorical
        # analysis, nuanced argumentation, and audience adaptation.
        # College and career readiness is the frame.
        # Chall (1983) Stage 4-5: multiple viewpoints, construction
        # and reconstruction of knowledge.
        # ----------------------------------------------------------------
        "cognitive_load_rule": (
            "Full complexity is appropriate. Challenge should come from "
            "the intellectual depth of the content, not from confusing "
            "instructions. Keep task framing clear even when the content "
            "is sophisticated. Chunk multi-part tasks explicitly."
        ),
        "vocab_ceiling": 150,
        "vocab_ceiling_note": (
            "Maximum 150 words per speaking prompt. "
            "Academic and domain-specific vocabulary is expected. "
            "Rhetorical, analytical, and discipline-specific terms "
            "are appropriate without inline definition."
        ),
        "narrative_types": [
            "Real-world policy and civic issues",
            "Philosophical and ethical questions",
            "Literary and rhetorical analysis",
            "Professional simulations (debates, interviews, presentations)",
            "Historical primary source analysis",
            "Scientific controversy and evidence evaluation",
        ],
        "speaking_task_length": (
            "5-8 sentences or a structured short speech (1-2 minutes). "
            "Students should demonstrate claim, evidence, reasoning, "
            "counterargument acknowledgment, and audience awareness."
        ),
        "scaffold_required": False,
        "scaffold_note": (
            "No sentence starters. Structural frameworks are optional "
            "and should be offered as one possible approach, not a "
            "required template. Students should develop their own "
            "rhetorical voice."
        ),
        "primary_voice_markers": [
            "Prosody",
            "Task Adherence",
            "Fluency & Fillers",
            "Speaking Rate",
        ],
        "ccss_descriptor": (
            "CCSS.ELA-Literacy.SL.9-12: Present information clearly, "
            "concisely, and logically. Adapt speech to a variety of "
            "contexts. Evaluate a speaker's point of view and use of "
            "rhetoric. Initiate and participate in collaborative "
            "discussions building on others' ideas persuasively."
        ),
        "forbidden_elements": [
            "Overly simplified tasks that don't challenge this age group",
            "Sentence starters or heavy scaffolding (patronising at this level)",
            "Topics without any genuine intellectual complexity",
        ],
        "lesson_tone": (
            "Collegiate and intellectually demanding. Students are "
            "treated as emerging adults. Frame tasks in terms of real "
            "consequences and audiences. Reward nuance and intellectual "
            "honesty over confident-sounding oversimplification."
        ),
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_spec(grade_band: str) -> dict:
    """
    Retrieve the spec for a given grade band.

    Args:
        grade_band: One of "K-2", "3-5", "6-8", "9-12"

    Returns:
        The spec dict for that grade band.

    Raises:
        KeyError: If the grade band is not found.
    """
    if grade_band not in GRADE_SPECS:
        raise KeyError(
            f"[grade_specs] Unknown grade band '{grade_band}'. "
            f"Valid options: {list(GRADE_SPECS.keys())}"
        )
    return GRADE_SPECS[grade_band]


def get_vocab_ceiling(grade_band: str) -> int:
    """
    Convenience function — returns just the vocabulary ceiling int.
    Used by checks.py for vocabulary ceiling validation.
    """
    return get_spec(grade_band)["vocab_ceiling"]


def format_spec_for_prompt(grade_band: str) -> str:
    """
    Format the grade band spec as a clean string block
    for injection into the LLM system prompt.

    Args:
        grade_band: One of "K-2", "3-5", "6-8", "9-12"

    Returns:
        A formatted multi-line string describing all rules
        for this grade band, ready to be embedded in a prompt.
    """
    spec = get_spec(grade_band)

    forbidden = "\n".join(f"    - {item}" for item in spec["forbidden_elements"])
    narratives = "\n".join(f"    - {item}" for item in spec["narrative_types"])
    markers = ", ".join(spec["primary_voice_markers"])

    return f"""
GRADE BAND: {grade_band}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COGNITIVE LOAD RULE:
    {spec["cognitive_load_rule"]}

VOCABULARY:
    Ceiling: {spec["vocab_ceiling"]} words per speaking prompt.
    {spec["vocab_ceiling_note"]}

SPEAKING TASK LENGTH:
    {spec["speaking_task_length"]}

SCAFFOLD REQUIRED: {spec["scaffold_required"]}
    {spec["scaffold_note"]}

APPROPRIATE NARRATIVE TYPES:
{narratives}

PRIMARY VOICE MARKERS TO TARGET:
    {markers}

CCSS STANDARD:
    {spec["ccss_descriptor"]}

LESSON TONE:
    {spec["lesson_tone"]}

FORBIDDEN — DO NOT INCLUDE:
{forbidden}
""".strip()