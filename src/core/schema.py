"""
src/core/schema.py
------------------
Defines the Lesson data model using Pydantic.

This is the single source of truth for what a Bantrly lesson looks like.
Every other module — the generator, the validator, the file handler —
imports and uses these models.

What will be defined here:
    - VoiceMarker         : Enum of all valid voice markers
    - GradeBand           : Enum of all valid grade bands
    - ELADomain           : Enum of all valid ELA domains
    - LessonType          : Enum of all valid lesson types
    - GuardrailStatus     : Enum — "pass" or "flag"
    - PracticePrompt      : A single speaking prompt within a lesson
    - LessonFlow          : The full Hook → Model → Practice → Reflect structure
    - LessonMetadata      : Grade, domain, skill, voice markers, CCSS anchor, etc.
    - GuardrailFlags      : Results of all guardrail checks
    - Lesson              : The complete lesson object (metadata + flow + flags)

Design note:
    Using Pydantic v2 for schema validation. This means if the LLM returns
    a lesson with a missing field or wrong type, Pydantic will catch it
    before it ever gets saved to disk.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# LAYER 1: ENUMS
# Valid values for every categorical field in a lesson.
# Using Enum means typos and invalid values are caught immediately.
# =============================================================================

class GradeBand(str, Enum):
    """
    The four grade bands, grounded in Sweller (1988) cognitive load groupings
    and CCSS ELA grade band clusters.
    """
    K2   = "K-2"
    G35  = "3-5"
    G68  = "6-8"
    G912 = "9-12"


class ELADomain(str, Enum):
    """
    The four ELA domains from the Bantrly brief.
    A lesson can also bridge two domains (e.g. Reading → Speaking).
    """
    SPEAKING  = "Speaking"
    LISTENING = "Listening"
    READING   = "Reading"
    WRITING   = "Writing"
    READING_TO_SPEAKING = "Reading → Speaking"


class LessonType(str, Enum):
    """
    The five lesson types defined in our Lesson Blueprint.
    Each type varies the narrative mode and student role.
    See blueprint Part 5 for design rationale.
    """
    STORY_RETELL  = "Story Retell"
    MISSION_BRIEF = "Mission Brief"
    DEBATE_DROP   = "Debate Drop"
    TEXT_EXPLORER = "Text Explorer"
    LISTEN_JUDGE  = "Listen & Judge"


class VoiceMarker(str, Enum):
    """
    The voice signals extracted by Bantrly's speech processing system.
    Defined in the brief. Each lesson targets 1-2 of these.
    """
    PRONUNCIATION  = "Pronunciation & Articulation"
    PROSODY        = "Prosody"
    SPEAKING_RATE  = "Speaking Rate"
    FLUENCY        = "Fluency & Fillers"
    VOLUME         = "Volume Control"
    TASK_ADHERENCE = "Task Adherence"


class GuardrailStatus(str, Enum):
    """
    The result of a guardrail check.
    'pass'  → no issues found
    'flag'  → an issue was detected; message explains what and why
    """
    PASS = "pass"
    FLAG = "flag"


class PromptType(str, Enum):
    """
    Whether a speaking prompt is scaffolded or fully independent.
    Scaffolded prompts include a sentence starter.
    Design grounding: Sweller (1994) worked example effect — scaffolds
    reduce extraneous load so students can focus on the target skill.
    """
    SUPPORTED   = "supported"
    INDEPENDENT = "independent"


# =============================================================================
# LAYER 2: SUB-MODELS
# Small building blocks that compose into the larger lesson structure.
# =============================================================================

class PracticePrompt(BaseModel):
    """
    A single speaking prompt within the Practice stage of a lesson.
    Lessons have 1-3 prompts, moving from supported → independent.
    """
    prompt_id : str        = Field(..., description="e.g. 'P1', 'P2', 'P3'")
    type      : PromptType = Field(..., description="supported or independent")
    text      : str        = Field(..., description="What the student is asked to say aloud")
    scaffold  : Optional[str] = Field(
        None,
        description="Sentence starter provided if type is 'supported'. Null if independent."
    )


class Hook(BaseModel):
    """
    Stage 1 of the lesson flow. Sets the narrative scene.
    Grounding: Gagné (1965) — gaining attention is the first event of instruction.
    """
    duration_seconds : int = Field(..., description="Approximate duration in seconds")
    content          : str = Field(..., description="The scene-setting narrative text")


class ModelStage(BaseModel):
    """
    Stage 2 of the lesson flow. Shows what the skill sounds/looks like.
    Grounding: Sweller (1994) worked example effect — reduces extraneous
    cognitive load by showing the target before asking for production.
    Named ModelStage (not Model) to avoid shadowing Pydantic's BaseModel.
    """
    duration_seconds     : int = Field(..., description="Approximate duration in seconds")
    content              : str = Field(..., description="The worked example or modeled response")
    skill_named_explicitly: str = Field(
        ...,
        description="The sentence that names the skill: 'Today we are practicing...'"
    )


class Reflect(BaseModel):
    """
    Stage 4 of the lesson flow. Closes the feedback loop.
    Grounding: Hattie & Timperley (2007) — feedback is the highest-leverage
    intervention in learning. Hamari et al. (2014) — immediate feedback is
    the most evidence-backed element of gamification.
    """
    duration_seconds : int = Field(..., description="Approximate duration in seconds")
    voice_marker_focus: VoiceMarker = Field(
        ...,
        description="Which voice marker is the focus of this lesson's feedback"
    )
    positive_signal  : str = Field(..., description="What strong performance sounds like")
    growth_signal    : str = Field(..., description="One concrete thing to try next time")


# =============================================================================
# LAYER 3: MID-MODELS
# Compose the sub-models into the three main sections of a lesson.
# =============================================================================

class LessonFlow(BaseModel):
    """
    The full 4-stage lesson structure: Hook → Model → Practice → Reflect.
    Grounding: Rosenshine (2012) Principles of Instruction + Gagné (1965)
    Nine Events of Instruction.
    """
    hook     : Hook
    model    : ModelStage
    practice : List[PracticePrompt] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="1-3 speaking prompts, moving from supported to independent"
    )
    reflect  : Reflect


class LessonMetadata(BaseModel):
    """
    All descriptive and classification fields for a lesson.
    This is what the generator uses to select, filter, and log lessons.
    """
    grade_band              : GradeBand
    ela_domain              : ELADomain
    lesson_type             : LessonType
    theme                   : str = Field(..., description="e.g. 'Space Exploration'")
    primary_skill           : str = Field(
        ...,
        description="One specific, measurable skill. Must be singular — no 'and'."
    )
    voice_markers           : List[VoiceMarker] = Field(
        ...,
        min_length=1,
        max_length=2,
        description="1-2 voice markers this lesson targets"
    )
    estimated_duration_minutes: int = Field(..., ge=4, le=10)
    ccss_anchor             : str = Field(
        ...,
        description="The CCSS standard this lesson maps to, e.g. CCSS.ELA-Literacy.SL.4.4"
    )
    design_notes            : Optional[str] = Field(
        None,
        description="Optional notes on design decisions and research grounding"
    )


class GuardrailCheck(BaseModel):
    """
    The result of a single guardrail check.
    Status is 'pass' or 'flag'. Message explains the outcome.
    """
    status  : GuardrailStatus
    message : str


class GuardrailFlags(BaseModel):
    """
    The results of all four guardrail checks, stored with the lesson.
    This makes every lesson self-documenting — you can always see
    whether it passed or was flagged, and why.
    """
    cognitive_load_check    : GuardrailCheck
    vocabulary_ceiling_check: GuardrailCheck
    cultural_bias_check     : GuardrailCheck
    single_skill_check      : GuardrailCheck


# =============================================================================
# LAYER 4: TOP MODEL
# The complete Lesson object. This is what gets saved to JSON.
# =============================================================================

class Lesson(BaseModel):
    """
    A complete Bantrly lesson.

    This is the single object that flows through the entire system:
        - The generator produces it
        - The validator checks it
        - The file handler saves it
        - The frontend displays it

    lesson_id format: L-{GRADEBAND}-{DOMAIN}-{NUMBER}
    e.g. L-K2-SPK-001, L-68-LST-007
    """
    lesson_id      : str = Field(..., description="Unique lesson identifier")
    metadata       : LessonMetadata
    lesson_flow    : LessonFlow
    guardrail_flags: GuardrailFlags

    def to_dict(self) -> dict:
        """Return the lesson as a plain Python dict (for JSON serialisation)."""
        return self.model_dump()

    def summary(self) -> str:
        """Return a one-line human-readable summary of the lesson."""
        return (
            f"[{self.lesson_id}] "
            f"{self.metadata.grade_band} | "
            f"{self.metadata.ela_domain} | "
            f"{self.metadata.lesson_type} | "
            f"Theme: {self.metadata.theme} | "
            f"Skill: {self.metadata.primary_skill}"
        )