import torch
import scipy.io.wavfile
import numpy as np
from transformers import AutoProcessor, MusicgenForConditionalGeneration, pipeline
import re

def generate_story_music_prompt(theme: str, short_story: str, full_story: str):
    """
    Uses a lightweight LLM (Flan-T5) to analyze a game story and generate 
    a music prompt without revealing plot spoilers.
    
    Returns:
        tuple: (base_prompt: str, style_options: dict)
    """
    print("\n--- Analyzing story for music cues (LLM) ---")
    
    device_id = 0 if torch.cuda.is_available() else -1
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    
    # Load a lightweight instruction model
    pipe = pipeline(
        "text2text-generation",
        model="google/flan-t5-large",
        device=device_id,
        dtype=dtype,
        model_kwargs={"low_cpu_mem_usage": True}
    )

    # Construct instruction
    # FIX: Moved the "Actual Context" to the VERY END.
    # We provide distinct examples first (Happy & Sci-Fi) to teach the format,
    # then present the actual dark story at the end so the model generates NEW content.
    prompt_text = f"""
    Role: Music Supervisor.
    Task: Describe background music for the given story.
    Format: Music: [Description] | Mood: [Adjectives] | Instruments: [List]

    --- Example 1 ---
    Story: A happy adventure in a magical meadow with bunnies.
    Output: Music: Upbeat orchestral adventure with playful melody | Mood: Cheerful, Bright | Instruments: Flute, Strings

    --- Example 2 ---
    Story: A futuristic cyberpunk chase scene in the rain.
    Output: Music: Fast-paced electronic synthwave with heavy bass | Mood: Energetic, Intense | Instruments: Synthesizer, Drum Machine

    --- YOUR TASK ---
    Theme: {theme}
    Story: {short_story}
    
    Output:
    """

    # Generate
    print("  > Asking AI Director...")
    
    outputs = pipe(
        prompt_text, 
        max_new_tokens=256,
        do_sample=True,      
        temperature=0.8,     # Slightly higher creativity to avoid copying examples
        top_p=0.9,
        repetition_penalty=1.2
    )
    
    generated_text = outputs[0]['generated_text']
    
    # Cleanup LLM immediately
    del pipe
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    print(f"  > Raw LLM Output:\n{generated_text}\n")

    # Parse the output (Pipe Separated)
    base_prompt = ""
    style_options = {}
    
    try:
        # Clean up text
        clean_text = generated_text.replace("\n", " ").strip()
        
        # Split by pipe |
        if "|" in clean_text:
            parts = clean_text.split("|")
            for part in parts:
                if ":" in part:
                    key, val = part.split(":", 1)
                    key = key.strip().lower()
                    val = val.strip()
                    
                    if "music" in key or "description" in key:
                        base_prompt = val
                    else:
                        style_options[key] = val
        else:
            # Fallback if no pipes found
            base_prompt = clean_text

    except Exception as e:
        print(f"  > Warning: Parsing failed ({e}). Using raw text.")
        base_prompt = generated_text

    # --- SMART FALLBACKS ---
    if not style_options and base_prompt:
        # Try to find instruments in the base prompt string
        common_instruments = ["piano", "synth", "guitar", "strings", "bass", "drums", "orchestra", "flute", "violin", "cello", "percussion"]
        found_instruments = [inst for inst in common_instruments if inst in base_prompt.lower()]
        if found_instruments:
            style_options["instruments"] = ", ".join(found_instruments)
            
        # Try to find mood in the base prompt string
        common_moods = ["dark", "happy", "tense", "sad", "fast", "slow", "scary", "upbeat", "eerie", "melancholy"]
        found_moods = [m for m in common_moods if m in base_prompt.lower()]
        if found_moods:
            style_options["mood"] = ", ".join(found_moods)

    # Final Safety Checks
    if not base_prompt or len(base_prompt) < 3:
        base_prompt = "Atmospheric background music fitting the story theme"
        
    print(f"  > Parsed Prompt: '{base_prompt}'")
    print(f"  > Parsed Options: {style_options}")
    
    return base_prompt, style_options

