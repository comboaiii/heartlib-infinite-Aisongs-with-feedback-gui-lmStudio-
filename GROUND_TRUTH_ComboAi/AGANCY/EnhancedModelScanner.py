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
ENHANCED LM STUDIO MODEL SCANNER
=================================
Scans LM Studio for available models and analyzes their capabilities
"""

import requests
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from colorama import Fore, init

init(autoreset=True)


class EnhancedModelScanner:
    """Enhanced scanner for LM Studio models with capability detection"""
    
    # Model capability patterns
    CAPABILITY_PATTERNS = {
        "reasoning": [r"reasoning", r"deepseek", r"r1", r"cot", r"think", r"distill"],
        "creative": [r"story", r"creative", r"writer", r"lumimaid", r"mythomax"],
        "uncensored": [r"uncensored", r"abliterated", r"dolphin", r"hermes", r"psyfighter"],
        "code": [r"code", r"coder", r"deepseek-coder", r"wizard"],
        "multilingual": [r"multilingual", r"qwen", r"aya"],
        "instruct": [r"instruct", r"chat", r"hermes"],
        "fast": [r"fast", r"speed", r"tiny", r"small"],
        "large": [r"70b", r"72b", r"405b", r"mixtral"]
    }
    
    def __init__(self, base_url="http://localhost:1234/v1"):
        self.base_url = base_url.rstrip('/')
    
    def check_connection(self) -> Tuple[bool, str]:
        """Check if LM Studio is running and accessible"""
        try:
            response = requests.get(f"{self.base_url}/models", timeout=3)
            if response.status_code == 200:
                return True, "Connected to LM Studio"
            return False, f"HTTP Error {response.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Connection refused - Is LM Studio server running?"
        except Exception as e:
            return False, str(e)
    
    def get_loaded_model(self) -> Dict:
        """Get currently loaded model information"""
        try:
            response = requests.get(f"{self.base_url}/models", timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    model = data['data'][0]
                    return {
                        'id': model.get('id', 'unknown'),
                        'owned_by': model.get('owned_by', 'unknown'),
                        'created': model.get('created', 0),
                        'object': model.get('object', 'model'),
                        'status': 'loaded'
                    }
        except Exception as e:
            print(f"{Fore.RED}Error getting loaded model: {e}")
        
        return None
    
    def detect_capabilities(self, model_id: str) -> List[str]:
        """Detect model capabilities based on name patterns"""
        model_lower = model_id.lower()
        capabilities = []
        
        for capability, patterns in self.CAPABILITY_PATTERNS.items():
            if any(re.search(pattern, model_lower) for pattern in patterns):
                capabilities.append(capability)
        
        # Add defaults if nothing detected
        if not capabilities:
            capabilities.append("general")
        
        return capabilities
    
    def estimate_size(self, model_id: str) -> str:
        """Estimate model size from name"""
        model_lower = model_id.lower()
        
        # Look for size indicators
        if any(x in model_lower for x in ['70b', '72b']):
            return "~40-50GB"
        elif any(x in model_lower for x in ['30b', '34b']):
            return "~20-25GB"
        elif any(x in model_lower for x in ['13b', '14b']):
            return "~8-10GB"
        elif any(x in model_lower for x in ['7b', '8b']):
            return "~4-6GB"
        elif any(x in model_lower for x in ['3b']):
            return "~2-3GB"
        elif any(x in model_lower for x in ['1b']):
            return "~1GB"
        else:
            return "Unknown"
    
    def get_model_info(self, model_id: str) -> Dict:
        """Get comprehensive model information"""
        capabilities = self.detect_capabilities(model_id)
        size = self.estimate_size(model_id)
        
        # Determine optimal use case
        if "reasoning" in capabilities:
            use_case = "Complex lyrics, narrative coherence"
        elif "creative" in capabilities:
            use_case = "Creative lyrics, storytelling"
        elif "uncensored" in capabilities:
            use_case = "Unrestricted content, mature themes"
        elif "fast" in capabilities:
            use_case = "Quick generation, drafting"
        else:
            use_case = "General purpose lyrics"
        
        return {
            'id': model_id,
            'capabilities': capabilities,
            'estimated_size': size,
            'recommended_use': use_case,
            'quality_rating': self._estimate_quality(model_id, capabilities)
        }
    
    def _estimate_quality(self, model_id: str, capabilities: List[str]) -> str:
        """Estimate model quality tier"""
        model_lower = model_id.lower()
        
        # High-end models
        if any(x in model_lower for x in ['70b', '72b', 'qwen-2.5']):
            return "Excellent"
        
        # Mid-tier
        elif any(x in model_lower for x in ['30b', '34b', 'mixtral']):
            return "Very Good"
        
        # Standard
        elif any(x in model_lower for x in ['13b', '14b']):
            return "Good"
        
        # Small but capable
        elif "reasoning" in capabilities or "creative" in capabilities:
            return "Good"
        
        # Basic
        else:
            return "Adequate"
    
    def scan_and_report(self) -> Dict:
        """Perform full scan and generate report"""
        print(f"\n{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.CYAN}  LM STUDIO MODEL SCANNER - Enhanced Edition")
        print(f"{Fore.CYAN}{'=' * 70}\n")
        
        # Check connection
        ok, msg = self.check_connection()
        print(f"Connection Status: ", end="")
        if ok:
            print(f"{Fore.GREEN}✓ {msg}")
        else:
            print(f"{Fore.RED}✗ {msg}")
            return {'status': 'error', 'message': msg}
        
        # Get loaded model
        loaded_model = self.get_loaded_model()
        
        if not loaded_model:
            print(f"{Fore.YELLOW}No model currently loaded")
            return {'status': 'no_model', 'message': 'No model loaded'}
        
        model_id = loaded_model['id']
        print(f"\n{Fore.WHITE}Currently Loaded Model:")
        print(f"{Fore.CYAN}  ID: {Fore.WHITE}{model_id}")
        
        # Analyze model
        info = self.get_model_info(model_id)
        
        print(f"{Fore.CYAN}  Size: {Fore.WHITE}{info['estimated_size']}")
        print(f"{Fore.CYAN}  Quality: {Fore.WHITE}{info['quality_rating']}")
        print(f"{Fore.CYAN}  Best For: {Fore.WHITE}{info['recommended_use']}")
        
        # Capabilities
        print(f"\n{Fore.WHITE}Detected Capabilities:")
        for cap in info['capabilities']:
            icon = {
                'reasoning': '🧠',
                'creative': '✨',
                'uncensored': '🔓',
                'code': '💻',
                'fast': '⚡',
                'large': '🐘',
                'instruct': '📋',
                'multilingual': '🌐',
                'general': '🤖'
            }.get(cap, '•')
            print(f"  {icon} {cap.capitalize()}")
        
        # Recommendations
        print(f"\n{Fore.YELLOW}Recommendations for Music Production:")
        if "reasoning" in info['capabilities']:
            print(f"  {Fore.GREEN}✓ Excellent for narrative albums")
            print(f"  {Fore.GREEN}✓ Good at maintaining story coherence")
        
        if "creative" in info['capabilities']:
            print(f"  {Fore.GREEN}✓ Great for original lyrics")
            print(f"  {Fore.GREEN}✓ Good at metaphors and imagery")
        
        if "fast" in info['capabilities']:
            print(f"  {Fore.GREEN}✓ Quick draft generation")
            print(f"  {Fore.YELLOW}⚠ May need more editing")
        
        if info['quality_rating'] in ['Excellent', 'Very Good']:
            print(f"  {Fore.GREEN}✓ High-quality output expected")
        
        print(f"\n{Fore.CYAN}{'=' * 70}\n")
        
        return {
            'status': 'success',
            'model': info
        }
    
    def save_scan_results(self, output_file: str = "model_scan_results.json"):
        """Save scan results to JSON file"""
        loaded_model = self.get_loaded_model()
        if not loaded_model:
            return False
        
        info = self.get_model_info(loaded_model['id'])
        
        scan_data = {
            'scan_timestamp': str(Path.cwd()),
            'lm_studio_url': self.base_url,
            'model': info
        }
        
        try:
            with open(output_file, 'w') as f:
                json.dump(scan_data, f, indent=2)
            print(f"{Fore.GREEN}✓ Scan results saved to: {output_file}")
            return True
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to save: {e}")
            return False


def main():
    """Standalone scanner execution"""
    scanner = EnhancedModelScanner()
    result = scanner.scan_and_report()
    
    if result['status'] == 'success':
        # Ask if user wants to save
        save = input(f"\n{Fore.CYAN}Save scan results? (y/n): ").strip().lower()
        if save == 'y':
            scanner.save_scan_results()


if __name__ == "__main__":
    main()
