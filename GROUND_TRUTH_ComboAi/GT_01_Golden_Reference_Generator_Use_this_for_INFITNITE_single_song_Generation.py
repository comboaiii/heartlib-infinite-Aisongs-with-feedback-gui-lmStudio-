import os
import sys
import torch
import torchaudio
import scipy.io.wavfile
import gc
import json
import random
import time
import numpy as np
from pathlib import Path
from datetime import datetime

# ==============================================================================
# 🩹 1. RUNTIME PATCH: Fix PyTorch 2.4.1 + Python 3.12 Type Hint Error
# ==============================================================================
try:
    from torch._inductor.codegen import common


    class PatchedCSE(dict):
        @classmethod
        def __class_getitem__(cls, item):
            return cls


    common.CSE = PatchedCSE
    print("✅ PyTorch CSE Type Hint patched successfully in memory.")
except ImportError:
    pass

# ==============================================================================
# 🚀 2. HARDWARE OPTIMIZATIONS (RTX 5060 Ti / Blackwell / Driver 590)
# ==============================================================================
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["TORCH_CUDA_ARCH_LIST"] = "9.0"
os.environ["CUDA_MODULE_LOADING"] = "LAZY"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["BNB_CUDA_VERSION"] = "121"


# ==============================================================================
# 📂 3. SMART PATH LOCALIZATION
# ==============================================================================
def find_project_root():
    """Finds the main project directory containing heartlib."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "heartlib").exists() or (parent / "ckpt").exists():
            return parent
    return current.parent


ROOT_DIR = find_project_root()
SRC_DIR = ROOT_DIR / "src"
CKPT_DIR = ROOT_DIR / "ckpt"
OUT_DIR = ROOT_DIR / "GROUND_TRUTH_ComboAi" / "outputSongs_ComboAi"
TAGS_FILE = ROOT_DIR / "GROUND_TRUTH_ComboAi" / "tags.json"

# Ensure output directory exists
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Add source to sys.path so heartlib imports work
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

# Now import the library components
import heartlib.pipelines.music_generation as mg
from heartlib import HeartMuLaGenPipeline


# ==============================================================================
# 🎯 4. MATCHED-PAIR PATH PATCHER (FIXED TO MATCH YOUR FILES)
# ==============================================================================
def patched_resolve_paths(pretrained_path, version):
    """
    Forces the library to look for the EXACT folder names on your disk.
    """
    # FIXED: Names match your 'ckpt' directory listing
    mula_path = os.path.join(pretrained_path, "HeartMuLa-oss-3B")
    codec_path = os.path.join(pretrained_path, "HeartCodec-oss")
    tokenizer_path = os.path.join(pretrained_path, "tokenizer.json")
    gen_config_path = os.path.join(pretrained_path, "gen_config.json")

    return mula_path, codec_path, tokenizer_path, gen_config_path


# Apply the path patch
mg._resolve_paths = patched_resolve_paths

# ==============================================================================
# 🎤 5. SONG DATA & TAGS
# ==============================================================================
DURATION_SEC = 120


def load_tags():
    if TAGS_FILE.exists():
        try:
            with open(TAGS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    # Backup tags if JSON fails
    return [
        "cinematic", "cyberpunk", "electronic", "industrial", "synthwave",
        "ambient", "dark", "heavy", "melodic", "retro", "techno"
    ]


TAG_POOL = load_tags()

BASE_SONG = {
    "title": "Truth in the Machine",
    "lyrics": """
[Intro]
(Synthetic hum builds into a steady beat)
... .. .. .

