import sys
import json
import random
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QListWidget, QListWidgetItem, QPushButton,
                               QTextEdit, QLabel, QScrollArea, QFileDialog, QSlider,
                               QGridLayout, QFrame, QMessageBox, QLineEdit, QSplitter,
                               QTabWidget, QGroupBox)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import Qt, QUrl, QTime, QSize
from PySide6.QtGui import QColor, QPainter, QBrush, QLinearGradient, QFont


# --- ROBUST PATH RESOLUTION ---
# Pobieramy absolutną ścieżkę do folderu, w którym znajduje się ten plik .py
SCRIPT_DIR = Path(__file__).parent.absolute()
# Folder z piosenkami jest o poziom wyżej względem GROUND_TRUTH_ComboAi
DEFAULT_VAULT_PATH = SCRIPT_DIR.parent / "outputSongs_ComboAi"

# Jeśli folder nie istnieje obok, sprawdź czy skrypt nie został przeniesiony BEZPOŚREDNIO do piosenek
if not DEFAULT_VAULT_PATH.exists():
    DEFAULT_VAULT_PATH = SCRIPT_DIR

# --- PRO STUDIO THEME COLORS ---
CORE_BLACK = "#0a0a0b"
PANEL_GRAY = "#161617"
BORDER_GRAY = "#2a2a2c"
ACCENT_GREEN = "#00ff7f"
ACCENT_RED = "#ff3b3b"
TEXT_DIM = "#88888e"
TEXT_BRIGHT = "#e1e1e6"

AUDIT_SCHEMA = {
    "VOCAL CHARACTERISTICS": [
        "No Vocals (Inst)", "Male Lead", "Female Lead", "Kid (Boy)", "Kid (Girl)",
        "Chorus/Choir", "Both (Duet)", "Spoken Word", "Vocal Chops", "Harmonies"
    ],
    "TEMPO & RHYTHM": [
        "Very Slow (Adagio/Lento)", "Slow (Andante)", "Normal (Moderato)", "Fast (Allegro)", "Very Fast (Presto)"
    ],
    "EMOTIONAL TONE": [
        "Uplifting/Joyful", "Melancholic/Sad", "Aggressive/Angry", "Dark/Eerie",
        "Chill/Relaxed", "Hopeful/Positive", "Tense/Anxious", "Nostalgic", "Romantic"
    ],
    "GENRE CLASSIFICATION": [
        "Pop", "Rock", "Hip-Hop", "R&B", "EDM-Dance", "Jazz", "Classical", # Changed EDM/Dance to EDM-Dance
        "Lo-Fi", "Cinematic", "Country", "Folk", "Metal", "Ambient", "Synthwave"
    ],
    "INSTRUMENTAL FOCUS": [
        "Strong Bass (808/Sub)", "Prominent Lead Synth-Melody", "Prominent Guitar Riff", # Changed Synth/Melody to Synth-Melody
        "Heavy/Driving Drums", "Full Orchestration-Strings", "Complex Piano-Keys", # Changed Orchestration/Strings to Orchestration-Strings and Piano/Keys to Piano-Keys
        "Sparse Arrangement", "Dense-Layered Arrangement" # Changed Dense/Layered to Dense-Layered
    ],
    "SONG STRUCTURE": [
        "Finished (Clear Intro-Verse-Chorus-Outro)", "Looping-No Clear End", "Abrupt Cut", # Changed Intro/Verse/Chorus/Outro to Intro-Verse-Chorus-Outro and Looping/No Clear End to Looping-No Clear End
        "Instrumental Focus Track", "Vocal Focus Track"
    ],
    "TECHNICAL QUALITY": [
        "Mixing-Clarity", "Clipping-Distortion", "Noise-Hiss", "Glitch Artifacts", # Changed Mixing/Clarity to Mixing-Clarity, Clipping/Distortion to Clipping-Distortion, Noise/Hiss to Noise-Hiss
        "Wide Stereo Image", "Good Dynamics", "Overly Compressed", "Low Quality"
    ]
}

