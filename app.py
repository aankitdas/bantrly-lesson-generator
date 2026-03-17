import gradio as gr
import json
import os
import sys
from datetime import datetime, timezone
import plotly.graph_objects as go


# Ensure src/ is importable
sys.path.insert(0, os.path.dirname(__file__))

from src.core.generator import LessonGenerator
from src.core.skill_selector import get_next_skill, get_coverage_report

# Initialise generator once at startup
gen = LessonGenerator(verbose=False)

GRADE_BANDS = ["K-2", "3-5", "6-8", "9-12"]
ELA_DOMAINS = ["Speaking", "Listening", "Reading", "Writing", "Reading → Speaking"]

GROQ_MODELS = {
    "llama-3.3-70b-versatile": "70B Versatile (recommended)",
    "llama-3.1-8b-instant":    "8B Instant (faster, lower quality)",
}

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
    """Build a clean modern coverage heatmap using Plotly."""
    data       = []
    text       = []
    hover_text = []

    for band in GRADE_BANDS:
        row       = []
        text_row  = []
        hover_row = []
        for domain in DOMAINS:
            report = get_coverage_report(band, domain)
            pct    = report["covered_count"] / report["total"] if report["total"] > 0 else 0
            row.append(pct)
            text_row.append(f"{int(pct * 100)}%")
            hover_row.append(
                f"<b>{band} — {domain}</b><br>"
                f"Covered: {report['covered_count']}/{report['total']}<br>"
                f"Coverage: {int(pct * 100)}%"
            )
        data.append(row)
        text.append(text_row)
        hover_text.append(hover_row)

    fig = go.Figure(data=go.Heatmap(
        z=data,
        x=DOMAINS,
        y=GRADE_BANDS,
        text=text,
        texttemplate="%{text}",
        textfont={"size": 14, "color": "white"},
        hovertext=hover_text,
        hoverinfo="text",
        colorscale=[
            [0.0,  "#c0392b"],   # 0%   — red
            [0.25, "#e67e22"],   # 25%  — orange
            [0.5,  "#f1c40f"],   # 50%  — yellow
            [0.75, "#2ecc71"],   # 75%  — light green
            [1.0,  "#27ae60"],   # 100% — full green
        ],
        zmin=0,
        zmax=1,
        showscale=True,
        xgap=4,
        ygap=4,
        colorbar=dict(
            title=dict(text="Coverage", font=dict(color="#e0e0e0", size=12)),
            tickvals=[0, 0.25, 0.5, 0.75, 1.0],
            ticktext=["0%", "25%", "50%", "75%", "100%"],
            tickfont=dict(color="#e0e0e0", size=11),
            outlinecolor="#333",
            outlinewidth=1,
            bgcolor="#1a1a2e",
        ),
    ))

    fig.update_layout(
        paper_bgcolor="#0f1117",
        plot_bgcolor="#0f1117",
        font=dict(color="#e0e0e0", size=12),
        margin=dict(l=60, r=60, t=40, b=40),
        height=280,
        xaxis=dict(
            side="top",
            tickfont=dict(size=12, color="#e0e0e0"),
            tickangle=0,
            showgrid=False,
            showline=False,
        ),
        yaxis=dict(
            tickfont=dict(size=12, color="#e0e0e0"),
            showgrid=False,
            showline=False,
            autorange="reversed",
        ),
    )

    return fig


