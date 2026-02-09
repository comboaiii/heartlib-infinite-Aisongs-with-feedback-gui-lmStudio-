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
ORPHIO SYSTEM SETUP CHECKER
============================
Validates your environment before running the production studio
"""

import sys
from pathlib import Path
from colorama import Fore, Style, init

init(autoreset=True)


class SystemChecker:
    """Comprehensive system validation"""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = 0
        
    def print_header(self):
        """Print checker header"""
        print(f"\n{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.CYAN}  ORPHIO PRODUCTION STUDIO - SYSTEM CHECKER")
        print(f"{Fore.CYAN}{'=' * 70}\n")
    
    def check(self, name, condition, error_msg, warning=False):
        """Perform a single check"""
        if condition:
            print(f"{Fore.GREEN}✓ {name}")
            self.checks_passed += 1
            return True
        else:
            if warning:
                print(f"{Fore.YELLOW}⚠ {name}")
                print(f"{Fore.YELLOW}  Warning: {error_msg}")
                self.warnings += 1
            else:
                print(f"{Fore.RED}✗ {name}")
                print(f"{Fore.RED}  Error: {error_msg}")
                self.checks_failed += 1
            return False
    
    def check_python_version(self):
        """Check Python version"""
        version = sys.version_info
        is_ok = version.major == 3 and version.minor >= 10
        
        if is_ok:
            version_str = f"{version.major}.{version.minor}.{version.micro}"
            print(f"{Fore.GREEN}✓ Python Version: {version_str}")
            self.checks_passed += 1
        else:
            print(f"{Fore.RED}✗ Python Version: {version.major}.{version.minor}")
            print(f"{Fore.RED}  Error: Python 3.10+ required")
            self.checks_failed += 1
        
        return is_ok
    
    def check_imports(self):
        """Check required Python packages"""
        print(f"\n{Fore.WHITE}Checking Python Dependencies:")
        
        packages = {
            "PyQt6": "PyQt6",
            "colorama": "colorama",
            "numpy": "numpy",
            "scipy": "scipy",
            "torch": "torch",
            "torchaudio": "torchaudio",
            "requests": "requests"
        }
        
        all_ok = True
        for display_name, import_name in packages.items():
            try:
                __import__(import_name)
                print(f"{Fore.GREEN}  ✓ {display_name}")
                self.checks_passed += 1
            except ImportError:
                print(f"{Fore.RED}  ✗ {display_name}")
                print(f"{Fore.RED}    Install: pip install {import_name}")
                self.checks_failed += 1
                all_ok = False
        
        return all_ok
    
    def check_file_structure(self):
        """Check directory structure"""
        print(f"\n{Fore.WHITE}Checking File Structure:")
        
        # Find project root
        current = Path.cwd()
        root = None
        
        for parent in [current] + list(current.parents):
            if (parent / "ckpt").exists() or (parent / "GROUND_TRUTH_ComboAi").exists():
                root = parent
                break
        
        if not root:
            print(f"{Fore.RED}  ✗ Project root not found")
            print(f"{Fore.RED}    Cannot locate ckpt or GROUND_TRUTH_ComboAi folder")
            self.checks_failed += 1
            return False
        
        print(f"{Fore.GREEN}  ✓ Project root: {root}")
        self.checks_passed += 1
        
        # Check key directories
        required_dirs = {
            "ckpt": "Model checkpoint directory",
            "GROUND_TRUTH_ComboAi": "Project directory",
            "GROUND_TRUTH_ComboAi/AGANCY": "Core scripts location"
        }
        
        all_ok = True
        for dir_name, description in required_dirs.items():
            dir_path = root / dir_name
            if self.check(
                f"  {description}",
                dir_path.exists() and dir_path.is_dir(),
                f"Missing: {dir_path}"
            ):
                pass
            else:
                all_ok = False
        
        return all_ok
    
    def check_models(self):
        """Check HeartMuLa models"""
        print(f"\n{Fore.WHITE}Checking HeartMuLa Models:")
        
        # Find ckpt directory
        current = Path.cwd()
        ckpt_dir = None
        
        for parent in [current] + list(current.parents):
            test_ckpt = parent / "ckpt"
            if test_ckpt.exists():
                ckpt_dir = test_ckpt
                break
        
        if not ckpt_dir:
            print(f"{Fore.RED}  ✗ ckpt directory not found")
            self.checks_failed += 1
            return False
        
        # Check required models
        required_items = {
            "HeartMuLa-oss-3B": "Brain model",
            "HeartCodec-oss": "Vocoder model",
            "tokenizer.json": "Tokenizer",
            "gen_config.json": "Generation config"
        }
        
        all_ok = True
        for item_name, description in required_items.items():
            item_path = ckpt_dir / item_name
            if self.check(
                f"  {description}",
                item_path.exists(),
                f"Missing: {item_path}"
            ):
                # Show size for directories
                if item_path.is_dir():
                    size_mb = sum(f.stat().st_size for f in item_path.rglob('*') if f.is_file()) / (1024**2)
                    print(f"{Fore.CYAN}    Size: {size_mb:.1f} MB")
            else:
                all_ok = False
        
        return all_ok
    
    def check_lm_studio(self):
        """Check LM Studio connection"""
        print(f"\n{Fore.WHITE}Checking LM Studio:")
        
        try:
            import requests
            response = requests.get("http://localhost:1234/v1/models", timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    model_id = data['data'][0].get('id', 'unknown')
                    print(f"{Fore.GREEN}  ✓ LM Studio connected")
                    print(f"{Fore.CYAN}    Active model: {model_id}")
                    self.checks_passed += 1
                    return True
        except:
            pass
        
        print(f"{Fore.YELLOW}  ⚠ LM Studio not connected")
        print(f"{Fore.YELLOW}    Start LM Studio and load a model before running")
        self.warnings += 1
        return False
    
    def check_gpu(self):
        """Check GPU availability"""
        print(f"\n{Fore.WHITE}Checking GPU:")
        
        try:
            import torch
            
            if torch.cuda.is_available():
                device = torch.cuda.get_device_properties(0)
                vram_gb = device.total_memory / (1024**3)
                
                print(f"{Fore.GREEN}  ✓ GPU detected: {device.name}")
                print(f"{Fore.CYAN}    VRAM: {vram_gb:.1f} GB")
                
                # Check if adequate for audio generation
                if vram_gb >= 8:
                    print(f"{Fore.GREEN}    Adequate for audio generation")
                    self.checks_passed += 1
                else:
                    print(f"{Fore.YELLOW}    Low VRAM - may have issues")
                    print(f"{Fore.YELLOW}    Recommended: 8GB+ for HeartMuLa")
                    self.warnings += 1
                
                return True
            else:
                print(f"{Fore.RED}  ✗ No CUDA GPU detected")
                print(f"{Fore.RED}    GPU required for audio generation")
                self.checks_failed += 1
                return False
        
        except ImportError:
            print(f"{Fore.RED}  ✗ PyTorch not installed")
            self.checks_failed += 1
            return False
    
    def check_config_files(self):
        """Check configuration files"""
        print(f"\n{Fore.WHITE}Checking Configuration:")
        
        # Find AGANCY directory
        current = Path.cwd()
        agancy_dir = None
        
        for parent in [current] + list(current.parents):
            test_agancy = parent / "GROUND_TRUTH_ComboAi" / "AGANCY"
            if test_agancy.exists():
                agancy_dir = test_agancy
                break
        
        if not agancy_dir:
            print(f"{Fore.RED}  ✗ AGANCY directory not found")
            self.checks_failed += 1
            return False
        
        # Check key files
        key_files = {
            "orphio_config.py": "Configuration",
            "orphio_engine.py": "Audio engine",
            "lmstudio_controler.py": "LLM controller",
            "Blueprint_Executor.py": "Album generator",
            "tags.json": "Tag library"
        }
        
        all_ok = True
        for filename, description in key_files.items():
            filepath = agancy_dir / filename
            if not self.check(
                f"  {description}",
                filepath.exists(),
                f"Missing: {filepath}"
            ):
                all_ok = False
        
        return all_ok
    
    def check_producer_strategies(self):
        """Check producer strategy files"""
        print(f"\n{Fore.WHITE}Checking Producer Strategies:")
        
        # Find strategies directory
        current = Path.cwd()
        strategies_dir = None
        
        for parent in [current] + list(current.parents):
            test_dir = parent / "GROUND_TRUTH_ComboAi" / "AGANCY" / "PRODUCER_STRATEGIES"
            if test_dir.exists():
                strategies_dir = test_dir
                break
        
        if not strategies_dir:
            print(f"{Fore.YELLOW}  ⚠ PRODUCER_STRATEGIES directory not found")
            self.warnings += 1
            return False
        
        # Count strategy files
        strategy_files = list(strategies_dir.glob("*.json"))
        
        if strategy_files:
            print(f"{Fore.GREEN}  ✓ Found {len(strategy_files)} strategies")
            for strategy_file in strategy_files:
                print(f"{Fore.CYAN}    - {strategy_file.name}")
            self.checks_passed += 1
            return True
        else:
            print(f"{Fore.YELLOW}  ⚠ No strategy files found")
            self.warnings += 1
            return False
    
    def print_summary(self):
        """Print check summary"""
        print(f"\n{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.WHITE}SUMMARY:")
        print(f"  {Fore.GREEN}Passed:  {self.checks_passed}")
        print(f"  {Fore.YELLOW}Warnings: {self.warnings}")
        print(f"  {Fore.RED}Failed:  {self.checks_failed}")
        
        print(f"\n{Fore.WHITE}Status: ", end="")
        if self.checks_failed == 0:
            if self.warnings == 0:
                print(f"{Fore.GREEN}✓ ALL CHECKS PASSED - READY TO RUN")
                print(f"\n{Fore.CYAN}Run the production studio:")
                print(f"{Fore.WHITE}  python OrphioProductionStudio_COMPLETE.py")
            else:
                print(f"{Fore.YELLOW}⚠ READY WITH WARNINGS")
                print(f"{Fore.YELLOW}  System will work but may have issues")
        else:
            print(f"{Fore.RED}✗ CRITICAL ISSUES FOUND")
            print(f"{Fore.RED}  Fix errors before running")
        
        print(f"{Fore.CYAN}{'=' * 70}\n")
    
    def run_all_checks(self):
        """Run all system checks"""
        self.print_header()
        
        # Core checks
        self.check_python_version()
        self.check_imports()
        self.check_file_structure()
        self.check_config_files()
        
        # Model checks
        self.check_models()
        
        # Runtime checks
        self.check_gpu()
        self.check_lm_studio()
        
        # Optional checks
        self.check_producer_strategies()
        
        # Summary
        self.print_summary()
        
        return self.checks_failed == 0


def main():
    """Run system checker"""
    checker = SystemChecker()
    success = checker.run_all_checks()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
