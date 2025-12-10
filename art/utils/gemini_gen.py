import os
import time
import json
import traceback
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

# --- NEW SDK IMPORTS ---
from google import genai
from google.genai import types

# --- CONFIGURATION ---
load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")

# Initialize Client globally to reuse across functions
client = None

def setup_gemini():
    """Initializes the new GenAI client."""
    global client
    if not API_KEY:
        print(" Error: GOOGLE_API_KEY not found in .env file.")
        return False
    
    try:
        client = genai.Client(api_key=API_KEY)
        return True
    except Exception as e:
        print(f" Error initializing GenAI client: {e}")
        return False

def generate_multimedia_concepts(theme, story_summary, story_full):
    """
    Generates prompts using the new SDK's text generation.
    """
    if not client: return None

    prompt_text = f"""
    You are the Creative Director for a minimalist "Dark Stories" mystery game.
    
    INPUT CONTEXT:
    Theme: {theme}
    Player Summary (Visible): {story_summary}
    Hidden Truth (Spoiler - INTERNAL ONLY): {story_full}
    
    CRITICAL CONSTRAINT: 
    Your generated prompts must be based on the VISIBLE summary. 
    Do NOT reveal elements from the Hidden Truth.

    TASK:
    Generate two distinct prompts in JSON format:
    1. "image_prompt": For a vector icon generator (Imagen).
       - Style: Minimalist flat vector illustration, clean lines.
       - CRITICAL INSTRUCTION: The output must be a pure artistic illustration. Do NOT generate a technical diagram, blueprint, schematic, or infographic.
       - ABSOLUTELY NO TEXT: The image must contain NO letters, numbers, code, XML, labels, dimensions, arrows, or UI elements.
       - Colors: Strictly Black, Red, and White. White background.
       - Content: ONE central symbolic object. 
       
    2. "music_prompt": For a background music generator (MusicGen).
       - Style: Atmospheric, looping background noise.
       - Content: Genre, Mood, and Instruments.
       - Format: Single descriptive sentence.
       - Constraint: No spoilers in the music description.
    
    OUTPUT JSON FORMAT:
    {{
      "image_prompt": "A minimalist flat vector illustration of [Object], black and red colors, isolated on a solid white background. Pure pictorial art, contains absolutely no text or labels.",
      "music_prompt": "Dark ambient background music..."
    }}
    """
    
    # Try the latest Flash model
    model_name = 'gemini-2.0-flash' 
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt_text,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        response_text = response.text.strip()
        
    except Exception as e:
        print(f" Error generating concepts: {e}")
        return None

    # Parse JSON
    try:
        # Clean up any markdown wrapping just in case
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        
        # Handle list wrapping [ { ... } ]
        if isinstance(data, list):
            data = data[0] if len(data) > 0 else {}

        # Post-Process: Strengthen Prompt Constraints
        if "white background" not in data.get("image_prompt", "").lower():
            data["image_prompt"] += ", solid white background"
        
        # Aggressive negative constraints appended to positive prompt
        data["image_prompt"] += ", strictly pictorial, absolutely no text, no letters, no numbers, no code, no XML, no labels, no dimensions, no diagrams, pure illustration only"
            
        print(f"  > Image Concept: {data['image_prompt'][:50]}...")
        print(f"  > Music Concept: {data['music_prompt'][:50]}...")
        
        return data
        
    except json.JSONDecodeError:
        print(f" Failed to parse JSON response: {response_text}")
        return None

def generate_image_gemini(prompt, output_file="gemini_card.png"):
    """
    Generates image using the NEW SDK (Imagen 3).
    """
    if not client: return False

    print("  > Sending request to Imagen...")

    # We try Imagen 3.0 first as it is widely available. 
    # If you have access to 4.0, change this string to 'imagen-4.0-generate-001'
    model_name = 'imagen-4.0-generate-001'

    try:
        response = client.models.generate_images(
            model=model_name,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
                # The new SDK handles constraints differently, usually baked into the prompt 
                # or strictly safety settings. We rely on the prompt engineering here.
            )
        )
        
        # The new SDK returns a list of GeneratedImage objects
        if response.generated_images:
            generated_image = response.generated_images[0]
            
            # generated_image.image is ALREADY a PIL Image object!
            # We can save it directly.
            generated_image.image.save(output_file)
            print(f"  > Success! Saved to {output_file}")
            return True
            
    except Exception as e:
        print(f" Error generating image with new SDK: {e}")
        # If 3.0 fails, you might try a fallback, but usually this error is definitive (quota/safety)
    
    return False

# --- GLUE FUNCTION FOR GRADIO ---
def generate_story_assets(topic, summary, hidden_story):
    """
    Orchestrates the generation pipeline for the Gradio App.
    Returns: img_path, audio_path, logs
    """
    logs = []
    
    if not setup_gemini():
        return None, None, "Error: Google API Key missing or Client failed."

    # 1. Generate Prompts
    concepts = generate_multimedia_concepts(topic, summary, hidden_story)
    if not concepts:
        return None, None, "Failed to generate concepts from Gemini."
    
    logs.append(f"Image Prompt: {concepts['image_prompt']}")
    logs.append(f"Music Prompt: {concepts['music_prompt']}")

    # 2. Setup Output Paths
    base_dir = os.getcwd()
    img_dir = os.path.join(base_dir, "outputs", "images")
    audio_dir = os.path.join(base_dir, "outputs", "audio")
    
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    
    timestamp = int(time.time())
    img_filename = f"card_{timestamp}.png"
    audio_filename = f"audio_{timestamp}.wav"
    
    img_full_path = os.path.join(img_dir, img_filename)
    audio_full_path = os.path.join(audio_dir, audio_filename)

    # 3. Generate Image
    img_success = generate_image_gemini(concepts['image_prompt'], img_full_path)
    
    # 4. Generate Audio (Placeholder)
    audio_success = False 
    
    return (
        img_full_path if img_success else None, 
        audio_full_path if audio_success else None, 
        "\n".join(logs)
    )

if __name__ == "__main__":
    # Test run
    print("Testing Generation...")
    summary = "The King's favorite jester was found dead in the moat, still wearing his bells. The water is shallow."
    hidden_story = "The King pushed him. The Jester was secretly having an affair with the Queen, and the King found a love letter in his cap."
    
    i, a, l = generate_story_assets("Medieval", summary, hidden_story)
    print(f"Image: {i}\nLog: {l}")