def build_skill_breakdown(grade_band_sel, domain_sel):
    """Return a markdown skill breakdown for a selected band + domain."""

    if not grade_band_sel or not domain_sel:
        return "*Select a grade band and domain above.*"
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
    """Show full skill taxonomy as a responsive CSS grid."""
    if not grade_band_sel:
        return "<p style='color:#888; padding:8px;'>Select a grade band above.</p>"
    from src.core.skill_selector import get_skills_for

    domains_to_show = DOMAINS + ["Reading → Speaking"]
    cards = []

    for domain in domains_to_show:
        if domain == "Reading → Speaking":
            all_skills = get_skills_for(grade_band_sel, "Reading → Speaking")
            report     = get_coverage_report(grade_band_sel, "Reading → Speaking")
        else:
            report     = get_coverage_report(grade_band_sel, domain)
            all_skills = report["covered"] + report["remaining"]

        covered_set   = set(s.lower() for s in report["covered"])
        covered_count = report["covered_count"]
        total         = report["total"]
        pct           = int((covered_count / total) * 100) if total > 0 else 0

        # Progress bar color
        if pct == 0:
            bar_color = "#e05c00"
        elif pct == 100:
            bar_color = "#2ecc71"
        else:
            bar_color = "#f0a500"

        # Skill rows
        skill_rows = ""
        for i, skill in enumerate(all_skills, 1):
            icon   = "✅" if skill.lower() in covered_set else "⬜"
            skill_rows += f"""
            <div style="
                display: flex;
                align-items: flex-start;
                gap: 8px;
                padding: 6px 0;
                border-bottom: 1px solid #2a2a2a;
                font-size: 13px;
                line-height: 1.4;
            ">
                <span style="min-width: 20px; color: #888;">{i}.</span>
                <span style="flex: 1; color: #e0e0e0;">{skill}</span>
                <span>{icon}</span>
            </div>
            """

        card = f"""
        <div style="
            background: #1a1a2e;
            border: 1px solid #2a2a3e;
            border-radius: 12px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        ">
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
            ">
                <span style="
                    font-size: 14px;
                    font-weight: 700;
                    color: #a78bfa;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                ">{domain}</span>
                <span style="
                    font-size: 12px;
                    color: #888;
                ">{covered_count}/{total}</span>
            </div>

            <div style="
                background: #2a2a3e;
                border-radius: 999px;
                height: 6px;
                overflow: hidden;
            ">
                <div style="
                    width: {pct}%;
                    height: 100%;
                    background: {bar_color};
                    border-radius: 999px;
                    transition: width 0.3s ease;
                "></div>
            </div>

            <div>{skill_rows}</div>
        </div>
        """
        cards.append(card)

    cards_html = "\n".join(cards)

    html = f"""
    <div style="padding: 8px 0;">
        <h2 style="
            color: #e0e0e0;
            font-size: 18px;
            margin-bottom: 16px;
        ">{grade_band_sel} — Skill Taxonomy</h2>

        <div style="
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        ">
            {cards_html}
        </div>
    </div>
    """

    return html


def generate_lesson(grade_band, ela_domain, theme, model_choice, history, lessons):
    # Resolve display label back to model string
    model_key = next(
        (k for k, v in GROQ_MODELS.items() if v == model_choice),
        "llama-3.3-70b-versatile"
    )
    if not theme.strip():
        return "⚠️ Please enter a theme.", "", history, history, lessons, gr.update()

    try:
        lesson = gen.generate(
            grade_band=grade_band,
            ela_domain=ela_domain,
            theme=theme.strip(),
            model=model_key
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
            datetime.now(timezone.utc).strftime("%H:%M:%S"),
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
            gr.update(visible=True), # launch button
            lesson, # demo lesson state
            gr.update(value=m["grade_band"]),    # sync breakdown_grade
            gr.update(value=m["ela_domain"] if m["ela_domain"] in DOMAINS else "Speaking"),  # sync breakdown_domain
            gr.update(value=m["grade_band"]), # sync taxonomy_grade
        )

    except ValueError as e:
        return f"⚠️ Input error: {e}", "", history, history, lessons, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(visible=False), None, gr.update(), gr.update(), gr.update()
    except RuntimeError as e:
        return f"⚠️ Generation failed: {e}", "", history, history, lessons, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(visible=False), None, gr.update(), gr.update(), gr.update()
    except Exception as e:
        return f"⚠️ Unexpected error: {e}", "", history, history, lessons, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(visible=False), None, gr.update(), gr.update(), gr.update()
    if not theme.strip():
        return "⚠️ Please enter a theme.", "", history, history, lessons, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(visible=False), None, gr.update(), gr.update(), gr.update()

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
    if m.get('voice_markers') and (m['ela_domain'] == "Speaking" or m['ela_domain'] == "Reading → Speaking"):
        lines.append(f"### 🎙️ Voice Markers")
        lines.append(", ".join(m['voice_markers']))
        lines.append("")

    # Hook
    lines.append(f"### 🪝 Hook")
    lines.append(flow['hook']['content'])
    lines.append("")
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
        lines.append("")
        if p.get('learning_goal_connection'):
            lines.append(f"*🔗 {p['learning_goal_connection']}*")
        lines.append("")

    # Reflect
    lines.append(f"### 🪞 Reflect")
    reflect = flow.get('reflect', {})
    # Handle both flat and nested feedback_anchors structure
    if 'feedback_anchors' in reflect:
        reflect_data = reflect['feedback_anchors']
    else:
        reflect_data = reflect
    lines.append(f"**Voice marker focus:** {reflect.get('voice_marker_focus', 'N/A')}")
    lines.append(f"✅ {reflect_data.get('positive_signal', 'N/A')}")
    lines.append("")
    lines.append(f"📈 {reflect_data.get('growth_signal', 'N/A')}")
    lines.append("")
    if reflect_data.get('learning_goal_connection'):
        lines.append(f"🔗 *{reflect_data['learning_goal_connection']}*")
    lines.append("")
    # Lesson ID
    lines.append(f"---")
    lines.append(f"*Lesson ID: {lesson['lesson_id']}*")

    return "\n".join(lines)


