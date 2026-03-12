# Bantrly Lesson Generator

A research-backed, LLM-powered lesson generation system for K–12 ELA speaking practice. Built as a 2-week prototype for the Bantrly product team.

Given three inputs — a grade band, an ELA domain, and a theme — the system generates a complete, structured lesson with a narrative hook, worked example, scaffolded practice prompts, and a voice-marker feedback anchor.

---

## How it works

```
Teacher inputs: Grade Band + ELA Domain + Theme
        ↓
1. Pre-generation guardrail checks
        ↓
2. Prompt construction (system + few-shot example + user request)
        ↓
3. Groq API call  (llama-3.3-70b-versatile)
        ↓
4. Output validation (parse → field check → guardrail flags)
        ↓
5. Unique ID assignment + save to data/generated/
        ↓
6. Deduplication registry update
        ↓
Validated lesson JSON
```

---

## Research foundation

Every design decision maps to a specific body of evidence:

| Decision | Research basis |
|---|---|
| Narrative hook in every lesson | Bruner (1990) — narrative mode of cognition |
| Worked example before practice | Sweller (1994) — worked example effect |
| Single skill per lesson | Rosenshine (2012) — one clear objective |
| Scaffolded → independent prompts | Vygotsky (1978) — Zone of Proximal Development |
| Specific voice-marker feedback | Hattie & Timperley (2007) — feedback and learning |
| Grade-band vocabulary ceilings | Sweller (1988) — cognitive load by developmental stage |
| Deduplication across generations | Ebbinghaus (1885) — spaced repetition, varied practice |

---

## Project structure

```
bantrly-lesson-generator/
├── src/
│   ├── core/
│   │   ├── schema.py           ← Pydantic data models for the lesson blueprint
│   │   └── generator.py        ← Main orchestrator — ties all modules together
│   ├── guardrails/
│   │   └── checks.py           ← Pre- and post-generation validation checks
│   ├── prompts/
│   │   ├── grade_specs.py      ← Research-grounded grade band rules as data
│   │   └── templates.py        ← Prompt construction (system + few-shot + user)
│   └── utils/
│       ├── file_handler.py     ← Save/load lessons, deduplication registry
│       └── validator.py        ← LLM output parsing and auto-correction
│
├── data/
│   ├── examples/               ← 5 hand-crafted lessons used as few-shot references
│   ├── generated/              ← LLM-generated lessons saved here (gitignored)
│   └── registry/               ← Deduplication log (gitignored)
│
├── notebooks/
│   ├── 01_schema.ipynb         ← Explore the Lesson data model and Pydantic validation
│   ├── 02_file_handler.ipynb   ← Save/load lessons and watch the registry grow
│   ├── 03_checks.ipynb         ← Run guardrail checks manually, trigger each flag
│   ├── 04_grade_specs.ipynb    ← Compare grade band rules side by side
│   ├── 05_templates.ipynb      ← Inspect the full prompt before it goes to Groq
│   ├── 06_validator.ipynb      ← Feed malformed JSON, watch it get caught or fixed
│   └── 07_full_pipeline.ipynb  ← End-to-end demo: input → Groq → validated lesson
│
├── main.py                     ← CLI entry point
├── pyproject.toml              ← uv project config
├── .env.example                ← Environment variable template
└── README.md
```

---

## Setup

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — fast Python package manager
- A free [Groq API key](https://console.groq.com)

### Install

```bash
git clone https://github.com/aankitdas/bantrly-lesson-generator.git
cd bantrly-lesson-generator
uv sync
```

### Configure

```bash
cp .env.example .env
```

Open `.env` and add your Groq key:

```
GROQ_API_KEY=your_key_here
```

---

## Usage

### CLI

```bash
uv run python main.py
```

You'll be prompted for grade band, ELA domain, and theme. The generated lesson is saved to `data/generated/`.

### Python

```python
from src.core.generator import LessonGenerator

gen = LessonGenerator(verbose=True)
lesson = gen.generate(
    grade_band = "6-8",
    ela_domain = "Speaking",
    theme      = "Climate Change"
)
```

### Notebooks

Open any notebook in `notebooks/` with Jupyter. Start with `01_schema.ipynb` and work through to `07_full_pipeline.ipynb` — each one builds on the last.

```bash
uv run jupyter notebook
```

---

## Grade bands

| Band | Name | Vocab ceiling | Scaffolds | CCSS cluster |
|---|---|---|---|---|
| K-2 | Story & Say | 30 words | Always required | SL.K–2 |
| 3-5 | Explore & Explain | 60 words | First prompt only | SL.3–5 |
| 6-8 | Argue & Analyze | 100 words | Not required | SL.6–8 |
| 9-12 | Persuade & Perform | 150 words | Never used | SL.9–12 |

---

## Guardrails

### Pre-generation (raises `ValueError` — stops the API call)
- Invalid grade band
- Invalid ELA domain
- Empty or malformed theme

### Post-generation (flags in lesson JSON — never crashes)
- **Single skill check** — detects conjunctions in the skill name
- **Vocabulary ceiling check** — practice prompts within grade band word limit
- **Cognitive load check** — hook length appropriate for grade band
- **Cultural bias check** — keyword scan for culturally specific references

---

## Lesson structure

Every generated lesson follows this blueprint:

```
Hook        (60–90s)   — Narrative scene, activates curiosity
Model       (60–120s)  — Skill demonstrated and named explicitly
Practice    (90–180s)  — 1–3 prompts, scaffolded → independent
Reflect     (30–60s)   — Specific feedback on one voice marker
```

Total lesson time: 5–8 minutes.

---

## Known limitations

- **Single skill check** — `"and"` detection produces false positives when "and" appears in descriptive language rather than joining two skills
- **Cultural bias detection** — keyword-based; misses subtle bias and may produce false positives
- **One few-shot example per grade band** — a production system would retrieve the most semantically similar example using embeddings
- **No structured output mode** — Groq supports `response_format` JSON schema enforcement, which would eliminate the practice dict auto-correction entirely
- **Registry is flat JSON** — works for a prototype; a production system would use a database with semantic deduplication via embeddings

---

## Testing

Module behaviour is tested interactively via notebooks 01–06 rather than automated unit tests. Unit test stubs are present in `tests/` — a formal test suite is the first addition planned for v2.

---

## Design decisions

| Decision | Alternative considered | Why we chose this |
|---|---|---|
| Groq + Llama 3.3 70B | Claude API | Free tier; sufficient instruction-following for structured JSON |
| Hybrid rule + LLM approach | Pure LLM | Guardrails needed for grade-appropriateness; LLM alone drifts |
| Few-shot examples over RAG | Vector DB retrieval | No infrastructure needed; effective for 5 hand-crafted examples |
| Flat JSON registry | SQLite / database | Human-readable; inspectable; appropriate for prototype scope |
| ID assigned post-generation | LLM-assigned ID | LLM anchors on example IDs and reuses numbers — discovered in testing |

---

## Built with

- [Groq](https://groq.com) — LLM inference (llama-3.3-70b-versatile)
- [Pydantic v2](https://docs.pydantic.dev) — data validation
- [python-dotenv](https://pypi.org/project/python-dotenv/) — environment config
- [uv](https://docs.astral.sh/uv/) — package management