STYLE_SHEET = f"""
QMainWindow {{ background-color: {CORE_BLACK}; }}
QFrame#Sidebar {{ background-color: {CORE_BLACK}; border-right: 1px solid {BORDER_GRAY}; }}
QFrame#GlassPanel {{ background-color: {PANEL_GRAY}; border: 1px solid {BORDER_GRAY}; border-radius: 8px; }}
QWidget {{ background-color: transparent; color: {TEXT_BRIGHT}; }}
QTabWidget::pane {{ border: 1px solid {BORDER_GRAY}; background: {PANEL_GRAY}; top: -1px; }}
QTabBar::tab {{ background: {CORE_BLACK}; color: {TEXT_DIM}; padding: 10px 25px; border: 1px solid {BORDER_GRAY}; border-bottom: none; }}
QTabBar::tab:selected {{ background: {PANEL_GRAY}; color: {ACCENT_GREEN}; border-bottom: 2px solid {ACCENT_GREEN}; }}
QScrollArea {{ border: none; background-color: {PANEL_GRAY}; }}
QScrollArea > QWidget > QWidget {{ background-color: {PANEL_GRAY}; }}
QGroupBox {{
    font-size: 11px;
    font-weight: bold;
    color: {ACCENT_GREEN};
    border: 1px solid {BORDER_GRAY};
    margin-top: 20px;
    padding-top: 15px;
    border-radius: 6px;
    background-color: #121213;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 15px;
    padding: 0 5px;
    background-color: {PANEL_GRAY};
}}
QTextEdit, QLineEdit {{
    background-color: #0d0d0e;
    border: 1px solid {BORDER_GRAY};
    color: #00cc66;
    font-family: 'Consolas', monospace;
}}
"""


