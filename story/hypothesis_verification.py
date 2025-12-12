"""
Hypothesis Verification Module for Black Stories AI Game.

This module verifies player hypotheses against the true story using Gemini API
with few-shot prompting to provide helpful feedback that guides the player
toward the complete solution.
"""

import os
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load env variables
load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")

# Initialize Client
client = None
if API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        logging.error(f"Failed to init Gemini Client for hypothesis verification: {e}")


# Few-shot examples for the hypothesis verification task
FEW_SHOT_EXAMPLES = """
--- EXAMPLE 1 ---
TRUE STORY: A man died in the desert holding a straw. He had been in a hot air balloon with other people, and someone had to jump to save the rest.

PLAYER HYPOTHESIS: "A man was stranded in the desert and died of thirst. The straw was for drinking water."

ANALYSIS:
📍 **Status: FAR**

❌ **What's wrong:**
- He was not stranded alone
- The straw was not for drinking
- Thirst was not the cause of death

✅ **What you got right:**
- A man died in the desert
- The straw is important

💡 **Hint:**
Think about how someone could end up in the desert suddenly.

--- EXAMPLE 2 ---
TRUE STORY: A woman shoots her husband, puts him underwater, and hangs him. Later, they go out together. He was never harmed.

PLAYER HYPOTHESIS: "The woman killed her husband, but he somehow survived."

ANALYSIS:
📍 **Status: FAR**

❌ **What's wrong:**
- No one was actually killed
- The actions are not literal

✅ **What you got right:**
- The husband is involved the whole time
- The situation is misleading on purpose

💡 **Hint:**
Consider that the words describe actions with more than one meaning.

--- EXAMPLE 3 ---
TRUE STORY: A man asks for water in a bar. The bartender points a gun at him. The man thanks him and leaves.

PLAYER HYPOTHESIS: "The man had hiccups, and the scare cured them."

ANALYSIS:
📍 **Status: CORRECT**

❌ **What's wrong:**
- Nothing essential is missing

✅ **What you got right:**
- The man had hiccups
- The gun was used to scare him
- The scare solved the problem

💡 **Hint:**
No further hint needed.

--- END OF EXAMPLES ---
"""



def verify_hypothesis(true_story: str, player_hypothesis: str) -> str:
    """
    Verifies the player's hypothesis against the true story using Gemini API.
    
    Uses few-shot prompting to help Gemini understand the expected format
    and provide helpful, guiding feedback without directly revealing the answer.
    
    Args:
        true_story: The complete hidden truth of the black story
        player_hypothesis: The player's attempt to explain what happened
        
    Returns:
        A formatted analysis string with closeness score, corrections, and guidance
    """
    if not client:
        return "⚠️ System Error: AI Client not connected. Check your API key."
    
    if not player_hypothesis or not player_hypothesis.strip():
        return "⚠️ Please enter your hypothesis before submitting."
    
    if not true_story or not true_story.strip():
        return "⚠️ No story loaded. Please start a new game first."

    # System instruction for the hypothesis verifier
    sys_instruction = """
    You are the Hypothesis Verifier for a "Black Stories" lateral thinking puzzle game.

    YOUR ROLE:
    Analyze the player's hypothesis and compare it to the TRUE STORY. Provide constructive feedback that:
    1) Labels how close they are: FAR / CLOSE / CORRECT
    2) Points out what's WRONG without revealing the answer
    3) Acknowledges what they got RIGHT
    4) Gives a subtle HINT to guide them closer

    CRITICAL RULES:
    - NEVER reveal the true story directly
    - NEVER give away key plot elements they haven't discovered
    - Be honest and direct (no sugarcoating)
    - Use the exact format shown in the examples
    - Keep hints short, cryptic, and helpful
    - Do NOT include numeric grades or percentages

    IMPORTANT INTERPRETATION RULES:
    - A hypothesis is CORRECT if the player correctly identifies:
    • the true cause of the event or death
    • AND the main misunderstanding (e.g. murder vs accident)
    - Missing secondary or cosmetic details (props, background explanations, why something looked strange)
    does NOT prevent a CORRECT status.
    - Use CLOSE only if the player has the right direction but is missing either the true cause
    OR the true nature of the event.
    - If Status is CORRECT:
    • "What's wrong" must say: "Nothing essential is missing"
    • Do NOT introduce new requirements or ask for extra details
    • The hint should indicate that no further hint is needed

    OUTPUT FORMAT (must match exactly):
    ANALYSIS:
    📍 **Status: FAR/CLOSE/CORRECT**

    ❌ **What's wrong:**
    - ...

    ✅ **What you got right:**
    - ...

    💡 **Hint:**
    ...

    Your goal is to GUIDE the player toward the truth, not to solve it for them.
    """

    # Build the prompt with few-shot examples
    user_prompt = f"""
{FEW_SHOT_EXAMPLES}

Now analyze this new case:

TRUE STORY: {true_story}

PLAYER HYPOTHESIS: "{player_hypothesis}"

ANALYSIS:
"""

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=sys_instruction,
                max_output_tokens=500,
                temperature=0.4  # Balanced between creativity and consistency
            )
        )
        
        analysis = response.text.strip()
        
        # Ensure the response starts properly
        if not analysis.startswith("🔍"):
            analysis = "🔍 " + analysis
            
        return analysis

    except Exception as e:
        logging.error(f"Hypothesis Verification Error: {e}")
        return "⚠️ Connection error. Please try again."


if __name__ == "__main__":
    # Test the module
    test_true_story = """
The "monster" was a prank gone wrong. A group of kids planned to scare the counselor, dressing up in mud and leaves. One of them tripped while chasing her, and the branch in their hand accidentally impaled her. The static was from the walkie-talkie falling as they fled, leaving the footprint as their only trace.
    """
    
    test_hypothesis_1 = "Someone killed the broker by turning off the cooling system."
    test_hypothesis_2 = "It was a kid that got lost and she went to save him tripping over and killing herself."
    
    print("=" * 60)
    print("TEST 1 - Partially correct hypothesis")
    print("=" * 60)
    print(verify_hypothesis(test_true_story, test_hypothesis_1))
    
    print("\n" + "=" * 60)
    print("TEST 2 - Close hypothesis")
    print("=" * 60)
    print(verify_hypothesis(test_true_story, test_hypothesis_2))
