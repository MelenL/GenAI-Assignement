import gradio as gr
import time
import os
import logging
import traceback

# Import CSS
from css.custom_css import custom_css, js_scroll_chat

# Story source (his)
try:
    from story.story_engine import get_story
except ImportError:
    print("WARNING: could not import story.story_engine — using mock logic.")
    def get_story(topic, difficulty, use_rag=True):
        return "Mock Summary", "Mock Hidden Story"

# Art / asset generation
try:
    from art.main import generate_story_assets
except ImportError:
    print("WARNING: 'art.main' not found. Using mock generator.")
    def generate_story_assets(topic, summary, hidden_story, generate_game_music=True):
        time.sleep(1)
        return "outputs/images/card_20251211_115546.png", "outputs/audio/gemini_story_theme.wav", "Mock generation complete."

# QA engine
try:
    from story.qa_engine import analyze_question_with_llm, generate_hint_with_llm
except ImportError:
    print("WARNING: could not import story.qa_engine — using mock logic.")
    def analyze_question_with_llm(q, truth, summary): return "Mock Answer: Yes"
    def generate_hint_with_llm(hist, truth, summary): return "Mock Hint: Check the ceiling."

# Hypothesis verification (his)
try:
    from story.hypothesis_verification import verify_hypothesis
except ImportError:
    print("WARNING: could not import story.hypothesis_verification — using mock logic.")
    def verify_hypothesis(truth, hypothesis): return "Mock Analysis: Your hypothesis is interesting!"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("debug.log", encoding="utf-8")]
)

# ==========================================
# GRADIO APP LOGIC
# ==========================================

def init_game_ui():
    """Hide setup, show game, reset components."""
    return (
        gr.update(visible=False),   # setup_group
        gr.update(visible=True),    # game_group
        gr.update(value=None),      # case_image
        gr.update(value=None),      # case_audio
        "",                         # case_summary (no 'Loading case files...' text)
        gr.update(value="", visible=False),  # answer_box hidden + cleared
        gr.update(value="AUDIO ON · CLICK TO MUTE", variant="primary"),  # audio_btn reset
        False                       # audio_on_state reset (we'll set to True after assets load)
    )

def generate_case_data(topic, difficulty, progress=gr.Progress()):
    """Generate story + assets and update UI."""
    print(f"\n--- Loading Case: {topic} ({difficulty}) ---")
    progress(0.1, desc="Consulting Archive...")
    time.sleep(0.2)
    

    # before: get_story(topic, difficulty, use_rag=True)
    summary, hidden_story = get_story(topic, difficulty, use_rag=True)
    # remove the generic LLM intro line (keep the actual story)
    summary = summary.replace("Okay, here's a dark story fitting your specifications:", "").strip()


    progress(0.35, desc="Generating Visuals & Audio...")
    img_path, audio_path, logs = None, None, ""
    try:
        img_path, audio_path, logs = generate_story_assets(
            topic, summary, hidden_story, generate_game_music=False
        )
    except Exception as e:
        tb = traceback.format_exc()
        print("ERROR IN GENERATION:", tb)
        logs = f"Error: generate_story_assets crashed.\n{str(e)}"

    progress(0.8, desc="Verifying Evidence...")

    # Use existence checks (safe), but keep original path state so toggle can turn back on
    final_img = os.path.abspath(img_path) if img_path and os.path.exists(img_path) else img_path
    final_audio = os.path.abspath(audio_path) if audio_path and os.path.exists(audio_path) else audio_path

    case_display_text = f"""
#### CASE FILE

# {topic.upper()}

**DIFFICULTY: {difficulty.upper()}**

{summary}
"""

    if logs and "Error" in logs:
        case_display_text += f"\n\n---\n\n⚠️ **System Alert:**\n```\n{logs}\n```"

    progress(1.0, desc="Investigation Ready")

    # Return:
    # image, audio component, audio_path_state, summary, hidden_story_state, chatbot reset, answer_box reset, audio_on_state
    return (
        gr.update(value=final_img),                    # case_image
        gr.update(value=final_audio, autoplay=True),   # case_audio
        final_audio,                                   # audio_path_state
        case_display_text,                             # case_summary
        hidden_story,                                  # hidden_story_state
        [],                                            # chatbot reset
        gr.update(value="", visible=False),            # answer_box hidden
        gr.update(value="AUDIO ON · CLICK TO MUTE", variant="primary"),  # audio_btn
        True                                           # audio_on_state
    )

