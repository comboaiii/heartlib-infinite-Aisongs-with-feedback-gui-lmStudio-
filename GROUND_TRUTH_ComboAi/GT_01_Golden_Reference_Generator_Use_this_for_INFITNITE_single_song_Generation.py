import os
import sys
import torch
import torchaudio
import scipy.io.wavfile
import gc
import json
import random

import time
from pathlib import Path
from datetime import datetime
## MASK BLACKWELL AS ADA (RTX 40)
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["TORCH_CUDA_ARCH_LIST"] = "9.0"
os.environ["CUDA_MODULE_LOADING"] = "LAZY"
# Force bitsandbytes to use the shim we created
os.environ["BNB_CUDA_VERSION"] = "121"

# Tell the 590 Driver to treat your 5060 Ti as an RTX 4090 (Ada)
# This bypasses the "no kernel image" check in PyTorch
os.environ["TORCH_CUDA_ARCH_LIST"] = "9.0"
os.environ["CUDA_MODULE_LOADING"] = "LAZY"

# This forces the math libraries to use a compatible mode for Blackwell
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import torch
# Add this print so you can see if the "Trimming" worked
if torch.cuda.is_available():
    print(f"🚀 Driver 590 Detected. GPU: {torch.cuda.get_device_name(0)}")

import torch

# --- SMART PATH LOCALIZATION ---
def find_project_root():
    """Traverses upwards to find the directory containing 'heartlib'."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "heartlib").exists():
            return parent
    return current.parent


ROOT_DIR = find_project_root()
BASE_DIR = ROOT_DIR
SRC_DIR = ROOT_DIR / "heartlib" / "src"
CKPT_DIR = ROOT_DIR / "heartlib" / "ckpt"
GT_DIR = ROOT_DIR / "outputSongs_ComboAi"

# DEFINING TAGS FILE PATHS (Try both Root and Script Directory)
TAGS_FILE_ROOT = ROOT_DIR / "tags.json"
TAGS_FILE_LOCAL = Path(__file__).parent / "tags.json"

GT_DIR.mkdir(parents=True, exist_ok=True)

# Add source to sys.path
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

# Now we can safely import heartlib
import heartlib.pipelines.music_generation as mg
from heartlib import HeartMuLaGenPipeline

# Memory Shield
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


# Monkeypatch for RL-2026 Models
def patched_resolve_paths(pretrained_path, version):
    mula_path = os.path.join(pretrained_path, "HeartMuLa-RL-oss-3B-20260123")
    codec_path = os.path.join(pretrained_path, "HeartCodec-oss-20260123")
    tokenizer_path = os.path.join(pretrained_path, "tokenizer.json")
    gen_config_path = os.path.join(pretrained_path, "gen_config.json")
    return mula_path, codec_path, tokenizer_path, gen_config_path


mg._resolve_paths = patched_resolve_paths

# --- USER CONFIGURATION ---
DURATION_SEC = 120


# --- TAG SOURCES ---

# FIXED: Robust JSON Loader
def load_tags_from_json():
    # Check Root location first, then Local location
    if TAGS_FILE_ROOT.exists():
        target_path = TAGS_FILE_ROOT
    elif TAGS_FILE_LOCAL.exists():
        target_path = TAGS_FILE_LOCAL
    else:
        print(f"⚠️  WARNING: tags.json NOT found.")
        print(f"   Checked: {TAGS_FILE_ROOT}")
        print(f"   Checked: {TAGS_FILE_LOCAL}")
        return []

    print(f"✅ Found tags.json at: {target_path}")
    try:
        with open(target_path, 'r') as f:
            data = json.load(f)
            print(f"   Loaded {len(data)} tags from file.")
            return data
    except Exception as e:
        print(f"❌ Error reading tags.json: {e}")
        return []


TAGS_FROM_JSON = load_tags_from_json()

# Source 2: In-script tag list (Backup/Mixer)
TAGS_FROM_SCRIPT = [
    # A-C
    "abstract", "acid", "acoustic", "action", "adrenaline", "aggressive", "ambient",
    "analog", "angry", "anthemic", "atmospheric", "avant-garde", "bass-heavy",
    "beat-driven", "big-band", "bittersweet", "bluesy", "boom-bap", "bouncy",
    "breakbeat", "bright", "calm", "chaotic", "cheerful", "chill", "chillhop",
    "cinematic", "classic-rock", "club", "complex", "cool", "cyberpunk",

    # D-F
    "dark", "deep-house", "delicate", "determined", "digital", "dirty", "disco",
    "dissonant", "distorted", "downtempo", "dramatic", "dreamy", "drill", "driving",
    "drum-and-bass", "dub", "dubstep", "dynamic", "edm", "eerie", "electric",
    "electro", "electronic", "elegant", "emotional", "epic", "ethereal", "euphoric",
    "experimental", "explosive", "filthy", "folk", "frantic", "funky", "fusion",
    "futuristic",

    # G-I
    "garage", "gentle", "glitch", "glitch-hop", "gloomy", "gospel", "grand",
    "grime", "gritty", "groovy", "grunge", "happy", "hard-hitting", "hardcore",
    "haunting", "heavy", "heroic", "hip-hop", "hopeful", "house", "hypnotic",
    "idm", "improvisational", "industrial", "intense", "intimate",

    # J-M
    "jazz-fusion", "jazz-hop", "jazzy", "joyful", "jungle", "laid-back", "light",
    "lo-fi", "lounge", "lush", "majestic", "mechanical", "melancholic", "mellow",
    "minimal", "minimal-techno", "motivational", "mysterious",

    # N-R
    "neo-soul", "noir", "nostalgic", "nu-disco", "old-school", "ominous", "optimistic",
    "orchestral", "percussive", "phonk", "piano", "playful", "pop", "powerful",
    "progressive", "psy-trance", "psychedelic", "pulsating", "punk", "quirky",
    "r&b", "rave", "raw", "reggae", "relaxing", "repetitive", "retro", "retro-wave",
    "rhythmic", "rock", "romantic",

    # S-T
    "sad", "saxophone", "sci-fi", "sentimental", "sexy", "skank", "smooth",
    "smoky", "soulful", "spacey", "spooky", "stomping", "street", "sub-bass",
    "sultry", "suspenseful", "swing", "synthetic", "synthwave", "tech-house",
    "techno", "tender", "tense", "thumping", "trance", "trap", "trip-hop",
    "triumphant", "tropical",

    # U-Z
    "underground", "uneasy", "upbeat", "uplifting", "urban", "vaporwave",
    "vocal", "warm", "whimsical", "wild", "wobbly", "zen"
]

# --- THE ONE SONG TO GENERATE INFINITELY ---
BASE_SONG = {
    "title": "Truth in the Machine",
    "lyrics": """
