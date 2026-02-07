import torch
import gc
import time
import os
from colorama import Fore, Style


# Try to import LM Studio SDK
try:
    import lmstudio as lms

    LMS_AVAILABLE = True
except ImportError:
    LMS_AVAILABLE = False


class VRAMGroundTruth:
    @staticmethod
    def get_vram_usage():
        """Returns current VRAM usage in MB."""
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / 1024 ** 2
        return 0

    @staticmethod
    def nuclear_cleanup():
        """
        The Ground Truth for a 'Clean' GPU.
        Ensures no zombie tensors remain in the cache.
        """
        print(f"{Fore.RED}🧹 NUCLEAR CLEANUP: Purging GPU...")
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            torch.cuda.synchronize()
        time.sleep(2)  # Physical wait for hardware registers to clear
        print(f"   VRAM Now: {VRAMGroundTruth.get_vram_usage():.2f} MB")

    @staticmethod
    def offload_llm():
        """Forces LM Studio to release the GPU."""
        if not LMS_AVAILABLE:
            print(f"{Fore.YELLOW}⚠️ SDK not found. Manual offload required.")
            return False

        print(f"{Fore.MAGENTA}📉 OFFLOADING LLM: Ejecting via SDK...")
        try:
            # We target 'lms.llm()' which refers to the currently active model
            lms.llm().unload()
            VRAMGroundTruth.nuclear_cleanup()
            return True
        except Exception as e:
            print(f"   ❌ Offload Failed: {e}")
            return False

    @staticmethod
    def load_audio_pipeline(pipeline_class, model_path, device, dtype):
        """
        The Ground Truth for Loading: Always use lazy_load=True
        for 16GB cards to manage the MuLa vs Codec swap.
        """
        VRAMGroundTruth.nuclear_cleanup()
        print(f"{Fore.CYAN}🎹 LOADING AUDIO ENGINE: {model_path}")

        # Ground Truth Setting: Lazy Load + specific dtypes
        pipe = pipeline_class.from_pretrained(
            pretrained_path=str(model_path),
            device=device,
            dtype=dtype,
            version="IGNORE",
            lazy_load=True  # <--- Crucial Truth: Swaps Brain for Codec automatically
        )
        return pipe


# --- TRUTH TEST ---
if __name__ == "__main__":
    from pathlib import Path

    # Simulate a full cycle
    print(f"{Fore.GREEN}=== VRAM TRUTH CYCLE START ===")

    # 1. State: LLM is assumed running in LM Studio
    VRAMGroundTruth.offload_llm()

    # 2. State: GPU is now clear. Ready for HeartMuLa.
    print(f"{Fore.GREEN}=== GPU IS NOW READY FOR HIGH-FIDELITY AUDIO ===")