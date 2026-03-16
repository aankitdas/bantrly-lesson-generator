import gradio as gr
import json
import os
import sys
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap


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

# Build coverage heatmap
DOMAINS = ["Speaking", "Listening", "Reading", "Writing"]

def build_coverage_heatmap():
    """Build a clean, styled coverage heatmap."""
    data = []
    for band in GRADE_BANDS:
        row = []
        for domain in DOMAINS:
            report = get_coverage_report(band, domain)
            pct = report["covered_count"] / report["total"] if report["total"] > 0 else 0
            row.append(pct)
        data.append(row)

    data_np = np.array(data)

    fig, ax = plt.subplots(figsize=(9, 4))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#0f1117")

    # Custom colormap — dark red → amber → green
    colors = ["#3d0000", "#8b1a1a", "#e05c00", "#f0a500", "#2ecc71"]
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("bantrly", colors, N=256)

    im = ax.imshow(data_np, cmap=cmap, vmin=0, vmax=1, aspect="auto")

    # Cell annotations
    for i in range(len(GRADE_BANDS)):
        for j in range(len(DOMAINS)):
            pct = data_np[i, j]
            label = f"{int(pct * 100)}%"
            color = "white" if pct < 0.6 else "#0f1117"
            ax.text(j, i, label, ha="center", va="center",
                    fontsize=13, fontweight="bold", color=color)

    # Axis labels
    ax.set_xticks(range(len(DOMAINS)))
    ax.set_xticklabels(DOMAINS, fontsize=11, color="white", fontweight="bold")
    ax.set_yticks(range(len(GRADE_BANDS)))
    ax.set_yticklabels(GRADE_BANDS, fontsize=11, color="white", fontweight="bold")

    # Move x labels to top
    ax.xaxis.set_label_position("top")
    ax.xaxis.tick_top()

    # Remove spines
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Grid lines between cells
    ax.set_xticks(np.arange(len(DOMAINS)) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(GRADE_BANDS)) - 0.5, minor=True)
    ax.grid(which="minor", color="#0f1117", linewidth=3)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.tick_params(which="major", bottom=False, left=False)

    # Colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.ax.yaxis.set_tick_params(color="white", labelsize=9)
    cbar.outline.set_edgecolor("#0f1117")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
    cbar.set_ticks([0, 0.25, 0.5, 0.75, 1.0])
    cbar.set_ticklabels(["0%", "25%", "50%", "75%", "100%"])

    # Title
    ax.set_title("Skills targeted by the generated lessons", fontsize=14, fontweight="bold",
                 color="white", pad=16)

    plt.tight_layout()
    return fig


def build_skill_breakdown(grade_band_sel, domain_sel):
    """Return a markdown skill breakdown for a selected band + domain."""
    report = get_coverage_report(grade_band_sel, domain_sel)

    lines = []
    lines.append(f"### {grade_band_sel} · {domain_sel}")
    lines.append(f"**{report['covered_count']}/{report['total']} skills covered**")
    lines.append("")

    lines.append("**Covered:**")
    if report["covered"]:
        for s in report["covered"]:
            lines.append(f"- ✅ {s}")
    else:
        lines.append("- *None yet*")

    lines.append("")
    lines.append("**Remaining:**")
    if report["remaining"]:
        for s in report["remaining"]:
            lines.append(f"- ⬜ {s}")
    else:
        lines.append("- 🎉 All skills covered!")

    return "\n".join(lines)

# Build guardrails
def build_guardrail_display(lesson):
    """Format guardrail flags from a lesson dict into readable markdown."""
    if not lesson:
        return "*Generate a lesson to see guardrail results.*"

    flags = lesson.get("guardrail_flags", {})

    check_labels = {
        "single_skill_check":       "Single Skill Check",
        "vocabulary_ceiling_check": "Vocabulary Ceiling Check",
        "cognitive_load_check":     "Cognitive Load Check",
        "cultural_bias_check":      "Cultural Bias Check",
    }

    lines = []
    lines.append(f"### Guardrail Results — `{lesson['lesson_id']}`")
    lines.append(f"*{lesson['metadata']['grade_band']} · {lesson['metadata']['ela_domain']} · {lesson['metadata']['theme']}*")
    lines.append("")

    for key, label in check_labels.items():
        result = flags.get(key, {})
        status  = result.get("status", "unknown")
        message = result.get("message", "No message.")
        icon    = "✅" if status == "pass" else "⚠️"
        lines.append(f"#### {icon} {label}")
        lines.append(f"**Status:** `{status.upper()}`")
        lines.append(f"{message}")
        lines.append("")

    return "\n".join(lines)

