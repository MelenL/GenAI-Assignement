import os
import time
import logging
import random
from PIL import Image
logging.basicConfig(level=logging.INFO)
from .utils.gemini_gen import setup_gemini, generate_multimedia_concepts, generate_image_gemini

def generate_story_assets(theme: str, story_summary: str, story_full: str, generate_game_music=True):
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
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")
    IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
    AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    image_fname = f"card_{timestamp}.png"
    audio_fname = f"audio_{timestamp}.wav"

    image_path = os.path.join(IMAGES_DIR, image_fname)
    audio_path = os.path.join(AUDIO_DIR, audio_fname)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    status_log = ["Concepts Generated successfully."]

    # 3. Generate Image
    print("\n[2/3] Generating Image...")
    image_success = False
    def _retry_generate_image(prompt, out_path, attempts=3, base_delay=2.0):
        """Retry wrapper with exponential backoff + jitter for flaky 503 / deadline errors."""
        for attempt in range(1, attempts + 1):
            try:
                logging.info("Image generation attempt %d/%d", attempt, attempts)
                res = generate_image_gemini(prompt, out_path)
                return res
            except Exception as ex:
                err = str(ex)
                logging.warning("Image generation failed (attempt %d): %s", attempt, err)
                # If last attempt, re-raise to be handled below
                if attempt == attempts:
                    raise
                # backoff with jitter
                sleep_for = base_delay * (2 ** (attempt - 1)) + random.random()
                time.sleep(sleep_for)

    try:
        try:
            image_success = _retry_generate_image(concepts["image_prompt"], image_path, attempts=3, base_delay=2.0)
        except Exception as e:
            # surfaced after retries
            status_log.append(f" Image generation crashed after retries: {str(e)}")
            image_success = False

        if image_success:
            status_log.append(" Image generated.")
        else:
            status_log.append(" Image generation failed (API returned no content).")
            image_path = None

    except Exception as e:
        # Last-resort fallback: write a simple placeholder image so UI can show something
        status_log.append(f" Image generation final failure: {str(e)}")
        try:
            # create a dark placeholder (512x512) - avoids failing the whole pipeline
            placeholder_size = (512, 512)
            placeholder = Image.new("RGB", placeholder_size, (30, 30, 30))
            placeholder.save(image_path)
            status_log.append(" Placeholder image created.")
            image_success = True
        except Exception as e2:
            status_log.append(f" Placeholder creation failed: {str(e2)}")
            image_path = None
            image_success = False

    # 4. Use pre-generated audio (music generation disabled for deployment)
    print("\n[3/3] Using pre-generated audio...")
    try:
        # Use the default pre-generated audio file
        audio_path = os.path.join(PROJECT_ROOT, "outputs", "audio", "gemini_story_theme.wav")

        # Verify file exists
        if os.path.exists(audio_path):
            status_log.append(" Pre-generated audio loaded.")
        else:
            status_log.append(" Warning: Pre-generated audio file not found.")
            audio_path = None

    except Exception as e:
        status_log.append(f" Audio loading failed: {str(e)}")
        audio_path = None

    # 5. Return results    
    rel_image = os.path.relpath(image_path, PROJECT_ROOT) if image_path else None
    rel_audio = os.path.relpath(audio_path, PROJECT_ROOT) if audio_path else None

    final_status = "\n".join(status_log)
    
    return rel_image, rel_audio, final_status

# --- Test Block (Simulates how Gradio will call it) ---
if __name__ == "__main__":
    
    # Test Data
    test_theme = "80s Sci-Fi Horror"
    test_summary = "A crew member is found frozen outside the airlock. He has a smile on his face."
    test_full = "The ship's AI hallucinated that the vacuum of space was a paradise and tricked him into opening the door."

    # Call the main function
    img, audio, log = generate_story_assets(test_theme, test_summary, test_full, generate_game_music=False)
    
    print("\n--- Final Result ---")
    print(f"Log: {log}")
    print(f"Image Path: {img}")
    print(f"Audio Path: {audio}")