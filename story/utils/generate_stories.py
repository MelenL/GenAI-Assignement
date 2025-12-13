import os
import json
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ----------------------------
# Setup logging
# ----------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ----------------------------
# Load environment
# ----------------------------
load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")

client = None
if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    logging.error("No API key found. Exiting.")
    exit(1)

# ----------------------------
# Output file
# ----------------------------
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "generated_stories.json")
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# ----------------------------
# Generation parameters
# ----------------------------
NUM_STORIES = 100
DIFFICULTY_CHOICES = ["Easy", "Detective", "Hard"]
GENRES = ["Fantasy", "Sci-Fi", "Crime", "Fairy Tale", "Horror", "Surreal"]

# ----------------------------
# Helper function
# ----------------------------
def generate_story(prompt: str):
    """
    Generate a story using Gemini 2.5+ (gemini-2.5-flash).
    Returns a JSON object if the model returns valid JSON, else None.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.7,  # Adjust creativity
                thinking_config=types.ThinkingConfig(thinking_budget=0)  # Disable thinking to reduce token usage
            )
        )
        text = response.text.strip()

        # Try to parse JSON if model is expected to return structured output
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logging.warning("Generated text is not valid JSON. Returning raw text.")
            return {"story": text}

    except Exception as e:
        logging.warning(f"Failed to generate story: {e}")
        return None


# ----------------------------
# Main generation loop
# ----------------------------
stories = []

for i in range(NUM_STORIES):
    topic = GENRES[i % len(GENRES)]
    difficulty = DIFFICULTY_CHOICES[i % len(DIFFICULTY_CHOICES)]

    prompt = f"""
Generate a short story example as JSON. The JSON must include:
- topic: short genre/topic (string)
- difficulty: one of {DIFFICULTY_CHOICES}
- short_story: 1-2 sentence premise
- full_story: 5-7 sentence story with a twist

Story genre/topic: {topic}
Difficulty: {difficulty}

Return ONLY valid JSON.
"""

    story = generate_story(prompt)
    if story:
        stories.append(story)
        logging.info(f"Generated story {i+1}/{NUM_STORIES}")

# ----------------------------
# Save to disk
# ----------------------------
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(stories, f, ensure_ascii=False, indent=2)

logging.info(f"Saved {len(stories)} stories to {OUTPUT_FILE}")
