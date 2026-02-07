import os
import sys
import json
import torch
import re
from pathlib import Path
from jiwer import wer


# --- FIXED PATH LOCALIZATION ---
def find_project_root():
    """Finds the main project directory containing the 'ckpt' folder."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        # We look for the folder that actually contains the models
        if (parent / "ckpt").exists():
            return parent
    return current.parent


ROOT_DIR = find_project_root()
# In your structure, heartlib is inside src/
SRC_DIR = ROOT_DIR / "src"
CKPT_DIR = ROOT_DIR / "ckpt"

# Add src to path so 'import heartlib' works
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from heartlib import HeartTranscriptorPipeline

    print(f"✅ Library loaded from: {SRC_DIR}")
except ImportError as e:
    print(f"❌ Failed to import heartlib. Check if {SRC_DIR} is correct. Error: {e}")
    sys.exit(1)


def clean(text):
    if not text: return ""
    # Remove text inside brackets [Intro], [Chorus], etc.
    text = re.sub(r'\[.*?\]', '', text)
    # Remove punctuation and newlines
    return re.sub(r'[^\w\s]', '', text).lower().replace('\n', ' ').strip()


def audit_system():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🕵️ LOADING AUDITOR (HeartTranscriptor)...")
    print(f"📂 Using CKPT_DIR: {CKPT_DIR}")

    # The pipeline expects the PARENT directory of HeartTranscriptor-oss
    try:
        model = HeartTranscriptorPipeline.from_pretrained(
            str(CKPT_DIR),
            device=device,
            dtype=torch.float16
        )
    except Exception as e:
        print(f"❌ FAILED TO LOAD TRANSCRIPTOR: {e}")
        print(f"💡 Make sure {CKPT_DIR}/HeartTranscriptor-oss exists and contains safetensors.")
        return

    results_log = []
    # Path to where your generated songs are
    search_dirs = [ROOT_DIR / "GROUND_TRUTH_ComboAi" / "outputSongs_ComboAi"]

    for folder in search_dirs:
        if not folder.exists():
            print(f"⚠️ Folder not found: {folder}")
            continue

        for json_path in folder.glob("*.json"):
            # Skip the report itself if it's in the same folder
            if "system_accuracy_report" in json_path.name: continue

            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if isinstance(data, list): data = data[0]

                wav_path = json_path.with_suffix('.wav')
                if not wav_path.exists(): continue

                print(f"📝 Auditing: {wav_path.name}")

                # Extract lyrics from your specific JSON schema
                config = data.get('configuration', {}).get('input_prompt', {})
                target_lyrics = clean(config.get('lyrics', ''))

                if not target_lyrics:
                    print(f"   ⚠️ No lyrics found in ledger for {json_path.name}")
                    continue

                with torch.no_grad():
                    res = model(str(wav_path), task="transcribe")
                    transcript = clean(res.get('text', ''))

                # Calculate Accuracy via Word Error Rate
                if target_lyrics and transcript:
                    error_rate = wer(target_lyrics, transcript)
                    accuracy = max(0, 1 - error_rate)
                else:
                    accuracy = 0.0

                results_log.append({
                    "file": wav_path.name,
                    "accuracy": round(accuracy, 4),
                    "match": "PASS" if accuracy > 0.75 else "FAIL",
                    "timestamp": data.get('provenance', {}).get('timestamp', 'unknown')
                })

                # Update the JSON file with the score (Injection)
                data['automated_metrics']['lyric_accuracy_score'] = round(accuracy, 4)
                data['automated_metrics']['raw_transcript'] = transcript
                data['automated_metrics']['audit_status'] = "AUDITED"

                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)

            except Exception as e:
                print(f"   ⚠️ Error processing {json_path.name}: {e}")

    # Save summary report
    report_path = ROOT_DIR / "GROUND_TRUTH_ComboAi" / "system_accuracy_report.json"
    with open(report_path, 'w') as f:
        json.dump(results_log, f, indent=4)

    print(f"\n📊 Audit Complete.")
    print(f"✅ Updated {len(results_log)} ledgers with accuracy scores.")
    print(f"📝 Summary saved to {report_path}")


if __name__ == "__main__":
    audit_system()