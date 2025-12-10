import gradio as gr
import time
import random
import os
import logging
import traceback

from css.custom_css import custom_css, js_scroll_chat

# Try to import your actual backend
try:
    # to run without generation, change the actual import path to something invalid like:
    # from RANDOM import generate_story_assets
    # Uncomment the line below to use the real generator
    from AWD import generate_story_assets
except ImportError:
    print("WARNING: 'art.main' not found. Using mock generator.")
    def generate_story_assets(topic, summary, hidden_story):
        time.sleep(2) 
        return "C:\\Eu\\Facultate\\EIT\\1_1\\GenAI\\GenAI-Assignement\\outputs\\images\\card_20251210_154532.png", "C:\\Eu\\Facultate\\EIT\\1_1\\GenAI\\GenAI-Assignement\\outputs\\audio\\audio_20251210_154532.wav", "Mock generation complete."

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

    def analyze_question(self, question, full_story):
        q_lower = question.lower()
        story_lower = full_story.lower()
        if "murder" in q_lower:
            return "No" if "murder" not in story_lower and "killed" not in story_lower else "Yes"
        elif "suicide" in q_lower:
            return "No"
        elif "accident" in q_lower:
            return "Yes"
        else:
            return random.choice(["Yes", "No", "That is irrelevant.", "I cannot answer that.", "Focus on the evidence."])

story_engine = MockStoryEngine()

# ==========================================
# 2. GRADIO APP LOGIC
# ==========================================

def init_game_ui():
    """
    STEP 1: Pure Layout Switch.
    This runs instantly to force the browser to render the empty Image/Audio components.
    """
    return (
        gr.update(visible=False), # Hide Setup
        gr.update(visible=True),  # Show Game
        gr.update(value=None),    # Clear Image (Placeholder)
        gr.update(value=None),    # Clear Audio (Placeholder)
        "Loading case files..."   # Temporary text
    )

def generate_case_data(topic, difficulty, progress=gr.Progress()):
    """
    STEP 2: Heavy Lifting & Data Injection.
    This runs AFTER the UI is visible.
    """
    print(f"\n--- Loading Case: {topic} ---")
    progress(0.1, desc="Consulting Archive...")
    time.sleep(0.5) 
    
    # A. Get Story
    summary, hidden_story = story_engine.get_story(topic)
    
    # B. Generate Assets
    progress(0.3, desc="Generating Visuals & Audio...")
    img_path, audio_path, logs = None, None, ""

    try:
        img_path, audio_path, logs = generate_story_assets(topic, summary, hidden_story)
    except Exception as e:
        tb = traceback.format_exc()
        print("ERROR IN GENERATION:", tb)
        logs = f"Error: generate_story_assets crashed.\n{str(e)}"

    progress(0.8, desc="Verifying Evidence...")
    
    # Absolute Path Enforcement
    final_img = os.path.abspath(img_path) if img_path and os.path.exists(img_path) else None
    final_audio = os.path.abspath(audio_path) if audio_path and os.path.exists(audio_path) else None

    # C. Prepare Text
    case_display_text = f"""
    # 🕵️‍♂️ Case File: {topic}
    ### **Difficulty:** {difficulty}
    
    > {summary}
    """
    if logs and "Error" in logs:
        case_display_text += f"\n\n---\n\n⚠️ **System Alert:**\n```\n{logs}\n```"
    
    progress(1.0, desc="Investigation Ready")
    
    return (
        gr.update(value=final_img),                    # Update Image
        gr.update(value=final_audio, autoplay=True),   # Update Audio
        final_audio,                                   # Save Audio State
        case_display_text,                             # Update Text
        hidden_story,                                  # Save Story State
        []                                             # Reset Chat
    )

def process_question(user_input, history, hidden_story):
    if not user_input: return "", history
    ai_answer = story_engine.analyze_question(user_input, hidden_story)
    time.sleep(0.3) 
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
    
    # State Variables
    hidden_story_state = gr.State()
    audio_path_state = gr.State()

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
        with gr.Column(scale=1):
            case_summary = gr.Markdown("Waiting for case file...")
            with gr.Row():
                audio_btn = gr.Button("🔊 Audio On (Click to Mute)", size="sm", variant="secondary")
                case_audio = gr.Audio(visible=True, interactive=False, autoplay=True, type="filepath", elem_id="invisible_audio")
            case_image = gr.Image(label="Visual Evidence", interactive=False, type="filepath", height=500)

        with gr.Column(scale=1, elem_id="right_col"):
            gr.Markdown("### 🗣️ Interrogation Log")
            chatbot = gr.Chatbot(label="Detective's Notes", elem_id="chatbot")
            with gr.Row():
                msg_input = gr.Textbox(show_label=False, placeholder="Type your question here...", scale=9, container=False)
                submit_btn = gr.Button("➤", variant="primary", scale=1, min_width=0)

    # --- CRITICAL EVENT CHAINING ---
    
    # 1. First Click: Switch Views ONLY (Fast)
    # This forces the browser to paint the 'game_group' and the image/audio containers.
    start_btn.click(
        fn=init_game_ui,
        inputs=None,
        outputs=[
            setup_group,  # Hide Setup
            game_group,   # Show Game
            case_image,   # Reset Image
            case_audio,   # Reset Audio
            case_summary  # Reset Text
        ],
        queue=False       # Run immediately
    ).then(
        # 2. Then: Generate Data (Slow)
        # Now that the components are visible on screen, we push the data into them.
        fn=generate_case_data,
        inputs=[topic_input, diff_input],
        outputs=[
            case_image,        # Inject Image
            case_audio,        # Inject Audio
            audio_path_state,  # Save State
            case_summary,      # Update Text
            hidden_story_state,# Save Story
            chatbot            # Clear Chat
        ]
    )

    audio_btn.click(toggle_audio, [audio_path_state, case_audio], [case_audio, audio_btn])
    submit_btn.click(process_question, [msg_input, chatbot, hidden_story_state], [msg_input, chatbot], js=js_scroll_chat)
    msg_input.submit(process_question, [msg_input, chatbot, hidden_story_state], [msg_input, chatbot], js=js_scroll_chat)

if __name__ == "__main__":
    output_dir = os.path.join(os.getcwd(), "outputs")
    demo.launch(theme=gr.themes.Monochrome(), allowed_paths=[os.getcwd(), output_dir])