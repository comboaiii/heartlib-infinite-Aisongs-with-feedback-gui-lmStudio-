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
        Aggressive Tag Scrubber: Converts LLM paragraphs/bullet points
        into a clean list of musical genre words for the ledger.
        """
        # Remove markdown bolding/italics
        text = raw_tags.replace('**', '').replace('__', '').replace('*', '')
        # Split by common delimiters
        parts = re.split(r'[\n,;\t•]', text)

        cleaned = []
        for p in parts:
            # Remove numbering (1., 2.)
            p = re.sub(r'^\d+[\.\)]\s*', '', p.strip())
            # If the LLM wrote "Genre: description", take only the genre
            if ':' in p: p = p.split(':')[0]

            p = p.strip().lower()
            # Valid tags are short (1-3 words) and not sentences
            if p and len(p.split()) <= 3 and len(p) < 35:
                cleaned.append(p)

        # Deduplicate and limit to top 6 tags
        final_tags = list(dict.fromkeys(cleaned))[:6]
        return final_tags if final_tags else ["melodic", "electronic"]

    # --- 1. LYRIC DRAFTING ---
    def generate_lyrics_stage(self, topic: str):
        self.log("🔗 Connecting to LM Studio...")
        ok, msg = self.lms.check_connection()
        if not ok: raise ConnectionError(msg)

        self.log(f"📝 Drafting Lyrics for: {topic}...")
        lyrics = self.lms.chat(conf.PROMPT_WRITER, f"Topic: {topic}")
        lyrics = self._enforce_tag_schema(lyrics)

        self.log("🏷️ Scrubbing Metadata Tags...")
        tags_raw = self.lms.chat(conf.PROMPT_TAGGER, lyrics, temp=0.2)
        tags_list = self._clean_tags_list(tags_raw)

        self.log(f"✅ Extracted: {', '.join(tags_list)}")
        return lyrics, tags_list

    # --- 2. SONIC ARCHITECTURE ---
    def decorate_lyrics_stage(self, current_lyrics, tags_list):
        schema_key = conf.CURRENT_DECORATOR_SCHEMA
        decorator_prompt = conf.DECORATOR_SCHEMAS.get(schema_key, conf.DECORATOR_SCHEMAS["inner_sonic"])

        self.log(f"🎨 Applying Decorator: {schema_key.upper()}")
        style_str = ", ".join(tags_list)
        user_prompt = f"Style: {style_str}\n\nLyrics:\n{current_lyrics}\n\nAction: Apply tokens."

        decorated_text = self.lms.chat(decorator_prompt, user_prompt, temp=0.7)
        if not decorated_text or len(decorated_text) < 10:
            return current_lyrics

        return self._enforce_tag_schema(decorated_text)

    # --- 3. AUDIO RENDERING ---
    def render_audio_stage(self, topic: str, lyrics: str, tags: list, duration_s: int, cfg: float, temp: float):
        start_time = time.time()

        self.log(f"🔊 Offloading LLM... Target: {duration_s}s, CFG: {cfg}, Temp: {temp}")
        # Unload model from LM Studio to free VRAM for HeartMuLa
        self.lms.unload_model()
        self.free_memory()
        time.sleep(conf.COOLFOOT_WAIT)

        # Inject Heartlib path
        if str(conf.SRC_DIR) not in sys.path:
            sys.path.append(str(conf.SRC_DIR))

        try:
            import heartlib.pipelines.music_generation as mg
            from heartlib import HeartMuLaGenPipeline

            # 🎯 MANDATORY MATCHED-PAIR PATH PATCHER
            def patched_resolve_paths(pretrained_path, version):
                return (
                    str(conf.CKPT_DIR / "HeartMuLa-oss-3B"),
                    str(conf.CKPT_DIR / "HeartCodec-oss"),
                    str(conf.CKPT_DIR / "tokenizer.json"),
                    str(conf.CKPT_DIR / "gen_config.json")
                )

            mg._resolve_paths = patched_resolve_paths

            # 🎧 TORCHAUDIO INTERCEPTOR
            def _interceptor(uri, src, sr, **kwargs):
                self.captured_audio.append(src.detach().cpu())

            original_save = torchaudio.save
            torchaudio.save = _interceptor
            self.captured_audio = []

            self.log("🎹 Loading HeartMuLa (oss-3B)...")
            pipeline = HeartMuLaGenPipeline.from_pretrained(
                pretrained_path=str(conf.CKPT_DIR),
                device=self.device,
                dtype={"mula": torch.bfloat16, "codec": torch.float32},
                version="IGNORE",  # Mandatory positional argument
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

            # Cleanup
            torchaudio.save = original_save
            del pipeline
            self.free_memory()

            if not self.captured_audio:
                raise RuntimeError("Audio pipeline finished but no audio was captured.")

            # Processing
            audio_np = self.captured_audio[0].numpy().squeeze()
            if audio_np.ndim > 1: audio_np = audio_np.T  # Ensure correct orientation

            # Normalize to -1db
            if np.abs(audio_np).max() > 0:
                audio_np = audio_np / np.abs(audio_np).max() * 0.9

            # Apply Fade Out
            fade_len = int(conf.FADE_OUT_DURATION * conf.SAMPLE_RATE)
            if fade_len < len(audio_np):
                audio_np[-fade_len:] *= np.linspace(1.0, 0.0, fade_len)

            # Master Ledger Generation
            gen_time = time.time() - start_time
            ledger = MasterLedger.create_new(
                topic=topic,
                lyrics=lyrics,
                tags=tags,
                seed=seed,
                duration=duration_s,
                gen_time=gen_time,
                root_path=conf.ROOT_DIR
            )

            wav_path = conf.OUTPUT_DIR / f"{ledger.provenance.id}.wav"
            json_path = conf.OUTPUT_DIR / f"{ledger.provenance.id}.json"

            # Save Files
            scipy.io.wavfile.write(str(wav_path), conf.SAMPLE_RATE, (audio_np * 32767).astype(np.int16))
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(ledger.model_dump_json(indent=4))

            return str(wav_path), ledger

        except Exception as e:
            self.log(f"❌ Render Engine Error: {e}")
            raise e