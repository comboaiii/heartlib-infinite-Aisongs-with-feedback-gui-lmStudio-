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

# AGANCY/lmstudio_controler.py
import requests
import json
import re
from colorama import Fore, Style


class LMStudioController:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')

    def get_active_model(self):
        """Fetches the exact ID of the currently loaded model from LM Studio."""
        try:
            res = requests.get(f"{self.base_url}/models", timeout=2)
            if res.status_code == 200:
                data = res.json()
                if data.get('data') and len(data['data']) > 0:
                    return data['data'][0]['id']
        except:
            pass
        return "local-model"

    def check_connection(self):
        """Returns (bool, message) regarding connection status."""
        try:
            model_id = self.get_active_model()
            res = requests.get(f"{self.base_url}/models", timeout=3)
            if res.status_code == 200:
                return True, f"Connected: {model_id}"
            return False, f"HTTP Error {res.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Connection Refused (Is LM Studio Server ON?)"
        except Exception as e:
            return False, str(e)

    def detect_and_clean_reasoning(self, content):
        """
        SMART DETECTOR: Removes DeepSeek/R1 <think> blocks and handles
        <|begin_of_box|> artifacts to ensure only the final lyrics remain.
        """
        original_len = len(content)

        # 1. Remove DeepSeek / Chain-of-Thought <think> blocks
        # re.DOTALL is crucial here to match newlines inside the thought block
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<thought>.*?</thought>', '', content, flags=re.DOTALL | re.IGNORECASE)

        # 2. Handle "Boxed" output (Common in R1 distillations)
        # If the model wraps the final answer in box tags, we ONLY want what's inside.
        if "<|begin_of_box|>" in content:
            # Split and take everything AFTER the begin tag
            content = content.split("<|begin_of_box|>")[-1]

        if "<|end_of_box|>" in content:
            # Split and take everything BEFORE the end tag
            content = content.split("<|end_of_box|>")[0]

        # 3. Clean up Markdown code blocks if the model wrapped lyrics in ```
        content = content.replace("```json", "").replace("```lyrics", "").replace("```", "")

        content = content.strip()

        if len(content) < original_len:
            print(f"{Fore.YELLOW}   🧹 Scrubbed {original_len - len(content)} chars of 'Thinking'/'System' tokens.")

        return content

    def chat(self, system_prompt, user_content, temp=0.7):
        """
        Sends a chat request. Includes reasoning detection and
        extended timeouts for slow models.
        """
        model_id = self.get_active_model()

        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": temp,
            "stream": False,
            "max_tokens": -1
        }

        try:
            # We set a long timeout (600s) because Reasoning models 'think'
            # for a long time before sending the first character.
            res = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=600
            )

            # Retry with generic ID if specific ID fails
            if res.status_code == 400:
                print(f"{Fore.YELLOW}⚠️  Retrying with generic 'local-model' ID...")
                payload["model"] = "local-model"
                res = requests.post(f"{self.base_url}/chat/completions", json=payload, timeout=600)

            if res.status_code != 200:
                raise Exception(f"LM Studio Error {res.status_code}: {res.text}")

            data = res.json()
            raw_response = data['choices'][0]['message']['content'].strip()
            print(raw_response)
            # Pass through the Smart Detector
            processed_response = self.detect_and_clean_reasoning(raw_response)

            return processed_response

        except requests.exceptions.Timeout:
            print(f"{Fore.RED}❌ ERROR: LLM timed out after 10 minutes.")
            raise TimeoutError("The model took too long to think. Try a smaller model (Llama-3 8B).")
        except requests.exceptions.ConnectionError:
            raise ConnectionError("Lost connection to LM Studio. Ensure the server is RUNNING.")
        except Exception as e:
            print(f"{Fore.RED}LLM Chat Error: {e}")
            raise e

    def unload_model(self):
        """
        Attempts to unload the model to free VRAM for the Audio Engine.
        (Requires LM Studio SDK to be installed in the environment)
        """
        try:
            import lmstudio as lms
            lms.llm().unload()
            return True
        except:
            # Fallback: Many setups don't have the SDK, so we just return False
            # and let the engine handle VRAM clearing via torch.cuda.empty_cache()
            return False