# =============================================================================
# GRADIO UI
# =============================================================================

# Demo App State
STEP_NAMES = ["Hook", "Skill", "Model", "Practice", "Reflect"]

def get_grade_style(grade_band):
    """Return tone config based on grade band."""
    styles = {
        "K-2": {
            "ready":    "I'm Ready! 🚀",
            "got_it":   "Got it! ⭐",
            "my_turn":  "My Turn! 🎤",
            "next":     "Next ➡️",
            "done":     "Yay! 🎉 All Done!",
            "restart":  "Try Another Lesson 🔄",
            "emoji":    True,
        },
        "3-5": {
            "ready":    "Let's Go! 🚀",
            "got_it":   "Got it!",
            "my_turn":  "My Turn!",
            "next":     "Next →",
            "done":     "Nice Work! ✅",
            "restart":  "Try Another Lesson",
            "emoji":    True,
        },
        "6-8": {
            "ready":    "Ready",
            "got_it":   "Understood",
            "my_turn":  "My Response",
            "next":     "Next",
            "done":     "Done ✅",
            "restart":  "Try Another Lesson",
            "emoji":    False,
        },
        "9-12": {
            "ready":    "Continue",
            "got_it":   "Noted",
            "my_turn":  "Respond",
            "next":     "Next",
            "done":     "Complete",
            "restart":  "Try Another Lesson",
            "emoji":    False,
        },
    }
    return styles.get(grade_band, styles["6-8"])


def build_progress_bar(current_step):
    steps = STEP_NAMES
    parts = []
    for i, name in enumerate(steps):
        if i < current_step:
            parts.append(f"~~{name}~~")
        elif i == current_step:
            parts.append(f"**[ {name} ]**")
        else:
            parts.append(f"{name}")
    bar    = " → ".join(parts)
    total  = len(steps)
    # Cap at 1.0 so step 5 shows 100% without division issues
    ratio  = min(current_step / (total - 1), 1.0)
    filled = int(ratio * 20)
    visual = "█" * filled + "░" * (20 - filled)
    return f"{bar}\n\n**{visual}** {int(ratio * 100)}%"


