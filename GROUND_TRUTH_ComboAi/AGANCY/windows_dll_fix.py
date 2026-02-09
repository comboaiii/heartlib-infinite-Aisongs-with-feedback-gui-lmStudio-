"""
CRITICAL: This module MUST be imported FIRST
Configures Windows environment to prevent DLL loading errors
"""

import os
import sys

# Fix DLL loading issues
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

# Add Windows DLL directories
if sys.platform == "win32":
    try:
        os.add_dll_directory(r"C:\Windows\System32")
        os.add_dll_directory(r"C:\Windows\SysWOW64")
    except (AttributeError, OSError):
        pass

print("[DLL FIX] Environment configured for Windows")
