# Bantrly Lesson Blueprint
### Design Document — Creative Lesson Generation System

---

## 1. What This Document Is

This document defines what a Bantrly lesson is, what it must contain, how its parts connect to learning goals, and what rules govern how lessons are adapted across grade bands. It is the design specification behind the lesson generator — the decisions here shaped every line of the system's code.

Audience: curriculum designers, product leads, engineers building on top of the system.

---

## 2. The Core Design Principle

A Bantrly lesson must do two things simultaneously: be genuinely engaging and teach a measurable skill. These goals are in tension. Engagement without structure produces activity without learning. Structure without engagement produces compliance without retention.

The blueprint resolves this tension through **narrative scaffolding** — every lesson is framed as a story, scenario, or mission, but the narrative exists to carry a single, specific, CCSS-aligned skill. The theme is the delivery mechanism. The skill is the destination.

This is grounded in Bruner (1990): narrative is not decoration — it is a distinct cognitive mode that improves encoding and recall. And in Rosenshine (2012): one clear objective per lesson is the single most consistent predictor of instructional effectiveness.

---

## 3. The 4-Stage Lesson Flow

Every Bantrly lesson follows a fixed four-stage structure. The stages are not interchangeable. Their sequence is deliberate.

```
Hook (60–90s) → Model (60–120s) → Practice (90–180s) → Reflect (30–60s)
Total: 5–8 minutes
```

### Stage 1 — Hook
Sets the narrative scene. Introduces the theme, character, or scenario. Does not yet introduce the skill. The student's job here is to become curious.

*Research grounding:* Gagné (1965) identifies gaining attention as the first event of instruction. Bruner (1990) suggests that narrative structures naturally engage attention and support meaning-making.

### Stage 2 — Model
Names the skill explicitly and shows what it sounds like in practice. This is a worked example — the student sees the target before being asked to produce it.

*Research grounding:* Sweller (1994) worked example effect — showing a complete, correct response before asking for production reduces extraneous cognitive load. Students can focus entirely on the target skill because the format is already demonstrated.

The Model stage must include the sentence: *"Today we are practising [skill]."* This is not optional — skill naming is required for students to self-monitor their own performance.

### Stage 3 — Practice
The student speaks. 1–3 prompts, moving from supported (scaffolded) to independent. This is the only stage where voice markers are actively measured.

*Research grounding:* Vygotsky (1978) Zone of Proximal Development — the progression from scaffolded to independent practice mirrors the gradual release of responsibility. The scaffold is faded, not removed abruptly.

### Stage 4 — Reflect
Closes the feedback loop. Targets one voice marker specifically. Names what strong performance sounds like (positive signal) and names one concrete thing to improve (growth signal).

*Research grounding:* Hattie & Timperley (2007) show that feedback is highly effective when it is specific, targeted, and actionable, particularly when it focuses on task and process rather than general praise.

---

## 4. The 7 Core Components

Every lesson is defined by exactly 7 components. These are the fields the generator must produce and the fields the system validates.

| # | Component | What it is |
|---|---|---|
| 1 | **Grade Band** | K–2 / 3–5 / 6–8 / 9–12 — determines all constraints |
| 2 | **ELA Domain** | Speaking / Listening / Reading / Writing / Reading → Speaking |
| 3 | **Primary Skill** | One measurable, CCSS-aligned skill — no compound skills |
| 4 | **Narrative Frame** | The theme, character, or scenario carrying the lesson |
| 5 | **Lesson Flow** | The full Hook → Model → Practice → Reflect structure |
| 6 | **Speaking Prompt** | What the student says aloud during Practice |
| 7 | **Feedback Anchor** | 1–2 voice markers evaluated during and after Practice |

The **single-skill rule** is enforced as a guardrail. A lesson with two skills ("practising sequencing and using evidence") is not a lesson — it is two lessons. Compound objectives are caught and flagged before saving.

---

## 5. The 5 Lesson Types

Lesson type determines the narrative mode and the student's role within it. Same skill, different lesson type — different engagement profile.

| Lesson Type | Narrative Mode | Student Role |
|---|---|---|
| **Story Retell** | Character-driven narrative | Retells what happened in sequence |
| **Mission Brief** | Problem or discovery scenario | Explains a plan or finding |
| **Debate Drop** | Two-sided issue or dilemma | Takes and defends a position |
| **Text Explorer** | Short text or passage as stimulus | Responds to what they read |
| **Listen & Judge** | Audio or spoken input as stimulus | Evaluates and responds to what they heard |

Lesson type is assigned by the generator based on domain and grade band. Debate Drop, for instance, is appropriate for 6–8 and 9–12 but not K–2. Story Retell is the primary type for K–2 and 3–5.

---

## 6. Voice Markers and How They Connect to Learning Goals

Bantrly's speech processing system extracts six signals from student audio. These are not abstract metrics — each maps directly to a teachable, practicable speaking behaviour.