# build taxonomy browser
def build_taxonomy_browser(grade_band_sel):
    """Show full skill taxonomy for a grade band with coverage indicators."""
    lines = []
    lines.append(f"## {grade_band_sel} Skill Taxonomy")
    lines.append("")

    for domain in DOMAINS:
        report = get_coverage_report(grade_band_sel, domain)
        covered_set = set(s.lower() for s in report["covered"])

        lines.append(f"### {domain} — {report['covered_count']}/{report['total']} covered")
        lines.append("")
        for skill in report["covered"] + report["remaining"]:
            icon = "✅" if skill.lower() in covered_set else "⬜"
            lines.append(f"{icon} {skill}")
            lines.append("")
        lines.append("")

    # Also show Reading → Speaking interleaved
    from src.core.skill_selector import get_skills_for
    interleaved = get_skills_for(grade_band_sel, "Reading → Speaking")
    rds_report  = get_coverage_report(grade_band_sel, "Reading → Speaking")
    covered_set = set(s.lower() for s in rds_report["covered"])

    lines.append(f"### Reading → Speaking (interleaved) — {rds_report['covered_count']}/{rds_report['total']} covered")
    lines.append("")
    for skill in interleaved:
        icon = "✅" if skill.lower() in covered_set else "⬜"
        lines.append(f"{icon} {skill}")
        lines.append("")
    lines.append("")

    return "\n".join(lines)


def generate_lesson(grade_band, ela_domain, theme, history, lessons):
    if not theme.strip():
        return "⚠️ Please enter a theme.", "", history, history, lessons, gr.update()

    try:
        lesson = gen.generate(
            grade_band=grade_band,
            ela_domain=ela_domain,
            theme=theme.strip()
        )

        formatted = format_lesson(lesson)
        raw       = json.dumps(lesson, indent=2)

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
        updated_lessons = lessons + [lesson]

        return (
            formatted,
            raw,
            updated_history,
            updated_history,
            updated_lessons,
            build_coverage_heatmap(),
            build_guardrail_display(lesson),
            preview_skill(m["grade_band"], m["ela_domain"]),
            build_taxonomy_browser(m["grade_band"]),
            build_skill_breakdown(m["grade_band"], m["ela_domain"]),
        )

    except ValueError as e:
        return f"⚠️ Input error: {e}", "", history, history, lessons, gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
    except RuntimeError as e:
        return f"⚠️ Generation failed: {e}", "", history, history, lessons, gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
    except Exception as e:
        return f"⚠️ Unexpected error: {e}", "", history, history, lessons, gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
    if not theme.strip():
        return "⚠️ Please enter a theme.", "", history, history, lessons, gr.update(), gr.update(), gr.update(), gr.update(), gr.update()

