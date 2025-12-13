import json
import os

INPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "generated_stories.json")
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    generated_stories = json.load(f)

# Difficulty mapping
difficulty_map = {
    "Easy": "Rookie",
    "Detective": "Detective",
    "Hard": "Sherlock"
}

clean_stories = []

for entry in generated_stories:
    story_str = entry["story"]
    
    # Remove ```json and ``` markers
    story_str = story_str.replace("```json", "").replace("```", "").strip()
    
    try:
        # Parse the inner JSON string
        story_json = json.loads(story_str)
        
        # Map difficulty
        old_difficulty = story_json.get("difficulty", "")
        new_difficulty = difficulty_map.get(old_difficulty, old_difficulty)
        
        # Keep only the fields we need
        clean_stories.append({
            "topic": story_json.get("topic", ""),
            "difficulty": new_difficulty,
            "short_story": story_json.get("short_story", ""),
            "full_story": story_json.get("full_story", "")
        })
    except json.JSONDecodeError as e:
        print("Failed to parse story:", e)
        print("Original:", story_str)

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "stories.json")
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(clean_stories, f, ensure_ascii=False, indent=2)

print(f"Converted {len(clean_stories)} stories to clean format.")
