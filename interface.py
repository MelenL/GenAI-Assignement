import gradio as gr
import time
import random
import os

from art.main import generate_story_assets

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
    """Handles the text logic (Question/Answer) only."""
    
    def get_story(self, topic):
        data = STORY_DB.get(topic, STORY_DB["Modern Crime"])
        return data["summary"], data["hidden_full_story"]

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

def switch_to_game_view():
    """
    Step 1: Just handle the layout switch.
    This runs instantly so the DOM is ready for data.
    """
    return (
        gr.update(visible=False), # Hide Setup
        gr.update(visible=True)   # Show Game
    )

def load_case_data(topic, difficulty):
    """
    Step 2: Load the actual heavy data.
    """
    print(f"\n--- Loading Case: {topic} ---")
    
    # A. Get Story Text
    summary, hidden_story = story_engine.get_story(topic)
    
    # B. HARDCODED PATHS - to not use gemini
    # img_path, audio_path, logs = generate_story_assets(topic, summary, hidden_story)
    img_path = "./art/gemini_dark_story.png"
    audio_path = "./art/gemini_story_theme.wav"
    
    # Validate files to prevent silent failures
    if not os.path.exists(img_path):
        print(f"[Warning] Image missing: {img_path}")
        img_path = None
    if not os.path.exists(audio_path):
        print(f"[Warning] Audio missing: {audio_path}")
        audio_path = None 

    # C. Prepare UI Data
    case_display_text = f"""
    # 🕵️‍♂️ Case File: {topic}
    ### **Difficulty:** {difficulty}
    
    > {summary}
    """
    
    return (
        gr.update(value=img_path),                  # Image
        gr.update(value=audio_path, autoplay=True), # Audio
        audio_path,                                 # Audio State
        case_display_text,                          # Text
        hidden_story,                               # Hidden State
        []                                          # Chat Reset
    )

def process_question(user_input, history, hidden_story):
    if not user_input:
        return "", history

    ai_answer = story_engine.analyze_question(user_input, hidden_story)
    time.sleep(0.3) 
    
    history = history or []
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": ai_answer})
    
    return "", history

def toggle_audio(current_path_state, audio_component_value):
    """
    Toggles audio playback.
    """
    if audio_component_value is not None:
        return None, "🔇 Audio Off (Click to Play)"
    else:
        return current_path_state, "🔊 Audio On (Click to Mute)"

# ==========================================
# 3. CSS (Layout Only)
# ==========================================
js_scroll_chat = """
(args) => { 
    setTimeout(() => { 
        const c = document.getElementById('chatbot').querySelector('.scroll-hide'); 
        if(c) c.scrollTop = c.scrollHeight; 
    }, 100); 
    return args; 
}
"""

custom_css = """
<style>
/* Flex Layout for Right Column */
#right_col { display: flex !important; flex-direction: column !important; }
#chatbot { flex-grow: 1 !important; min-height: 500px !important; }

/* Hide Scrollbar */
#chatbot *::-webkit-scrollbar { display: none; }
#chatbot * { -ms-overflow-style: none; scrollbar-width: none; }

/* Invisible Audio Player (Rendered but Hidden) */
#invisible_audio {
    height: 0px !important;
    width: 0px !important;
    opacity: 0;
    overflow: hidden;
    position: absolute;
    z-index: -1;
}
</style>
"""

# ==========================================
# 4. UI LAYOUT
# ==========================================

with gr.Blocks(title="Dark Stories AI") as demo:
    gr.HTML(custom_css)
    
    # State
    hidden_story_state = gr.State()
    audio_path_state = gr.State()

    # --- SETUP SCREEN ---
    with gr.Column(visible=True) as setup_group:
        gr.Markdown("# 🔍 AI-Driven Dynamic Detective Simulator")
        gr.Markdown("### Initialize Investigation")
        
        with gr.Row():
            topic_input = gr.Dropdown(
                ["Modern Crime", "Cyberpunk", "Medieval", "80s Horror"], 
                label="Setting", value="80s Horror"
            )
            diff_input = gr.Dropdown(
                ["Rookie", "Detective", "Sherlock"], 
                label="Difficulty", value="Detective"
            )
        
        start_btn = gr.Button("📂 Generate New Case", variant="primary", size="lg")

    # --- GAME SCREEN ---
    with gr.Row(visible=False, equal_height=True) as game_group:
        
        # LEFT COLUMN
        with gr.Column(scale=1):
            case_summary = gr.Markdown("Waiting for case file...")
            
            with gr.Row():
                # Audio Controls
                audio_btn = gr.Button("🔊 Audio On (Click to Mute)", size="sm", variant="secondary")
                
                # Audio Component (Hidden via CSS)
                case_audio = gr.Audio(
                    visible=True, 
                    interactive=False, 
                    autoplay=True,
                    type="filepath",
                    elem_id="invisible_audio" 
                )

            case_image = gr.Image(
                label="Visual Evidence", interactive=False, type="filepath", height=500
            )

        # RIGHT COLUMN
        with gr.Column(scale=1, elem_id="right_col"):
            gr.Markdown("### 🗣️ Interrogation Log")
            chatbot = gr.Chatbot(label="Detective's Notes", elem_id="chatbot")
            
            with gr.Row():
                msg_input = gr.Textbox(show_label=False, placeholder="Type your question here...", scale=9, container=False)
                submit_btn = gr.Button("➤", variant="primary", scale=1, min_width=0)

    # --- EVENT LISTENERS ---
    
    # CRITICAL FIX: Chained events to solve "Double Click" issue
    # 1. Switch View (Instant) -> 2. Load Data (After view is rendered)
    start_btn.click(
        fn=switch_to_game_view,
        inputs=None,
        outputs=[setup_group, game_group]
    ).then(
        fn=load_case_data,
        inputs=[topic_input, diff_input],
        outputs=[
            case_image, 
            case_audio, 
            audio_path_state, 
            case_summary, 
            hidden_story_state, 
            chatbot
        ]
    )

    audio_btn.click(
        fn=toggle_audio,
        inputs=[audio_path_state, case_audio],
        outputs=[case_audio, audio_btn]
    )

    submit_btn.click(
        fn=process_question,
        inputs=[msg_input, chatbot, hidden_story_state],
        outputs=[msg_input, chatbot],
        js=js_scroll_chat
    )
    
    msg_input.submit(
        fn=process_question,
        inputs=[msg_input, chatbot, hidden_story_state],
        outputs=[msg_input, chatbot],
        js=js_scroll_chat
    )

if __name__ == "__main__":
    demo.launch(
        theme=gr.themes.Monochrome(), 
        allowed_paths=[os.getcwd()]
    )