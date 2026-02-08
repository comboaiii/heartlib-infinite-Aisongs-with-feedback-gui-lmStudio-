# AGANCY/orphio_config.py
import os
from pathlib import Path
from dataclasses import dataclass

def find_actual_root():
    """Finds the folder containing the 'ckpt' directory."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "ckpt").exists():
            return parent
    return Path(__file__).resolve().parent.parent

@dataclass
class Config:
    ROOT_DIR: Path = find_actual_root()
    CKPT_DIR: Path = ROOT_DIR / "ckpt"
    SRC_DIR: Path = ROOT_DIR / "src"
    OUTPUT_DIR: Path = ROOT_DIR / "GROUND_TRUTH_ComboAi" / "outputSongs_ComboAi"
    TAGS_FILE: Path = ROOT_DIR / "GROUND_TRUTH_ComboAi" / "tags.json"

    LM_STUDIO_URL: str = "http://localhost:1234/v1"
    COOLFOOT_WAIT: int = 5
    SAMPLE_RATE: int = 48000
    FADE_OUT_DURATION: float = 2.5
    CURRENT_DECORATOR_SCHEMA: str = "inner_sonic"

    PROMPT_WRITER: str = (
        "You are a professional Songwriter. Write lyrics based on the user's topic.\n"
        "STRICT FORMATTING: Use UPPERCASE tags in brackets: [INTRO], [VERSE 1], [CHORUS], [OUTRO].\n"
        "Do NOT use markdown bolding (**)."
    )
    PROMPT_TAGGER: str = (
        "You are a metadata tagger. Classify the provided lyrics into 4-6 musical genres or moods.\n"
        "STRICT RULES:\n"
        "1. Output ONLY comma-separated words.\n"
        "2. NO descriptions, NO bolding, NO bullet points, NO numbering.\n"
        "3. NO conversational filler (e.g., 'Here are the tags...').\n"
        "Example Output: electronic, dark, rhythmic, ambient"
    )

    DECORATOR_SCHEMAS = {
        "inner_sonic": "Inject symbols into lines: ^^^ (pitch up), ~~~ (vibrato), +++ (accent), ___ (breath).",
        "structural_heavy": "Wrap section headers in heavy ASCII blocks.",
        "midi_tracker": "Prefix lines with [VEL:99] and use === for sustain.",
        "sheet_music_dynamic": "Add dynamics: (pp), (ff), < < < (crescendo), (stacc.).",
        "word_emphasis_actor": "Attach emotion tags in curly braces: {whisper}, {shout}, {cry}.",
        "vocal_technique_pro": "Annotate technical singing: [FALSETTO], [FRY], [BELT], [VIBRATO].",
        "phonetic_sculptor": "Rewrite words phonetically for sound design: D-D-Don't sto-OP!"
    }

    def validate(self):
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if not self.TAGS_FILE.exists():
            import json
            with open(self.TAGS_FILE, 'w') as f:
                json.dump(["pop", "rock", "electronic", "acoustic", "sad", "dark"], f)

conf = Config()
conf.validate()