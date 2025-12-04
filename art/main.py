import os
import time
from .utils.gemini_gen import setup_gemini, generate_multimedia_concepts, generate_image_gemini
from .utils.local_music_gen import generate_game_music

def generate_story_assets(theme: str, story_summary: str, story_full: str):
    """
    Orchestrator function suitable for Gradio.
    Returns: (image_path, audio_path, log_message)
    """
    
    # 1. Setup API
    if not setup_gemini():
        return None, None, " Error: Google API Key missing. Check .env file."

    # 2. Get Concepts (Text/JSON Phase)
    print("\n[1/3] Fetching Concepts from Creative Director...")
    try:
        concepts = generate_multimedia_concepts(theme, story_summary, story_full)

        if not concepts:
            return None, None, " Error: Failed to generate concepts from Gemini."
            
        print(f"   > Image Prompt: {concepts['image_prompt'][:40]}...")
        print(f"   > Music Prompt: {concepts['music_prompt'][:40]}...")
        
    except Exception as e:
        return None, None, f" Error during concept generation: {str(e)}"

    # Define output paths
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    image_path = f"output_card_{timestamp}.png"
    audio_path = f"output_audio_{timestamp}.wav"
    
    status_log = ["Concepts Generated successfully."]

    # 3. Generate Image
    print("\n[2/3] Generating Image...")
    image_success = False
    try:
        image_success = generate_image_gemini(concepts["image_prompt"], "gemini_dark_story.png")
        if image_success:
            status_log.append(" Image generated.")
        else:
            status_log.append(" Image generation failed (API error).")
            image_path = None # Return None to UI if failed
    except Exception as e:
        status_log.append(f" Image generation crashed: {str(e)}")
        image_path = None

    # 4. Generate Audio
    print("\n[3/3] Generating Audio (Local GPU)...")
    try:
        # MusicGen is heavy. We wrap it tightly to prevent crashing the whole app if VRAM is full.
        generate_game_music(
            base_prompt=concepts['music_prompt'],
            style_options=None, # Gemini provided full context in base_prompt
            duration=45,
            output_filename=audio_path,
            model_size="small" # Keep small for speed, change to 'medium' for quality
        )
        
        # Verify file actually exists
        if os.path.exists(audio_path):
            status_log.append(" Audio generated.")
        else:
            status_log.append(" Audio file not found after generation.")
            audio_path = None
            
    except Exception as e:
        status_log.append(f" Music generation crashed: {str(e)}")
        audio_path = None

    # 5. Return results
    final_status = "\n".join(status_log)
    return image_path, audio_path, final_status

# --- Test Block (Simulates how Gradio will call it) ---
if __name__ == "__main__":
    
    # Test Data
    test_theme = "80s Sci-Fi Horror"
    test_summary = "A crew member is found frozen outside the airlock. He has a smile on his face."
    test_full = "The ship's AI hallucinated that the vacuum of space was a paradise and tricked him into opening the door."

    # Call the main function
    img, audio, log = generate_story_assets(test_theme, test_summary, test_full)
    
    print("\n--- Final Result ---")
    print(f"Log: {log}")
    print(f"Image Path: {img}")
    print(f"Audio Path: {audio}")