# AGANCY/lmstudio_controler.py
import requests
import json
from colorama import Fore


class LMStudioController:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')

    def get_active_model(self):
        """Fetches the exact ID of the currently loaded model."""
        try:
            res = requests.get(f"{self.base_url}/models", timeout=2)
            if res.status_code == 200:
                data = res.json()
                # LM Studio returns a list of models; usually the loaded one is first
                if data.get('data') and len(data['data']) > 0:
                    return data['data'][0]['id']
        except:
            pass
        # Fallback if we can't find it
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
            return False, "Connection Refused (Is LM Studio running?)"
        except Exception as e:
            return False, str(e)

    def chat(self, system_prompt, user_content, temp=0.7):
        """
        Sends a chat request using the correct Model ID.
        Includes retry logic for common 400 errors.
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
            "max_tokens": -1  # -1 tells LM Studio to use the context limit
        }

        try:
            # Attempt 1: Use specific Model ID
            res = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=120
            )

            # If specific ID fails (400 Bad Request), try generic 'local-model'
            if res.status_code == 400:
                print(f"{Fore.YELLOW}⚠️  Specific Model ID failed, retrying with generic 'local-model'...")
                payload["model"] = "local-model"
                res = requests.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    timeout=120
                )

            # If it still fails, raise error with the Server's explanation
            if res.status_code != 200:
                error_msg = f"HTTP {res.status_code}"
                try:
                    # Try to parse the server's error message
                    err_json = res.json()
                    if 'error' in err_json:
                        error_msg += f": {err_json['error'].get('message', str(err_json))}"
                except:
                    error_msg += f": {res.text}"
                raise Exception(error_msg)

            # Success
            data = res.json()
            return data['choices'][0]['message']['content'].strip()

        except requests.exceptions.ConnectionError:
            raise ConnectionError("Lost connection to LM Studio during generation.")
        except Exception as e:
            print(f"{Fore.RED}LLM Chat Error: {e}")
            raise e

    def unload_model(self):
        """
        Attempts to unload the model to free VRAM.
        """
        try:
            import lmstudio as lms
            lms.llm().unload()
            return True
        except ImportError:
            return False
        except:
            return False