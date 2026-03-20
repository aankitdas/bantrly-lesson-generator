# Deliverables — Bantrly Lesson Generator

Candidate Trial · Aankit Das · March 2026

This folder contains the formal deliverables for the Creative Lesson Generation challenge. Everything else referenced below lives in the main repository.

---

## 1. Slide Deck

**`deliverables/bantrly_deck.pptx`**

20-minute presentation covering: the problem, research foundation, competitor analysis, lesson blueprint, generator architecture, skill taxonomy, guardrails, key engineering stories, live demo walkthrough, known limitations, and V2 roadmap.

---

## 2. Lesson Blueprint (Design Document)

**`deliverables/bantrly_lesson_blueprint.md`**

Standalone design document defining what a Bantrly lesson contains, how its components connect to learning goals and voice markers, and the rules governing grade-band differentiation and accessibility. Written for a curriculum designer or teacher audience — no code required.

Covers:
- 4-stage lesson flow (Hook → Model → Practice → Reflect)
- 7 core components and the single-skill rule
- 5 lesson types
- Voice markers and how they connect to the Reflect stage
- Grade band guidelines with exact vocabulary ceilings, scaffold rules, and forbidden elements for all four bands (K–2, 3–5, 6–8, 9–12)
- Accessibility and cognitive load rules
- Known limitations and V2 design gaps
- Full research references

---

## 3. Generator Code

**`src/`** — full source, 8 modules across 4 packages

| Module | Responsibility |
|---|---|
| `src/core/schema.py` | Pydantic v2 data models — 15 classes, 4 layers |
| `src/core/generator.py` | Main orchestrator — 9-step generation pipeline |
| `src/core/skill_selector.py` | CCSS taxonomy loading, skill selection, coverage tracking |
| `src/guardrails/checks.py` | Pre- and post-generation validation checks |
| `src/prompts/grade_specs.py` | Grade band rules as data (vocab ceilings, scaffolds, narrative types) |
| `src/prompts/templates.py` | Prompt construction — system prompt + few-shot + user turn |
| `src/utils/file_handler.py` | Save/load lessons, skill coverage registry I/O |
| `src/utils/validator.py` | LLM output parsing and auto-correction |

**Entry points:**
- `app.py` — Gradio web UI, deployed on Hugging Face Spaces
- `main.py` — CLI entry point for local generation

**Setup:** see `README.md` at the repo root for installation instructions.

---

## 4. Notebooks

**`notebooks/`** — 8 notebooks, each isolating one system component

| Notebook | What it demonstrates |
|---|---|
| `01_schema.ipynb` | Pydantic data model — validation catching malformed data |
| `02_file_handler.ipynb` | Save/load lessons, registry growth, coverage tracking |
| `03_checks.ipynb` | Guardrails firing manually, dedup check with ela_domain |
| `04_grade_specs.ipynb` | Grade band rules compared side by side |
| `05_templates.ipynb` | Exact prompt the model receives, skill injected |
| `06_validator.ipynb` | Malformed JSON caught and auto-corrected |
| `07_full_pipeline.ipynb` | End-to-end demo: theme input → Groq → validated lesson |
| `08_skill_selector.ipynb` | Taxonomy exploration, coverage reports, cycling behaviour |

---

## 5. Example Lessons (JSON)

**`data/examples/`** — 5 hand-crafted lessons used as few-shot references during generation

These are the seed examples injected into the LLM prompt. One per grade band, varied across domains and lesson types.

| Lesson ID | Grade | Domain | Lesson Type | Theme |
|---|---|---|---|---|
| L-K2-SPK-001 | K–2 | Speaking | Story Retell | Nature & Animals |
| L-35-LST-002 | 3–5 | Listening | Listen & Judge | Community & Belonging |
| L-68-SPK-003 | 6–8 | Speaking | Debate Drop | Ethics & Dilemmas |
| L-912-RDG-SPK-004 | 9–12 | Reading → Speaking | Text Explorer | History & Change |
| L-35-SPK-005 | 3–5 | Speaking | Mission Brief | Adventure & Discovery |

**`data/generated/`** — lessons produced by the live system (gitignored from repo, available on request)

A sample of generated lessons covering the full grade and domain range is available below for reference. These were produced by the live generator running on `llama-3.1-8b-instant` via Groq.

| Lesson ID | Grade | Domain | Theme | All Guardrails Pass |
|---|---|---|---|---|
| L-K2-SPK-012 | K–2 | Speaking | Beautiful Colors | ✅ |
| L-K2-WRT-001 | K–2 | Writing | Red Balloons | ⚠️ single_skill_check false-positive |
| L-35-SPK-013 | 3–5 | Speaking | The Water Cycle | ✅ |
| L-68-SPK-003 | 6–8 | Speaking | Climate Change | ✅ |
| L-68-WRT-001 | 6–8 | Writing | Space Exploration | ⚠️ single_skill_check false-positive |
| L-912-SPK-005 | 9–12 | Speaking | Bullying Prevention | ✅ |
| L-912-WRT-002 | 9–12 | Writing | USA vs China | ⚠️ cultural_bias_check flagged |

The flagged lessons are included deliberately — they demonstrate the guardrail system working as intended. Flags are recorded and transparent; they do not block saving (except cultural bias, which retries up to 5 times).

---
## 7. Skill Taxonomy

**`data/skills/skill_taxonomy.json`**

80 CCSS-aligned skills across 4 grade bands × 4 domains × 5 skills each. Used by `skill_selector.py` to enforce progressive, non-repeating skill coverage. Editable as plain JSON without code changes.

---

## 8. Live Demo

**Hugging Face Spaces:** https://huggingface.co/spaces/aankitdas/bantrly-lesson-generator

**GitHub:** https://github.com/aankitdas/bantrly-lesson-generator

---

