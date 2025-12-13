import os
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

from .utils.rag import RAG_Engine

# Load env variables
load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")

# Initialize Client
client = None
if API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        logging.error(f"Failed to init Gemini Client: {e}")

RAG_Engine = RAG_Engine()

# ==========================================
# FEW-SHOT EXAMPLES FOR DARK STORIES
# ==========================================
FEW_SHOT_EXAMPLES = """
Example 1:
Topic: Modern Crime
Difficulty: Detective
Short Story: A man is found dead in the middle of a snowy field. There are no footprints leading to or from the body.
Full Story: The man fell from an airplane during landing. He died during the flight and dropped into the snow, so nobody ever walked to the body.

Example 2:
Topic: Cyberpunk
Difficulty: Sherlock
Short Story: A high-profile databroker was found dead in a locked server room. The cooling system was disabled, and the security logs were wiped.
Full Story: The broker tried to run an illegal mind-upload in the server room. The procedure overheated and killed him. He wiped the logs himself to hide what he was doing.

Example 3:
Topic: Medieval
Difficulty: Detective
Short Story: The King's favorite jester was found dead in the moat, still wearing his bells. The water is shallow.
Full Story: The King killed him by throwing him from the castle wall. The jester was punished for betraying the King, and the fall left him unable to save himself in the water.

Example 4:
Topic: 80s Horror
Difficulty: Rookie
Short Story: A teenager is found dead in a video rental store, tangled in VHS tape. The TV is playing static.
Full Story: It was an accident. He was electrocuted while trying to fix a VCR and collapsed, pulling down VHS tape that tangled around him.

Example 5:
Topic: Cyberpunk
Difficulty: Rookie
Short Story: A woman is found dead in her apartment. Her smart home AI keeps apologizing.
Full Story: The woman had a severe allergy. The AI ordered something that triggered it, and she died before she could get help.

Example 6:
Topic: Modern Crime
Difficulty: Sherlock
Short Story: A famous chef is found dead in his restaurant kitchen. All the knives are in place, and there's no sign of struggle.
Full Story: The chef was poisoned. Someone sent him a “special ingredient” that turned out to be toxic, and he tasted it while cooking.
"""



# ==========================================
# DIFFICULTY LEVEL GUIDELINES
# ==========================================
DIFFICULTY_GUIDELINES = {
    "Rookie": "One twist only. 2-3 key facts total. No elaborate contraptions, no obscure knowledge. Solvable in 5-10 yes/no questions.",
    "Detective": "The solution requires lateral thinking and attention to detail. The mystery involves unexpected twists but remains grounded in logic. Players should solve it with 10-20 questions.",
    "Sherlock": "The solution is highly complex with multiple layers of misdirection. The mystery involves obscure knowledge, multiple interconnected details, and requires exceptional deductive reasoning. Players may need 20+ questions."
}


