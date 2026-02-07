# agency_styles.py

MODERN_STYLES = """
/* 1. GLOBAL DEFAULTS */
QMainWindow, QDialog {
    background-color: #09090B;
}

QWidget {
    color: #E4E4E7;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    font-size: 13px;
}

/* 2. PANELS & SIDEBAR */
QFrame#Sidebar {
    background-color: #121217;
    border-right: 1px solid #27272A;
}

QFrame#MainEditor {
    background-color: #09090B;
}

/* 3. SECTION HEADERS (Muted DAW Style) */
QLabel#SectionHeader {
    color: #71717A;
    font-weight: 800;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-top: 15px;
    margin-bottom: 5px;
}

/* 4. INPUT FIELDS (Clean Carbon) */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {
    background-color: #050505;
    border: 1px solid #3F3F46;
    border-radius: 6px;
    padding: 10px;
    color: #FFFFFF;
    selection-background-color: #FF9F1A;
    selection-color: #000000;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #FF9F1A;
}

/* 5. TAB WIDGET (Dark Workflow Style) */
QTabWidget::pane {
    border: 1px solid #27272A;
    background-color: #09090B;
    top: -1px;
}

QTabBar::tab {
    background-color: #18181B;
    border: 1px solid #27272A;
    padding: 10px 25px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    color: #71717A;
    font-weight: bold;
}

QTabBar::tab:hover {
    background-color: #27272A;
    color: #E4E4E7;
}

QTabBar::tab:selected {
    background-color: #09090B;
    color: #FF9F1A;
    border-bottom: 2px solid #FF9F1A;
}

/* 6. BUTTONS */
/* Action Button (Amber Gradient) */
QPushButton#PrimaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFB020, stop:1 #FF8A00);
    color: #000000;
    font-weight: 900;
    border-radius: 6px;
    padding: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

QPushButton#PrimaryBtn:hover {
    background: #FFB020;
}

QPushButton#PrimaryBtn:pressed {
    background: #D97706;
}

/* Utility Button (Dark Muted) */
QPushButton#SecondaryBtn {
    background-color: #27272A;
    border: 1px solid #3F3F46;
    border-radius: 6px;
    padding: 8px;
    font-weight: 600;
}

QPushButton#SecondaryBtn:hover {
    border: 1px solid #FF9F1A;
    color: #FF9F1A;
    background-color: #2D2D33;
}

/* 7. DROPDOWNS (ComboBox) */
QComboBox {
    background-color: #18181B;
    border: 1px solid #3F3F46;
    border-radius: 6px;
    padding: 8px 12px;
    color: #E4E4E7;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox QAbstractItemView {
    background-color: #18181B;
    border: 1px solid #3F3F46;
    selection-background-color: #FF9F1A;
    selection-color: #000000;
    outline: none;
}

/* 8. THE MANIFEST BOX (Status Display) */
QFrame#ManifestBox {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1A1A1A, stop:1 #0D0D0D);
    border-left: 4px solid #FF9F1A;
    border-radius: 4px;
    padding: 15px;
}

/* 9. TAG BUBBLES (High Contrast Neon) */
QLabel#TagHighlight {
    color: #FF9F1A;
    background-color: rgba(255, 159, 26, 0.12);
    border: 1px solid rgba(255, 159, 26, 0.4);
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 800;
    text-transform: lowercase;
}

/* 10. CUSTOM CHECKBOXES (Tag Matrix) */
QCheckBox {
    spacing: 10px;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    background-color: #050505;
    border: 1px solid #3F3F46;
    border-radius: 5px;
}

QCheckBox::indicator:hover {
    border: 1px solid #FF9F1A;
}

QCheckBox::indicator:checked {
    background-color: #FF9F1A;
    border: 1px solid #FFB020;
    /* Drawing a custom tick mark using a standard bullet or image */
    image: url(none); 
}

/* 11. SLIDERS (Modern Cyan/Amber) */
QSlider::groove:horizontal {
    border: 1px solid #27272A;
    height: 4px;
    background: #18181B;
    margin: 2px 0;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #FF9F1A;
    border: 1px solid #FFB020;
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}

/* 12. SCROLLBARS (Minimalist Dark) */
QScrollBar:vertical {
    background: #09090B;
    width: 12px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: #27272A;
    min-height: 20px;
    border-radius: 6px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: #3F3F46;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* 13. MISC UI ELEMENTS */
QGroupBox {
    border: 1px solid #27272A;
    border-radius: 8px;
    margin-top: 15px;
    padding-top: 10px;
    font-weight: bold;
    color: #71717A;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
"""