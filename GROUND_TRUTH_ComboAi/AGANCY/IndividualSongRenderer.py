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

"""
INDIVIDUAL SONG RENDERER
========================
Utility for rendering single songs from drafts with fine control
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime
from colorama import Fore, init

init(autoreset=True)

try:
    from orphio_config import conf
    from orphio_engine import OrphioEngine
except ImportError:
    print(f"{Fore.RED}Error: Cannot import required modules.")
    print(f"{Fore.YELLOW}Make sure this script is in the AGANCY folder.")
    sys.exit(1)


class IndividualSongRenderer:
    """Handles rendering of individual songs from draft files"""
    
    def __init__(self):
        self.engine = OrphioEngine(log_callback=self.log)
        
    def log(self, message, color="white"):
        """Print colored log message"""
        colors = {
            "red": Fore.RED,
            "green": Fore.GREEN,
            "yellow": Fore.YELLOW,
            "cyan": Fore.CYAN,
            "magenta": Fore.MAGENTA,
            "white": Fore.WHITE
        }
        color_code = colors.get(color, Fore.WHITE)
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{color_code}[{timestamp}] {message}")
    
    def find_albums(self):
        """Find all album directories"""
        return [d for d in conf.OUTPUT_DIR.iterdir() if d.is_dir() and "ALBUM_" in d.name]
    
    def find_drafts_in_album(self, album_dir):
        """Find all draft files in an album"""
        return sorted(list(Path(album_dir).glob("*_DRAFT.json")))
    
    def load_draft(self, draft_file):
        """Load draft data from file"""
        try:
            with open(draft_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.log(f"Error loading draft: {e}", "red")
            return None
    
    def render_song(self, draft_file, duration=120, cfg_scale=1.5):
        """Render a single song from draft"""
        self.log(f"Loading draft: {draft_file.name}", "cyan")
        
        draft_data = self.load_draft(draft_file)
        if not draft_data:
            return False
        
        # Extract parameters
        params = draft_data.get("parameters", {})
        title = draft_data.get("title", "Untitled")
        lyrics = params.get("lyrics", "")
        tags = params.get("tags", [])
        
        if not lyrics:
            self.log("No lyrics found in draft!", "red")
            return False
        
        self.log(f"Title: {title}", "white")
        self.log(f"Tags: {', '.join(tags)}", "yellow")
        self.log(f"Duration: {duration}s, CFG: {cfg_scale}", "yellow")
        
        # Render
        try:
            self.log("Starting audio generation...", "magenta")
            self.engine.free_memory()
            
            wav_path, ledger = self.engine.render_audio_stage(
                topic=title,
                lyrics=lyrics,
                tags=tags,
                duration_s=duration,
                cfg=cfg_scale,
                temp=1.0
            )
            
            # Move rendered file to album directory
            album_dir = draft_file.parent
            safe_title = "".join([c for c in title if c.isalnum() or c in " _-"]).replace(" ", "_")
            track_num = draft_data.get("track_number", 1)
            
            final_wav = album_dir / f"{track_num:02d}_{safe_title}.wav"
            final_json = album_dir / f"{track_num:02d}_{safe_title}.json"
            
            # Move files
            if Path(wav_path).exists():
                Path(wav_path).rename(final_wav)
                self.log(f"✓ Audio saved: {final_wav.name}", "green")
            
            json_path = Path(wav_path).with_suffix('.json')
            if json_path.exists():
                json_path.rename(final_json)
                self.log(f"✓ Ledger saved: {final_json.name}", "green")
            
            # Delete draft file
            draft_file.unlink()
            self.log(f"✓ Removed draft: {draft_file.name}", "yellow")
            
            return True
            
        except Exception as e:
            self.log(f"✗ Render failed: {str(e)}", "red")
            import traceback
            traceback.print_exc()
            return False
    
    def interactive_select_and_render(self):
        """Interactive mode to select and render a song"""
        print(f"\n{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.CYAN}  INDIVIDUAL SONG RENDERER")
        print(f"{Fore.CYAN}{'=' * 70}\n")
        
        # Find albums
        albums = self.find_albums()
        
        if not albums:
            self.log("No albums found!", "red")
            return
        
        # Select album
        print(f"{Fore.WHITE}Available Albums:")
        for i, album in enumerate(albums, 1):
            draft_count = len(list(album.glob("*_DRAFT.json")))
            print(f"  {Fore.YELLOW}[{i}]{Fore.WHITE} {album.name} {Fore.CYAN}({draft_count} drafts)")
        
        try:
            album_choice = int(input(f"\n{Fore.GREEN}Select album number: ")) - 1
            if album_choice < 0 or album_choice >= len(albums):
                raise ValueError
        except (ValueError, KeyboardInterrupt):
            self.log("Invalid selection or cancelled", "red")
            return
        
        selected_album = albums[album_choice]
        drafts = self.find_drafts_in_album(selected_album)
        
        if not drafts:
            self.log("No drafts found in this album!", "red")
            return
        
        # Select draft
        print(f"\n{Fore.WHITE}Available Drafts:")
        for i, draft in enumerate(drafts, 1):
            draft_data = self.load_draft(draft)
            if draft_data:
                title = draft_data.get("title", "Unknown")
                status = draft_data.get("status", "DRAFT")
                print(f"  {Fore.YELLOW}[{i}]{Fore.WHITE} {title} {Fore.CYAN}[{status}]")
        
        print(f"  {Fore.YELLOW}[0]{Fore.WHITE} Render ALL drafts")
        
        try:
            draft_choice = int(input(f"\n{Fore.GREEN}Select draft number (0 for all): "))
            if draft_choice < 0 or draft_choice > len(drafts):
                raise ValueError
        except (ValueError, KeyboardInterrupt):
            self.log("Invalid selection or cancelled", "red")
            return
        
        # Get render settings
        print(f"\n{Fore.WHITE}Render Settings:")
        try:
            duration = int(input(f"{Fore.CYAN}Duration (seconds) [120]: ") or "120")
            cfg_input = input(f"{Fore.CYAN}CFG Scale (1.0-3.0) [1.5]: ") or "1.5"
            cfg_scale = float(cfg_input)
        except ValueError:
            self.log("Invalid settings, using defaults", "yellow")
            duration = 120
            cfg_scale = 1.5
        
        # Render
        if draft_choice == 0:
            # Render all
            self.log(f"\nRendering ALL {len(drafts)} songs...", "cyan")
            success_count = 0
            
            for i, draft in enumerate(drafts, 1):
                self.log(f"\n--- Song {i}/{len(drafts)} ---", "white")
                if self.render_song(draft, duration, cfg_scale):
                    success_count += 1
                time.sleep(2)  # Brief pause between renders
            
            self.log(f"\n✓ Completed: {success_count}/{len(drafts)} songs rendered", "green")
        else:
            # Render single
            selected_draft = drafts[draft_choice - 1]
            self.render_song(selected_draft, duration, cfg_scale)
        
        print(f"\n{Fore.CYAN}{'=' * 70}\n")


def main():
    """Main entry point"""
    renderer = IndividualSongRenderer()
    renderer.interactive_select_and_render()


if __name__ == "__main__":
    main()