| Voice Marker | What it measures | How it appears in lessons |
|---|---|---|
| **Pronunciation & Articulation** | Clarity of speech sounds, consonant and vowel precision | Reflect stage: named as the feedback target for K–2 lessons |
| **Prosody** | Rhythm, stress, intonation, melodic variation | Reflect stage: primary marker for 6–12 analytical and persuasive tasks |
| **Speaking Rate** | Speech tempo, pause placement, timing control | Practice stage: students coached on pacing; primary marker for K–2 and 3–5 |
| **Fluency & Fillers** | Speech flow, hesitation markers, self-repairs | Reflect stage: primary marker for 3–5 and 6–8 |
| **Volume Control** | Loudness consistency, dynamic range, projection | Primary marker for K–2; less prominent in upper grades |
| **Task Adherence** | Follows topic, format, and required structure | Primary marker for 3–5, 6–8, and 9–12 |

Each lesson targets **1–2 voice markers maximum**. The Reflect stage names one marker as the feedback focus. This constraint is deliberate — feedback on multiple simultaneous dimensions diffuses attention and reduces retention (Hattie & Timperley, 2007).

### The Learning Goal Connection

For Speaking and Reading → Speaking lessons, each component of the lesson flow carries a **learning goal connection** — a single sentence explaining how that component connects to the primary skill and targeted voice marker. This appears on the Hook, each Practice prompt, and the Reflect stage.

This is a prompt-level convention, not a formal schema field. The generator instructs the LLM to produce it for Speaking-domain lessons; the validator removes it from non-Speaking lessons. The display layer renders it when present.

Its purpose is pedagogical transparency — a teacher reviewing a generated lesson should be able to trace the line from narrative frame to skill to voice marker without reading the code.

In v2, this should be formalised as `Optional[str] = None` on the `Hook`, `PracticePrompt`, and `Reflect` Pydantic models.

---

## 7. Grade Band Guidelines

Grade band is the primary constraint that governs everything else in a lesson. The same skill taught to a K–2 student and a 9–12 student requires entirely different vocabulary, narrative type, scaffolding, and tone.

All rules below are derived from Sweller (1988, 1994) cognitive load theory, Chall (1983) Stages of Reading Development, and the CCSS ELA Speaking & Listening standards by grade cluster.

---

### K–2 — "Story & Say"
*Ages 5–8. Early readers and speakers. Concrete, character-driven learning.*

- **Vocabulary ceiling:** 30 words per speaking prompt
- **Response length:** 1–2 sentences maximum
- **Scaffolds:** Required on all practice prompts — sentence starters must be provided
- **Cognitive load rule:** Introduce only ONE new element per lesson — either a new theme or a new skill, never both simultaneously
- **Appropriate narratives:** Animal characters, fantasy settings, familiar community contexts (school, home, playground), simple cause-and-effect plots
- **Primary voice markers:** Pronunciation & Articulation, Speaking Rate, Volume Control
- **Tone:** Warm, playful, encouraging. Frame everything as an adventure. Celebrate attempt over accuracy.
- **CCSS anchor:** SL.K–2 — Participate in collaborative conversations; speak audibly and express thoughts clearly with prompting and support

**Do not include:** abstract or philosophical themes, multi-part instructions, idioms or figurative language, historical or current events, any prompt requiring more than 2 sentences

---

### 3–5 — "Explore & Explain"
*Ages 8–11. Developing readers and speakers. Beginning causal reasoning.*

- **Vocabulary ceiling:** 60 words per speaking prompt
- **Response length:** 2–4 sentences; one point supported by one detail or reason
- **Scaffolds:** Required on first prompt only; second prompt is independent (gradual release)
- **Cognitive load rule:** Theme and skill can both be new, but format must be scaffolded on the first prompt
- **Appropriate narratives:** Adventure and mystery, science discovery, accessible historical fiction, community problem-solving
- **Primary voice markers:** Fluency & Fillers, Speaking Rate, Task Adherence
- **Tone:** Curious and energetic. Frame tasks as missions or problems to solve. Treat students as junior experts.
- **CCSS anchor:** SL.3–5 — Report on topics using appropriate facts; speak clearly at an understandable pace

**Do not include:** unexplained technical jargon, politically charged content, speaking tasks requiring more than 4 sentences

---

### 6–8 — "Argue & Analyze"
*Ages 11–14. Abstract reasoning developing. Peer perception is highly salient.*

- **Vocabulary ceiling:** 100 words per speaking prompt
- **Response length:** 4–6 sentences; claim, evidence, and acknowledgment of complexity or counterpoint
- **Scaffolds:** Not required; structural frameworks offered but sentence starters are not provided
- **Cognitive load rule:** All three dimensions (theme, skill, format) can be new — but the Model stage must provide a clear worked example
- **Appropriate narratives:** Ethical dilemmas, current events (balanced framing required), historical turning points, science and technology ethics, interpersonal conflict
- **Primary voice markers:** Prosody, Task Adherence, Fluency & Fillers
- **Tone:** Direct and intellectually serious. Frame tasks as real stakes. Acknowledge that reasonable people disagree on hard questions.
- **CCSS anchor:** SL.6–8 — Present claims and findings coherently; use appropriate volume and pronunciation; delineate a speaker's argument