def select_lesson_json(evt: gr.SelectData, lessons):
    """Called when a row is clicked in the history table."""
    if not lessons or evt.index[0] >= len(lessons):
        return ""
    selected_lesson = lessons[evt.index[0]]
    return json.dumps(selected_lesson, indent=2)


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
    if flow['hook'].get('learning_goal_connection'):
        lines.append(f"*🔗 {flow['hook']['learning_goal_connection']}*")
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
        if p.get('learning_goal_connection'):
            lines.append(f"*🔗 {p['learning_goal_connection']}*")
        lines.append("")

    # Reflect
    lines.append(f"### 🪞 Reflect")
    reflect = flow.get('reflect', {})
    lines.append(f"**Voice marker focus:** {reflect.get('voice_marker_focus', 'N/A')}")
    lines.append(f"✅ {reflect.get('positive_signal', 'N/A')}")
    lines.append(f"📈 {reflect.get('growth_signal', 'N/A')}")
    if reflect.get('learning_goal_connection'):
        lines.append(f"*🔗 {reflect['learning_goal_connection']}*")
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
    lessons_state = gr.State([])

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

        # =====================================================================
        # TAB 3 — COVERAGE HEATMAP
        # =====================================================================
        with gr.Tab("Coverage Report"):

            gr.Markdown("### Skill Focus Heatmap")
            gr.Markdown("*Updates automatically after each generation. Green = fully covered, red = not started.*")

            heatmap_plot = gr.Plot(label="")

            gr.Markdown("### Skill Breakdown")
            gr.Markdown("Select a grade band and domain to see covered and remaining skills.")

            with gr.Row():
                breakdown_grade  = gr.Radio(
                    choices=GRADE_BANDS,
                    value="3-5",
                    label="Grade Band",
                )
                breakdown_domain = gr.Radio(
                    choices=DOMAINS,
                    value="Speaking",
                    label="ELA Domain",
                )

            skill_breakdown_output = gr.Markdown(value="")
        
        # =====================================================================
        # TAB 4 — GUARDRAIL INSPECTOR
        # =====================================================================
        with gr.Tab("Guardrail Inspector"):
            gr.Markdown("""
            ### Guardrail Inspector
            Shows the 4 post-generation checks run on every lesson.
            - ✅ **Pass** — no issues detected
            - ⚠️ **Flag** — issue detected, recorded in lesson JSON but never blocks generation

            *Updates automatically after each generation.*
            """)
            guardrail_output = gr.Markdown(
                value="*Generate a lesson to see guardrail results.*"
            )
        # =====================================================================
        # TAB 5 — SKILL TAXONOMY BROWSER
        # =====================================================================
        with gr.Tab("Skill Taxonomy"):

            gr.Markdown("""
            ### Skill Taxonomy Browser
            CCSS-aligned skills per grade band and domain.
            ✅ = covered this session · ⬜ = not yet covered
            
            *Select a grade band to explore its full skill set.*
            """)

            taxonomy_grade = gr.Radio(
                choices=GRADE_BANDS,
                value="3-5",
                label="Grade Band",
            )

            taxonomy_output = gr.Markdown(value="")
        
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
            inputs=[grade_band, ela_domain, theme, history_state, lessons_state],
            outputs=[
            lesson_output,
            raw_json_output,
            history_state,
            history_table,
            lessons_state,
            heatmap_plot,
            guardrail_output,
            skill_preview,
            taxonomy_output,
            skill_breakdown_output,
        ],
        )

        theme.submit(
        fn=generate_lesson,
        inputs=[grade_band, ela_domain, theme, history_state, lessons_state],
        outputs=[
            lesson_output,
            raw_json_output,
            history_state,
            history_table,
            lessons_state,
            heatmap_plot,
            guardrail_output,
            skill_preview,
            taxonomy_output,
            skill_breakdown_output,
        ],
    )

        breakdown_grade.change(
            fn=build_skill_breakdown,
            inputs=[breakdown_grade, breakdown_domain],
            outputs=skill_breakdown_output,
        )
        breakdown_domain.change(
            fn=build_skill_breakdown,
            inputs=[breakdown_grade, breakdown_domain],
            outputs=skill_breakdown_output,
        )

        history_table.select(
            fn=select_lesson_json,
            inputs=[lessons_state],
            outputs=raw_json_output,
        )

        taxonomy_grade.change(
            fn=build_taxonomy_browser,
            inputs=[taxonomy_grade],
            outputs=taxonomy_output,
        )

        demo.load(
            fn=build_coverage_heatmap,
            outputs=heatmap_plot,
        )
        demo.load(
            fn=build_skill_breakdown,
            inputs=[breakdown_grade, breakdown_domain],
            outputs=skill_breakdown_output,
        )
        demo.load(
            fn=lambda: "*Generate a lesson to see guardrail results.*",
            outputs=guardrail_output,
        )
        demo.load(
            fn=build_taxonomy_browser,
            inputs=[taxonomy_grade],
            outputs=taxonomy_output,
        )

demo.launch()
