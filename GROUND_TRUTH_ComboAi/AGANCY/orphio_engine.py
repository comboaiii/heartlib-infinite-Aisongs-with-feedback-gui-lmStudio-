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

# PyTorch 3.12 Patch
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
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()

    def _enforce_tag_schema(self, text):
        def replace_tag(match):
            return f"[{match.group(2).strip().upper()}]"

        return re.sub(r'(\*\*|__)?\[\s*(.*?)\s*\](\*\*|__)?', replace_tag, text)

    def generate_lyrics_stage(self, topic: str):
        self.log("🔗 Connecting to LM Studio...")
        ok, msg = self.lms.check_connection()
        if not ok: raise ConnectionError(msg)
        lyrics = self.lms.chat(conf.PROMPT_WRITER, f"Topic: {topic}")
        lyrics = self._enforce_tag_schema(lyrics)
        tags_raw = self.lms.chat(conf.PROMPT_TAGGER, lyrics, temp=0.3)
        tags_list = [t.strip().lower() for t in tags_raw.split(',') if t.strip()]
        return lyrics, tags_list

    def decorate_lyrics_stage(self, current_lyrics, tags_list):
        schema_key = conf.CURRENT_DECORATOR_SCHEMA
        prompt = conf.DECORATOR_SCHEMAS.get(schema_key, "")
        res = self.lms.chat(prompt, f"Lyrics:\n{current_lyrics}", temp=0.7)
        return self._enforce_tag_schema(res) if res else current_lyrics

    def render_audio_stage(self, topic: str, lyrics: str, tags: list, duration_s: int):
        start_time = time.time()

        # Verify paths before starting
        mula_dir = conf.CKPT_DIR / "HeartMuLa-oss-3B"
        if not mula_dir.exists():
            raise FileNotFoundError(f"OS Error 2: Model directory not found: {mula_dir}")

        self.log("🔊 Offloading LLM & Purging VRAM...")
        self.lms.unload_model()
        self.free_memory()
        time.sleep(conf.COOLFOOT_WAIT)

        if str(conf.SRC_DIR) not in sys.path:
            sys.path.append(str(conf.SRC_DIR))

        try:
            import heartlib.pipelines.music_generation as mg
            from heartlib import HeartMuLaGenPipeline

            # Match the exact patcher logic from GT_01
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

            self.log("🎹 Loading HeartMuLa (oss-3B)...")
            pipe = HeartMuLaGenPipeline.from_pretrained(
                pretrained_path=str(conf.CKPT_DIR),
                device=self.device,
                dtype={"mula": torch.bfloat16, "codec": torch.float32},
                version="IGNORE",
                lazy_load=True
            )

            seed = random.randint(0, 2 ** 32 - 1)
            torch.manual_seed(seed)
            self.log(f"🚀 Rendering {duration_s}s (Seed: {seed})...")

            with torch.inference_mode():
                pipe(
                    inputs={"lyrics": lyrics, "tags": ", ".join(tags)},
                    max_audio_length_ms=duration_s * 1000,
                    cfg_scale=1.5,
                    temperature=1.0
                )

            torchaudio.save = original_save
            del pipe
            self.free_memory()

            if not self.captured_audio: raise RuntimeError("Capture failed.")

            audio_np = self.captured_audio[0].numpy().squeeze()
            if audio_np.ndim > 1: audio_np = audio_np.T
            if np.abs(audio_np).max() > 0: audio_np = audio_np / np.abs(audio_np).max() * 0.9

            # Finalize
            ledger = MasterLedger.create_new(topic, lyrics, tags, seed, duration_s, time.time() - start_time,
                                             conf.ROOT_DIR)
            wav_path = conf.OUTPUT_DIR / f"{ledger.provenance.id}.wav"

            scipy.io.wavfile.write(str(wav_path), conf.SAMPLE_RATE, (audio_np * 32767).astype(np.int16))
            with open(wav_path.with_suffix('.json'), 'w') as f:
                f.write(ledger.model_dump_json(indent=4))

            return str(wav_path), ledger

        except Exception as e:
            self.log(f"❌ Error: {e}")
            raise e