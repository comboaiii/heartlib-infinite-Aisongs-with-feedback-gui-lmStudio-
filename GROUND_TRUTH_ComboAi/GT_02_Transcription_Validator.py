
import os
import sys
import json
import torch
import re
from pathlib import Path
from jiwer import wer



# --- SMART PATH LOCALIZATION ---
def find_project_root():
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "heartlib").exists():
            return parent
    return current.parent


ROOT_DIR = find_project_root()
SRC_DIR = ROOT_DIR / "heartlib" / "src"
CKPT_DIR = ROOT_DIR / "heartlib" / "ckpt"

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from heartlib import HeartTranscriptorPipeline


def clean(text):
    if not text: return ""
    text = re.sub(r'\[.*?\]', '', text)
    return re.sub(r'[^\w\s]', '', text).lower().strip()


def audit_system():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🕵️ LOADING AUDITOR (HeartTranscriptor)...")
    print(f"📂 Using CKPT_DIR: {CKPT_DIR}")

    try:
        model = HeartTranscriptorPipeline.from_pretrained(str(CKPT_DIR), device=device, dtype=torch.float16)
    except Exception as e:
        print(f"❌ FAILED TO LOAD TRANSCRIPTOR: {e}")
        return

    results_log = []
    # Search in both standard output and Ground Truth folder
    search_dirs = [ROOT_DIR / "outputSongs_ComboAi", ROOT_DIR / "single_output"]

    for folder in search_dirs:
        if not folder.exists(): continue
        for json_path in folder.glob("*.json"):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Handle cases where JSON might be a list
                if isinstance(data, list): data = data[0]

                wav_path = json_path.with_suffix('.wav')
                if not wav_path.exists(): continue

                print(f"📝 Auditing: {wav_path.name}")

                # SCHEMA FIX: Correctly look deep into configuration -> input_prompt -> lyrics
                config = data.get('configuration', {}).get('input_prompt', {})
                target_lyrics = clean(config.get('lyrics', ''))

                with torch.no_grad():
                    res = model(str(wav_path), task="transcribe")
                    transcript = clean(res.get('text', ''))

                # Calculate WER
                error_rate = wer(target_lyrics, transcript) if target_lyrics and transcript else 1.0
                accuracy = max(0, 1 - error_rate)

                results_log.append({
                    "file": str(wav_path.relative_to(ROOT_DIR)),
                    "accuracy": round(accuracy, 4),
                    "match": "PASS" if accuracy > 0.7 else "FAIL"
                })
            except Exception as e:
                print(f"   ⚠️ Error processing {json_path.name}: {e}")

    # Save Truth Report
    report_path = ROOT_DIR / "system_accuracy_report.json"
    with open(report_path, 'w') as f:
        json.dump(results_log, f, indent=4)

    print(f"📊 Audit Complete. Report saved to {report_path}")


if __name__ == "__main__":
    audit_system()