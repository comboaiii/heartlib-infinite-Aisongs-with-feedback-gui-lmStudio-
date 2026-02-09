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

import json
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QScrollArea, QWidget,
                             QCheckBox, QPushButton, QLineEdit, QGridLayout,
                             QSizePolicy)
from PyQt6.QtCore import Qt
from orphio_config import conf


class TagSelectorDialog(QDialog):
    def __init__(self, current_tags_str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Global Tag Library")
        self.setMinimumSize(800, 700)

        self.initially_selected = [t.strip().lower() for t in current_tags_str.split(",") if t.strip()]
        self.checkboxes = []
        self.init_ui()
        self.load_tags()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filter genre or mood...")
        self.search_input.textChanged.connect(self.filter_tags)
        layout.addWidget(self.search_input)

        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.container = QWidget()
        self.container.setObjectName("TagContainer")
        # Ensure background is dark
        self.container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(8)  # Space between tiles

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        # Apply Button
        self.ok_btn = QPushButton("APPLY SELECTED TAGS")
        self.ok_btn.setObjectName("PrimaryBtn")
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.clicked.connect(self.accept)
        layout.addWidget(self.ok_btn)

    def load_tags(self):
        try:
            if not conf.TAGS_FILE.exists(): return
            with open(conf.TAGS_FILE, 'r') as f:
                data = json.load(f)

            # Check if it's the new Dict structure or old List structure
            if isinstance(data, list):
                # Fallback for old style
                all_tags = sorted(data)
                self._populate_grid(all_tags, 0)
            else:
                # NEW HIERARCHICAL STYLE
                row_pointer = 0
                for category, tags in sorted(data.items()):
                    # Add a Section Header
                    lbl = QLabel(category)
                    lbl.setStyleSheet("color: #FF9F1A; font-weight: bold; margin-top: 10px;")
                    self.grid_layout.addWidget(lbl, row_pointer, 0, 1, 4)  # Span 4 columns
                    row_pointer += 1

                    # Add the tags for this category
                    row_pointer = self._populate_grid(tags, row_pointer)

        except Exception as e:
            print(f"Error loading tags: {e}")

    def _populate_grid(self, tags, start_row):
        col = 0
        row = start_row
        for tag in tags:
            cb = QCheckBox(tag)
            cb.setObjectName("TagTile")
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

            # Logic: If checking this, uncheck others in same category?
            # For now, we trust the user, but visually grouping helps.

            if tag.lower() in self.initially_selected:
                cb.setChecked(True)

            self.checkboxes.append(cb)
            self.grid_layout.addWidget(cb, row, col)

            col += 1
            if col > 3:  # 4 tiles per row
                col = 0
                row += 1

        # Return the next available row
        return row + 1 if col == 0 else row + 1

    def filter_tags(self, text):
        text = text.lower()
        for cb in self.checkboxes:
            cb.setVisible(text in cb.text().lower())

    def get_selected_tags(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]