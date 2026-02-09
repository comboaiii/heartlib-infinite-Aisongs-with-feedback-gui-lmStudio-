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

import json
import re
import time
import os
from pathlib import Path
from colorama import Fore, Style, init

from orphio_config import conf
from lmstudio_controler import LMStudioController
from orphio_engine import OrphioEngine

# Initialize colorama for Green/Black console output
init(autoreset=True)


class ProducerBlueprintEngine:
    def __init__(self):
        self.lms = LMStudioController(conf.LM_STUDIO_URL)
        self.engine = OrphioEngine(log_callback=print)
        # Point to the strategies folder
        self.strategies_path = Path(__file__).parent / "PRODUCER_STRATEGIES"
        self.strategies_path.mkdir(parents=True, exist_ok=True)

    def list_producers(self):
        """
        DYNAMIC SCANNER: Scans the PRODUCER_STRATEGIES folder.
        Ensures all .json files (1, 2, 3, 4) are loaded and sorted.
        """
        # Sort files by name so 1_ comes before 4_
        files = sorted(list(self.strategies_path.glob("*.json")))
        producers_data = []

        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as j:
                    data = json.load(j)
                    producers_data.append({
                        "path": f,
                        "name": data.get("name", f.stem.replace("_", " ")),
                        "desc": data.get("description", "Dynamic Strategy"),
                        "file_id": f.stem
                    })
            except Exception as e:
                print(f"{Fore.RED}⚠️ Error loading blueprint {f.name}: {e}")
                continue

        return producers_data

    def load_blueprint(self, filepath):
        """Loads a specific JSON blueprint file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _extract_json_from_response(self, text):
        """Helper to extract JSON from LLM markdown responses."""
        try:
            clean_text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    return None
        return None

    def stage_1_draft_content(self, blueprint, user_topic, user_track_count=None, tag_mode="AI", manual_tags=None):
        """
        PHASE 1: Planning and Lyric Generation.
        Propagates Album Title, Theme, and Sequence Context to every song.
        """
        print(f"\n{Fore.GREEN}╔════════════════════════════════════════════════╗")
        print(f"{Fore.GREEN}║  📝 PHASE 1: CONTENT DRAFTING & PROPAGATION   ║")
        print(f"{Fore.GREEN}╚════════════════════════════════════════════════╝")

        # 1. Determine Track Count
        target_count = blueprint['executive_strategy'].get('track_count', 3)
        if user_track_count and user_track_count > 0:
            target_count = user_track_count

        # 2. Executive Producer Plans the Album
        exec_prompt = (
            f"{blueprint['executive_strategy']['system_prompt']}\n"
            f"USER CONCEPT: {user_topic}\n"
            f"MANDATORY: Plan exactly {target_count} songs.\n"
            "FORMAT: JSON with 'album_title', 'album_theme_summary', and 'tracklist' (array of objects with 'title' and 'scene_description')."
        )

        print(f"{Fore.GREEN}🧠 [PRODUCER] Blueprinting the album structure...")
        plan_raw = self.lms.chat("You are a Master Executive Music Producer.", exec_prompt)
        plan = self._extract_json_from_response(plan_raw)

        if not plan:
            print(f"{Fore.RED}❌ Failed to plan album. LLM output was not valid JSON.")
            return None

        album_title = plan.get('album_title', 'Untitled Project')
        album_theme = plan.get('album_theme_summary', user_topic)
        track_list = plan.get('tracklist', [])
        total_tracks = len(track_list)

        print(f"{Fore.GREEN}✅ [PLAN READY] {album_title} | {total_tracks} tracks")

        # Create Album Directory
        safe_album_title = "".join([c for c in album_title if c.isalnum() or c in " _-"]).strip().replace(" ", "_")
        album_dir = conf.OUTPUT_DIR / f"ALBUM_{safe_album_title}"
        album_dir.mkdir(parents=True, exist_ok=True)

        # Save Manifest for reference
        with open(album_dir / "00_ALBUM_MANIFEST.json", "w", encoding='utf-8') as f:
            json.dump(plan, f, indent=4)

        context_history = []

        # 3. Iterative Generation Loop
        for i, track in enumerate(track_list):
            current_num = i + 1
            t_title = track.get('title', f"Track {current_num}")
            t_description = track.get('scene_description', "Atmospheric development.")

            print(f"\n{Fore.GREEN}✍️  Drafting Song {current_num}/{total_tracks}: {t_title}")

            # Prepare Sequence Context (Narrative Flow)
            prev_context_text = context_history[-1]['summary'] if context_history else "This is the opening track."

            # Inject Blueprint Logic
            template = blueprint['propagation_logic']['lyric_instruction_template']
            smart_prompt = template.replace("{album_title}", album_title) \
                .replace("{album_theme}", album_theme) \
                .replace("{track_title}", t_title) \
                .replace("{track_num}", str(current_num)) \
                .replace("{total_tracks}", str(total_tracks)) \
                .replace("{scene_description}", t_description) \
                .replace("{prev_context}", prev_context_text)

            # 4. Generate Lyrics
            lyrics = self.lms.chat(conf.PROMPT_WRITER, smart_prompt)
            lyrics = self.engine._enforce_tag_schema(lyrics)

            # 5. Generate Tags
            if tag_mode == "MANUAL":
                tags = manual_tags if manual_tags else ["Electronic"]
            else:
                try:
                    print(f"{Fore.GREEN}   🏷️  Analyzing genre and vibe...")
                    tags_raw = self.lms.chat(conf.PROMPT_TAGGER, f"Album: {album_title}\nLyrics: {lyrics}", temp=0.2)
                    tags = self.engine._clean_tags_list(tags_raw)
                except Exception:
                    tags = ["melodic", "modern", album_title.split()[0]]

            print(f"{Fore.WHITE}   Final Style: {', '.join(tags)}")

            # 6. Save Draft Ledger
            draft_data = {
                "track_number": current_num,
                "total_tracks": total_tracks,
                "album_title": album_title,
                "title": t_title,
                "status": "DRAFT_READY",
                "parameters": {
                    "topic": t_title,
                    "lyrics": lyrics,
                    "tags": tags,
                    "scene": t_description
                }
            }

            safe_title = "".join([c for c in t_title if c.isalnum() or c in " _-"]).replace(" ", "_")
            fname = f"{current_num:02d}_{safe_title}_DRAFT.json"
            with open(album_dir / fname, "w", encoding='utf-8') as f:
                json.dump(draft_data, f, indent=4)

            # Update context for the next song (first 200 chars of current lyrics)
            summary = lyrics.replace("\n", " ")
            context_history.append({"summary": summary[:200] + "..."})
            time.sleep(1.0)

        return album_dir

    def stage_2_batch_render(self, album_dir, user_duration, cfg_scale=1.5):
        """
        PHASE 2: Batch Audio Rendering.
        """
        album_dir = Path(album_dir)
        drafts = sorted(list(album_dir.glob("*_DRAFT.json")))

        print(f"\n{Fore.GREEN}╔════════════════════════════════════════════════╗")
        print(f"{Fore.GREEN}║  🔊 PHASE 2: BATCH AUDIO RENDERING             ║")
        print(f"{Fore.GREEN}╚════════════════════════════════════════════════╝")

        for idx, json_file in enumerate(drafts):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                params = data.get("parameters", {})
                self.engine.free_memory()

                print(f"{Fore.GREEN}🚀 Rendering [{idx + 1}/{len(drafts)}]: {data.get('title')}")

                wav_path, ledger = self.engine.render_audio_stage(
                    topic=data.get("title"),
                    lyrics=params.get("lyrics"),
                    tags=params.get("tags"),
                    duration_s=user_duration,
                    cfg=cfg_scale,
                    temp=1.0
                )

                # Rename to final clean naming convention
                dest_wav_name = json_file.name.replace("_DRAFT.json", ".wav")
                dest_json_name = json_file.name.replace("_DRAFT.json", ".json")

                if Path(wav_path).exists():
                    Path(wav_path).rename(album_dir / dest_wav_name)
                    ledger_source = Path(wav_path).with_suffix('.json')
                    if ledger_source.exists():
                        ledger_source.rename(album_dir / dest_json_name)

                os.remove(json_file)  # Remove draft once rendered
                print(f"{Fore.GREEN}   ✅ Finished Production: {dest_wav_name}")

            except Exception as e:
                print(f"{Fore.RED}❌ Batch Render Error on {json_file.name}: {e}")

    def execute_album(self, blueprint, user_topic, user_duration=120, user_track_count=None):
        """Full Pipeline Orchestrator."""
        album_path = self.stage_1_draft_content(blueprint, user_topic, user_track_count)
        if album_path:
            self.stage_2_batch_render(album_path, user_duration)
            return album_path
        return None