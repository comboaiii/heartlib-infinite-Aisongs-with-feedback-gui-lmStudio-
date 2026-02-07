import os
import sys
import torch
import torchaudio
import scipy.io.wavfile
import gc
import time
import json
import random
import re
import numpy as np
from datetime import datetime
from pathlib import Path
from colorama import Fore, Style, init, Back

# =========================================================================
# ⚙️ SYSTEM SETTINGS & SMART PATHS (MATCHED TO WORKING SCRIPT A)
# =========================================================================
init(autoreset=True)
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["CUDA_MODULE_LOADING"] = "LAZY"


def find_project_root():
    """Finds the root folder containing the 'ckpt' directory."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "ckpt").exists():
            return parent
    return current.parent


ROOT_DIR = find_project_root()
# Match Script A's source path
SRC_DIR = ROOT_DIR / "src"
CKPT_DIR = ROOT_DIR / "ckpt"
OUT_DIR = ROOT_DIR / "outputSongs_ComboAi"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Add source to path
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

# --- DIAGNOSTIC CHECK ---
print(f"{Fore.CYAN}🔍 DIAGNOSING PATHS...")
print(f"   Root: {ROOT_DIR}")
print(f"   Ckpt: {CKPT_DIR}")

required_files = ["tokenizer.json", "gen_config.json", "HeartMuLa-oss-3B", "HeartCodec-oss"]
missing = []
for f in required_files:
    fpath = CKPT_DIR / f
    if not fpath.exists():
        missing.append(f)
    else:
        print(f"   ✅ Found: {f}")

if missing:
    print(f"{Fore.RED}❌ CRITICAL ERROR: The following files are missing in {CKPT_DIR}:")
    for m in missing: print(f"      - {m}")
    print(f"{Fore.YELLOW}Check if your 'ckpt' folder is actually inside a 'heartlib' folder or at the root.")
    sys.exit(1)

# Now import the library components
import heartlib.pipelines.music_generation as mg
from heartlib import HeartMuLaGenPipeline


# =========================================================================
# 🎯 MATCHED-PAIR PATCHER (EXACT MATCH TO SCRIPT A)
# =========================================================================
def apply_matched_patch(mode="NORMAL"):
    # If mode is RL, we change the folder names.
    # If these folders don't exist, it WILL throw OS Error 2.
    if mode == "RL":
        mula_name = "HeartMuLa-RL-oss-3B-20260123"
        codec_name = "HeartCodec-oss-20260123"
        engine_uid = "HEARTMULA_RL_v2026_01"
    else:
        mula_name = "HeartMuLa-oss-3B"
        codec_name = "HeartCodec-oss"
        engine_uid = "HEARTMULA_STD_v3B"

    def _patch(pretrained_path, version):
        return (os.path.join(pretrained_path, mula_name),
                os.path.join(pretrained_path, codec_name),
                os.path.join(pretrained_path, "tokenizer.json"),
                os.path.join(pretrained_path, "gen_config.json"))

    mg._resolve_paths = _patch
    return engine_uid


def nuclear_cleanup():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def slugify(text):
    return re.sub(r'[\W_]+', '_', text).strip('_')


# =========================================================================
# 🎧 AUDIO INTERCEPTOR
# =========================================================================
CAPTURED_AUDIO = []


def save_interceptor(uri, src, sr, **kwargs):
    CAPTURED_AUDIO.append(src.detach().cpu())


torchaudio.save = save_interceptor


# =========================================================================
# 🚀 MAIN PRODUCTION
# =========================================================================
def main():
    print(f"\n{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════════════════════════╗")
    print(f"{Fore.CYAN}║ {Fore.WHITE}{Style.BRIGHT}   🎹 ORPHIO GROUND TRUTH: LEDGER v6.2 (FIXED)         {Fore.CYAN}║")
    print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════════╝")

    # --- 1. CONFIGURATION ---
    song_title = input(f"\n{Fore.GREEN} SONG TITLE: ") or "Untitled_Reference"

    print(f"{Fore.YELLOW} [1] RL Mode (Requires RL folders) | [2] Normal (Confirmed Working)")
    mode_choice = input(f" SELECT ENGINE [2]: ") or "2"
    mode = "RL" if mode_choice == "1" else "NORMAL"
    engine_uid = apply_matched_patch(mode)

    raw_tags = input(" PROMPT TAGS: ") or "pop, warm, strings"
    tag_list = [t.strip() for t in raw_tags.split(',') if t.strip()]
    duration_sec = int(input(" DURATION (sec) [30]: ") or 30)
    seed = random.randint(0, 2 ** 32 - 1)

    lyrics_input = input("\n Enter Lyrics (Leave empty for default): ")
    if not lyrics_input.strip():
        lyrics_input = "[Intro]\n(Synth pulse)\n[Verse]\nSilicon lungs...\n[Chorus]\nOrphio rise!\n[Outro]\n(Fade)"

    # --- 2. GENERATION PHASE ---
    print(f"\n{Fore.MAGENTA}🎹 PHASE 1: GENERATION (Wait for model load)...")
    nuclear_cleanup()
    gen_start = time.time()

    try:
        pipe = HeartMuLaGenPipeline.from_pretrained(
            pretrained_path=str(CKPT_DIR),
            device=torch.device("cuda"),
            dtype={"mula": torch.bfloat16, "codec": torch.float32},
            version="IGNORE",
            lazy_load=True
        )

        CAPTURED_AUDIO.clear()
        torch.manual_seed(seed)

        with torch.inference_mode():
            pipe(inputs={"lyrics": lyrics_input, "tags": raw_tags},
                 max_audio_length_ms=duration_sec * 1000,
                 cfg_scale=1.5,
                 temperature=1.0)

        if not CAPTURED_AUDIO: raise Exception("Pipeline finished but no audio was captured.")

        audio_np = CAPTURED_AUDIO[0].numpy()
        if audio_np.shape[0] < audio_np.shape[1]: audio_np = audio_np.T
        max_val = np.max(np.abs(audio_np))
        if max_val > 0: audio_np = audio_np / max_val * 0.9

        safe_id = f"{slugify(song_title)}_{seed}"
        wav_path = OUT_DIR / f"{safe_id}.wav"
        scipy.io.wavfile.write(str(wav_path), 48000, audio_np)

        print(f"\n{Fore.GREEN}✅ AUDIO SAVED: {wav_path.name}")

        # --- 3. EVALUATION & LEDGER ---
        print(f"\n{Back.WHITE}{Fore.BLACK} PHASE 2: EVALUATION ")
        # (Simplified for brevity, matches your schema)
        overall_score = input(" OVERALL QUALITY (1-10): ") or "5"
        notes = input(" NOTES: ") or "Standard generation."

        master_ledger = {
            "provenance": {"id": safe_id, "title": song_title, "timestamp": datetime.now().isoformat(),
                           "engine_uid": engine_uid},
            "configuration": {"seed": seed, "duration_sec": duration_sec,
                              "input_prompt": {"tags": tag_list, "lyrics": lyrics_input}},
            "automated_metrics": {"generation_time_sec": round(time.time() - gen_start, 2), "audit_status": "PENDING"},
            "human_evaluation": {"overall_score": int(overall_score), "qualitative_notes": notes,
                                 "status": "VALIDATED"},
            "status": "PRODUCED_AWAITING_AUDIT"
        }

        with open(wav_path.with_suffix('.json'), 'w', encoding='utf-8') as f:
            json.dump(master_ledger, f, indent=4)
        print(f"{Fore.GREEN}✅ LEDGER SAVED.")

    except Exception as e:
        print(f"{Fore.RED}❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()