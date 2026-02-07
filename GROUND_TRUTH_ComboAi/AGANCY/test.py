#!/usr/bin/env python3
"""
LM Studio Connection Diagnostic Tool
Run this to verify LM Studio is properly configured
"""

import requests
import json
from colorama import Fore, Style, init

init(autoreset=True)

LM_STUDIO_URL = "http://localhost:1234/v1"

print(f"\n{Fore.CYAN}{'=' * 70}")
print(f"{Fore.WHITE}🔍 LM STUDIO CONNECTION DIAGNOSTIC")
print(f"{Fore.CYAN}{'=' * 70}\n")

# Test 1: Can we connect to LM Studio?
print(f"{Fore.YELLOW}[Test 1] Checking if LM Studio is running...")
try:
    response = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
    print(f"{Fore.GREEN}✅ LM Studio is running and responding")
    print(f"{Fore.WHITE}   Status Code: {response.status_code}")
except requests.exceptions.ConnectionError:
    print(f"{Fore.RED}❌ FAILED: Cannot connect to LM Studio")
    print(f"{Fore.YELLOW}   Make sure LM Studio is running")
    print(f"{Fore.YELLOW}   Expected URL: {LM_STUDIO_URL}")
    exit(1)
except Exception as e:
    print(f"{Fore.RED}❌ FAILED: {e}")
    exit(1)

# Test 2: Is a model loaded?
print(f"\n{Fore.YELLOW}[Test 2] Checking for loaded models...")
try:
    response = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
    data = response.json()

    if 'data' in data and len(data['data']) > 0:
        print(f"{Fore.GREEN}✅ Models are loaded:")
        for model in data['data']:
            model_id = model.get('id', 'unknown')
            print(f"{Fore.WHITE}   📦 {model_id}")
    else:
        print(f"{Fore.RED}❌ FAILED: No models are loaded")
        print(f"{Fore.YELLOW}   Please load a model in LM Studio:")
        print(f"{Fore.WHITE}   1. Open LM Studio")
        print(f"{Fore.WHITE}   2. Go to 'My Models'")
        print(f"{Fore.WHITE}   3. Click 'Load' on any model")
        print(f"{Fore.WHITE}   4. Wait for it to fully load")
        exit(1)
except Exception as e:
    print(f"{Fore.RED}❌ FAILED: {e}")
    exit(1)

# Test 3: Can we make a simple chat completion?
print(f"\n{Fore.YELLOW}[Test 3] Testing chat completion...")
try:
    test_payload = {
        "model": "local-model",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello!' and nothing else."}
        ],
        "temperature": 0.7,
        "max_tokens": 10
    }

    response = requests.post(
        f"{LM_STUDIO_URL}/chat/completions",
        json=test_payload,
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()

        # Check response structure
        if 'choices' in data and len(data['choices']) > 0:
            content = data['choices'][0]['message']['content']
            print(f"{Fore.GREEN}✅ Chat completion successful")
            print(f"{Fore.WHITE}   Response: {Fore.CYAN}{content.strip()}")
        else:
            print(f"{Fore.RED}❌ FAILED: Unexpected response structure")
            print(f"{Fore.YELLOW}   Response data:")
            print(f"{Fore.WHITE}{json.dumps(data, indent=2)[:300]}")
    else:
        print(f"{Fore.RED}❌ FAILED: HTTP {response.status_code}")
        print(f"{Fore.YELLOW}   Response: {response.text[:200]}")

except requests.exceptions.Timeout:
    print(f"{Fore.RED}❌ FAILED: Request timed out (>30s)")
    print(f"{Fore.YELLOW}   Model might be too slow or stuck")
except Exception as e:
    print(f"{Fore.RED}❌ FAILED: {e}")

# Test 4: Check model capabilities
print(f"\n{Fore.YELLOW}[Test 4] Checking model information...")
try:
    response = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
    data = response.json()

    if 'data' in data and len(data['data']) > 0:
        model = data['data'][0]
        model_id = model.get('id', 'unknown')

        print(f"{Fore.GREEN}✅ Active Model Details:")
        print(f"{Fore.WHITE}   ID: {Fore.CYAN}{model_id}")

        # Try to get more info
        if 'object' in model:
            print(f"{Fore.WHITE}   Type: {model.get('object', 'N/A')}")
        if 'owned_by' in model:
            print(f"{Fore.WHITE}   Owner: {model.get('owned_by', 'N/A')}")

except Exception as e:
    print(f"{Fore.YELLOW}⚠️  Could not retrieve detailed model info: {e}")

# Final Summary
print(f"\n{Fore.CYAN}{'=' * 70}")
print(f"{Fore.GREEN}✅ ALL TESTS PASSED!")
print(f"{Fore.CYAN}{'=' * 70}")
print(f"\n{Fore.WHITE}Your LM Studio setup is working correctly.")
print(f"{Fore.WHITE}You can now run Orphio AGANCY without issues.\n")
print(f"{Fore.CYAN}Next step:")
print(f"{Fore.WHITE}  python orphio_gui.py\n")