def process_question(user_input, history, hidden_story, current_summary_text):
    """Yes/No Q&A loop."""
    if not user_input:
        return "", history

    clean_summary = (current_summary_text or "").replace(">", "").strip()
    ai_answer = analyze_question_with_llm(user_input, hidden_story, clean_summary)

    history = history or []
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": ai_answer})
    return "", history

def process_hint(history, hidden_story, current_summary_text):
    clean_summary = (current_summary_text or "").replace(">", "").strip()
    hint_text = generate_hint_with_llm(history, hidden_story, clean_summary)

    history = history or []
    history.append({"role": "assistant", "content": hint_text})
    return history

def reveal_answer(hidden_story):
    return gr.update(value=f"### 🕵️‍♂️ THE TRUTH:\n{hidden_story}", visible=True)

def process_hypothesis(hypothesis_text, hidden_story, history):
    if not hypothesis_text or not hypothesis_text.strip():
        return "", history, gr.update()

    analysis = verify_hypothesis(hidden_story, hypothesis_text)

    history = history or []
    history.append({"role": "user", "content": f"🎯 **My Theory:** {hypothesis_text}"})
    history.append({"role": "assistant", "content": analysis})

    # show answer box after verification (optional)
    return "", history, gr.update(visible=True)

def toggle_audio(current_path_state, is_on):
    """
    Your reliable toggle: uses explicit boolean state.
    Also switches button variant for CSS color:
    - primary  -> ON (red)
    - secondary -> OFF (grey)
    """
    if is_on:
        return (
            gr.update(value=None, autoplay=False),
            gr.update(value="AUDIO OFF · CLICK TO PLAY", variant="secondary"),
            False
        )

    if current_path_state:
        return (
            gr.update(value=current_path_state, autoplay=True),
            gr.update(value="AUDIO ON · CLICK TO MUTE", variant="primary"),
            True
        )

    return (
        gr.update(value=None, autoplay=False),
        gr.update(value="AUDIO OFF · CLICK TO PLAY", variant="secondary"),
        False
    )

# ==========================================
# UI
# ==========================================

