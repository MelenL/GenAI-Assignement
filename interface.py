import gradio as gr
import time
import random
import os
import logging
import traceback

# Import CSS
from css.custom_css import custom_css, js_scroll_chat

# Try to import the art module
try:
    # to run without generation, change the actual import path to something invalid like:
    # from RANDOM import generate_story_assets
    # Uncomment the line below to use the real generator
    from art.main import generate_story_assets
except ImportError:
    print("WARNING: 'art.main' not found. Using mock generator.")
    def generate_story_assets(topic, summary, hidden_story, generate_game_music=True):
        time.sleep(2) 
        return "outputs\\images\\card_20251211_115546.png", "outputs\\audio\\gemini_story_theme.wav", "Mock generation complete."
    

# Import the QA Engine (The Detective Logic)
try:
    from story.qa_engine import analyze_question_with_llm, generate_hint_with_llm
except ImportError:
    print("WARNING: could not import story.qa_engine — using mock logic.")
    def analyze_question_with_llm(q, truth, summary): return "Mock Answer: Yes"
    def generate_hint_with_llm(hist, truth, summary): return "Mock Hint: Check the ceiling."

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("debug.log", encoding="utf-8")]
)

# ==========================================
# 1. MOCK STORY DATABASE
# ==========================================
STORY_DB = {
    "Cyberpunk": {
        "summary": "A high-profile databroker was found 'flatlined' in a locked server room. The cooling system was disabled.",
        "hidden_full_story": "The broker wasn't murdered. He tried to upload his consciousness to the net, but a firewall AI trapped him halfway, overheating his brain."
    },
    "Medieval": {
        "summary": "The King's favorite jester was found dead in the moat, still wearing his bells. The water is shallow.",
        "hidden_full_story": "The King pushed him. The Jester was secretly having an affair with the Queen, and the King found a love letter in his cap."
    },
    "Modern Crime": {
        "summary": "A man lies dead in the middle of a snowy field. There are no footprints leading to or from the body.",
        "hidden_full_story": "He was a stowaway in an airplane's landing gear compartment. He froze to death and fell when the gear opened for landing."
    },
    "80s Horror": {
        "summary": "A teenager is found dead in a video rental store, tangled in VHS tape. The TV is playing static.",
        "hidden_full_story": "He wasn't killed by a person. He tried to fix a jammed VCR while it was plugged in, got shocked, and panicked, entangling himself in the tape as he fell."
    }
}

class MockStoryEngine:
    def get_story(self, topic, options=None):
        if topic in STORY_DB:
            data = STORY_DB[topic]
            return data["summary"], data["hidden_full_story"]
        else:
            return "No story found for this topic.", "N/A"

story_engine = MockStoryEngine()

# ==========================================
# 2. GRADIO APP LOGIC
# ==========================================

def init_game_ui():
    """Step 1: Layout Switch"""
    return (
        gr.update(visible=False), # Hide Setup
        gr.update(visible=True),  # Show Game
        gr.update(value=None),    # Clear Image
        gr.update(value=None),    # Clear Audio
        "Loading case files..."   # Temporary text
    )

def generate_case_data(topic, difficulty, progress=gr.Progress()):
    """Step 2: Generate Data"""
    print(f"\n--- Loading Case: {topic} ---")
    progress(0.1, desc="Consulting Archive...")
    time.sleep(0.5) 
    
    summary, hidden_story = story_engine.get_story(topic)
    
    progress(0.3, desc="Generating Visuals & Audio...")
    img_path, audio_path, logs = None, None, ""

    try:
        img_path, audio_path, logs = generate_story_assets(topic, summary, hidden_story, generate_game_music=False)
    except Exception as e:
        tb = traceback.format_exc()
        print("ERROR IN GENERATION:", tb)
        logs = f"Error: generate_story_assets crashed.\n{str(e)}"

    progress(0.8, desc="Verifying Evidence...")
    
    # Check paths
    final_img = os.path.abspath(img_path) if img_path and os.path.exists(img_path) else None
    final_audio = os.path.abspath(audio_path) if audio_path and os.path.exists(audio_path) else None

    case_display_text = f"""
    # 🕵️‍♂️ Case File: {topic}
    ### **Difficulty:** {difficulty}
    
    > {summary}
    """
    if logs and "Error" in logs:
        case_display_text += f"\n\n---\n\n⚠️ **System Alert:**\n```\n{logs}\n```"
    
    progress(1.0, desc="Investigation Ready")
    
    return (
        gr.update(value=final_img),                    # Image
        gr.update(value=final_audio, autoplay=True),   # Audio
        final_audio,                                   # Audio State
        case_display_text,                             # Text
        hidden_story,                                  # Story State
        []                                             # Chat Reset
    )

