import torch
from diffusers import DiffusionPipeline
from transformers import pipeline

def generate_story_image_prompt(theme: str, short_story: str, full_story: str):
    """
    Uses a lightweight LLM (Flan-T5) to create a symbolic, spoiler-free 
    image generation prompt suitable for a 'Dark Stories' style game card.
    """
    print("\n--- Analyzing story for visual symbols (LLM) ---")
    
    device_id = 0 if torch.cuda.is_available() else -1
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    
    # 1. Load the Director Model
    pipe = pipeline(
        "text2text-generation",
        model="google/flan-t5-large",
        device=device_id,
        torch_dtype=dtype,
        model_kwargs={"low_cpu_mem_usage": True}
    )

    # 2. Construct the instruction
    # We put the Context at the END to prevent the model from getting confused.
    prompt_text = f"""
    Role: Art Director.
    Task: Write a text-to-image prompt for a minimalist vector icon.
    
    Guidelines:
    - Describe ONE main object.
    - Style: Flat vector, black and red colors, white background.
    - NO text, NO faces, NO blood.
    
    --- Example 1 ---
    Story: A man died because his parachute failed.
    Output: Flat vector icon of a torn backpack strap, black and red, minimalist, white background
    
    --- Example 2 ---
    Story: A woman is found frozen in a field.
    Output: Flat vector icon of a single ice crystal on a leaf, black and red, minimalist, white background

    --- YOUR TASK ---
    Story: {short_story}
    Theme: {theme}
    
    Output:
    """

    # 3. Generate the prompt
    print("  > Designing Card Tile...")
    outputs = pipe(
        prompt_text, 
        max_new_tokens=60, # Keep it short
        do_sample=True,      
        temperature=0.6,
        top_p=0.95,
    )
    
    generated_prompt = outputs[0]['generated_text']
    
    # Fallback if LLM just copies the story (length check)
    if len(generated_prompt) > 150:
         generated_prompt = "Flat vector icon of a mystery object, black and red, minimalist"

    # Ensure strict style keywords are present
    style_suffix = ", flat vector, minimalist, white background, high contrast, 2d game icon, black and red colors only"
    if "vector" not in generated_prompt:
        generated_prompt += style_suffix
        
    print(f"  > Generated Image Prompt: '{generated_prompt}'")
    
    # Cleanup LLM
    del pipe
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        
    return generated_prompt

def generate_game_image(
    prompt: str,
    output_filename: str = "story_card.png",
    num_inference_steps: int = 40 # Increased slightly for SDXL quality
):
    """
    Generates the actual image using Stable Diffusion XL.
    """
    print(f"\n--- Generating Image on GPU ---")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    # SDXL Base 1.0
    model_id = "stabilityai/stable-diffusion-xl-base-1.0"
    
    try:
        # USE DiffusionPipeline (Auto-loader) instead of StableDiffusionPipeline
        # This automatically handles SDXL architecture correctly.
        pipe = DiffusionPipeline.from_pretrained(
            model_id, 
            torch_dtype=dtype,
            use_safetensors=True,
            variant="fp16" # Ensure we pull the fp16 weights if available
        ).to(device)
        
        print(f"  > Rendering: {prompt}")
        
        # SDXL works best at 1024x1024
        image = pipe(
            prompt=prompt,
            negative_prompt="text, words, letters, watermark, signature, writing, realistic, 3d render, photo, face, human, messy, blurry, colorful",
            num_inference_steps=num_inference_steps,
            guidance_scale=8.0, # High guidance for strict style adherence
            height=1024, 
            width=1024
        ).images[0]
        
        image.save(output_filename)
        print(f"  > Success! Saved card to {output_filename}")
        
        # Cleanup
        del pipe
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
    except Exception as e:
        print(f"Error generating image: {e}")

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
    """

    # 1. Get Prompt
    visual_prompt = generate_story_image_prompt(story_theme, story_summary, story_full)
    
    # 2. Render Image
    generate_game_image(visual_prompt, "dark_story_card.png")