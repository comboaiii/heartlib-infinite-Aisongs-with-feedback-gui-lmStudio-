import os
import torch
import gc
from pathlib import Path
from colorama import Fore, Style, init



class OrphioHealthScanner:
    def __init__(self):
        init(autoreset=True)
        self.root = self._find_heartlib_root()
        self.ckpt_dir = self.root / "ckpt" if self.root else None

    def _find_heartlib_root(self):
        """Searches 2-3 levels up and down for the heartlib directory."""
        start_path = Path(__file__).resolve()

        # Search Upwards (up to 3 levels)
        for parent in [start_path] + list(start_path.parents)[:3]:
            # Check if this is the root containing heartlib
            if (parent / "heartlib").is_dir():
                return parent / "heartlib"
            # Check if we are ALREADY inside heartlib
            if parent.name == "heartlib" and (parent / "src").is_dir():
                return parent

        return None

    def check_hardware(self):
        print(f"\n{Fore.CYAN}🖥️  HARDWARE GROUND TRUTH")
        print("-" * 50)

        if not torch.cuda.is_available():
            print(f"{Fore.RED}❌ CUDA NOT AVAILABLE. AI generation impossible.")
            return

        t = torch.cuda.get_device_properties(0)
        free_vram = torch.cuda.mem_get_info()[0] / 1024 ** 3
        total_vram = t.total_memory / 1024 ** 3

        print(f"   GPU: {Fore.WHITE}{t.name}")
        v_color = Fore.GREEN if free_vram > 7 else Fore.RED
        print(f"   VRAM: {v_color}{free_vram:.2f}GB Free {Fore.WHITE}/ {total_vram:.2f}GB Total")

        bf16 = torch.cuda.is_bf16_supported()
        bf16_status = f"{Fore.GREEN}✅ Supported (Optimal)" if bf16 else f"{Fore.YELLOW}❌ Not Supported (Standard Quality Only)"
        print(f"   BF16: {bf16_status}")

    def check_model_inventory(self):
        print(f"\n{Fore.CYAN}📂 MODEL INVENTORY & PATH TRUTH")
        print("-" * 50)

        if not self.root:
            print(f"{Fore.RED}❌ CRITICAL: Could not locate 'heartlib' folder in search radius.")
            return

        print(f"   Root Found: {Fore.LIGHTBLACK_EX}{self.root}")

        # Define versions to look for
        mula_patterns = ["HeartMuLa-RL-oss-3B-20260123", "HeartMuLa-oss-3B"]
        codec_patterns = ["HeartCodec-oss-20260123", "HeartCodec-oss"]
        configs = ["tokenizer.json", "gen_config.json"]

        print(f"\n   {Style.BRIGHT}Brain (MuLa) Models:")
        for p in mula_patterns:
            target = self.ckpt_dir / p
            status = f"{Fore.GREEN}✅ Found" if target.exists() else f"{Fore.LIGHTBLACK_EX}   Missing"
            print(f"   - {p:<30} {status}")

        print(f"\n   {Style.BRIGHT}Vocoder (Codec) Models:")
        for p in codec_patterns:
            target = self.ckpt_dir / p
            status = f"{Fore.GREEN}✅ Found" if target.exists() else f"{Fore.LIGHTBLACK_EX}   Missing"
            print(f"   - {p:<30} {status}")

        print(f"\n   {Style.BRIGHT}System Configs:")
        for c in configs:
            target = self.ckpt_dir / c
            status = f"{Fore.GREEN}✅ Found" if target.exists() else f"{Fore.RED}❌ Missing"
            print(f"   - {c:<30} {status}")

    def run_diagnostic(self):
        print(f"{Style.BRIGHT}  ⚖️  ORPHIO SYSTEM DIAGNOSTIC  ")
        self.check_hardware()
        self.check_model_inventory()

        print("\n" + "=" * 50)
        if self.root and (self.ckpt_dir / "gen_config.json").exists():
            print(f"{Fore.GREEN}✨ DIAGNOSTIC COMPLETE: System is ready for production.")
        else:
            print(f"{Fore.RED}🛑 DIAGNOSTIC FAILED: Check missing files above.")


if __name__ == "__main__":
    scanner = OrphioHealthScanner()
    scanner.run_diagnostic()