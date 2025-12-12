import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")

client = None
if API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        print(f"Error init STT client: {e}")

def transcribe_audio(audio_filepath):
    """
    Sends audio to Gemini 2.0 Flash for fast transcription.
    """
    if not client:
        return "Error: API Key missing."
    
    if not audio_filepath:
        return ""

    try:
        # 1. Read the audio file bytes
        with open(audio_filepath, "rb") as f:
            audio_bytes = f.read()

        # 2. Prompt Gemini to transcribe
        # Gemini 2.0 Flash is extremely fast at this
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                        types.Part.from_text(text="Transcribe this audio exactly. Do not add any commentary.")
                    ]
                )
            ]
        )
        return response.text.strip()

    except Exception as e:
        print(f"STT Error: {e}")
        return "Error processing audio."