import os
import google.generativeai as genai
from PIL import Image
import requests
import base64
import io
import json
import re
from dotenv import load_dotenv

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
    ONE CALL to rule them all.
    Asks Gemini to generate both the Image Prompt and the Music Prompt 
    in a single JSON response to save money and latency.
    """
        
    prompt_text = f"""
    You are the Creative Director for a minimalist "Dark Stories" mystery game.
    
    INPUT CONTEXT:
    Theme: {theme}
    Player Summary (Visible): {story_summary}
    Hidden Truth (Spoiler - INTERNAL ONLY): {story_full}
    
    CRITICAL CONSTRAINT: 
    Your generated prompts must be based on the VISIBLE summary. 
    Do NOT reveal elements from the Hidden Truth (e.g., do not show the murderer if the player doesn't know them yet).
    Use the Hidden Truth only to inform the mood/atmosphere.

    TASK:
    Generate two distinct prompts in JSON format:
    1. "image_prompt": For a vector icon generator (Imagen).
       - Style: Flat vector art, minimalist, SVG style.
       - Colors: Strictly Black, Red, and White. White background.
       - Content: ONE central symbolic object. No text/words. No faces.
       
    2. "music_prompt": For a background music generator (MusicGen).
       - Style: Atmospheric, looping background noise.
       - Content: Genre, Mood, and Instruments.
       - Format: Single descriptive sentence.
       - Constraint: No spoilers in the music description.
    
    OUTPUT JSON FORMAT:
    {{
      "image_prompt": "Flat vector icon of [Object], black and red, white background...",
      "music_prompt": "Dark ambient background music with tense mood, featuring synthesizer and bass, slow tempo"
    }}
    """
    
    # efficient models first
    models_to_try = ['gemini-2.5-flash-preview-09-2025', 'gemini-2.0-flash', 'gemini-1.5-flash']
    
    response_text = None
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            # Request JSON response type if supported by the model version
            generation_config = {"response_mime_type": "application/json"}
            response = model.generate_content(prompt_text, generation_config=generation_config)
            response_text = response.text.strip()
            break 
        except Exception as e:
            if "404" in str(e) or "MIME" in str(e):
                # Fallback to standard text generation if JSON mode isn't supported
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
        # Clean up any markdown code blocks if present
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        
        # Post-process to ensure safety/style compliance
        if "white background" not in data["image_prompt"].lower():
            data["image_prompt"] += ", white background"
            
        print(f"  > Image Concept: {data['image_prompt'][:50]}...")
        print(f"  > Music Concept: {data['music_prompt'][:50]}...")
        
        return data
        
    except json.JSONDecodeError:
        print(f" Failed to parse JSON response: {response_text}")
        return None

def generate_image_rest_fallback(prompt, output_file):
    """Fallback if Python SDK is outdated."""
    print("  > SDK helper missing. Switching to REST API Fallback...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"sampleCount": 1, "aspectRatio": "1:1", "personGeneration": "dont_allow"}
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
    """Generates the image using Imagen 4."""
    
    if not hasattr(genai, "ImageGenerationModel"):
        return generate_image_rest_fallback(prompt, output_file)

    try:
        imagen_model = genai.ImageGenerationModel("imagen-4.0-generate-001")
        images = imagen_model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="1:1",
            safety_filter_level="block_only_high", 
            person_generation="dont_allow" 
        )
        if images and images[0]:
            images[0].save(location=output_file)
            print(f"  > Success! Saved to {output_file}")
            return True
    except AttributeError:
        return generate_image_rest_fallback(prompt, output_file)
    except Exception as e:
        print(f" Error generating image: {e}")
        return False