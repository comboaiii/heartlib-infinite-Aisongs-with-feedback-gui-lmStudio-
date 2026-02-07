import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QScrollArea,
                               QWidget, QCheckBox, QPushButton, QLineEdit, QGridLayout)
from PySide6.QtCore import Qt
from orphio_config import conf


class TagSelectorDialog(QDialog):
    def __init__(self, current_tags_str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Genre Tags")
        self.setMinimumSize(500, 600)

        # Parse current tags to pre-check boxes
        self.initially_selected = [t.strip().lower() for t in current_tags_str.split(",") if t.strip()]
        self.checkboxes = []

        self.init_ui()
        self.load_tags()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter tags...")
        self.search_input.textChanged.connect(self.filter_tags)
        layout.addWidget(self.search_input)

        # 2. Scroll Area for Tags
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.grid_layout = QGridLayout(container)
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # 3. Buttons
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("Apply Tags")
        self.ok_btn.setObjectName("PrimaryBtn")  # Use your existing style
        self.ok_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)

    def load_tags(self):
        try:
            with open(conf.TAGS_FILE, 'r') as f:
                tags = json.load(f)

            tags.sort()
            row, col = 0, 0
            for tag in tags:
                cb = QCheckBox(tag)
                if tag.lower() in self.initially_selected:
                    cb.setChecked(True)

                self.checkboxes.append(cb)
                self.grid_layout.addWidget(cb, row, col)

                col += 1
                if col > 2:  # 3 columns
                    col = 0
                    row += 1
        except Exception as e:
            print(f"Error loading tags: {e}")

    def filter_tags(self, text):
        text = text.lower()
        for cb in self.checkboxes:
            cb.setVisible(text in cb.text().lower())

    def get_selected_tags(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]