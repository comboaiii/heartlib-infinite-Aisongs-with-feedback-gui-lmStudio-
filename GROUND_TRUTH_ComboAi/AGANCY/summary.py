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
from datetime import datetime
from pathlib import Path

# --- Configuration ---

# The name of the output file where the summary will be saved.
OUTPUT_FILENAME = "summary.txt"

# The intended name of this script file to exclude it.
SCRIPT_FILENAME = "_summary.py"

# --- MODIFICATION TIME FLAG ---
# Set to True to show modification times at the end of the filename, False to hide them.
SHOW_MOD_TIME = True

# Byte limit to prevent loading massive files into memory.
MAX_FILE_SIZE = 5_000_000  # 5 MB

# Character limit for inclusion in the document.
MAX_CHAR_LIMIT = 20000

# A set of all files and directories to be explicitly excluded.
EXCLUDED_ITEMS = {
    "__pycache__", "node_modules", "venv", ".git",
    ".vscode", ".idea", "dist", "build", "target",
    ".DS_Store", "tool_stats.json",
    OUTPUT_FILENAME,
    SCRIPT_FILENAME,
}


def is_text_file(file_path):
    """Checks if a file is likely a text file."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' not in chunk
    except (IOError, OSError):
        return False


def should_exclude(item_name):
    """Determines if a given file or directory should be excluded."""
    if item_name in EXCLUDED_ITEMS:
        return True
    if item_name.startswith('.') and item_name != ".env":
        return True
    if item_name == os.path.basename(__file__):
        return True
    return False


def get_file_content(file_path):
    """Reads file content with character limit and error handling."""
    try:
        file_size = os.path.getsize(file_path)

        if file_size > MAX_FILE_SIZE:
            return f"[File too large: {file_size / (1024 * 1024):.2f} MB]"

        if not is_text_file(file_path):
            return "[Binary file]"

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

            if len(content) > MAX_CHAR_LIMIT:
                return f"[Content omitted: Exceeds {MAX_CHAR_LIMIT} character limit]"

            content = content.strip()
            return content if content else "[Empty file]"

    except Exception as e:
        return f"[Error reading file: {e}]"


def write_tree(root_path, output_file, prefix="", include_content=True):
    """
    Recursively writes the directory tree.
    """
    try:
        all_items = os.listdir(root_path)
        valid_items = [item for item in all_items if not should_exclude(item)]
        valid_items.sort(key=lambda x: (not os.path.isdir(os.path.join(root_path, x)), x.lower()))
    except OSError as e:
        output_file.write(f"{prefix}[Error: Cannot access directory - {e}]\n")
        return

    for i, item_name in enumerate(valid_items):
        item_path = os.path.join(root_path, item_name)
        is_last = (i == len(valid_items) - 1)
        connector = "└── " if is_last else "├── "
        child_prefix = prefix + ("    " if is_last else "│   ")

        # Get modification time if flag is enabled
        mod_time_str = ""
        if SHOW_MOD_TIME:
            try:
                mtime = os.path.getmtime(item_path)
                dt = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                mod_time_str = f"  [Mod: {dt}]"
            except Exception:
                mod_time_str = " [Time Error]"

        if os.path.isdir(item_path):
            output_file.write(f"{prefix}{connector}{item_name}/{mod_time_str}\n")
            write_tree(item_path, output_file, child_prefix, include_content)
        else:
            output_file.write(f"{prefix}{connector}{item_name}{mod_time_str}\n")

            if include_content:
                content = get_file_content(item_path)
                # Only show "Content:" label for actual text
                if not (content.startswith("[") and content.endswith("]")):
                    output_file.write(f"{child_prefix}Content:\n")

                for line in content.splitlines():
                    output_file.write(f"{child_prefix}{line}\n")
                output_file.write(f"{child_prefix}\n")


def create_summary():
    """Main function to generate the directory summary file."""
    script_dir = Path(__file__).resolve().parent
    output_path = script_dir / OUTPUT_FILENAME

    print(f"Creating summary for: {script_dir}")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            # Header
            f.write("DIRECTORY SUMMARY\n")
            f.write("=" * 60 + "\n")
            f.write(f"Path: {script_dir}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Timestamps: {'Enabled' if SHOW_MOD_TIME else 'Disabled'}\n")
            f.write("=" * 60 + "\n\n")

            # SECTION 1: Detailed Tree (with Contents)
            f.write("SECTION 1: FILE CONTENTS\n")
            f.write("-" * 30 + "\n")
            f.write(f"{script_dir.name}/\n")
            write_tree(str(script_dir), f, prefix="│   ", include_content=True)

            f.write("\n\n")
            f.write("=" * 60 + "\n")
            # SECTION 2: Structure Only
            f.write("SECTION 2: DIRECTORY STRUCTURE\n")
            f.write("-" * 30 + "\n")
            f.write(f"{script_dir.name}/\n")
            write_tree(str(script_dir), f, prefix="│   ", include_content=False)

        print(f"✅ Summary created successfully: {output_path}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    create_summary()