# GenAI-Assignement

Simple setup and run instructions.

## Prerequisites
- Python 3.8+
- Git (optional)
- ffmpeg (for audio, required by pydub) — install system ffmpeg if using audio features.

## Setup
1. Open a terminal in the project folder: `GenAI-Assignement`

2. Create a virtual environment:
```sh
python -m venv .venv
```

3. Activate the virtual environment:
- Windows (cmd):
```sh
.venv\Scripts\activate
```
- Windows (PowerShell):
```ps1
.venv\Scripts\Activate.ps1
```
- macOS / Linux:
```sh
source .venv/bin/activate
```

4. Upgrade pip and install dependencies:
```sh
python -m pip install --upgrade pip
pip install -r requirements.txt
```
(See the project requirements at [GenAI-Assignement/requirements.txt](GenAI-Assignement/requirements.txt).)

5. Configure environment variables:
- Make the [.env](GenAI-Assignement/.env) file and add the required API keys (Google API key). The project uses the helper [`setup_gemini`](GenAI-Assignement/art/utils/gemini_gen.py) to read the API key.

## Run the app
- Start the Gradio UI:
```sh
python interface.py
```
(See the UI code in [GenAI-Assignement/interface.py](GenAI-Assignement/interface.py).)

- Or run the asset generator test script:
```sh
python art/main.py
```
(This calls [`generate_story_assets`](GenAI-Assignement/art/main.py) which orchestrates image and audio generation.)

## Notes
- If you only use remote APIs (Google Gemini), you can remove heavy local ML packages from `requirements.txt` to save space.
- Ensure ffmpeg is on PATH for audio features (pydub).
- If using Hugging Face models locally, you may need `torch`, `transformers`, and enough GPU/CPU memory.