with gr.Blocks(title="Dark Stories AI") as demo:
    gr.HTML(custom_css)

    hidden_story_state = gr.State()
    audio_path_state = gr.State()
    audio_on_state = gr.State(False)

    # SETUP (new top bar style)
    with gr.Column(visible=True, elem_id="top_bar") as setup_group:
        gr.Markdown("## AI DETECTIVE SIMULATOR")
        gr.Markdown("#### Initialize Investigation")

        with gr.Row():
            topic_input = gr.Dropdown(
                ["Modern Crime", "Cyberpunk", "Medieval", "80s Horror"],
                label="Setting",
                value="80s Horror",
                scale=1
            )
            diff_input = gr.Dropdown(
                ["Rookie", "Detective", "Sherlock"],
                label="Difficulty",
                value="Detective",
                scale=1
            )

        start_btn = gr.Button("LOAD CASE FILE", variant="primary", size="lg")

    # GAME SCREEN (new card layout, plus before reveal/theory features)
    with gr.Row(visible=False, equal_height=True) as game_group:

        # LEFT PANEL
        with gr.Column(scale=3, elem_classes=["case-panel"]):
            case_summary = gr.Markdown("Waiting for case file...", elem_id="case_header")

            with gr.Row():
                reveal_btn = gr.Button("REVEAL", variant="secondary", size="sm")

            answer_box = gr.Markdown(value="", visible=False)

            audio_btn = gr.Button(
                "AUDIO ON · CLICK TO MUTE",
                size="sm",
                variant="primary",
                elem_id="audio_btn"
            )

            case_audio = gr.Audio(
                visible=True,
                interactive=False,
                autoplay=True,
                type="filepath",
                elem_id="invisible_audio"
            )

            case_image = gr.Image(
                label=None,
                show_label=False,
                interactive=False,
                type="filepath",
                height=450,
                elem_id="evidence_image"
            )

        # RIGHT PANEL
        with gr.Column(scale=2, elem_classes=["log-panel"], elem_id="right_col"):
            gr.Markdown("### INTERROGATION LOG", elem_id="log_title")

            chatbot = gr.Chatbot(label="", show_label=False, elem_id="chatbot")

            with gr.Row(elem_id="question_row"):
                msg_input = gr.Textbox(
                    show_label=False,
                    placeholder="Ask a yes/no question about the case…",
                    scale=7,
                    container=False,
                    elem_id="question_box"
                )
                hint_btn = gr.Button("HINT", variant="secondary", scale=1, min_width=0, elem_id="hint_btn")
                submit_btn = gr.Button("ASK", variant="primary", scale=1, min_width=0, elem_id="ask_btn")

            gr.Markdown("### SUBMIT YOUR THEORY")
            gr.Markdown("*Think you've solved it? Describe what happened:*")

            with gr.Row():
                hypothesis_input = gr.Textbox(
                    show_label=False,
                    placeholder="Explain your complete theory…",
                    scale=7,
                    container=False,
                    lines=2
                )
                hypothesis_btn = gr.Button("VERIFY", variant="primary", scale=1, min_width=80)

    # ==========================================
    # EVENTS
    # ==========================================

    start_btn.click(
        fn=init_game_ui,
        inputs=None,
        outputs=[setup_group, game_group, case_image, case_audio, case_summary, answer_box],
        queue=False
    ).then(
        fn=generate_case_data,
        inputs=[topic_input, diff_input],
        outputs=[case_image, case_audio, audio_path_state, case_summary, hidden_story_state, chatbot],
        queue=False,                 # <- IMPORTANT: removes "waiting for..."
    )



    audio_btn.click(
        fn=toggle_audio,
        inputs=[audio_path_state, audio_on_state],
        outputs=[case_audio, audio_btn, audio_on_state]
    )

    submit_btn.click(
        fn=process_question,
        inputs=[msg_input, chatbot, hidden_story_state, case_summary],
        outputs=[msg_input, chatbot]
    ).then(fn=None, js=js_scroll_chat)

    msg_input.submit(
        fn=process_question,
        inputs=[msg_input, chatbot, hidden_story_state, case_summary],
        outputs=[msg_input, chatbot]
    ).then(fn=None, js=js_scroll_chat)

    hint_btn.click(
        fn=process_hint,
        inputs=[chatbot, hidden_story_state, case_summary],
        outputs=[chatbot]
    ).then(fn=None, js=js_scroll_chat)

    reveal_btn.click(
        fn=reveal_answer,
        inputs=[hidden_story_state],
        outputs=[answer_box]
    )

    hypothesis_btn.click(
        fn=process_hypothesis,
        inputs=[hypothesis_input, hidden_story_state, chatbot],
        outputs=[hypothesis_input, chatbot, answer_box]
    ).then(fn=None, js=js_scroll_chat)

    hypothesis_input.submit(
        fn=process_hypothesis,
        inputs=[hypothesis_input, hidden_story_state, chatbot],
        outputs=[hypothesis_input, chatbot, answer_box]
    ).then(fn=None, js=js_scroll_chat)

if __name__ == "__main__":
    output_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    demo.launch(
        theme=gr.themes.Soft(primary_hue="red", neutral_hue="slate"),
        allowed_paths=[os.getcwd(), output_dir]
    )