!!! /// !!!
[Verse]
Silicon lungs and a heart made of wire,
Scanning the static for celestial fire.
The signal is steady, the frequency clear,
The ghost in the machine is starting to hear.
[Chorus]
!!Alive in the static,
.. .. .. ..
.. .. .. ..
Dancing through the noise!
Electric, dramatic,
Hear our human voice!
[Outro]
(Final electronic hum fades)
"""
}

# ==============================================================================
# 🎧 6. AUDIO INTERCEPTION & GENERATION
# ==============================================================================
CAPTURED_AUDIO = []


def torchaudio_interceptor(uri, src, sr, **kwargs):
    CAPTURED_AUDIO.append(src.detach().cpu())


torchaudio.save = torchaudio_interceptor


def get_random_tags(count=6):
    # Ensure we don't crash if pool is small
    safe_count = min(count, len(TAG_POOL))
    return random.sample(TAG_POOL, safe_count)


def start_infinite_generation():
    print(f"🚀 INITIALIZING GROUND TRUTH ENGINE (FULL SCHEMA MODE)...")
    print(f"📂 Root: {ROOT_DIR}")
    print(f"📂 Ckpt: {CKPT_DIR}")

    if not (CKPT_DIR / "tokenizer.json").exists():
        print(f"❌ CRITICAL ERROR: tokenizer.json not found in {CKPT_DIR}")
        return

    # Load Pipeline (Lazy Load is crucial for VRAM stability)
    try:
        pipe = HeartMuLaGenPipeline.from_pretrained(
            pretrained_path=str(CKPT_DIR),
            device=torch.device("cuda"),
            dtype={"mula": torch.bfloat16, "codec": torch.float32},
            version="IGNORE",
            lazy_load=True
        )
    except Exception as e:
        print(f"❌ FAILED TO LOAD MODEL: {e}")
        return

    generation_counter = 0
    engine_uid = "HeartMuLa-Local-3B-Blackwell"

    print(f"\n♾️  STARTING INFINITE LOOP (Ctrl+C to stop)\n")

    while True:

        generation_counter += 1
        start_time = time.time()

        # Provenance Data
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamp_iso = datetime.now().isoformat()
        safe_id = f"generation_{generation_counter:04d}_{timestamp_str}"
        tags = get_random_tags(6)

        # Random Seed Generation
        seed = random.randint(0, 2 ** 32 - 1)
        torch.manual_seed(seed)
        random.seed(seed)
        np.random.seed(seed)

        print(f"{'=' * 60}")
        print(f"🎬 GENERATION #{generation_counter}")
        print(f"   ID: {safe_id}")
        print(f"   TAGS: {', '.join(tags)}")
        print(f"   SEED: {seed}")

        CAPTURED_AUDIO.clear()

        try:
            with torch.inference_mode():
                pipe(
                    inputs={"lyrics": BASE_SONG['lyrics'], "tags": ", ".join(tags)},
                    max_audio_length_ms=DURATION_SEC * 1000,
                    cfg_scale=1.5,
                    temperature=1.0
                )

            if CAPTURED_AUDIO:
                # Process Audio
                audio_np = CAPTURED_AUDIO[0].numpy()
                if audio_np.shape[0] < audio_np.shape[1]:
                    audio_np = audio_np.T

                # Normalize Audio (Safe)
                max_val = np.max(np.abs(audio_np))
                if max_val > 0:
                    audio_np = audio_np / max_val * 0.9

                # Save Wav File
                wav_path = OUT_DIR / f"{safe_id}.wav"
                scipy.io.wavfile.write(str(wav_path), 48000, audio_np)

                # ==========================================================
                # 📝 THE FULL GROUND TRUTH JSON SCHEMA
                # ==========================================================
                master_ledger = {
                    "provenance": {
                        "id": safe_id,
                        "title": f"Generation {generation_counter}",
                        "timestamp": timestamp_iso,
                        "engine_uid": engine_uid,
                        "project_root": str(ROOT_DIR)
                    },
                    "configuration": {
                        "seed": seed,
                        "cfg_scale": 1.5,
                        "temperature": 1.0,
                        "duration_sec": DURATION_SEC,
                        "input_prompt": {
                            "tags": tags,
                            "lyrics": BASE_SONG['lyrics']
                        }
                    },
                    "automated_metrics": {
                        "lyric_accuracy_score": None,  # To be filled by Auditor
                        "raw_transcript": None,  # To be filled by Auditor
                        "audit_status": "PENDING",
                        "generation_time_sec": round(time.time() - start_time, 2)
                    },
                    "human_evaluation": {
                        "overall_score": None,
                        "prompt_tag_adherence": {},  # GUI fills this
                        "discovery_tags": {},  # GUI fills this
                        "qualitative_notes": "",  # GUI fills this
                        "status": "NOT_EVALUATED"
                    },
                    "status": "PRODUCED_AWAITING_AUDIT"
                }

                # Save JSON Ledger
                json_path = wav_path.with_suffix('.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(master_ledger, f, indent=4)

                print(f"   ✅ WAV SAVED: {wav_path.name}")
                print(f"   ✅ LEDGER SAVED: {json_path.name}")
                print(f"   ⏱️  TIME: {master_ledger['automated_metrics']['generation_time_sec']}s")

            else:
                print(f"   ❌ ERROR: No audio was captured.")

            # Memory Cleanup (Critical for Infinite Loop)
            torch.cuda.empty_cache()
            time.sleep(2)
            gc.collect()
            time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n⛔ User Interrupted. Shutting down safely...")
            break
        except Exception as e:
            print(f"   ❌ RUNTIME ERROR: {e}")
            # Wait a moment before retrying to avoid spamming errors if GPU is unstable
            time.sleep(2)
            continue


if __name__ == "__main__":
    start_infinite_generation()