def generate_game_music(
    base_prompt: str,
    style_options: dict = None,
    duration: int = 60,
    output_filename: str = "background_music.wav",
    model_size: str = "small",
    loop_duration: int = 1200
):
    """
    Generates background music using the Facebook MusicGen model via Hugging Face.
    Optimized for local execution on NVIDIA GPUs (Ada/Ampere/etc).

    Args:
        base_prompt (str): The core description of the music.
        style_options (dict): A map of additional modifiers.
        duration (int): Duration in seconds.
        output_filename (str): Path to save the .wav file.
        model_size (str): 'small', 'medium', or 'large'.
        loop_duration (int): If specified, loops the audio to reach this duration in seconds.
    """
    
    # 1. Hardware Configuration
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    print(f"\n--- Initializing MusicGen ({model_size}) on {device} ---")

    # 2. Construct the full prompt
    full_prompt = base_prompt
    if style_options:
        modifiers = ", ".join([f"{k} {v}" for k, v in style_options.items()])
        full_prompt = f"{full_prompt}, {modifiers}"
    
    print(f"Generating with final prompt: '{full_prompt}'")

    # 3. Load Model
    model_id = f"facebook/musicgen-{model_size}"
    
    try:
        processor = AutoProcessor.from_pretrained(model_id)
        model = MusicgenForConditionalGeneration.from_pretrained(
            model_id, 
            dtype=dtype
        ).to(device)
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    # 4. Prepare Inputs
    inputs = processor(
        text=[full_prompt],
        padding=True,
        return_tensors="pt"
    ).to(device)

    # 5. Generation Loop (Chunking)
    max_duration_per_chunk = 30.0
    tokens_per_second = 50 
    
    sampling_rate = model.config.audio_encoder.sampling_rate
    collected_audio_segments = []
    
    remaining_duration = duration
    chunk_idx = 1
    
    print(f"Total requested duration: {duration}s. Splitting into chunks...")

    try:
        while remaining_duration > 0:
            chunk_duration = min(remaining_duration, max_duration_per_chunk)
            max_new_tokens = int(chunk_duration * tokens_per_second)
            
            print(f"  > Generating Chunk {chunk_idx}: {chunk_duration}s ({max_new_tokens} tokens)...")
            
            with torch.no_grad():
                audio_values = model.generate(
                    **inputs, 
                    max_new_tokens=max_new_tokens,
                    do_sample=True,
                    guidance_scale=3.0,
                    temperature=1.0 
                )
            
            # Move to CPU/float32 immediately
            chunk_data = audio_values[0, 0].cpu().numpy().astype(np.float32)
            collected_audio_segments.append(chunk_data)
            
            remaining_duration -= chunk_duration
            chunk_idx += 1
            
            # Strict Cleanup
            del audio_values
            if device == "cuda":
                torch.cuda.empty_cache()
                
    except Exception as e:
        print(f"Error during generation loop: {e}")
        if not collected_audio_segments:
            return

    # 6. Save
    print("Stitching segments together...")
    final_audio_data = np.concatenate(collected_audio_segments)

     # --- LOOPING LOGIC ---
    if loop_duration > duration:
        current_len_sec = len(final_audio_data) / sampling_rate
        repeats = int(np.ceil(loop_duration / current_len_sec))
        
        print(f"  > Looping audio {repeats} times to reach ~{loop_duration}s ({loop_duration/60:.1f} mins)...")
        final_audio_data = np.tile(final_audio_data, repeats)
            
    # Normalize
    max_val = np.abs(final_audio_data).max()
    if max_val > 1.0:
        final_audio_data = final_audio_data / max_val
    
    scipy.io.wavfile.write(output_filename, rate=sampling_rate, data=final_audio_data)
    
    del model
    del processor
    del inputs
    if device == "cuda":
        torch.cuda.empty_cache()

    print(f"Success! Saved to {output_filename}")


# --- Test Block ---
if __name__ == "__main__":
    
    # Example Story Data
    story_theme = "80s years"
    story_summary = """
    A man is found dead in his living room, sitting upright in an armchair. 
    His phone is on the floor next to him, the screen cracked. 
    On the wall behind him, someone has written a single word in large, shaky letters: “SORRY.”
    """
    story_full = """
    The man suffered a fatal heart attack caused by extreme stress. 
    He had been receiving threatening anonymous messages for days. 
    Earlier that evening, his ex-business partner broke into the house. 
    When the partner entered, the man panicked, had a heart attack, and died. 
    The partner, fearing murder charges, wrote 'SORRY' to look remorseful and fled.
    """

    # 1. Generate Prompt from Story
    # generated_prompt, generated_options = generate_story_music_prompt(
    #     theme=story_theme,
    #     short_story=story_summary,
    #     full_story=story_full
    # )

    # 2. Generate Music using that prompt
    generate_game_music(
        base_prompt='generated_prompt',
        style_options=None,
        duration=5,
        loop_duration=1200,
        output_filename="dark_story_theme.wav",
        model_size="small" # Use 'medium' or 'large' for better quality but requires more VRAM
    )