**Do not include:** one-sided political content, overly simplified binary choices on complex issues

---

### 9–12 — "Persuade & Perform"
*Ages 14–18. Full abstract reasoning. College and career readiness frame.*

- **Vocabulary ceiling:** 150 words per speaking prompt
- **Response length:** 5–8 sentences or a structured short speech (1–2 minutes); claim, evidence, reasoning, counterargument, audience awareness
- **Scaffolds:** None — no sentence starters; structural frameworks optional and non-prescriptive
- **Cognitive load rule:** Full complexity is appropriate; challenge comes from intellectual depth, not confusing instructions
- **Appropriate narratives:** Real-world policy and civic issues, philosophical and ethical questions, literary and rhetorical analysis, professional simulations, primary source analysis
- **Primary voice markers:** Prosody, Task Adherence, Fluency & Fillers, Speaking Rate
- **Tone:** Collegiate and intellectually demanding. Students are treated as emerging adults. Reward nuance over confident-sounding oversimplification.
- **CCSS anchor:** SL.9–12 — Present information clearly and logically; adapt speech to context; evaluate a speaker's rhetoric

**Do not include:** sentence starters or heavy scaffolding (patronising at this level), tasks without genuine intellectual complexity

---

## 8. Accessibility and Cognitive Load Guidelines

These rules apply across all grade bands and are not negotiable.

**One skill per lesson.** Compound objectives are not permitted. If a lesson appears to target two skills, it must be split into two lessons or one skill must be designated primary and the other removed.

**Vocabulary is a cognitive load lever, not just a readability metric.** The ceilings above (30 / 60 / 100 / 150 words) exist because exceeding them forces students to split attention between decoding the prompt and producing a response. Both suffer.

**Scaffolds are faded, not removed.** The K–2 to 3–5 transition does not abruptly remove all support. The gradual release pattern — full scaffold → first-prompt scaffold → no scaffold — mirrors developmental progression.

**Cultural bias is a guardrail, not a style preference.** Lessons referencing specific national holidays, religion-specific content, Western-centric narratives, or US-specific cultural references are flagged and regenerated. A lesson that is inaccessible to a student because of its cultural assumptions has failed its primary purpose. The generator retries up to 5 times on a bias flag; if all attempts fail, the lesson is not saved.

**Cognitive load rule specificity by band.** The constraint tightens with age, not loosens. K–2 students get one new element per lesson. 9–12 students can handle full complexity — but the task framing must remain clear. Complexity in content is appropriate; complexity in instructions is always a design failure.

---

## 9. Known Limitations and V2 Design Gaps

This blueprint reflects the current prototype. The following gaps are known and should inform v2 design decisions.

| Gap | Current state | V2 fix |
|---|---|---|
| `learning_goal_connection` not in schema | Prompt-level convention, validator strips for non-Speaking | Add as `Optional[str]` to Hook, PracticePrompt, Reflect in schema.py |
| Voice marker validation not post-generation | Pydantic catches it only if Lesson object is constructed; generator saves raw dicts | Add a guardrail check that validates voice_markers against the VoiceMarker enum |
| Cultural bias detection is keyword-based | Catches explicit terms; misses subtle cultural assumptions | Semantic similarity check or LLM-as-judge pass |
| Skill cycling is deterministic | Cycles through taxonomy by index when all skills covered | Replace with student performance data — cycle toward weak skills |
| No voice analysis in prototype | Lessons show prompts only; no speech recording or analysis | Connect to Bantrly's voice processing pipeline |

---

## 10. Research References

Bruner, J. S. (1990). *Acts of Meaning.* Harvard University Press.

Chall, J. S. (1983). *Stages of Reading Development.* McGraw-Hill.

Gagné, R. M. (1965). *The Conditions of Learning.* Holt, Rinehart & Winston.

Hamari, J., Koivisto, J., & Sarsa, H. (2014). Does gamification work? *HICSS.* https://doi.org/10.1109/HICSS.2014.377

Hattie, J. & Timperley, H. (2007). The power of feedback. *Review of Educational Research, 77*(1), 81–112. https://doi.org/10.3102/003465430298487

Rosenshine, B. (2012). Principles of instruction. *American Educator, Spring 2012.* https://www.aft.org/sites/default/files/periodicals/Rosenshine.pdf

Sweller, J. (1988). Cognitive load during problem solving. *Cognitive Science, 12*(2), 257–285. https://doi.org/10.1207/s15516709cog1202_4

Sweller, J. (1994). Cognitive load theory, learning difficulty, and instructional design. *Learning and Instruction, 4*(4), 295–312. https://doi.org/10.1016/0959-4752(94)90003-5

Vygotsky, L. S. (1978). *Mind in Society.* Harvard University Press.