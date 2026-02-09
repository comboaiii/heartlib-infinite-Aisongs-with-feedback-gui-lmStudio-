# === AUTO-PATCHED: DLL Fix Import (DO NOT REMOVE) ===
try:
    import windows_dll_fix
except ImportError:
    import os, sys
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    if sys.platform == "win32":
        try: 
            os.add_dll_directory(r"C:\Windows\System32")
        except: 
            pass
# === END AUTO-PATCH ===

# AGANCY/orphio_engine.py
import sys
import time
import torch
import gc
import re
import os
import random
import numpy as np
import scipy.io.wavfile
import torchaudio
from pathlib import Path

from orphio_config import conf
from lmstudio_controler import LMStudioController
from orphio_schema import MasterLedger

# ==============================================================================
# 🩹 RUNTIME PATCH: Fix PyTorch 2.4.1 + Python 3.12 Type Hint Error
# ==============================================================================
try:
    from torch._inductor.codegen import common


    class PatchedCSE(dict):
        @classmethod
        def __class_getitem__(cls, item): return cls


    common.CSE = PatchedCSE
except ImportError:
    pass


class OrphioEngine:
    def __init__(self, log_callback=print):
        self.log = log_callback
        self.lms = LMStudioController(conf.LM_STUDIO_URL)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.captured_audio = []

    def free_memory(self):
        """Clears GPU cache and forces garbage collection."""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()

    def _enforce_tag_schema(self, text):
        """Removes LLM bolding (**[INTRO]**) and forces uppercase tags."""

        def replace_tag(match):
            content = match.group(2).strip().upper()
            return f"[{content}]"

        return re.sub(r'(\*\*|__)?\[\s*(.*?)\s*\](\*\*|__)?', replace_tag, text)

    def _clean_tags_list(self, raw_tags):
        """
        Smart Scrubber: Enforces 8-Pillar Priority.
        """
        text = raw_tags.replace('**', '').replace('__', '').replace('*', '')
        parts = re.split(r'[\n,;\t•]', text)

        # Define the High-Priority Anchors manually
        known_genres = ["pop", "rock", "electronic", "hiphop", "jazz", "classical", "techno", "trance", "ambient",
                        "folk", "country"]

        found_anchors = []
        other_tags = []

        for p in parts:
            p = re.sub(r'^\d+[\.\)]\s*', '', p.strip())
            if ':' in p: p = p.split(':')[0]
            clean_tag = p.strip().lower()

            if not clean_tag or len(clean_tag) < 2: continue

            # Sort into Anchor vs Seasoning
            if clean_tag in known_genres:
                found_anchors.append(clean_tag)
            else:
                other_tags.append(clean_tag)

        # Remove duplicates while preserving order
        found_anchors = list(dict.fromkeys(found_anchors))
        other_tags = list(dict.fromkeys(other_tags))

        # REASSEMBLE: Anchors FIRST (Crucial for HeartMuLa stability)
        # Limit to 1 Anchor (to avoid conflict) + 5 Seasoning tags
        final_tags = found_anchors[:1] + other_tags

        # Ensure we don't exceed 6 tags total (Prompting Strategy: "Less is More")
        return final_tags[:6] if final_tags else ["melodic", "electronic"]

    def generate_lyrics_stage(self, topic: str):
        self.log("🔗 Connecting to LM Studio...")
        ok, msg = self.lms.check_connection()
        if not ok: raise ConnectionError(msg)
        lyrics = self.lms.chat(conf.PROMPT_WRITER, f"Topic: {topic}")
        lyrics = self._enforce_tag_schema(lyrics)
        tags_raw = self.lms.chat(conf.PROMPT_TAGGER, lyrics, temp=0.2)
        tags_list = self._clean_tags_list(tags_raw)
        return lyrics, tags_list

    def decorate_lyrics_stage(self, current_lyrics, tags_list):
        schema_key = conf.CURRENT_DECORATOR_SCHEMA

        # --- FIXED LOGIC HERE ---
        # 1. Try to get the specific requested schema
        # 2. If not found, default to 'vocal_dynamics'
        # 3. If that fails, just take the first one in the dictionary
        decorator_prompt = conf.DECORATOR_SCHEMAS.get(
            schema_key,
            conf.DECORATOR_SCHEMAS.get("vocal_dynamics", next(iter(conf.DECORATOR_SCHEMAS.values())))
        )

        user_prompt = f"Style: {', '.join(tags_list)}\n\nLyrics:\n{current_lyrics}"
        decorated_text = self.lms.chat(decorator_prompt, user_prompt, temp=0.7)
        return self._enforce_tag_schema(decorated_text) if decorated_text else current_lyrics

    def render_audio_stage(self, topic: str, lyrics: str, tags: list, duration_s: int, cfg: float, temp: float):
        start_time = time.time()
        self.log(f"🔊 Offloading LLM... Duration: {duration_s}s, CFG: {cfg}")
        self.lms.unload_model()
        self.free_memory()
        time.sleep(conf.COOLFOOT_WAIT)

        if str(conf.SRC_DIR) not in sys.path:
            sys.path.append(str(conf.SRC_DIR))

        try:
            import heartlib.pipelines.music_generation as mg
            from heartlib import HeartMuLaGenPipeline

            def patched_resolve_paths(pretrained_path, version):
                return (
                    str(conf.CKPT_DIR / "HeartMuLa-oss-3B"),
                    str(conf.CKPT_DIR / "HeartCodec-oss"),
                    str(conf.CKPT_DIR / "tokenizer.json"),
                    str(conf.CKPT_DIR / "gen_config.json")
                )

            mg._resolve_paths = patched_resolve_paths

            def _interceptor(uri, src, sr, **kwargs):
                self.captured_audio.append(src.detach().cpu())

            original_save = torchaudio.save
            torchaudio.save = _interceptor
            self.captured_audio = []

            pipeline = HeartMuLaGenPipeline.from_pretrained(
                pretrained_path=str(conf.CKPT_DIR),
                device=self.device,
                dtype={"mula": torch.bfloat16, "codec": torch.float32},
                version="IGNORE",
                lazy_load=True
            )

            seed = random.randint(0, 2 ** 32 - 1)
            torch.manual_seed(seed)
            self.log(f"🚀 Rendering Audio (Seed: {seed})...")

            with torch.inference_mode():
                pipeline(
                    inputs={"lyrics": lyrics, "tags": ", ".join(tags)},
                    max_audio_length_ms=duration_s * 1000,
                    cfg_scale=cfg,
                    temperature=temp
                )

            torchaudio.save = original_save
            del pipeline
            self.free_memory()

            if not self.captured_audio:
                raise RuntimeError("Audio pipeline finished but no audio was captured.")

            # --- FIXED BROADCASTING LOGIC ---
            audio_np = self.captured_audio[0].numpy().squeeze()

            # Ensure shape is (Samples, Channels) for consistent processing
            if audio_np.ndim == 2 and audio_np.shape[0] < audio_np.shape[1]:
                audio_np = audio_np.T

            # Normalize
            if np.abs(audio_np).max() > 0:
                audio_np = audio_np / np.abs(audio_np).max() * 0.9

            # Apply Fade Out (Safe for Stereo/Mono)
            fade_len = int(conf.FADE_OUT_DURATION * conf.SAMPLE_RATE)
            if fade_len < len(audio_np):
                fade_ramp = np.linspace(1.0, 0.0, fade_len)
                # If audio is stereo (N, 2), expand ramp to (N, 1) so it broadcasts
                if audio_np.ndim == 2:
                    fade_ramp = fade_ramp[:, np.newaxis]
                audio_np[-fade_len:] *= fade_ramp

            # Ledger
            ledger = MasterLedger.create_new(topic, lyrics, tags, seed, duration_s, time.time() - start_time,
                                             conf.ROOT_DIR)
            wav_path = conf.OUTPUT_DIR / f"{ledger.provenance.id}.wav"

            # Save
            scipy.io.wavfile.write(str(wav_path), conf.SAMPLE_RATE, (audio_np * 32767).astype(np.int16))
            with open(wav_path.with_suffix('.json'), 'w') as f:
                f.write(ledger.model_dump_json(indent=4))

            return str(wav_path), ledger

        except Exception as e:
            self.log(f"❌ Error: {e}")
            raise e