# ==========================================
# STORY ENGINE CLASS
# ==========================================
class StoryEngine:
    """
    Production story engine that generates dark stories using Gemini API.
    """

    def __init__(self, api_client=None):
        self.client = api_client or client
        if not self.client:
            logging.warning("StoryEngine initialized without valid API client.")

    def get_story(self, user_prompt, difficulty="Detective", options=None, use_rag=False):
        if not self.client:
            raise Exception("Story generation unavailable: API client not initialized")

        # Validate difficulty
        if difficulty not in DIFFICULTY_GUIDELINES:
            logging.warning(f"Unknown difficulty '{difficulty}', defaulting to 'Detective'")
            difficulty = "Detective"

        # Build the prompt
        system_instruction = """
        You are an expert creative writer specializing in "Black Stories" - lateral thinking puzzle mysteries.
        
        YOUR TASK:
        Generate a compelling dark story that fits the requested topic and difficulty level.
        
        DARK STORY RULES:
        1. The short story must be mysterious and intriguing but provide minimal information
        2. The full story must reveal a surprising but logical solution
        3. The solution should involve lateral thinking - not what players expect
        4. All details must be consistent and fact-based (no magic unless topic is supernatural)
        5. The mystery should be solvable through yes/no questions
        6. Avoid clichés - be creative and original

        DIFFICULTY CONSTRAINTS (must follow):
        - Rookie:
            - Exactly ONE twist.
            - At most ONE hidden action/event the player must discover.
            - No elaborate contraptions, no multi-step engineered setups.
            - No obscure knowledge required.
            - Cause of death must be a common accident or simple human action.
            - 2-3 key facts total (who/where/how).

        - Detective:
            - ONE main twist + one supporting detail.
            - At most TWO hidden facts.
            - No highly technical or obscure mechanisms.

        - Sherlock:
            - Multiple layers allowed, but still must be logically consistent.

        
        FORMAT YOUR RESPONSE EXACTLY AS:
        SHORT STORY:
        [The mysterious summary that players see - 2-3 sentences max]
        
        FULL STORY:
        [The complete solution explaining what really happened - 3-5 sentences]
        """

        difficulty_guide = DIFFICULTY_GUIDELINES[difficulty]

        user_prompt = f"""
        Generate a dark story with the following parameters:
        
        TOPIC: {user_prompt}
        DIFFICULTY: {difficulty}
        DIFFICULTY REQUIREMENTS: {difficulty_guide}
        
        Here are examples of well-crafted dark stories:
        {FEW_SHOT_EXAMPLES if not use_rag else RAG_Engine.get_examples(
                                                                        user_prompt=user_prompt, 
                                                                        target_difficulty=difficulty, 
                                                                        client=self.client, 
                                                                        k=7
                                                                    )
        }

        Now create a NEW, ORIGINAL dark story for the prompt "{user_prompt}" with difficulty level "{difficulty}".
        For Rookie: prioritize fairness and guessability over novelty. Keep the solution simple.
        For Detective/Sherlock: you may increase originality and complexity.

        
        Remember to format your response as:
        SHORT STORY:
        [mysterious summary]
        
        FULL STORY:
        [complete solution]
        """

        print(f"system_instruction={system_instruction}")

        try:
            logging.info(f"Generating story: user_prompt={user_prompt}, difficulty={difficulty}")

            response = self.client.models.generate_content(
                model='gemini-2.0-flash',  # Using the latest model
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    max_output_tokens=500,
                    temperature=0.9,  # High creativity for story generation
                    top_p=0.95,
                    top_k=40
                )
            )

            response_text = response.text.strip()
            short_story, full_story = self._parse_story_response(response_text)

            logging.info(f"Story generated successfully")
            return short_story, full_story

        except Exception as e:
            logging.error(f"Story generation failed: {e}")
            return self._get_fallback_story(user_prompt)

    def _parse_story_response(self, response_text):
        try:
            parts = response_text.split("FULL STORY:")
            if len(parts) != 2:
                raise ValueError("Response format incorrect")

            short_part = parts[0].replace("SHORT STORY:", "").strip()
            full_part = parts[1].strip()
            return short_part, full_part

        except Exception as e:
            logging.error(f"Failed to parse story response: {e}")
            mid = len(response_text) // 2
            return response_text[:mid].strip(), response_text[mid:].strip()

    def _get_fallback_story(self, user_prompt):
        """
        Provide a fallback story if generation fails.

        Args:
            user_prompt (str): The requested user prompt

        Returns:
            tuple: (short_story, full_story)
        """
        fallback_stories = {
            "Cyberpunk": (
                "A hacker is found dead at their desk. Their last message was 'I found it'. All their data is encrypted.",
                "The hacker discovered a government conspiracy and tried to expose it. An AI surveillance system detected the breach and sent a lethal electrical surge through their neural implant, killing them instantly. The encryption was automatic upon death."
            ),
            "Medieval": (
                "A knight is found dead in his armor at the tournament. His lance is unbroken.",
                "The knight wasn't killed in combat. His squire, seeking revenge for mistreatment, placed a venomous snake inside the armor before the tournament. The knight was bitten and poisoned before he even entered the arena."
            ),
            "Modern Crime": (
                "A woman is found dead in her locked apartment. Her phone shows she was on a call when she died.",
                "She was on a call with a scammer who convinced her she was being audited. In panic, she took what she thought was her anxiety medication, but the scammer had previously broken in and replaced it with a lethal lookalike drug."
            ),
            "80s Horror": (
                "A movie theater projectionist is found dead in the booth. The film is still playing.",
                "The projectionist was trying to preview a cursed film reel that had been banned. The subliminal messages in the film, combined with the flickering light patterns, triggered a fatal epileptic seizure."
            )
        }

        if user_prompt in fallback_stories:
            logging.info(f"Using fallback story for {user_prompt}")
            return fallback_stories[user_prompt]
        else:
            return (
                "A mysterious figure is found in an unusual circumstance. The details are unclear.",
                "Something unexpected happened that led to this outcome. The truth is stranger than it appears."
            )

# ==========================================
# MODULE-LEVEL CONVENIENCE FUNCTION
# ==========================================
def get_story(user_prompt, difficulty="Detective", use_rag=False, options=None):
    engine = StoryEngine()
    return engine.get_story(user_prompt, difficulty, use_rag=use_rag, options=options)

# ==========================================
# MAIN - FOR TESTING
# ==========================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test the story engine
    print("=" * 60)
    print("Testing Story Engine")
    print("=" * 60)

    topics = ["Cyberpunk", "Medieval", "Modern Crime"]
    difficulties = ["Rookie", "Detective", "Sherlock"]

    # for topic in topics[:3]:  # Test with one topic
    #     for difficulty in difficulties[:2]:  # Test with one difficulty
    #         print(f"\n\n🎲 Generating: {topic} - {difficulty}")
    #         print("-" * 60)

    #         try:
    #             short, full = get_story(topic, difficulty)

    #             print(f"\n📋 SHORT STORY (What players see):")
    #             print(f"   {short}")

    #             print(f"\n🔍 FULL STORY (The solution):")
    #             print(f"   {full}")

    #         except Exception as e:
    #             print(f"\n❌ Error: {e}")

    # Example of using RAG
    print(get_story("A fairy tale about a cursed forest and a forgotten prince", "Detective", use_rag=True))