def render_demo_step(lesson, step, practice_index=0):
    """
    Render the current demo step as markdown.
    Returns (content_md, button_label, show_next, show_restart)
    """
    if lesson is None:
        return "*No lesson loaded.*", "Start", False, False

    flow  = lesson["lesson_flow"]
    meta  = lesson["metadata"]
    grade = meta["grade_band"]
    style = get_grade_style(grade)

    # Step 0 — Hook
    if step == 0:
        content = f"## 🪝 {meta['theme']}\n\n"
        content += f"{flow['hook']['content']}"
        return content, style["ready"], True, False, False

    # Step 1 — Skill
    elif step == 1:
        skill = meta["primary_skill"]
        content = f"## 🎯 Today's Skill\n\n"
        if grade in ("K-2", "3-5"):
            content += f"**We're going to practice:**\n\n> {skill}"
        else:
            content += f"**Learning objective:**\n\n> {skill}"
        return content, style["got_it"], True, False, False

    # Step 2 — Model
    elif step == 2:
        model  = flow["model"]
        content = f"## 📖 Watch & Listen\n\n"
        content += f"*{model['skill_named_explicitly']}*\n\n"
        content += f"{model['content']}"
        return content, style["my_turn"], True, False, False

    # Step 3 — Practice
    elif step == 3:
        practice = flow["practice"]
        if practice_index >= len(practice):
            return render_demo_step(lesson, 4, 0)

        p       = practice[practice_index]
        total_p = len(practice)
        content = f"## 🗣️ Your Turn ({practice_index + 1}/{total_p})\n\n"
        content += f"{p['text']}\n\n"
        if p.get("scaffold"):
            content += f"> 💡 *{p['scaffold']}*\n\n"

        is_last_prompt = practice_index >= total_p - 1
        btn_label = style["next"] if not is_last_prompt else style["my_turn"]
        show_finish = is_last_prompt
        return content, btn_label, True, False, show_finish

    # Step 4 — Reflect
    elif step == 4:
        reflect = flow.get("reflect", {})
        if "feedback_anchors" in reflect:
            reflect = reflect["feedback_anchors"]

        content = f"## 🪞 Reflect\n\n"
        vmf = reflect.get("voice_marker_focus", "")
        if vmf:
            content += f"**Voice focus:** {vmf}\n\n"
        content += f"✅ {reflect.get('positive_signal', '')}\n\n"
        content += f"📈 {reflect.get('growth_signal', '')}\n\n"
        if reflect.get("learning_goal_connection"):
            content += f"*🔗 {reflect['learning_goal_connection']}*"

        return content, style["done"], False, False, True

    return "*Unknown step.*", "Next", False, False, False


def launch_demo(lesson):
    """Called when Launch Student Experience button is clicked."""
    if lesson is None:
        return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), 0, None, 0

    content, btn_label, show_next, show_restart, show_finish = render_demo_step(lesson, 0)
    progress = build_progress_bar(0)

    return (
        gr.update(selected=4),   # switch to Demo App tab (index 4)
        progress,
        content,
        gr.update(value=btn_label, visible=show_next),
        gr.update(visible=show_restart),
        gr.update(visible=show_finish),
        0,                       # demo_step_state
        lesson,                  # demo_lesson_state
        0,                       # practice_index_state
    )


def demo_next(lesson, step, practice_index):
    """Advance to the next step or practice prompt."""
    if lesson is None:
        return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), step, practice_index

    practice = lesson["lesson_flow"]["practice"]

    # If on practice step and more prompts remain — advance practice index
    if step == 3 and practice_index < len(practice) - 1:
        new_practice_index = practice_index + 1
        content, btn_label, show_next, show_restart, show_finish = render_demo_step(
            lesson, 3, new_practice_index
        )
        progress = build_progress_bar(3)
        return (
            progress,
            content,
            gr.update(value=btn_label, visible=show_next),
            gr.update(visible=show_restart),
            gr.update(visible=show_finish),
            3,
            new_practice_index,
        )

    # Otherwise advance to next main step
    new_step = step + 1
    new_practice_index = 0
    content, btn_label, show_next, show_restart, show_finish = render_demo_step(
        lesson, new_step, new_practice_index
    )
    progress = build_progress_bar(new_step)
    return (
        progress,
        content,
        gr.update(value=btn_label, visible=show_next),
        gr.update(visible=show_restart),
        gr.update(visible=show_finish),
        new_step,
        new_practice_index,
    )


