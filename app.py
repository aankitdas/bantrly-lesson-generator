import gradio as gr
import json
import os
import sys
from datetime import datetime
# Ensure src/ is importable
sys.path.insert(0, os.path.dirname(__file__))

from src.core.generator import LessonGenerator
from src.core.skill_selector import get_next_skill, get_coverage_report

# Initialise generator once at startup
gen = LessonGenerator(verbose=False)

GRADE_BANDS = ["K-2", "3-5", "6-8", "9-12"]
ELA_DOMAINS = ["Speaking", "Listening", "Reading", "Writing", "Reading → Speaking"]


def preview_skill(grade_band, ela_domain):
    """Called when grade band or domain changes — shows next skill."""
    if not grade_band or not ela_domain:
        return ""
    try:
        skill = get_next_skill(grade_band, ela_domain)
        return f"**Next skill to cover:** {skill}"
    except Exception as e:
        return f"Error: {e}"


def generate_lesson(grade_band, ela_domain, theme, history):
    """Main generation function — called on button click."""
    if not theme.strip():
        return "⚠️ Please enter a theme.", "", history, history

    try:
        lesson = gen.generate(
            grade_band=grade_band,
            ela_domain=ela_domain,
            theme=theme.strip()
        )

        # Formatted lesson for Tab 1
        formatted = format_lesson(lesson)

        # Raw JSON for Tab 2
        raw = json.dumps(lesson, indent=2)

        # Update history
        m = lesson["metadata"]
        new_row = [
            lesson["lesson_id"],
            m["grade_band"],
            m["ela_domain"],
            m["primary_skill"][:50] + "...",
            m["theme"],
            datetime.utcnow().strftime("%H:%M:%S"),
        ]
        updated_history = history + [new_row]

        return formatted, raw, updated_history, updated_history

    except ValueError as e:
        return f"⚠️ Input error: {e}", "", history, history
    except RuntimeError as e:
        return f"⚠️ Generation failed: {e}", "", history, history
    except Exception as e:
        return f"⚠️ Unexpected error: {e}", "", history, history


def format_lesson(lesson):
    """Format a lesson dict into clean readable markdown."""
    m    = lesson["metadata"]
    flow = lesson["lesson_flow"]

    lines = []

    # Header
    lines.append(f"# {m['theme']}")
    lines.append(f"**{m['grade_band']} · {m['ela_domain']} · {m['lesson_type']}**")
    lines.append(f"*{m['ccss_anchor']} · ~{m['estimated_duration_minutes']} minutes*")
    lines.append("")

    # Skill
    lines.append(f"### 🎯 Skill")
    lines.append(f"{m['primary_skill']}")
    lines.append("")

    # Voice markers
    lines.append(f"### 🎙️ Voice Markers")
    lines.append(", ".join(m['voice_markers']))
    lines.append("")

    # Hook
    lines.append(f"### 🪝 Hook")
    lines.append(flow['hook']['content'])
    lines.append("")

    # Model
    lines.append(f"### 📖 Model")
    lines.append(f"*{flow['model']['skill_named_explicitly']}*")
    lines.append("")
    lines.append(flow['model']['content'])
    lines.append("")

    # Practice
    lines.append(f"### 🗣️ Practice")
    for p in flow['practice']:
        lines.append(f"**{p['prompt_id']} ({p['type']})**")
        lines.append(f"{p['text']}")
        if p.get('scaffold'):
            lines.append(f"*Scaffold: {p['scaffold']}*")
        lines.append("")

    # Reflect
    lines.append(f"### 🪞 Reflect")
    lines.append(f"**Voice marker focus:** {flow['reflect']['voice_marker_focus']}")
    lines.append(f"✅ {flow['reflect']['positive_signal']}")
    lines.append(f"📈 {flow['reflect']['growth_signal']}")
    lines.append("")

    # Lesson ID
    lines.append(f"---")
    lines.append(f"*Lesson ID: {lesson['lesson_id']}*")

    return "\n".join(lines)


# =============================================================================
# GRADIO UI
# =============================================================================

with gr.Blocks(title="Bantrly Lesson Generator") as demo:

    # In-memory session state for generation history
    history_state = gr.State([])

    gr.Markdown("""
    # 📚 Bantrly Lesson Generator
    Research-backed K–12 ELA lesson generation. Enter a grade band, domain, and theme — the system selects the next uncovered CCSS-aligned skill and generates a complete structured lesson.
    """)

    with gr.Tabs():

        # =====================================================================
        # TAB 1 — GENERATE
        # =====================================================================
        with gr.Tab("Generate"):
            with gr.Row():
                with gr.Column(scale=1):

                    gr.Markdown("### Inputs")

                    grade_band = gr.Radio(
                        choices=GRADE_BANDS,
                        value="3-5",
                        label="Grade Band",
                    )

                    ela_domain = gr.Radio(
                        choices=ELA_DOMAINS,
                        value="Speaking",
                        label="ELA Domain",
                    )

                    theme = gr.Textbox(
                        label="Theme",
                        placeholder="e.g. Space Exploration, Climate Change...",
                        lines=1,
                    )

                    skill_preview = gr.Markdown(value="")

                    generate_btn = gr.Button("Generate Lesson", variant="primary")

                with gr.Column(scale=2):
                    gr.Markdown("### Generated Lesson")
                    lesson_output = gr.Markdown(value="*Your lesson will appear here.*")

        # =====================================================================
        # TAB 2 — RAW JSON + HISTORY
        # =====================================================================
        with gr.Tab("Raw JSON & History"):

            gr.Markdown("### Last Generated Lesson — Raw JSON")
            raw_json_output = gr.Code(
                label="",
                language="json",
                lines=30,
                value="",
            )

            gr.Markdown("### Generation History (this session)")
            history_table = gr.Dataframe(
                headers=["Lesson ID", "Grade", "Domain", "Skill", "Theme", "Time"],
                datatype=["str", "str", "str", "str", "str", "str"],
                value=[],
                label="",
                interactive=False,
            )

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    grade_band.change(
        fn=preview_skill,
        inputs=[grade_band, ela_domain],
        outputs=skill_preview,
    )
    ela_domain.change(
        fn=preview_skill,
        inputs=[grade_band, ela_domain],
        outputs=skill_preview,
    )

    generate_btn.click(
        fn=generate_lesson,
        inputs=[grade_band, ela_domain, theme, history_state],
        outputs=[lesson_output, raw_json_output, history_state, history_table],
    )

    demo.load(
        fn=preview_skill,
        inputs=[grade_band, ela_domain],
        outputs=skill_preview,
    )

demo.launch()
