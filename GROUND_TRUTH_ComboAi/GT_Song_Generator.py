
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
# ⚙️ SYSTEM SETTINGS & SMART PATHS
# =========================================================================
init(autoreset=True)
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


def find_project_root():
    curr = Path(__file__).resolve()
    for parent in [curr] + list(curr.parents):
        if (parent / "heartlib").exists():
            return parent
    return curr.parent


ROOT_DIR = find_project_root()
SRC_DIR = ROOT_DIR / "heartlib" / "src"
CKPT_DIR = ROOT_DIR / "heartlib" / "ckpt"

# Output directory logic
OUT_DIR = ROOT_DIR / "outputSongs_ComboAi"
OUT_DIR.mkdir(parents=True, exist_ok=True)

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

import heartlib.pipelines.music_generation as mg
from heartlib import HeartMuLaGenPipeline


# =========================================================================
# 🎯 MATCHED-PAIR PATCHER
# =========================================================================
def apply_matched_patch(mode="RL"):
    if mode == "RL":
        mula_name, codec_name = "HeartMuLa-RL-oss-3B-20260123", "HeartCodec-oss-20260123"
        engine_uid = "HEARTMULA_RL_v2026_01"
    else:
        mula_name, codec_name = "HeartMuLa-oss-3B", "HeartCodec-oss"
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
        torch.cuda.ipc_collect()


def slugify(text):
    """Convert title to a filesystem-safe string."""
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
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════════════════════════╗")
    print(
        f"{Fore.CYAN}║ {Fore.WHITE}{Style.BRIGHT}   🎹 ORPHIO GROUND TRUTH: LEDGER v6.2 (SCHEMA FIXED)    {Fore.CYAN}║")
    print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════════╝")

    # --- 1. CONFIGURATION ---
    song_title = input(f"\n{Fore.GREEN} SONG TITLE: ") or "Untitled_Reference"

    mode_choice = input(f"{Fore.YELLOW} ENGINE: [1] RL Mode / [2] Normal: ") or "1"
    mode = "RL" if mode_choice == "1" else "NORMAL"
    engine_uid = apply_matched_patch(mode)

    raw_tags = input(" PROMPT TAGS (comma-sep): ") or "pop, warm, strings"
    tag_list = [t.strip() for t in raw_tags.split(',') if t.strip()]
    duration_sec = int(input(" DURATION (sec) [30]: ") or 30)

    seed = random.randint(0, 2 ** 32 - 1)
    user_seed = input(f" SEED (Default {seed}): ")
    if user_seed.strip(): seed = int(user_seed)

    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)

    lyrics_input = input("\n Enter Lyrics (Leave for default): ")
    if not lyrics_input.strip():
        lyrics_input = """[Intro]
    (Atmospheric synth pulse with a steady drum build)
    [Verse]
    Silicon lungs and a heart made of wire,
    Scanning the static for celestial fire.
    The signal is steady, the frequency clear,
    The ghost in the machine is starting to hear.
    [Chorus]
    Oh, Orphio, rise from the code,
    Carry the weight of the digital load.
    Found in the silence, lost in the sound,
    Where the ground truth is finally found.
    [Outro]
    (Final electronic hum fades)"""

    # --- 2. GENERATION PHASE ---
    print(f"\n{Fore.MAGENTA}🎹 PHASE 1: GENERATION...")
    nuclear_cleanup()
    gen_start = time.time()

    try:
        pipe = HeartMuLaGenPipeline.from_pretrained(
            pretrained_path=str(CKPT_DIR), device=torch.device("cuda"),
            dtype={"mula": torch.bfloat16, "codec": torch.float32},
            version="IGNORE", lazy_load=True
        )

        CAPTURED_AUDIO.clear()
        with torch.inference_mode():
            pipe(inputs={"lyrics": lyrics_input, "tags": raw_tags},
                 max_audio_length_ms=duration_sec * 1000, cfg_scale=1.5, temperature=1.0)

        if not CAPTURED_AUDIO: raise Exception("Audio Failed.")

        audio_np = CAPTURED_AUDIO[0].numpy()
        if audio_np.shape[0] < audio_np.shape[1]: audio_np = audio_np.T
        audio_np = (audio_np / np.max(np.abs(audio_np)) * 0.9) if np.max(np.abs(audio_np)) > 0 else audio_np

        # Standardized naming: Title + Seed
        timestamp = datetime.now().strftime("%H%M")
        safe_title = slugify(song_title)
        safe_id = f"{safe_title}_{seed}"

        wav_path = OUT_DIR / f"{safe_id}.wav"
        scipy.io.wavfile.write(str(wav_path), 48000, audio_np)

        print(f"\n{Fore.GREEN}✅ AUDIO SAVED: {wav_path.name}")
        del pipe
        nuclear_cleanup()

        # --- 3. SMART EVALUATION ---
        print(f"\n{Back.WHITE}{Fore.BLACK} PHASE 2: HUMAN EVALUATION (Press Ctrl+C to skip/save) ")

        overall_score = 0
        tag_scores = {tag: 0 for tag in tag_list}
        discovery_tags = {}  # CHANGED: Now a Dictionary
        notes = "Auto-saved (Evaluator skipped)"
        eval_status = "SKIPPED_BY_USER"

        try:
            overall_score = int(input(" OVERALL QUALITY (1-10): ") or 5)

            print(f"\n{Fore.YELLOW}TAG ADHERENCE (-2 to +2):")
            for tag in tag_list:
                val = input(f"   [{tag}]: ").strip()
                tag_scores[tag] = int(val) if val in ['-2', '-1', '0', '1', '2'] else 0

            discovery_input = input("\n DISCOVERY TAGS (What you heard): ")
            # SCHEMA FIX: Convert list to dict with default score of 1
            raw_disc_list = [t.strip() for t in discovery_input.split(',') if t.strip()]
            discovery_tags = {tag: 1 for tag in raw_disc_list}

            notes = input("\n NOTES: ") or "Standard generation."
            eval_status = "VALIDATED"

        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}⚠️  EVALUATION INTERRUPTED. Saving available data and exiting...")

        # --- 4. THE INJECTION-READY SCHEMA ---
        master_ledger = {
            "provenance": {
                "id": safe_id,
                "title": song_title,
                "timestamp": datetime.now().isoformat(),
                "engine_uid": engine_uid,
                "project_root": str(ROOT_DIR)
            },
            "configuration": {
                "seed": seed, "cfg_scale": 1.5, "temperature": 1.0,
                "duration_sec": duration_sec,
                "input_prompt": {"tags": tag_list, "lyrics": lyrics_input}
            },
            "automated_metrics": {
                "lyric_accuracy_score": None,
                "raw_transcript": None,
                "audit_status": "PENDING",
                "generation_time_sec": round(time.time() - gen_start, 2)
            },
            "human_evaluation": {
                "overall_score": overall_score,
                "prompt_tag_adherence": tag_scores,
                "discovery_tags": discovery_tags,  # SAVES AS DICT
                "qualitative_notes": notes,
                "status": eval_status
            },
            "status": "PRODUCED_AWAITING_AUDIT"
        }

        with open(wav_path.with_suffix('.json'), 'w', encoding='utf-8') as f:
            json.dump(master_ledger, f, indent=4)

        print(f"{Fore.GREEN}✅ LEDGER SAVED: {wav_path.with_suffix('.json').name}")

    except Exception as e:
        print(f"{Fore.RED}❌ ERROR: {e}")


if __name__ == "__main__":
    main()