def demo_restart():
    """Reset demo and switch back to Generate tab."""
    return (
        gr.update(selected=0),  # switch back to Generate tab
        "",                     # clear lesson output
        gr.update(visible=False),  # hide launch button
    )

def demo_finish(lesson):
    """Show congratulations and skill summary."""
    if lesson is None:
        return gr.update(), gr.update(), gr.update(), gr.update()

    meta  = lesson["metadata"]
    grade = meta["grade_band"]
    style = get_grade_style(grade)

    if grade == "K-2":
        congrats = "# 🌟 Amazing Work!\n\nYou did it! Great job today!"
    elif grade == "3-5":
        congrats = "# 🎉 Well Done!\n\nFantastic effort today!"
    elif grade == "6-8":
        congrats = "# ✅ Lesson Complete!\n\nGreat work today."
    else:
        congrats = "# Lesson Complete\n\nWell done."

    content  = congrats + "\n\n---\n\n"
    content += f"## 📋 What You Practiced\n\n"
    content += f"**Skill:** {meta['primary_skill']}\n\n"

    if meta.get("voice_markers"):
        content += f"**Voice focus:** {', '.join(meta['voice_markers'])}\n\n"

    content += f"**Lesson:** {meta['theme']} · {meta['grade_band']} · {meta['ela_domain']}\n\n"
    content += f"*{meta.get('ccss_anchor', '')}*\n\n"
    content += "---\n\n"

    if grade in ("K-2", "3-5"):
        content += "⭐ Keep practicing — you're getting better every time!"
    elif grade in ("6-8",):
        content += "Keep practicing this skill — consistency builds fluency."
    else:
        content += "Continued practice will strengthen both skill and delivery."

    progress = build_progress_bar(5)

    return (
        progress,
        content,
        gr.update(visible=False),   # hide next btn
        gr.update(visible=False),   # hide finish btn
        gr.update(visible=True),    # show restart btn
    )

