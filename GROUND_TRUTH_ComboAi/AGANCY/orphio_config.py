# AGANCY/orphio_config.py
import os
import json
from pathlib import Path
from dataclasses import dataclass


def find_actual_root():
    """Matches the logic in your working GT_01 script to find the project root."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        # Look for the directory that actually contains the ckpt folder
        if (parent / "ckpt").exists():
            return parent
    # Fallback to two levels up if not found
    return Path(__file__).resolve().parent.parent.parent


@dataclass
class Config:
    # --- DYNAMIC PATHS ---
    ROOT_DIR: Path = find_actual_root()
    CKPT_DIR: Path = ROOT_DIR / "ckpt"
    SRC_DIR: Path = ROOT_DIR / "src"
    # Output inside the GROUND_TRUTH_ComboAi folder
    OUTPUT_DIR: Path = ROOT_DIR / "GROUND_TRUTH_ComboAi" / "outputSongs_ComboAi"
    TAGS_FILE: Path = ROOT_DIR / "GROUND_TRUTH_ComboAi" / "tags.json"

    # Connection
    LM_STUDIO_URL: str = "http://localhost:1234/v1"

    # Audio
    COOLFOOT_WAIT: int = 5
    SAMPLE_RATE: int = 48000
    FADE_OUT_DURATION: float = 2.5

    # Logic
    CURRENT_DECORATOR_SCHEMA: str = "inner_sonic"

    # Prompts
    PROMPT_WRITER: str = (
        "You are a professional Songwriter. Write lyrics based on the user's topic.\n"
        "STRICT FORMATTING: Use UPPERCASE tags in brackets: [INTRO], [VERSE], [Bridge], [CHORUS], [OUTRO].\n"
        "Do NOT use markdown bolding."
    )
    PROMPT_TAGGER: str = "Classify into 4 comma-separated musical genres."

    DECORATOR_SCHEMAS = {
        "inner_sonic": "Inject rhythmic symbols: ^^^ (pitch up), ~~~ (vibrato), +++ (accent), ___ (breath).",
        "structural_heavy": "Wrap headers [CHORUS] in heavy ASCII block symbols.",
        "midi_tracker": "Prefix lines with [VEL:99] and use === for sustain.",
        "sheet_music_dynamic": "Add dynamic markers: (pp), (ff), < < <, (stacc.).",
        "word_emphasis_actor": "Attach emotion tags in curly braces: {whisper}, {shout}.",
        "vocal_technique_pro": "Annotate words: [FALSETTO], [VIBRATO], [SLIDE].",
        "phonetic_sculptor": "Rewrite words phonetically: D-D-Don't sto-OP!"
    }

    def validate(self):
        """Creates output directory and checks for critical files."""
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"🔍 Root: {self.ROOT_DIR}")
        print(f"🔍 Ckpt: {self.CKPT_DIR}")

        required = ["tokenizer.json", "gen_config.json", "HeartMuLa-oss-3B", "HeartCodec-oss"]
        for f in required:
            if not (self.CKPT_DIR / f).exists():
                print(f"❌ MISSING CRITICAL FILE: {self.CKPT_DIR / f}")


conf = Config()
conf.validate()