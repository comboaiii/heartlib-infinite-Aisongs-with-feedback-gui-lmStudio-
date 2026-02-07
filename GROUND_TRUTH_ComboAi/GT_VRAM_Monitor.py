import sys
import time
import psutil
import subprocess
import shutil
from colorama import Fore, Back, Style, init



class OrphioMonitor:
    """
    A reusable high-density hardware monitor for AI projects.
    Tracks NVIDIA GPU VRAM, Load, Processes, and System RAM.
    """

    def __init__(self, vram_threshold_gb=6.8):
        init(autoreset=True)
        self.vram_threshold_mb = vram_threshold_gb * 1024
        self.last_line_len = 0

    def _safe_shell(self, cmd):
        """Internal helper to run shell commands safely."""
        try:
            return subprocess.check_output(cmd.split(), stderr=subprocess.DEVNULL).decode().strip()
        except:
            return ""

    def get_gpu_stats(self):
        """Returns a dictionary of current GPU metrics."""
        raw = self._safe_shell(
            "nvidia-smi --query-gpu=memory.used,memory.total,memory.free,utilization.gpu --format=csv,nounits,noheader")
        if not raw:
            return {"used": 0, "total": 0, "free": 0, "load": 0}

        parts = [float(x) for x in raw.split(',')]
        return {
            "used": parts[0],
            "total": parts[1],
            "free": parts[2],
            "load": parts[3]
        }

    def get_active_ai_app(self):
        """Identifies the top process using the GPU compute cores."""
        raw = self._safe_shell("nvidia-smi --query-compute-apps=process_name,used_memory --format=csv,nounits,noheader")
        if not raw:
            return "IDLE", 0

        # Take the first process found
        first_proc = raw.split('\n')[0]
        try:
            path, mem = first_proc.split(',')
            name = path.split('/')[-1]
            return name[:12], int(mem)
        except:
            return "UNKNOWN", 0


    def get_system_stats(self):
        """Returns Motherboard RAM usage."""
        mem = psutil.virtual_memory()
        return {
            "used": mem.used / 1024 ** 2,
            "total": mem.total / 1024 ** 2,
            "perc": mem.percent
        }

    def construct_powerline(self):
        """Builds the high-density informational string."""
        g = self.get_gpu_stats()
        s = self.get_system_stats()
        app_name, app_mem = self.get_active_ai_app()

        # Dynamic Coloring
        v_color = Fore.GREEN if g['used'] < (g['total'] * 0.7) else (
            Fore.YELLOW if g['used'] < (g['total'] * 0.9) else Fore.RED)
        f_color = Fore.GREEN if g['free'] > self.vram_threshold_mb else Fore.RED
        l_color = Fore.CYAN if g['load'] > 5 else Fore.LIGHTBLACK_EX

        # Build Segments
        gpu_seg = f"{Fore.MAGENTA}GPU:{v_color}{g['used'] / 1024:4.1f}/{g['total'] / 1024:4.1f}G {l_color}({g['load']:2.0f}%)"
        free_seg = f"{Fore.WHITE}FREE:{f_color}{g['free'] / 1024:4.1f}G"
        app_seg = f"{Fore.YELLOW}APP:{Fore.WHITE}{app_name}"
        sys_seg = f"{Fore.BLUE}SYS:{Fore.WHITE}{s['used'] / 1024:4.1f}/{s['total'] / 1024:4.1f}G"

        # Verdict logic
        if g['free'] < self.vram_threshold_mb:
            verdict = f"{Back.RED}{Fore.WHITE} LOW-VRAM "
        elif app_name != "IDLE":
            verdict = f"{Fore.CYAN}BUSY"
        else:
            verdict = f"{Fore.GREEN}READY"

        # Construct full line with separators
        return f" {gpu_seg} {free_seg} {app_seg} | {sys_seg} | {verdict} "

    def print_inline(self):
        """Updates the terminal line in-place with no flicker."""
        line = self.construct_powerline()
        # \r = return to start, \033[K = clear to end of line
        sys.stdout.write(f"\r{line}\033[K")
        sys.stdout.flush()

    def run(self, interval=0.5):
        """Starts a standalone monitoring loop."""
        print(f"{Fore.CYAN}{Style.BRIGHT}ORPHIO MONITOR ACTIVE {Fore.WHITE}| {Fore.LIGHTBLACK_EX}Interval: {interval}s")
        print(f"{Fore.LIGHTBLACK_EX}Threshold: {self.vram_threshold_mb / 1024}GB Free")
        print("-" * shutil.get_terminal_size().columns)
        try:
            while True:
                self.print_inline()
                time.sleep(interval)
        except KeyboardInterrupt:
            # Clean exit: move to next line and show cursor
            print(f"\n{Fore.YELLOW}Monitor suspended.")


# =========================================================================
# STANDALONE EXECUTION
# =========================================================================
if __name__ == "__main__":
    # Initialize with a 7GB Free VRAM requirement (Standard for HeartMuLa 3B)
    monitor = OrphioMonitor(vram_threshold_gb=7.0)
    monitor.run()