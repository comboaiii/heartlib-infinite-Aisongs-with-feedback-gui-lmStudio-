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

import os
import json
import numpy as np
import scipy.io.wavfile
from pathlib import Path
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)


class AlbumPostProcessor:
    def __init__(self, album_path):
        self.album_path = Path(album_path)
        self.dist_path = self.album_path / "DISTRIBUTION_READY"
        self.dist_path.mkdir(exist_ok=True)

    def _load_wav(self, path):
        rate, data = scipy.io.wavfile.read(path)
        # Convert to float32 for processing
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        return rate, data

    def _save_wav(self, path, rate, data):
        # Convert back to int16
        data_int16 = np.int16(data * 32767)
        scipy.io.wavfile.write(path, rate, data_int16)

    def normalize_audio(self, audio_data, target_dB=-1.0):
        """
        Applies Peak Normalization so all tracks have consistent volume.
        """
        peak = np.max(np.abs(audio_data))
        if peak == 0: return audio_data

        # Calculate scalar
        scalar = 10 ** (target_dB / 20) / peak
        return audio_data * scalar

    def generate_analytics(self, track_jsons):
        """
        Compiles the 'further analytics' requested.
        """
        total_time = 0
        vocab_set = set()
        genre_distribution = {}

        for tm in track_jsons:
            # Time
            dur = tm.get('configuration', {}).get('duration_sec', 0)
            total_time += dur

            # Vocab (Rough estimate from lyrics)
            lyrics = tm.get('configuration', {}).get('input_prompt', {}).get('lyrics', "")
            words = lyrics.lower().split()
            vocab_set.update(words)

            # Genres
            tags = tm.get('configuration', {}).get('input_prompt', {}).get('tags', [])
            for t in tags:
                genre_distribution[t] = genre_distribution.get(t, 0) + 1

        return {
            "total_runtime_seconds": total_time,
            "total_runtime_formatted": f"{total_time // 60}m {total_time % 60}s",
            "vocabulary_size": len(vocab_set),
            "genre_dominance": dict(sorted(genre_distribution.items(), key=lambda item: item[1], reverse=True)),
            "track_count": len(track_jsons),
            "processed_date": datetime.now().isoformat()
        }

    def process_album(self):
        print(f"\n{Fore.CYAN}🎧 STARTING POST-PRODUCTION: {self.album_path.name}")

        # Find all generated JSONs
        json_files = sorted(list(self.album_path.glob("*.json")))

        # Filter out manifest files (only want song ledgers)
        track_ledgers = []
        for j in json_files:
            if "manifest" in j.name or "MASTER" in j.name: continue

            try:
                with open(j, 'r') as f:
                    data = json.load(f)
                    # Check if it looks like a song ledger
                    if 'provenance' in data:
                        track_ledgers.append((j, data))
            except:
                pass

        if not track_ledgers:
            print(f"{Fore.RED}❌ No track ledgers found via JSON scan.")
            return

        print(f"{Fore.GREEN}✅ Found {len(track_ledgers)} tracks. Mastering...")

        cleaned_metadata = []

        # PROCESSING LOOP
        for idx, (json_path, data) in enumerate(track_ledgers):
            track_num = idx + 1

            # 1. Identify Audio File
            wav_path = json_path.with_suffix('.wav')
            if not wav_path.exists():
                print(f"{Fore.RED}   ⚠️ Missing Audio for: {json_path.name}")
                continue

            title = data.get('configuration', {}).get('input_prompt', {}).get('topic', f"Untitled_{track_num}")
            safe_title = "".join([c for c in title if c.isalnum() or c in " _-"]).strip().replace(" ", "_")

            print(f"{Fore.LIGHTBLACK_EX}   🎚️  Mastering Track {track_num}: {title}")

            # 2. Load & Normalize Audio
            try:
                rate, audio = self._load_wav(wav_path)
                norm_audio = self.normalize_audio(audio)

                # 3. Save to Distribution Folder (Clean Name)
                final_filename = f"{track_num:02d}_{safe_title}.wav"
                final_path = self.dist_path / final_filename

                self._save_wav(final_path, rate, norm_audio)

            except Exception as e:
                print(f"{Fore.RED}      Error processing audio: {e}")
                continue

            # 4. Append to Metadata List
            cleaned_metadata.append(data)

        # 5. Generate Master Analytics
        analytics = self.generate_analytics(cleaned_metadata)

        # 6. Save Master JSON
        master_release = {
            "album_name": self.album_path.name.replace("ALBUM_", "").replace("_", " "),
            "analytics": analytics,
            "tracks": cleaned_metadata
        }

        with open(self.dist_path / "MASTER_RELEASE_LOG.json", "w") as f:
            json.dump(master_release, f, indent=4)

        print(f"\n{Fore.GREEN}✨ ALBUM MASTERED SUCCESSFULLY!")
        print(f"📂 Output: {self.dist_path}")
        print(f"📊 Stats: {analytics['total_runtime_formatted']} | {analytics['vocabulary_size']} unique words")


# --- STANDALONE RUNNER ---
if __name__ == "__main__":
    from orphio_config import conf

    # Simple menu to pick an album to process
    albums = [d for d in conf.OUTPUT_DIR.iterdir() if d.is_dir() and "ALBUM_" in d.name]

    if not albums:
        print(f"{Fore.RED}No albums found in {conf.OUTPUT_DIR}")
    else:
        print(f"{Fore.WHITE}Select Album to Master:")
        for i, alb in enumerate(albums):
            print(f"[{i + 1}] {alb.name}")

        choice = int(input("Number: ")) - 1

        processor = AlbumPostProcessor(albums[choice])
        processor.process_album()