with gr.Blocks(title="Bantrly Lesson Generator") as demo:

    # In-memory session state for generation history
    history_state = gr.State([])
    lessons_state = gr.State([])

    active_tab_state  = gr.State(0)
    demo_lesson_state = gr.State(None)
    demo_step_state   = gr.State(0)
    practice_index_state = gr.State(0)

    gr.Markdown("""
    # 📚 Bantrly Lesson Generator
    Research-backed K–12 ELA lesson generation. Enter a grade band, domain, and theme. The system selects the next uncovered CCSS-aligned skill and generates a complete structured lesson.
    """)

    with gr.Tabs() as tabs:

        # =====================================================================
        # TAB 1 — GENERATE
        # =====================================================================
        with gr.Tab("Generate", id=0):
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
                    model_choice = gr.Radio(
                        choices=list(GROQ_MODELS.values()),
                        value="70B Versatile (recommended)",
                        label="Model",
                    )

                    theme = gr.Textbox(
                        label="Theme",
                        placeholder="e.g. Space Exploration, Climate Change...",
                        lines=1,
                    )

                    skill_preview = gr.Markdown(value="")

                    generate_btn = gr.Button("Generate Lesson", variant="primary")
                    stop_btn     = gr.Button("Stop", variant="stop")

                with gr.Column(scale=2):
                    gr.Markdown("### Generated Lesson")
                    lesson_output = gr.Markdown(value="*Your lesson will appear here.*")
                    launch_btn = gr.Button(
                        "▶ Launch Student Experience",
                        variant="primary",
                        visible=False,
                    )

        # =====================================================================
        # TAB 2 — RAW JSON + HISTORY
        # =====================================================================
        with gr.Tab("Raw JSON & History", id=1):

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
        with gr.Tab("Coverage Report", id=2):

            gr.Markdown("### Skill Focus Heatmap")
            gr.Markdown("*Updates automatically after each generation. Green = fully covered, red = not started.*")

            with gr.Column(scale=1):
                heatmap_plot = gr.Plot(label="", show_label=False)

            gr.Markdown("### Skill Breakdown")
            gr.Markdown("Select a grade band and domain to see covered and remaining skills.")

            with gr.Row():
                breakdown_grade  = gr.Radio(
                    choices=GRADE_BANDS,
                    value=None,
                    label="Grade Band",
                )
                breakdown_domain = gr.Radio(
                    choices=DOMAINS,
                    value=None,
                    label="ELA Domain",
                )

            skill_breakdown_output = gr.Markdown(value="")
        
        # =====================================================================
        # TAB 4 — GUARDRAIL INSPECTOR
        # =====================================================================
        with gr.Tab("Guardrail Inspector", id=3):
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
        # TAB 5 — DEMO APP (Student Experience)
        # =====================================================================
        with gr.Tab("▶ Student Experience", id=4):

            gr.Markdown("### Student Lesson Experience")
            gr.Markdown("*Navigate through the lesson step by step.*")

            demo_progress   = gr.Markdown(value="")
            demo_content    = gr.Markdown(value="*Generate a lesson first, then click Launch Student Experience.*")

            with gr.Row():
                demo_next_btn    = gr.Button("Next", variant="primary", visible=False)
                demo_restart_btn = gr.Button("Try Another Lesson", variant="secondary", visible=False)
                demo_finish_btn  = gr.Button("🎓 Finish Lesson", variant="primary", visible=False)
        # =====================================================================
        # TAB 6 — SKILL TAXONOMY BROWSER
        # =====================================================================
        with gr.Tab("Skill Taxonomy", id=5):

            gr.Markdown("""
            ### Skill Taxonomy Browser
            CCSS-aligned skills per grade band and domain.
            ✅ = covered this session · ⬜ = not yet covered
            
            *Select a grade band to explore its full skill set.*
            """)

            taxonomy_grade = gr.Radio(
                choices=GRADE_BANDS,
                value=None,
                label="Grade Band",
            )

            taxonomy_output = gr.HTML(value="")
        
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

    gen_event = generate_btn.click(
        fn=generate_lesson,
        inputs=[grade_band, ela_domain, theme, model_choice, history_state, lessons_state],
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
        launch_btn,
        demo_lesson_state,
        breakdown_grade,     # sync to generated lesson
        breakdown_domain,    # sync to generated lesson
        taxonomy_grade,      # sync to generated lesson
    ],
    )

    submit_event = theme.submit(
        fn=generate_lesson,
        inputs=[grade_band, ela_domain, theme, model_choice, history_state, lessons_state],
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
        launch_btn,
        demo_lesson_state,
        breakdown_grade,     # sync to generated lesson
        breakdown_domain,    # sync to generated lesson
        taxonomy_grade,      # sync to generated lesson
    ],
    )
    stop_btn.click(
        fn=None,
        cancels=[gen_event, submit_event],
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
        fn=lambda: "*Generate a lesson to see guardrail results.*",
        outputs=guardrail_output,
    )
    
    demo.load(
        fn=preview_skill,
        inputs=[grade_band, ela_domain],
        outputs=skill_preview,
    )

    launch_btn.click(
    fn=launch_demo,
    inputs=[demo_lesson_state],
    outputs=[
        tabs,
        demo_progress,
        demo_content,
        demo_next_btn,
        demo_restart_btn,
        demo_finish_btn,
        demo_step_state,
        demo_lesson_state,
        practice_index_state,
    ],
    )

    demo_next_btn.click(
        fn=demo_next,
        inputs=[demo_lesson_state, demo_step_state, practice_index_state],
        outputs=[
            demo_progress,
            demo_content,
            demo_next_btn,
            demo_restart_btn,
            demo_finish_btn,
            demo_step_state,
            practice_index_state,
        ],
    )
    demo_finish_btn.click(
        fn=demo_finish,
        inputs=[demo_lesson_state],
        outputs=[
            demo_progress,
            demo_content,
            demo_next_btn,
            demo_finish_btn,
            demo_restart_btn,
        ],
    )

    demo_restart_btn.click(
        fn=demo_restart,
        outputs=[
            tabs,
            lesson_output,
            launch_btn,
        ],
    )
    
demo.launch()