def process_question(user_input, history, hidden_story, current_summary_text):
    """
    Step 3: The Interactive QA Loop
    """
    if not user_input: 
        return "", history
    
    # Extract just the summary text if it has markdown formatting
    clean_summary = current_summary_text.replace(">", "").strip()
    
    ai_answer = analyze_question_with_llm(user_input, hidden_story, clean_summary)
    
    history = history or []
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": ai_answer})
    return "", history

def process_hint(history, hidden_story, current_summary_text):
    """
    Calls the LLM to get a hint based on history.
    """
    # Clean summary text (remove markdown blockquotes if present)
    clean_summary = current_summary_text.replace(">", "").strip() if current_summary_text else ""
    
    # Get Hint
    hint_text = generate_hint_with_llm(history, hidden_story, clean_summary)
    
    # Append to chat
    history = history or []
    # We add it as an 'assistant' message so it appears on the left
    history.append({"role": "assistant", "content": hint_text})
    
    return history

def process_question(user_input, history, hidden_story, current_summary_text):
    if not user_input: return "", history
    
    clean_summary = current_summary_text.replace(">", "").strip()
    ai_answer = analyze_question_with_llm(user_input, hidden_story, clean_summary)
    
    history = history or []
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": ai_answer})
    return "", history

def toggle_audio(current_path_state, audio_component_value):
    if audio_component_value is not None:
        return None, "🔇 Audio Off (Click to Play)"
    else:
        return current_path_state, "🔊 Audio On (Click to Mute)"


with gr.Blocks(title="Dark Stories AI") as demo:
    gr.HTML(custom_css)
    
    hidden_story_state = gr.State()
    audio_path_state = gr.State()
    current_summary_state = gr.State()

    # --- SETUP SCREEN ---
    with gr.Column(visible=True) as setup_group:
        gr.Markdown("# 🔍 AI-Driven Dynamic Detective Simulator")
        gr.Markdown("### Initialize Investigation")
        with gr.Row():
            topic_input = gr.Dropdown(["Modern Crime", "Cyberpunk", "Medieval", "80s Horror"], label="Setting", value="80s Horror")
            diff_input = gr.Dropdown(["Rookie", "Detective", "Sherlock"], label="Difficulty", value="Detective")
        start_btn = gr.Button("📂 Generate New Case", variant="primary", size="lg")

    # --- GAME SCREEN ---
    with gr.Row(visible=False, equal_height=True) as game_group:
        # Left Column
        with gr.Column(scale=1):
            case_summary = gr.Markdown("Waiting for case file...")
            with gr.Row():
                audio_btn = gr.Button("🔊 Audio On (Click to Mute)", size="sm", variant="secondary")
                case_audio = gr.Audio(visible=True, interactive=False, autoplay=True, type="filepath", elem_id="invisible_audio")
            case_image = gr.Image(label="Visual Evidence", interactive=False, type="filepath", height=500)

        with gr.Column(scale=1, elem_id="right_col"):
            gr.Markdown("### 🗣️ Interrogation Log")
            
            # FIX: Removed 'type="messages"' (Gradio infers it automatically now)
            chatbot = gr.Chatbot(label="Detective's Notes", elem_id="chatbot")
            
            with gr.Row():
                msg_input = gr.Textbox(show_label=False, placeholder="Ask a Yes/No question...", scale=7, container=False)
                # FIX: Removed 'tooltip="Get a Hint"' (Deprecated)
                hint_btn = gr.Button("💡", variant="secondary", scale=1, min_width=0)
                submit_btn = gr.Button("➤", variant="primary", scale=1, min_width=0)

    # --- EVENT LISTENERS ---
    
    # 1. Start Game
    start_btn.click(
        fn=init_game_ui,
        inputs=None,
        outputs=[setup_group, game_group, case_image, case_audio, case_summary],
        queue=False 
    ).then(
        fn=generate_case_data,
        inputs=[topic_input, diff_input],
        outputs=[case_image, case_audio, audio_path_state, case_summary, hidden_story_state, chatbot]
    )

    # 2. Audio Toggle
    audio_btn.click(toggle_audio, [audio_path_state, case_audio], [case_audio, audio_btn])

    # 3. Chat Logic    
    submit_event = submit_btn.click(
        fn=process_question, 
        inputs=[msg_input, chatbot, hidden_story_state, case_summary],
        outputs=[msg_input, chatbot]
    ).then(
        fn=None, js=js_scroll_chat
    )
    
    msg_input.submit(
        fn=process_question, 
        inputs=[msg_input, chatbot, hidden_story_state, case_summary],
        outputs=[msg_input, chatbot]
    ).then(
        fn=None, js=js_scroll_chat
    )

    # Hint Logic
    hint_btn.click(
        fn=process_hint,
        inputs=[chatbot, hidden_story_state, case_summary],
        outputs=[chatbot]
    ).then(fn=None, js=js_scroll_chat)

if __name__ == "__main__":
    output_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(output_dir, exist_ok=True) # Ensure output dir exists to prevent path errors
    demo.launch(theme=gr.themes.Monochrome(), allowed_paths=[os.getcwd(), output_dir])