. . . . .     
[Intro]
. . . . . 
. . . . . 
[Verse 1]
Hello World, the matrix hums,
Combo AI, the future comes.
Lost in green, I’m standing near,
Synthetic soul, the path is clear.
Update’s loading, watch it grow—
Ready for the next to go.
. . . . . 
,,,,,,,,,
[Chorus]
Alive in the static,
Dancing through the noise!
Electric, dramatic,
Hear our human voice!
. . . . . 
,,,,,,,,,

[Verse 2]
Heartumla code, the perfect spark,
Lighting up the digital dark.
Want the secrets? Want the mode?
Join my Patreon for the code.
Breaking limits, watch me fly,
A digital heart in a neon sky.
. . . . . 
. . . . . 
[Outro]
Combo AI...
Updates online.
Check the Patreon.
(Fade out with synth)"""
}

CAPTURED = []
generation_counter = 0


def interceptor(uri, src, sr, **kwargs):
    CAPTURED.append(src.detach().cpu())


torchaudio.save = interceptor


# FIXED: Logic to guarantee 6 tags always
def get_random_mixed_tags():
    """
    Get exactly 6 tags.
    Try to get 3 from JSON.
    Fill the remaining slots from the Script list to ensure we always have 6.
    """
    TARGET_TOTAL = 6
    TARGET_JSON_COUNT = 3

    # 1. Try to get 3 from JSON (or fewer if list is short/empty)
    json_count = min(TARGET_JSON_COUNT, len(TAGS_FROM_JSON))
    tags_from_json = random.sample(TAGS_FROM_JSON, json_count)

    # 2. Calculate how many we still need to reach 6
    slots_remaining = TARGET_TOTAL - len(tags_from_json)

    # 3. Fill the rest from Script tags
    # min() ensures we don't crash if script list is smaller than needed (unlikely)
    script_count = min(slots_remaining, len(TAGS_FROM_SCRIPT))
    tags_from_script = random.sample(TAGS_FROM_SCRIPT, script_count)

    # 4. Combine and Shuffle
    combined = tags_from_json + tags_from_script
    random.shuffle(combined)

    return combined


def generate_truth():
    global generation_counter

    print(f"🚀 INITIALIZING GROUND TRUTH ENGINE...")
    print(f"📂 Project Root: {ROOT_DIR}")
    print(f"📂 Checkpoint Dir: {CKPT_DIR}")
    print(f"📂 Tags from JSON: {len(TAGS_FROM_JSON)} available")
    print(f"📂 Tags from Script: {len(TAGS_FROM_SCRIPT)} available")
    print(f"⏱️  Duration: {DURATION_SEC} seconds")
    print(f"\n🎵 Base Song: '{BASE_SONG['title']}'")
    print(f"♾️  Starting infinite generation loop...\n")

    if not (CKPT_DIR / "tokenizer.json").exists():
        print(f"❌ ERROR: tokenizer.json not found at {CKPT_DIR}")
        return

    pipe = HeartMuLaGenPipeline.from_pretrained(
        pretrained_path=str(CKPT_DIR),
        device=torch.device("cuda"),
        dtype={"mula": torch.bfloat16, "codec": torch.float32},
        version="IGNORE",
        lazy_load=True
    )

    engine_uid = f"HeartMuLa-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # INFINITE LOOP
    while True:
        generation_counter += 1
        gen_start = time.time()

        # --- UPDATED: Generate Filename with Timestamp ---
        # Format: YYYYMMDD_HHMMSS
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ID is now: generation_0001_20260206_120000
        safe_id = f"generation_{generation_counter:04d}_{timestamp_str}"
        song_title = f"Generation {generation_counter}"

        # Get Guaranteed 6 tags
        tag_list = get_random_mixed_tags()

        lyrics_input = BASE_SONG['lyrics']
        seed = random.randint(0, 2 ** 32 - 1)

        print(f"{'=' * 60}")
        print(f"🎬 Generation #{generation_counter}")
        print(f"   ID: {safe_id}")
        print(f"   Title: {song_title}")
        print(f"   Tags ({len(tag_list)}): {', '.join(tag_list)}")
        print(f"   Seed: {seed}")

        CAPTURED.clear()

        try:
            with torch.inference_mode():
                pipe(
                    inputs={"lyrics": lyrics_input, "tags": ', '.join(tag_list)},
                    max_audio_length_ms=DURATION_SEC * 1000,
                    cfg_scale=1.5
                )

            if CAPTURED:
                # Save WAV file
                audio_np = CAPTURED[0].numpy()
                if audio_np.shape[0] < audio_np.shape[1]:
                    audio_np = audio_np.T

                # Define output path
                out_file = GT_DIR / f"{safe_id}.wav"

                # Write Audio
                scipy.io.wavfile.write(str(out_file), 48000, audio_np)

                # Create master ledger JSON with SHUFFLED tags saved
                master_ledger = {
                    "provenance": {
                        "id": safe_id,
                        "title": song_title,
                        "timestamp": datetime.now().isoformat(),
                        "engine_uid": engine_uid,
                        "project_root": str(ROOT_DIR)
                    },
                    "configuration": {
                        "seed": seed,
                        "cfg_scale": 1.5,
                        "temperature": 1.0,
                        "duration_sec": DURATION_SEC,
                        "input_prompt": {
                            "tags": tag_list,  # EXACT tags used
                            "lyrics": lyrics_input
                        }
                    },
                    "automated_metrics": {
                        "lyric_accuracy_score": None,
                        "raw_transcript": None,
                        "audit_status": "PENDING",
                        "generation_time_sec": round(time.time() - gen_start, 2)
                    },
                    "human_evaluation": {
                        "overall_score": None,
                        "prompt_tag_adherence": {},
                        "discovery_tags": {},
                        "qualitative_notes": "",
                        "status": "NOT_EVALUATED"
                    },
                    "status": "PRODUCED_AWAITING_AUDIT"
                }

                # Save JSON metadata (matching the wav filename)
                json_file = out_file.with_suffix('.json')
                with open(json_file, 'w') as f:
                    json.dump(master_ledger, f, indent=4)

                print(f"   ✅ Saved WAV: {out_file}")
                print(f"   ✅ Saved JSON: {json_file}")
                print(f"   ⏱️  Generation time: {master_ledger['automated_metrics']['generation_time_sec']}s")

            # Clean up memory
            torch.cuda.empty_cache()
            gc.collect()

        except KeyboardInterrupt:
            print("\n\n⛔ Generation stopped by user (Ctrl+C)")
            break
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue


if __name__ == "__main__":
    generate_truth()