class ModernTagBtn(QPushButton):
    def __init__(self, text, initial_score=0):
        super().__init__(text)
        self.tag_name = text
        self.score = initial_score
        self.setMinimumHeight(38)
        self.setCursor(Qt.PointingHandCursor)
        self.update_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.score = (self.score + 1) if self.score < 2 else 0
        elif event.button() == Qt.RightButton:
            self.score = (self.score - 1) if self.score > -2 else 0
        self.update_ui()

    def update_ui(self):
        palette = {
            2: (ACCENT_GREEN, "#000", f"1px solid {ACCENT_GREEN}"),
            1: ("#0a331a", ACCENT_GREEN, f"1px solid #0f4d26"),
            0: ("#1c1c1e", TEXT_DIM, f"1px solid {BORDER_GRAY}"),
            -1: ("#330a0a", ACCENT_RED, "1px solid #4d0f0f"),
            -2: (ACCENT_RED, "#000", f"1px solid {ACCENT_RED}")
        }
        bg, fg, border = palette.get(self.score, palette[0])
        self.setText(f"{self.tag_name} (+{self.score})" if self.score > 0 else (
            f"{self.tag_name} ({self.score})" if self.score < 0 else self.tag_name))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg}; color: {fg}; border: {border};
                border-radius: 4px; font-size: 10px; font-weight: bold; text-transform: uppercase;
            }}
            QPushButton:hover {{ background-color: #2a2a2c; border: 1px solid {ACCENT_GREEN}; color: white; }}
        """)


class WaveformDisplay(QWidget):
    def __init__(self, player):
        super().__init__()
        self.player = player
        self.setFixedHeight(100)
        self.bars = []
        self.pos, self.dur = 0, 1

    def set_data(self, seed_name):
        random.seed(seed_name)
        self.bars = [random.uniform(0.1, 0.9) for _ in range(160)]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(self.rect(), QColor(CORE_BLACK))
        if not self.bars: return
        bar_w = w / len(self.bars)
        progress = (self.pos / self.dur) if self.dur > 0 else 0
        for i, val in enumerate(self.bars):
            bar_h = val * h * 0.7
            x, y = i * bar_w, (h - bar_h) / 2
            color = QColor(ACCENT_GREEN if (i / len(self.bars)) < progress else "#222")
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x, y, bar_w - 2, bar_h, 1, 1)

    def mousePressEvent(self, event):
        if self.dur > 0: self.player.setPosition(int((event.position().x() / self.width()) * self.dur))


class OrphioAuditorPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ORPHIO VAULT AUDITOR PRO")
        self.resize(1400, 950)
        self.setStyleSheet(STYLE_SHEET)

        # Używamy zdefiniowanej ścieżki robust
        self.vault_path = DEFAULT_VAULT_PATH
        self.current_json = None
        self.category_btns = {}

        self.player = QMediaPlayer()
        self.audio_out = QAudioOutput()
        self.player.setAudioOutput(self.audio_out)
        self.player.positionChanged.connect(self.sync_playhead)
        self.player.durationChanged.connect(self.sync_duration)

        self.init_ui()
        self.scan_vault()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal)

        # --- SIDEBAR ---
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        side_layout = QVBoxLayout(sidebar)
        btn_open = QPushButton("📁 MOUNT VAULT")
        btn_open.setStyleSheet(f"background: {PANEL_GRAY}; padding: 12px; border: 1px solid {BORDER_GRAY};")
        btn_open.clicked.connect(self.load_vault_dialog)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter vault...")
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.load_project)
        self.stats_lbl = QLabel("0/0 Audited")

        # Pokazujemy ścieżkę dla pewności w sidebarze
        self.path_lbl = QLabel(f"Path: .../{self.vault_path.name}")
        self.path_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px;")

        side_layout.addWidget(btn_open)
        side_layout.addWidget(self.search_box)
        side_layout.addWidget(self.file_list)
        side_layout.addWidget(self.path_lbl)
        side_layout.addWidget(self.stats_lbl)

        # --- WORKSPACE ---
        workspace = QWidget()
        work_layout = QVBoxLayout(workspace)
        work_layout.setContentsMargins(20, 20, 20, 20)

        header_row = QHBoxLayout()
        self.title_lbl = QLabel("SELECT STEM")
        self.title_lbl.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 24px; font-weight: 900;")
        self.help_lbl = QLabel("🖱 L-CLICK: +SCORE  |  R-CLICK: -SCORE")
        self.help_lbl.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 10px; font-weight: bold; border: 1px solid {BORDER_GRAY}; padding: 5px; border-radius: 4px;")
        header_row.addWidget(self.title_lbl)
        header_row.addStretch()
        header_row.addWidget(self.help_lbl)

        self.wave_view = WaveformDisplay(self.player)
        ctrl_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶ PLAY")
        self.btn_play.setFixedSize(120, 40)
        self.btn_play.setStyleSheet(f"background: {ACCENT_GREEN}; color: #000; font-weight: bold;")
        self.btn_play.clicked.connect(self.toggle_play)
        self.timer_lbl = QLabel("00:00 / 00:00")
        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addWidget(self.timer_lbl)
        ctrl_layout.addStretch()

        self.tabs = QTabWidget()
        tab_align = QWidget()
        ta_layout = QHBoxLayout(tab_align)
        self.lyrics_txt = QTextEdit()
        self.prompt_tags_layout = QGridLayout()
        pt_widget = QWidget()
        pt_widget.setLayout(self.prompt_tags_layout)
        ta_layout.addWidget(self.lyrics_txt, 1)
        ta_layout.addWidget(pt_widget, 1)

        self.tab_discovery = QScrollArea()
        self.tab_discovery.setWidgetResizable(True)
        disc_content = QWidget()
        disc_vbox = QVBoxLayout(disc_content)
        for cat_name, tags in AUDIT_SCHEMA.items():
            group = QGroupBox(cat_name)
            g_layout = QGridLayout(group)
            self.category_btns[cat_name] = []
            for i, tag in enumerate(tags):
                btn = ModernTagBtn(tag)
                g_layout.addWidget(btn, i // 4, i % 4)
                self.category_btns[cat_name].append(btn)
            disc_vbox.addWidget(group)
        self.tab_discovery.setWidget(disc_content)

        self.tabs.addTab(tab_align, "STEM ALIGNMENT")
        self.tabs.addTab(self.tab_discovery, "DISCOVERY & AUDIT")

        footer = QFrame()
        footer.setObjectName("GlassPanel")
        foot_layout = QVBoxLayout(footer)
        score_row = QHBoxLayout()
        self.score_lbl = QLabel("OVERALL SCORE: 5")
        self.score_slider = QSlider(Qt.Horizontal)
        self.score_slider.setRange(1, 10)
        self.score_slider.setValue(5)
        self.score_slider.valueChanged.connect(lambda v: self.score_lbl.setText(f"OVERALL SCORE: {v}"))
        score_row.addWidget(self.score_lbl)
        score_row.addWidget(self.score_slider)

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Qualitative notes...")
        self.btn_commit = QPushButton("COMMIT AUDIT")
        self.btn_commit.setFixedHeight(50)
        self.btn_commit.setStyleSheet(f"background: {TEXT_BRIGHT}; color: #000; font-weight: 900;")
        self.btn_commit.clicked.connect(self.save_audit)

        foot_layout.addLayout(score_row)
        foot_layout.addWidget(self.notes_input)
        foot_layout.addWidget(self.btn_commit)

        work_layout.addLayout(header_row)
        work_layout.addWidget(self.wave_view)
        work_layout.addLayout(ctrl_layout)
        work_layout.addWidget(self.tabs)
        work_layout.addWidget(footer)

        self.splitter.addWidget(sidebar)
        self.splitter.addWidget(workspace)
        main_layout.addWidget(self.splitter)

    def load_vault_dialog(self):
        p = QFileDialog.getExistingDirectory(self, "Open Vault", str(self.vault_path))
        if p:
            self.vault_path = Path(p)
            self.path_lbl.setText(f"Path: .../{self.vault_path.name}")
            self.scan_vault()

    def scan_vault(self):
        self.file_list.clear()
        if not self.vault_path.exists(): return
        jsons = list(self.vault_path.glob("*.json"))
        audited = 0
        for f in sorted(jsons):
            try:
                with open(f, "r", encoding='utf-8') as file:
                    data = json.load(file)
                status = data.get("human_evaluation", {}).get("status", "PENDING")
                icon = "●" if status == "VALIDATED" else "○"
                if status == "VALIDATED": audited += 1
                item = QListWidgetItem(f"{icon}  {data.get('provenance', {}).get('title', f.stem)}")
                item.setData(Qt.UserRole, f.stem)
                self.file_list.addItem(item)
            except:
                pass
        self.stats_lbl.setText(f"{audited}/{len(jsons)} Audited")

    def load_project(self, item):
        self.player.stop()
        stem = item.data(Qt.UserRole)
        self.current_json = self.vault_path / f"{stem}.json"
        wav = self.vault_path / f"{stem}.wav"

        with open(self.current_json, "r", encoding='utf-8') as f:
            data = json.load(f)
        eval_data = data.get("human_evaluation", {})

        self.title_lbl.setText(stem.upper())
        self.lyrics_txt.setPlainText(data.get('configuration', {}).get('input_prompt', {}).get('lyrics', ""))

        # --- FIX APPLIED HERE ---
        # Handle case where score is None or 0 or missing
        raw_score = eval_data.get("overall_score")
        if raw_score is None:
            raw_score = 5
        self.score_slider.setValue(int(raw_score))
        self.score_lbl.setText(f"OVERALL SCORE: {raw_score}")
        # ------------------------

        self.notes_input.setText(eval_data.get("qualitative_notes", ""))

        discovery_saved = eval_data.get("discovery_tags", {})

        # SCHEMA FIX: Handle legacy files where this might be a List
        if isinstance(discovery_saved, list):
            discovery_saved = {tag: 1 for tag in discovery_saved}
        elif not isinstance(discovery_saved, dict):
            discovery_saved = {}

        for cat, btns in self.category_btns.items():
            for btn in btns:
                btn.score = discovery_saved.get(btn.tag_name, 0)
                btn.update_ui()

        while self.prompt_tags_layout.count(): self.prompt_tags_layout.takeAt(0).widget().deleteLater()
        self.prompt_btns = []
        tags = data.get('configuration', {}).get('input_prompt', {}).get('tags', [])
        prompt_scores = eval_data.get("prompt_tag_adherence", {})
        for i, t in enumerate(tags):
            btn = ModernTagBtn(t, prompt_scores.get(t, 0) if isinstance(prompt_scores, dict) else 0)
            self.prompt_tags_layout.addWidget(btn, i // 2, i % 2)
            self.prompt_btns.append(btn)

        if wav.exists():
            self.player.setSource(QUrl.fromLocalFile(str(wav.absolute())))
            self.wave_view.set_data(stem)

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶ PLAY")
        else:
            self.player.play()
            self.btn_play.setText("⏸ PAUSE")

    def sync_playhead(self, p):
        self.wave_view.pos = p
        self.wave_view.update()
        cur = QTime(0, 0).addMSecs(p).toString("mm:ss")
        total = QTime(0, 0).addMSecs(self.player.duration()).toString("mm:ss")
        self.timer_lbl.setText(f"{cur} / {total}")

    def sync_duration(self, d):
        self.wave_view.dur = d

    def save_audit(self):
        if not self.current_json: return
        with open(self.current_json, "r", encoding='utf-8') as f:
            data = json.load(f)
        discovery_results = {}
        for cat, btns in self.category_btns.items():
            for btn in btns:
                if btn.score != 0: discovery_results[btn.tag_name] = btn.score

        data["human_evaluation"] = {
            "status": "VALIDATED",
            "overall_score": self.score_slider.value(),
            "prompt_tag_adherence": {b.tag_name: b.score for b in self.prompt_btns},
            "discovery_tags": discovery_results,
            "qualitative_notes": self.notes_input.text(),
            "timestamp": datetime.now().isoformat()
        }
        with open(self.current_json, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        self.scan_vault()
        self.title_lbl.setText("✅ AUDIT COMMITTED")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = OrphioAuditorPro()
    win.show()
    sys.exit(app.exec())