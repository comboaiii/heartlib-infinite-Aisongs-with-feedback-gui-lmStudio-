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

# agency_styles.py
# THEME: CYBER GREEN & DARK NOIR

MODERN_STYLES = """
/* 0. GLOBAL RESET */
* {
    selection-background-color: #00FF7F !important;
    selection-color: #000000 !important;
    outline: none;
}

QMainWindow, QDialog, QFrame, QAbstractScrollArea {
    background-color: #09090B !important;
    color: #E4E4E7 !important;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

/* 1. SECTION HEADERS */
QLabel#SectionHeader {
    color: #71717A !important;
    font-weight: 800;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-top: 15px;
    margin-bottom: 5px;
}

/* 2. MAIN INPUT AREAS */
QPlainTextEdit#TopicInput, QTextEdit, QLineEdit {
    background-color: #050505 !important;
    border: 1px solid #27272A !important;
    border-radius: 6px;
    padding: 10px;
    color: #FFFFFF !important;
}
QPlainTextEdit#TopicInput:focus, QTextEdit:focus, QLineEdit:focus {
    border: 1px solid #00FF7F !important;
}

/* Specific styling for the Live Tags field to make it "Active Green" */
QLineEdit#LiveTags {
    color: #00FF7F !important;
    font-weight: bold;
    background-color: #0D0D0F !important;
    border: 1px solid #3F3F46 !important;
}

/* 3. SIDEBAR & SPLITTERS */
QFrame#Sidebar {
    background-color: #0D0D0F !important;
    border-right: 1px solid #18181B !important;
}

QSplitter::handle {
    background-color: #18181B;
}
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }

/* 4. THE TAG LIBRARY TILES (High-End Badge Look) */
QCheckBox#TagTile {
    color: #A1A1AA !important;
    background-color: #121214 !important;
    border: 1px solid #27272A !important;
    border-radius: 4px;
    padding: 12px 5px;
    font-weight: bold;
}
QCheckBox#TagTile::indicator { width: 0px; height: 0px; } 

QCheckBox#TagTile:hover {
    background-color: #1C1C1F !important;
    border: 1px solid #3F3F46 !important;
    color: #FFFFFF !important;
}
QCheckBox#TagTile:checked {
    background-color: #00FF7F !important;
    color: #000000 !important;
    border: 1px solid #00FF7F !important;
}

/* 5. BUTTONS */
QPushButton#PrimaryBtn {
    background-color: #00FF7F !important;
    color: #000000 !important;
    font-weight: 900;
    border-radius: 4px;
    padding: 14px;
    text-transform: uppercase;
}
QPushButton#PrimaryBtn:hover { 
    background-color: #22C55E !important; 
}

QPushButton#SecondaryBtn {
    background-color: #18181B !important;
    border: 1px solid #3F3F46 !important;
    color: #E4E4E7 !important;
    font-weight: bold;
}
QPushButton#SecondaryBtn:hover { 
    border: 1px solid #00FF7F !important; 
    color: #00FF7F !important; 
}

QPushButton#FolderBtn {
    background-color: transparent !important;
    border: 1px solid #27272A !important;
    color: #00FF7F !important;
    font-size: 16px;
}
QPushButton#FolderBtn:hover { 
    background-color: #00FF7F !important; 
    color: #000000 !important; 
}

/* 6. TABS (Album Queue / Lyric Editor) */
/* These target the buttons used as tabs in the center pane */
QPushButton#TabBtn {
    background-color: #18181B;
    color: #71717A;
    border: none;
    padding: 12px 20px;
    font-weight: bold;
    text-transform: uppercase;
    font-size: 11px;
}
QPushButton#TabBtn:hover {
    color: #00FF7F;
}
QPushButton#TabBtn[active="true"] {
    background-color: #00FF7F !important;
    color: #000000 !important;
}

/* 7. VAULT & LISTS */
QListWidget {
    background-color: #050505 !important;
    border: 1px solid #18181B !important;
    border-radius: 6px;
}
QListWidget::item {
    padding: 10px;
    border-bottom: 1px solid #0D0D0F !important;
}
QListWidget::item:selected {
    background-color: #18181B !important;
    color: #00FF7F !important;
    border-left: 3px solid #00FF7F !important;
}

/* 8. PROGRESS BAR (Batch Rendering) */
QProgressBar {
    background-color: #18181B;
    border: none;
    border-radius: 2px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #00FF7F;
    border-radius: 2px;
}

/* 9. PRO-AUDIO SLIDERS */
QSlider::groove:horizontal {
    height: 4px;
    background: #18181B;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #00FF7F;
    border: 2px solid #09090B;
    width: 16px; height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}

/* 10. INSPECTOR GRID LABELS */
QLabel#SpecLabel {
    color: #00FF7F !important;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 11px;
    background: #121214;
    padding: 5px;
    border-radius: 3px;
}

/* 11. SCROLLBARS */
QScrollBar:vertical {
    background: #09090B !important;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #27272A !important;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #3F3F46 !important;
}
QScrollBar::add-line, QScrollBar::sub-line { height: 0px; }

/* 12. VIEWPORT FIX */
QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {
    background-color: #09090B !important;
    border: none !important;
}
"""