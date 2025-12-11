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
        logging.error(f"Failed to init Gemini Client: {e}")

def analyze_question_with_llm(user_question, full_hidden_story, current_summary):
    """
    Sends the player's question and the hidden truth to Gemini.
    Gemini acts as the referee and returns strictly one of the allowed game responses.
    """
    if not client:
        return "System Error: AI Client not connected."

    # Prompt Engineering: The "Game Master" Persona
    sys_instruction = """
    You are the Game Master for a "Dark Stories" lateral thinking puzzle game.
    
    YOUR GOAL:
    Analyze the Player's Question based on the Hidden Truth.
    
    THE RULES:
    1. You can ONLY answer with one of these exact phrases:
       - "Yes"
       - "No"
       - "It is irrelevant."
       - "I cannot answer that." (Use if the question is not a Yes/No question or assumes false premises)
       - "Focus on the evidence." (Use if they are straying too far)
       
    2. BE STRICT:
       - If the player guesses a detail correctly (e.g. "Was he poisoned?"), say "Yes".
       - If the player guesses incorrectly, say "No".
       - If the specific detail doesn't matter to the core mystery, say "It is irrelevant."
    """

    user_prompt = f"""
    Hidden Truth (DO NOT REVEAL): {full_hidden_story}
    Visible Summary (Context): {current_summary}
    
    Player's Question: "{user_question}"
    
    Your Response (One phrase only):
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash', # Best price/performance currently
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=sys_instruction,
                max_output_tokens=20, # We only need a short phrase
                temperature=0.1       # Low temp for deterministic, strict answers
            )
        )
        
        # Clean up response just in case
        answer = response.text.strip().replace('"', '').replace('.', '')
        
        # Simple validaton to ensure the UI looks clean
        valid_answers = ["Yes", "No", "It is irrelevant", "I cannot answer that", "Focus on the evidence"]
        
        # If the model adds punctuation or small variations, normalize it
        for va in valid_answers:
            if answer.lower().startswith(va.lower()):
                return va + "."
                
        return answer

    except Exception as e:
        logging.error(f"QA Engine Error: {e}")
        return "Connection lost. Try again."
    

def generate_hint_with_llm(chat_history, full_hidden_story, current_summary):
    """
    Generates a context-aware hint based on what the user has already asked.
    """
    if not client:
        return "System Error: AI Client not connected."

    # 1. Format the history so the AI can read the investigation progress
    # chat_history comes in as: [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]
    conversation_log = ""
    if chat_history:
        for msg in chat_history:
            role = "Player" if msg['role'] == 'user' else "Game Master"
            conversation_log += f"{role}: {msg['content']}\n"
    else:
        conversation_log = "(No questions asked yet)"

    # 2. System Instruction for the "Hint Master"
    sys_instruction = """
    You are the Game Master for a lateral thinking mystery game. 
    The player is stuck and asking for a hint.
    
    YOUR GOAL:
    Provide a subtle clue that nudges the player toward the solution WITHOUT giving it away.
    
    GUIDELINES:
    1. Review the "Conversation Log" to see what they already know.
    2. Identify a key concept or angle they have completely missed.
    3. Phrase the hint as a question or a cryptic observation (e.g., "Have you considered the timing of the event?" or "The weapon wasn't held by a hand.")
    4. Keep it short (under 20 words).
    """

    # 3. The Prompt
    user_prompt = f"""
    Hidden Truth (DO NOT REVEAL): {full_hidden_story}
    Visible Summary: {current_summary}
    
    --- Conversation Log ---
    {conversation_log}
    --- End Log ---
    
    Generate a helpful but vague hint:
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=sys_instruction,
                max_output_tokens=50,
                temperature=0.3 
            )
        )
        return f"💡 Hint: {response.text.strip()}"

    except Exception as e:
        return "Hint system unavailable."
    

if __name__ == "__main__":
    # Simple test
    test_question = "Was the databroker not murdered?"

    full_hidden_story = "The broker wasn't murdered. He tried to upload his consciousness to the net, but a firewall AI trapped him halfway, overheating his brain."
    current_summary = "A high-profile databroker was found 'flatlined' in a locked server room. The cooling system was disabled."

    print(analyze_question_with_llm(test_question, full_hidden_story, current_summary))