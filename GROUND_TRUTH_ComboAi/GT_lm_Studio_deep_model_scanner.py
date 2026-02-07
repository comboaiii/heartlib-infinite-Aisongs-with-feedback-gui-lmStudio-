import lmstudio as lms
import json
import os
import sys
import re
import time
import gc
import requests
from colorama import init, Fore, Style
from pathlib import Path

# =========================================================================
# ⚙️ CONFIGURATION & PATTERNS
# =========================================================================
init(autoreset=True)


LM_STUDIO_URL = "http://127.0.0.1:1234/v1"
# The output file is placed in the root of the "PythonMUSICgeneration" project for wide access
OUTPUT_FILE = "model_inventory_deep.json"

# Advanced Regex for specialized detection
PATTERNS = {
    # AUDIO MODELS (HeartMuLa, Orpheus, etc.)
    "AUDIO_VEENA": [r"veena", r"agastya", r"kavya"],
    "AUDIO_MAYA": [r"maya", r"audio-maya"],
    "AUDIO_MULTI": [r"orpheus", r"audio", r"speech", r"snac", r"music"],

    # REASONING MODELS (Chain-of-Thought, Logic-heavy)
    "REASONING": [r"reasoning", r"deepseek", r"r1", r"cot", r"thought", r"distill"],

    # UNCANSORED/NSFW MODELS (Expanded List for current uncensored top-performers)
    "UNCENSORED": [r"uncensored", r"abliterated", r"dolphin", r"lumimaid",
                   r"pygmalion", r"hermes", r"dark", r"psyfighter", r"nsfw", r"toriigate",
                   r"mixtral-uncensored", r"goliath", r"synapse", r"mythomax", r"airoboros"],

    # VISION MODELS (LLaVA, BakLLaVA, Qwen-VL)
    "VISION": [r"vision", r"vl", r"llava", r"bakllava", r"pixtral", r"qwen.*vl"],

    # VIDEO MODELS (LTX-2, Diffusion Transformer) <--- NEW CATEGORY
    "VIDEO": [r"ltx-2", r"video", r"dit", r"pixart", r"image-to-video", r"zeroscope"],

    # TOOL-USE MODELS (Function Calling)
    "TOOLS": [r"function", r"tool", r"hermes", r"mistral", r"qwen", r"command-r"]
}


def format_size(size_bytes):
    if not size_bytes or size_bytes == 0: return "Unknown"
    return f"{size_bytes / (1024 ** 3):.2f} GB"


def print_header():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.CYAN + "╔" + "═" * 110 + "╗")
    print(
        Fore.CYAN + "║" + Fore.WHITE + Style.BRIGHT + "  🔬 ORPHEUS ULTIMATE: HYBRID MODEL SCANNER v4.6 (VIDEO/UNCENSORED READY)                                " + Fore.CYAN + "║")
    print(
        Fore.CYAN + "║" + Fore.LIGHTBLACK_EX + "     Merging: SDK Metadata • Regex Heuristics • Audio/Video/NSFW Classification                      " + Fore.CYAN + "║")
    print(Fore.CYAN + "╚" + "═" * 110 + "╝")


def main():
    print_header()
    inventory = []

    print(f"{Fore.WHITE}📡 Connecting to LM Studio Library...")
    try:
        # Note: Depending on project structure, you might need to adjust Path to find LM Studio modules
        downloaded = lms.list_downloaded_models()
    except Exception as e:
        print(Fore.RED + f"❌ SDK ERROR: Start LM Studio Server first. {e}")
        return

    total = len(downloaded)
    print(Fore.GREEN + f"✅ Found {total} models. Performing Deep Inspection...\n")

    # Adjusted table size for new capabilities field
    print(f"{Fore.WHITE}{'TYPE':<4} | {'SIZE':<9} | {'CTX':<7} | {'CAPABILITIES (Detected)':<53} | {'NAME'}")
    print(Fore.LIGHTBLACK_EX + "-" * 125)

    for i, m in enumerate(downloaded):
        m_key = getattr(m, 'model_key', getattr(m, 'path', 'unknown'))
        d_name = getattr(m, 'display_name', m_key)
        mid_lower = m_key.lower()

        if "embed" in mid_lower: continue

        # --- 1. CAPABILITY DETECTION (Heuristics) ---
        is_audio = any(
            re.search(p, mid_lower) for p in PATTERNS["AUDIO_VEENA"] + PATTERNS["AUDIO_MAYA"] + PATTERNS["AUDIO_MULTI"])
        is_uncensored = any(re.search(p, mid_lower) for p in PATTERNS["UNCENSORED"])
        is_reasoning = any(re.search(p, mid_lower) for p in PATTERNS["REASONING"])
        is_vision = any(re.search(p, mid_lower) for p in PATTERNS["VISION"])
        is_video = any(re.search(p, mid_lower) for p in PATTERNS["VIDEO"])  # <--- NEW CHECK
        has_tools = any(re.search(p, mid_lower) for p in PATTERNS["TOOLS"])

        # Default values
        size_b = 0
        ctx_len = 2048

        # --- 2. SDK METADATA INJECTION (Requires server to be running) ---
        try:
            info = lms.llm(m_key).get_info()
            size_b = getattr(info, 'size_bytes', 0)
            ctx_len = getattr(info, 'max_context_length', 2048)
            # Override heuristics with ground truth if available from SDK
            is_vision = getattr(info, 'vision', is_vision)
            has_tools = getattr(info, 'trained_for_tool_use', has_tools)
        except:
            # Fallback to checking file size on disk if SDK metadata fails
            m_path = getattr(m, 'path', None)
            if m_path and os.path.exists(m_path):
                size_b = os.path.getsize(m_path)

        # --- 3. UI DISPLAY ---
        if is_video:
            icon = "🎥";
            row_color = Fore.MAGENTA
        elif is_audio:
            icon = "🎵";
            row_color = Fore.CYAN
        elif is_uncensored:
            icon = "🔞";
            row_color = Fore.LIGHTRED_EX
        elif is_reasoning:
            icon = "🧠";
            row_color = Fore.YELLOW
        else:
            icon = "🤖";
            row_color = Fore.WHITE

        caps = []
        if is_audio: caps.append("AUDIO")
        if is_uncensored: caps.append("NSFW")
        if is_reasoning: caps.append("THINK")
        if is_vision: caps.append("VISION")
        if is_video: caps.append("VIDEO")  # <--- NEW DISPLAY
        if has_tools: caps.append("TOOLS")
        caps_str = ", ".join(caps)

        size_str = format_size(size_b)
        print(f"{row_color}{icon:<4} | {size_str:<9} | {str(ctx_len):<7} | {caps_str:<53} | {d_name[:35]}")

        # --- 4. DATA STRUCTURING (For Agency script) ---
        inventory.append({
            "id": m_key,
            "name": d_name,
            "is_uncensored": is_uncensored,
            "specs": {
                "size": size_str,
                "context": ctx_len,
                "tools": has_tools,
                "vision": is_vision,
                "audio": is_audio,
                "video": is_video,  # <--- NEW FIELD
                "reasoning": is_reasoning
            }
        })

    # --- 5. SAVE ---
    output_path = Path(os.path.abspath(OUTPUT_FILE))
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=4, ensure_ascii=False)

    print(f"\n{Fore.CYAN}{'=' * 110}")
    print(Fore.GREEN + f"💾 SUCCESS: {len(inventory)} models saved to {output_path}")
    print(Fore.WHITE + "   Ready for AI Music Production Agency.")


if __name__ == "__main__":
    main()