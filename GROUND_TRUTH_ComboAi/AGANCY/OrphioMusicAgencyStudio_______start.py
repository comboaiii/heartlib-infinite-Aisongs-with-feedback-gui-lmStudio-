import sys
import json
import threading
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QFrame,
    QProgressBar, QComboBox, QMessageBox, QSlider, QDialog, QScrollArea, QCheckBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QTextCursor

# Localization
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from agency_styles import MODERN_STYLES
from orphio_config import conf
from orphio_engine import OrphioEngine

class TagLibraryDialog(QDialog):
    def __init__(self, current_tags_str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Global Tag Library")
        self.setMinimumSize(600, 500)
        self.setStyleSheet(MODERN_STYLES + "QDialog { background-color: #09090B; }")
        self.selected_tags = [t.strip().lower() for t in current_tags_str.split(",") if t.strip()]
        self.checkboxes = []
        self.init_ui()
        self.load_tags()

    def init_ui(self):
        layout = QVBoxLayout(self)
        header = QLabel("SELECT GENRE & MOOD TAGS", objectName="SectionHeader")
        layout.addWidget(header)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Filter tags...")
        self.search_bar.textChanged.connect(self.filter_tags)
        layout.addWidget(self.search_bar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.container = QWidget(objectName="TagContainer")
        self.grid_layout = QGridLayout(self.container)
        scroll.setWidget(self.container)
        layout.addWidget(scroll)
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("CANCEL", objectName="SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        apply_btn = QPushButton("APPLY", objectName="PrimaryBtn")
        apply_btn.clicked.connect(self.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)

    def load_tags(self):
        try:
            with open(conf.TAGS_FILE, 'r') as f:
                tags = json.load(f)
            tags.sort(); row, col = 0, 0
            for tag in tags:
                cb = QCheckBox(tag)
                if tag.lower() in self.selected_tags: cb.setChecked(True)
                self.checkboxes.append(cb); self.grid_layout.addWidget(cb, row, col)
                col += 1
                if col > 3: col, row = 0, row + 1
        except: pass

    def filter_tags(self, text):
        for cb in self.checkboxes: cb.setVisible(text.lower() in cb.text().lower())

    def get_result(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]

class WorkerSignals(QObject):
    log = pyqtSignal(str)
    finished_draft = pyqtSignal(str, list)
    finished_decorate = pyqtSignal(str)
    finished_render = pyqtSignal(str)
    error = pyqtSignal(str)

class OrphioStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ORPHIO AGENCY - Advanced Studio")
        self.resize(1400, 950)
        self.setStyleSheet(MODERN_STYLES)
        self.signals = WorkerSignals()
        self.signals.log.connect(self.log_system)
        self.signals.finished_draft.connect(self.on_draft_complete)
        self.signals.finished_decorate.connect(self.on_decorate_complete)
        self.signals.finished_render.connect(self.on_render_complete)
        self.signals.error.connect(self.on_error)
        self.engine = OrphioEngine(log_callback=lambda m: self.signals.log.emit(m))
        self.ai_generated_tags = []
        self.init_ui()

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0); main_layout.setSpacing(0)
        sidebar = QFrame(objectName="Sidebar"); sidebar.setFixedWidth(380)
        side_lyt = QVBoxLayout(sidebar); side_lyt.setContentsMargins(20,20,20,20)
        title = QLabel("ORPHIO AGENCY"); title.setStyleSheet("color:#FF9F1A; font-weight:900; font-size:22px;")
        side_lyt.addWidget(title)
        side_lyt.addWidget(QLabel("SONG CONCEPT", objectName="SectionHeader"))
        self.input_topic = QLineEdit(); self.input_topic.setPlaceholderText("Enter topic...")
        side_lyt.addWidget(self.input_topic)
        side_lyt.addWidget(QLabel("TAG STRATEGY", objectName="SectionHeader"))
        self.combo_strategy = QComboBox(); self.combo_strategy.addItems(["AI GENERATED", "USER DEFINED", "MIXED (AI + USER)"])
        side_lyt.addWidget(self.combo_strategy)
        tag_row = QHBoxLayout()
        self.input_manual_tags = QLineEdit(); self.input_manual_tags.setPlaceholderText("Manual tags...")
        lib_btn = QPushButton("LIBRARY", objectName="SecondaryBtn"); lib_btn.setFixedWidth(80)
        lib_btn.clicked.connect(self.open_tag_library)
        tag_row.addWidget(self.input_manual_tags); tag_row.addWidget(lib_btn)
        side_lyt.addLayout(tag_row)
        self.btn_draft = QPushButton("1. DRAFT LYRICS", objectName="PrimaryBtn")
        self.btn_draft.clicked.connect(self.run_draft_thread); side_lyt.addWidget(self.btn_draft)
        side_lyt.addWidget(QLabel("DURATION (SECONDS)", objectName="SectionHeader"))
        dur_row = QHBoxLayout()
        self.slider_duration = QSlider(Qt.Orientation.Horizontal); self.slider_duration.setRange(10, 300); self.slider_duration.setValue(60)
        self.lbl_dur_val = QLabel("60s"); self.lbl_dur_val.setStyleSheet("color:#FF9F1A; font-weight:bold;")
        self.slider_duration.valueChanged.connect(lambda v: self.lbl_dur_val.setText(f"{v}s"))
        dur_row.addWidget(self.slider_duration); dur_row.addWidget(self.lbl_dur_val)
        side_lyt.addLayout(dur_row)
        self.btn_render = QPushButton("3. RENDER AUDIO", objectName="PrimaryBtn")
        self.btn_render.setStyleSheet("background-color:#2ECC71; color:black;")
        self.btn_render.clicked.connect(self.run_render_thread); side_lyt.addWidget(self.btn_render)
        side_lyt.addStretch()
        self.txt_log = QTextEdit(); self.txt_log.setReadOnly(True); self.txt_log.setFixedHeight(200)
        self.txt_log.setStyleSheet("font-family:Consolas; background-color:#050505;"); side_lyt.addWidget(self.txt_log)
        main_layout.addWidget(sidebar)
        editor_frame = QFrame(objectName="MainEditor"); ed_lyt = QVBoxLayout(editor_frame)
        tool_row = QHBoxLayout()
        tool_row.addWidget(QLabel("SONIC ARCHITECT:", objectName="SectionHeader"))
        self.combo_decorator = QComboBox(); self.combo_decorator.addItems(list(conf.DECORATOR_SCHEMAS.keys()))
        self.btn_decorate = QPushButton("2. DECORATE", objectName="SecondaryBtn"); self.btn_decorate.clicked.connect(self.run_decorate_thread)
        tool_row.addWidget(self.combo_decorator); tool_row.addWidget(self.btn_decorate); tool_row.addStretch()
        ed_lyt.addLayout(tool_row)
        self.txt_lyrics = QTextEdit(); self.txt_lyrics.setPlaceholderText("Lyrics appear here...")
        self.txt_lyrics.setFont(QFont("Inter", 13)); ed_lyt.addWidget(self.txt_lyrics)
        self.progress = QProgressBar(); self.progress.setTextVisible(False); self.progress.setFixedHeight(4)
        ed_lyt.addWidget(self.progress); main_layout.addWidget(editor_frame)

    def get_active_tags(self):
        strat = self.combo_strategy.currentText()
        manual = [t.strip().lower() for t in self.input_manual_tags.text().split(",") if t.strip()]
        if strat == "AI GENERATED": return self.ai_generated_tags
        if strat == "USER DEFINED": return manual
        return list(set(self.ai_generated_tags + manual))

    def log_system(self, msg):
        self.txt_log.append(f"> {msg}"); self.txt_log.moveCursor(QTextCursor.MoveOperation.End)

    def lock_ui(self, busy):
        self.btn_draft.setEnabled(not busy); self.btn_render.setEnabled(not busy)
        self.progress.setRange(0, 0 if busy else 100)

    def open_tag_library(self):
        dlg = TagLibraryDialog(self.input_manual_tags.text(), self)
        if dlg.exec(): self.input_manual_tags.setText(", ".join(dlg.get_result()))

    def run_draft_thread(self):
        topic = self.input_topic.text()
        if not topic: return
        self.lock_ui(True)
        threading.Thread(target=self._bg_draft, args=(topic,), daemon=True).start()

    def _bg_draft(self, topic):
        try:
            l, t = self.engine.generate_lyrics_stage(topic)
            self.signals.finished_draft.emit(l, t)
        except Exception as e: self.signals.error.emit(str(e))

    def on_draft_complete(self, l, t):
        self.txt_lyrics.setPlainText(l); self.ai_generated_tags = t; self.lock_ui(False)

    def run_decorate_thread(self):
        l = self.txt_lyrics.toPlainText()
        if len(l) < 10: return
        conf.CURRENT_DECORATOR_SCHEMA = self.combo_decorator.currentText()
        self.lock_ui(True)
        threading.Thread(target=self._bg_decorate, args=(l, self.get_active_tags()), daemon=True).start()

    def _bg_decorate(self, l, t):
        try:
            res = self.engine.decorate_lyrics_stage(l, t)
            self.signals.finished_decorate.emit(res)
        except Exception as e: self.signals.error.emit(str(e))

    def on_decorate_complete(self, res):
        self.txt_lyrics.setPlainText(res); self.lock_ui(False)

    def run_render_thread(self):
        topic = self.input_topic.text() or "Untitled"
        l = self.txt_lyrics.toPlainText(); tags = self.get_active_tags(); d = self.slider_duration.value()
        self.lock_ui(True)
        threading.Thread(target=self._bg_render, args=(topic, l, tags, d), daemon=True).start()

    def _bg_render(self, topic, l, t, d):
        try:
            path, ledg = self.engine.render_audio_stage(topic, l, t, d)
            self.signals.finished_render.emit(path)
        except Exception as e: self.signals.error.emit(str(e))

    def on_render_complete(self, path):
        self.lock_ui(False); QMessageBox.information(self, "Success", f"Saved: {path}")

    def on_error(self, e):
        self.lock_ui(False); QMessageBox.critical(self, "Error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv); win = OrphioStudio(); win.show(); sys.exit(app.exec())