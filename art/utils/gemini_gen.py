import os
import time
import json
import base64
import io
import requests
from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai

# --- CONFIGURATION ---
load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")

def setup_gemini():
    if not API_KEY:
        print(" Error: GOOGLE_API_KEY not found in .env file.")
        return False
    genai.configure(api_key=API_KEY)
    return True

def generate_multimedia_concepts(theme, story_summary, story_full):
    """
    Generates prompts. 
    """
    
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
       - Style: Flat vector art, minimalist, crisp lines, digital illustration.
       - IMPORTANT: The image must be a PICTURE, not code. 
       - INSTRUCTION: Do NOT include text, letters, or code snippets in the image.
       - Colors: Strictly Black, Red, and White. White background.
       - Content: ONE central symbolic object. 
       
    2. "music_prompt": For a background music generator (MusicGen).
       - Style: Atmospheric, looping background noise.
       - Content: Genre, Mood, and Instruments.
       - Format: Single descriptive sentence.
       - Constraint: No spoilers in the music description.
    
    OUTPUT JSON FORMAT:
    {{
      "image_prompt": "Flat vector icon of [Object], black and red, white background, no text...",
      "music_prompt": "Dark ambient background music..."
    }}
    """
    
    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
    response_text = None
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            generation_config = {"response_mime_type": "application/json"}
            response = model.generate_content(prompt_text, generation_config=generation_config)
            response_text = response.text.strip()
            break 
        except Exception as e:
            if "404" in str(e) or "MIME" in str(e):
                try:
                    response = model.generate_content(prompt_text)
                    response_text = response.text.strip()
                    break
                except:
                    continue
            print(f"    (Skipping {model_name}: {e})")

    if not response_text:
        print(" Failed to get concepts from Gemini.")
        return None

    # Parse JSON
    try:
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        
        # FIX: Handle if Gemini wraps the dict in a list [ { ... } ]
        if isinstance(data, list):
            if len(data) > 0:
                data = data[0]
            else:
                print("Error: Gemini returned an empty list.")
                return None
        
        # Post-process to ensure safety/style compliance
        if "white background" not in data["image_prompt"].lower():
            data["image_prompt"] += ", white background"
        
        data["image_prompt"] += ", object only, no text, no code, no letters"
            
        print(f"  > Image Concept: {data['image_prompt'][:50]}...")
        print(f"  > Music Concept: {data['music_prompt'][:50]}...")
        
        return data
        
    except json.JSONDecodeError:
        print(f" Failed to parse JSON response: {response_text}")
        return None
    except Exception as e:
        print(f" Unexpected error parsing data: {e}")
        return None

def generate_image_rest_fallback(prompt, output_file):
    """Fallback if Python SDK is outdated."""
    print("  > SDK helper missing. Switching to REST API Fallback...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    # FIX: Removed negativePrompt
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1, 
            "aspectRatio": "1:1", 
            "personGeneration": "dont_allow"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code != 200:
            print(f" REST API Error: {response.text}")
            return False
            
        result = response.json()
        if "predictions" in result:
            b64_data = result["predictions"][0]["bytesBase64Encoded"]
            image = Image.open(io.BytesIO(base64.b64decode(b64_data)))
            image.save(output_file)
            return True
    except Exception as e:
        print(f" REST Fallback failed: {e}")
    return False

def generate_image_gemini(prompt, output_file="gemini_card.png"):
    """Generates the image using Imagen."""
    
    if not hasattr(genai, "ImageGenerationModel"):
        return generate_image_rest_fallback(prompt, output_file)

    try:
        # Try Imagen 3 first (Standard)
        imagen_model = genai.ImageGenerationModel("imagen-3.0-generate-001") 
        
        images = imagen_model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="1:1",
            safety_filter_level="block_only_high", 
            person_generation="dont_allow"
            # FIX: Removed negative_prompt
        )
        if images and images[0]:
            images[0].save(location=output_file)
            print(f"  > Success! Saved to {output_file}")
            return True
    except AttributeError:
        return generate_image_rest_fallback(prompt, output_file)
    except Exception as e:
        print(f" Error generating image (SDK): {e}")
        # Try fallback if SDK fails
        return generate_image_rest_fallback(prompt, output_file)

# --- GLUE FUNCTION FOR GRADIO ---
def generate_story_assets(topic, summary, hidden_story):
    """
    Orchestrates the generation pipeline for the Gradio App.
    Returns: img_path, audio_path, logs
    """
    logs = []
    
    if not setup_gemini():
        return None, None, "Error: Google API Key missing."

    # 1. Generate Prompts
    concepts = generate_multimedia_concepts(topic, summary, hidden_story)
    if not concepts:
        return None, None, "Failed to generate concepts from Gemini."
    
    logs.append(f"Image Prompt: {concepts['image_prompt']}")
    logs.append(f"Music Prompt: {concepts['music_prompt']}")

    # 2. Setup Output Paths
    # Ensure outputs directory exists
    base_dir = os.getcwd()
    img_dir = os.path.join(base_dir, "outputs", "images")
    audio_dir = os.path.join(base_dir, "outputs", "audio")
    
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    
    timestamp = int(time.time())
    img_filename = f"card_{timestamp}.png"
    audio_filename = f"audio_{timestamp}.wav" # Placeholder name
    
    img_full_path = os.path.join(img_dir, img_filename)
    audio_full_path = os.path.join(audio_dir, audio_filename)

    # 3. Generate Image
    img_success = generate_image_gemini(concepts['image_prompt'], img_full_path)
    
    # 4. Generate Audio (Placeholder / TODO)
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