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

import sys
import time
from pathlib import Path
from colorama import Fore, Style, init

# Import your classes
from Blueprint_Executor import ProducerBlueprintEngine
from Album_Post_Processor import AlbumPostProcessor
from orphio_config import conf

init(autoreset=True)


def main():
    print(f"\n{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════════════════════════╗")
    print(f"{Fore.CYAN}║ {Fore.WHITE}{Style.BRIGHT}   ORPHIO ALBUM PIPELINE: PRODUCTION SELECTION         {Fore.CYAN}║")
    print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════════╝")

    executor = ProducerBlueprintEngine()

    # 1. SCAN FOR STRATEGIES
    producers = executor.list_producers()

    if not producers:
        print(f"{Fore.RED}❌ No producer blueprints found in: {executor.strategies_path}")
        return

    print(f"\n{Fore.YELLOW}SELECT YOUR LEAD PRODUCER:")
    print(f"{Fore.LIGHTBLACK_EX}{'-' * 60}")

    for i, p in enumerate(producers):
        p_name = p['name'] if isinstance(p, dict) else p.name
        p_desc = p['desc'] if isinstance(p, dict) else "Strategy File"

        print(f"{Fore.GREEN}[{i + 1}] {Fore.WHITE}{Style.BRIGHT}{p_name.upper()}")
        print(f"    {Fore.LIGHTBLACK_EX}{p_desc}")
        print(f"{Fore.LIGHTBLACK_EX}{'-' * 60}")

    try:
        user_input = input(f"\n{Fore.CYAN}ENTER PRODUCER NUMBER: ")
        choice = int(user_input) - 1
        if choice < 0 or choice >= len(producers):
            raise ValueError
    except ValueError:
        print(f"{Fore.RED}Invalid selection.")
        return

    selected_data = producers[choice]
    blueprint_path = selected_data['path'] if isinstance(selected_data, dict) else selected_data
    blueprint = executor.load_blueprint(blueprint_path)

    # 2. GET TOPIC
    print(f"\n{Fore.YELLOW}ALBUM CONCEPT:")
    topic = input(f"{Fore.WHITE}Describe the album (Story, Mood, or Theme): ")

    if not topic.strip():
        print(f"{Fore.RED}No concept entered. Aborting.")
        return

    # 3. GET DURATION
    print(f"\n{Fore.YELLOW}TRACK DURATION:")
    try:
        dur_input = input(f"{Fore.WHITE}Enter duration per song in seconds (Default 120): ")
        user_duration = int(dur_input) if dur_input.strip() else 120
    except ValueError:
        print(f"{Fore.RED}Invalid number. Defaulting to 120 seconds.")
        user_duration = 120

    # 4. GET TRACK COUNT (NEW)
    print(f"\n{Fore.YELLOW}TRACK COUNT:")
    default_count = blueprint.get('executive_strategy', {}).get('track_count', 3)
    try:
        count_input = input(f"{Fore.WHITE}How many songs? (Default from Blueprint: {default_count}): ")
        user_count = int(count_input) if count_input.strip() else None
    except ValueError:
        print(f"{Fore.RED}Invalid number. Using Blueprint default.")
        user_count = None

    # 5. RUN GENERATION
    p_name_display = selected_data['name'] if isinstance(selected_data, dict) else "Producer"
    print(f"\n{Fore.MAGENTA}🚀 HANDING OVER TO {p_name_display.upper()}...")

    # PASS COUNT TO EXECUTOR
    executor.execute_album(blueprint, topic, user_duration, user_count)

    # 6. AUTO-MASTERING
    print(f"\n{Fore.YELLOW}⏳ GENERATION COMPLETE. SCANNING FOR ALBUM OUTPUT...")
    time.sleep(2)

    all_albums = [d for d in conf.OUTPUT_DIR.glob("ALBUM_*") if d.is_dir()]
    if not all_albums:
        print(f"{Fore.RED}❌ Error: No album folder found.")
        return

    latest_album = max(all_albums, key=lambda p: p.stat().st_ctime)

    print(f"{Fore.CYAN}🎚️  MASTERING ENGINEER: Normalizing '{latest_album.name}'...")

    processor = AlbumPostProcessor(latest_album)
    processor.process_album()

    print(f"\n{Fore.GREEN}{Style.BRIGHT}✅ PRODUCTION CYCLE COMPLETE.")
    print(f"{Fore.WHITE}📂 LOCATION: {latest_album / 'DISTRIBUTION_READY'}")


if __name__ == "__main__":
    main()