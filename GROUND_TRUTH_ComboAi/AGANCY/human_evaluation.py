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

import sys
import json
import random
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QListWidget, QListWidgetItem, QPushButton,
                               QTextEdit, QLabel, QScrollArea, QFileDialog, QSlider,
                               QGridLayout, QFrame, QMessageBox, QLineEdit, QSplitter,
                               QProgressBar, QSizePolicy, QAbstractItemView)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import Qt, QUrl, QSize, QTimer
from PySide6.QtGui import QColor, QPainter, QBrush, QAction, QFont, QIcon, QKeySequence, QShortcut

# --- CONFIG & PATHS ---
try:
    from tagSelector import TagSelectorDialog
    from orphio_config import conf

    TAGS_FILE = conf.TAGS_FILE
except ImportError:
    conf = None
    TAGS_FILE = Path("tags.json")

SCRIPT_DIR = Path(__file__).parent.absolute()
DEFAULT_VAULT_PATH = SCRIPT_DIR.parent / "outputSongs_ComboAi"
if not DEFAULT_VAULT_PATH.exists():
    DEFAULT_VAULT_PATH = SCRIPT_DIR

# --- AGENCY STUDIO THEME ---
COLOR_BG = "#050505"
COLOR_PANEL = "#09090B"
COLOR_BORDER = "#27272A"
COLOR_ACCENT = "#FF9F1A"  # Amber
COLOR_SUCCESS = "#00FF7F"  # Spring Green
COLOR_TEXT_MAIN = "#E4E4E7"
COLOR_TEXT_DIM = "#71717A"

STYLESHEET = f"""
    QMainWindow {{ background-color: {COLOR_BG}; color: {COLOR_TEXT_MAIN}; }}

    QFrame#Panel {{ 
        background-color: {COLOR_PANEL}; 
        border: 1px solid {COLOR_BORDER}; 
        border-radius: 6px; 
    }}

    QLabel {{ color: {COLOR_TEXT_MAIN}; font-family: 'Segoe UI', sans-serif; }}
    QLabel#Header {{ 
        color: {COLOR_TEXT_DIM}; font-weight: 800; font-size: 10px; 
        text-transform: uppercase; letter-spacing: 1px; 
    }}
    QLabel#BigTitle {{ font-size: 18px; font-weight: 900; color: white; }}

    /* List Widget */
    QListWidget {{ 
        background-color: {COLOR_PANEL}; border: none; outline: none; 
        font-family: 'Consolas', monospace; font-size: 13px;
    }}
    QListWidget::item {{ padding: 8px; color: {COLOR_TEXT_DIM}; border-bottom: 1px solid #121212; }}
    QListWidget::item:selected {{ 
        background-color: #18181B; color: {COLOR_ACCENT}; 
        border-left: 2px solid {COLOR_ACCENT}; 
    }}

    /* Sliders */
    QSlider::groove:horizontal {{ height: 4px; background: {COLOR_BORDER}; border-radius: 2px; }}
    QSlider::handle:horizontal {{ 
        background: {COLOR_TEXT_MAIN}; width: 14px; margin: -5px 0; border-radius: 7px; 
    }}
    QSlider::handle:horizontal:hover {{ background: {COLOR_ACCENT}; }}

    /* Buttons */
    QPushButton {{
        background-color: #18181B; border: 1px solid {COLOR_BORDER};
        color: {COLOR_TEXT_MAIN}; padding: 8px; border-radius: 4px; font-weight: bold;
    }}
    QPushButton:hover {{ border-color: {COLOR_TEXT_MAIN}; background-color: #27272A; }}
    QPushButton#PrimaryBtn {{ 
        background-color: {COLOR_ACCENT}; color: black; border: none; font-weight: 900; 
    }}
    QPushButton#PrimaryBtn:hover {{ background-color: #FFB020; }}

    QPushButton#TechBtn {{ 
        background-color: #121212; color: #555; border: 1px solid #222; font-size: 11px;
    }}
    QPushButton#TechBtn:checked {{ 
        background-color: #1A2218; color: {COLOR_SUCCESS}; border: 1px solid {COLOR_SUCCESS}; 
    }}

    /* Scroll Area */
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ background: {COLOR_BG}; width: 8px; }}
    QScrollBar::handle:vertical {{ background: #333; border-radius: 4px; }}
"""


# --- LOGIC & WIDGETS ---

class AdherenceRow(QWidget):
    """A single row to judge one tag: Label | Slider | Score"""

    def __init__(self, tag_name, score=5):
        super().__init__()
        self.tag_name = tag_name
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Label
        self.lbl = QLabel(tag_name.upper())
        self.lbl.setFixedWidth(140)
        self.lbl.setStyleSheet(f"font-weight:bold; color: {COLOR_TEXT_DIM};")

        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 10)
        self.slider.setValue(score)

        # Score Display
        self.score_lbl = QLabel(str(score))
        self.score_lbl.setFixedWidth(30)
        self.score_lbl.setAlignment(Qt.AlignCenter)
        self.score_lbl.setStyleSheet("font-weight:bold; background: #111; border-radius: 3px;")

        self.slider.valueChanged.connect(self.update_visuals)
        self.update_visuals(score)  # Init color

        layout.addWidget(self.lbl)
        layout.addWidget(self.slider)
        layout.addWidget(self.score_lbl)

    def update_visuals(self, val):
        self.score_lbl.setText(str(val))
        # Color scale: Red (0) -> Yellow (5) -> Green (10)
        if val < 4:
            color = "#FF4444"
        elif val < 8:
            color = "#FF9F1A"
        else:
            color = "#00FF7F"
        self.score_lbl.setStyleSheet(f"color: {color}; font-weight:bold; background: #111; border-radius: 3px;")

    def get_score(self):
        return self.slider.value()


class LiveWaveform(QWidget):
    """Visualizes audio playback"""

    def __init__(self, player):
        super().__init__()
        self.player = player
        self.setFixedHeight(60)
        self.bars = []
        self.pos_ratio = 0
        self.setStyleSheet(f"background: {COLOR_PANEL}; border-radius: 4px; border: 1px solid {COLOR_BORDER};")

    def generate_bars(self, seed_val):
        random.seed(seed_val)
        # Generate symmetrical-ish bars for a "waveform" look
        self.bars = [random.uniform(0.1, 0.9) for _ in range(80)]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        if not self.bars: return

        bar_w = w / len(self.bars)

        for i, val in enumerate(self.bars):
            bar_h = val * (h - 10)
            x = i * bar_w
            y = (h - bar_h) / 2

            # Active color vs Inactive color
            if (i / len(self.bars)) < self.pos_ratio:
                painter.setBrush(QBrush(QColor(COLOR_ACCENT)))
            else:
                painter.setBrush(QBrush(QColor("#222")))

            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(bar_w - 1), int(bar_h), 2, 2)

    def mousePressEvent(self, event):
        dur = self.player.duration()
        if dur > 0:
            pos = int((event.position().x() / self.width()) * dur)
            self.player.setPosition(pos)


class OrphioAuditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ORPHIO AGENCY EVALUATOR")
        self.resize(1400, 850)
        self.setStyleSheet(STYLESHEET)

        self.vault_path = DEFAULT_VAULT_PATH
        self.current_json_path = None
        self.adherence_widgets = []
        self.feedback_tags = []
        self.tech_btns = {}

        # Audio Setup
        self.player = QMediaPlayer()
        self.audio_out = QAudioOutput()
        self.audio_out.setVolume(1.0)
        self.player.setAudioOutput(self.audio_out)
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.playbackStateChanged.connect(self.on_state_changed)

        # Shortcuts
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.space_shortcut.activated.connect(self.toggle_play)

        self.init_ui()
        self.scan_vault()

    def init_ui(self):
        main = QWidget()
        self.setCentralWidget(main)
        main_layout = QHBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # === LEFT: FILE BROWSER ===
        sidebar = QFrame()
        sidebar.setObjectName("Panel")
        sidebar.setFixedWidth(320)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(10, 10, 10, 10)

        # Header
        sb_layout.addWidget(QLabel("SOURCE VAULT", objectName="Header"))
        self.btn_load = QPushButton(f"📂 {self.vault_path.name}")
        self.btn_load.clicked.connect(self.open_vault)
        sb_layout.addWidget(self.btn_load)

        # List
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.file_list.itemClicked.connect(self.load_song)
        sb_layout.addWidget(self.file_list)

        # Stats
        self.lbl_stats = QLabel("0/0 VALIDATED")
        self.lbl_stats.setStyleSheet(f"color:{COLOR_TEXT_DIM}; font-size:11px; font-weight:bold;")
        sb_layout.addWidget(self.lbl_stats, alignment=Qt.AlignCenter)

        # === RIGHT: WORKSPACE ===
        workspace = QWidget()
        ws_layout = QVBoxLayout(workspace)
        ws_layout.setContentsMargins(20, 20, 20, 20)

        # 1. TOP BAR (Title + Playback)
        top_bar = QFrame()
        top_bar.setFixedHeight(80)
        top_lyt = QHBoxLayout(top_bar)
        top_lyt.setContentsMargins(0, 0, 0, 0)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(50, 50)
        self.btn_play.setObjectName("PrimaryBtn")
        self.btn_play.setStyleSheet(f"font-size: 20px; border-radius: 25px;")
        self.btn_play.clicked.connect(self.toggle_play)

        info_lyt = QVBoxLayout()
        self.lbl_title = QLabel("NO TRACK SELECTED")
        self.lbl_title.setObjectName("BigTitle")
        self.lbl_sub = QLabel("Select a file to begin evaluation")
        self.lbl_sub.setStyleSheet(f"color: {COLOR_ACCENT}; font-family: monospace;")
        info_lyt.addWidget(self.lbl_title)
        info_lyt.addWidget(self.lbl_sub)

        self.wave_view = LiveWaveform(self.player)
        self.wave_view.setFixedWidth(400)

        top_lyt.addWidget(self.btn_play)
        top_lyt.addLayout(info_lyt)
        top_lyt.addStretch()
        top_lyt.addWidget(self.wave_view)

        ws_layout.addWidget(top_bar)

        # 2. EVALUATION AREA (Scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        eval_widget = QWidget()
        eval_lyt = QVBoxLayout(eval_widget)

        # SECTION A: PROMPT ADHERENCE
        eval_lyt.addWidget(QLabel("1. PROMPT ADHERENCE (Did it listen?)", objectName="Header"))
        self.adherence_container = QFrame()
        self.adherence_container.setObjectName("Panel")
        self.adh_layout = QVBoxLayout(self.adherence_container)
        eval_lyt.addWidget(self.adherence_container)

        # SECTION B: DISCOVERY (What is it?)
        eval_lyt.addSpacing(10)
        disc_head = QHBoxLayout()
        disc_head.addWidget(QLabel("2. PERCEIVED ATTRIBUTES (What do you hear?)", objectName="Header"))
        btn_tags = QPushButton("+ TAGS")
        btn_tags.setFixedSize(80, 20)
        btn_tags.setStyleSheet(
            f"background: transparent; border: 1px solid {COLOR_ACCENT}; color: {COLOR_ACCENT}; font-size: 10px;")
        btn_tags.clicked.connect(self.open_tag_selector)
        disc_head.addWidget(btn_tags)
        disc_head.addStretch()
        eval_lyt.addLayout(disc_head)

        self.txt_feedback = QTextEdit()
        self.txt_feedback.setFixedHeight(60)
        self.txt_feedback.setReadOnly(True)
        self.txt_feedback.setStyleSheet(
            f"background: #000; border: 1px solid {COLOR_BORDER}; color: {COLOR_ACCENT}; padding: 10px;")
        eval_lyt.addWidget(self.txt_feedback)

        # SECTION C: TECH AUDIT
        eval_lyt.addSpacing(10)
        eval_lyt.addWidget(QLabel("3. TECHNICAL MATRIX", objectName="Header"))

        tech_frame = QFrame()
        tech_frame.setObjectName("Panel")
        tech_grid = QGridLayout(tech_frame)
        tech_grid.setSpacing(5)

        audit_schema = {
            "MIX": ["Muddy", "Quiet", "Clipping", "Wide", "Punchy"],
            "VOCAL": ["Robotic", "Buried", "Clear", "Slurring", "Angelic"],
            "ARRANGEMENT": ["Repetitive", "Abrupt End", "Coherent", "Complex"]
        }

        r = 0
        for cat, opts in audit_schema.items():
            tech_grid.addWidget(QLabel(cat, styleSheet="font-weight:bold; color:#555;"), r, 0)
            c = 1
            self.tech_btns[cat] = []
            for opt in opts:
                btn = QPushButton(opt)
                btn.setCheckable(True)
                btn.setObjectName("TechBtn")
                btn.setFixedHeight(25)
                self.tech_btns[cat].append(btn)
                tech_grid.addWidget(btn, r, c)
                c += 1
            r += 1

        eval_lyt.addWidget(tech_frame)
        eval_lyt.addStretch()
        scroll.setWidget(eval_widget)
        ws_layout.addWidget(scroll)

        # 3. FOOTER (COMMIT)
        footer = QFrame()
        footer.setObjectName("Panel")
        footer.setFixedHeight(70)
        foot_lyt = QHBoxLayout(footer)

        self.slider_overall = QSlider(Qt.Horizontal)
        self.slider_overall.setRange(1, 10)
        self.slider_overall.setValue(5)
        self.slider_overall.setFixedWidth(200)

        self.lbl_overall = QLabel("OVERALL: 5/10")
        self.lbl_overall.setStyleSheet(f"color: {COLOR_ACCENT}; font-weight: 900; font-size: 14px;")
        self.slider_overall.valueChanged.connect(lambda v: self.lbl_overall.setText(f"OVERALL: {v}/10"))

        self.btn_save = QPushButton("✅ MARK AS VALIDATED")
        self.btn_save.setObjectName("PrimaryBtn")
        self.btn_save.setFixedSize(200, 40)
        self.btn_save.clicked.connect(self.save_evaluation)

        foot_lyt.addWidget(QLabel("FINAL VERDICT:", styleSheet="font-weight:bold;"))
        foot_lyt.addWidget(self.slider_overall)
        foot_lyt.addWidget(self.lbl_overall)
        foot_lyt.addStretch()
        foot_lyt.addWidget(self.btn_save)

        ws_layout.addWidget(footer)

        splitter.addWidget(sidebar)
        splitter.addWidget(workspace)
        main_layout.addWidget(splitter)

    # --- LOGIC ---

    def scan_vault(self):
        self.file_list.clear()
        if not self.vault_path.exists(): return

        # Get all JSONs
        files = sorted(list(self.vault_path.glob("*.json")), key=lambda f: f.stat().st_mtime, reverse=True)

        evaluated_cnt = 0
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as jf:
                    data = json.load(jf)

                status = data.get('human_evaluation', {}).get('status', 'PENDING')
                prov_id = data.get('provenance', {}).get('id', f.stem)

                # Visual Indicator
                if status == "VALIDATED":
                    icon = "🟢"
                    evaluated_cnt += 1
                    color = COLOR_SUCCESS
                else:
                    icon = "⚪"
                    color = COLOR_TEXT_DIM

                display_text = f"{icon}  {prov_id}"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, str(f))
                item.setForeground(QColor(color))
                self.file_list.addItem(item)

            except Exception as e:
                print(f"Error reading {f.name}: {e}")

        self.lbl_stats.setText(f"{evaluated_cnt} / {len(files)} VALIDATED")
        self.btn_load.setText(f"📂 {self.vault_path.name}")

    def load_song(self, item):
        json_path = Path(item.data(Qt.UserRole))
        self.current_json_path = json_path
        wav_path = json_path.with_suffix(".wav")

        # Clear UI
        self.player.stop()
        for i in reversed(range(self.adh_layout.count())):
            self.adh_layout.itemAt(i).widget().setParent(None)
        self.adherence_widgets.clear()

        # Load Data
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        config = data.get('configuration', {})
        prompt = config.get('input_prompt', {})
        eval_data = data.get('human_evaluation', {})

        # Header Info
        self.lbl_title.setText(data.get('provenance', {}).get('id', "Unknown"))
        seed = config.get('seed', 0)
        self.lbl_sub.setText(f"Seed: {seed} | CFG: {config.get('cfg_scale')} | Time: {config.get('duration_sec')}s")

        # Waveform Seed
        self.wave_view.generate_bars(seed)

        # 1. Load Audio
        if wav_path.exists():
            self.player.setSource(QUrl.fromLocalFile(str(wav_path)))
        else:
            self.lbl_title.setText("⚠️ AUDIO MISSING")

        # 2. Populate Adherence
        target_tags = prompt.get('tags', [])
        saved_adh = eval_data.get('prompt_adherence_scores', {})

        if not target_tags:
            self.adh_layout.addWidget(QLabel("No target tags found in metadata."))

        for tag in target_tags:
            score = saved_adh.get(tag, 5)
            row = AdherenceRow(tag, score)
            self.adh_layout.addWidget(row)
            self.adherence_widgets.append(row)

        # 3. Populate Feedback
        self.feedback_tags = eval_data.get('perceived_tags', [])
        self.txt_feedback.setText(", ".join(self.feedback_tags))

        # 4. Tech Audit
        saved_tech = eval_data.get('technical_audit_scores', {})
        for cat, btns in self.tech_btns.items():
            for btn in btns:
                val = saved_tech.get(btn.text(), 0)
                btn.setChecked(val == 1)

        # 5. Overall
        self.slider_overall.setValue(eval_data.get('overall_score', 5))

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            if self.player.mediaStatus() == QMediaPlayer.NoMedia and self.current_json_path:
                # Reload if needed
                self.load_song(self.file_list.currentItem())
            self.player.play()

    def on_state_changed(self, state):
        self.btn_play.setText("⏸" if state == QMediaPlayer.PlayingState else "▶")

    def on_position_changed(self, pos):
        dur = self.player.duration()
        if dur > 0:
            self.wave_view.pos_ratio = pos / dur
            self.wave_view.update()

    def open_tag_selector(self):
        """Uses the shared Agency Tag Selector"""
        dlg = TagSelectorDialog(", ".join(self.feedback_tags), self)
        if dlg.exec():
            self.feedback_tags = dlg.get_selected_tags()
            self.txt_feedback.setText(", ".join(self.feedback_tags))

    def save_evaluation(self):
        if not self.current_json_path: return

        # 1. Collect Data
        adh_scores = {w.tag_name: w.get_score() for w in self.adherence_widgets}
        tech_scores = {}
        for cat, btns in self.tech_btns.items():
            for btn in btns:
                if btn.isChecked(): tech_scores[btn.text()] = 1

        # 2. Load & Update JSON
        try:
            with open(self.current_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data['human_evaluation'] = {
                "status": "VALIDATED",
                "timestamp": datetime.now().isoformat(),
                "overall_score": self.slider_overall.value(),
                "prompt_adherence_scores": adh_scores,
                "perceived_tags": self.feedback_tags,
                "technical_audit_scores": tech_scores
            }

            with open(self.current_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)

            # 3. Update UI
            curr_item = self.file_list.currentItem()
            curr_item.setText(f"🟢  {data['provenance']['id']}")
            curr_item.setForeground(QColor(COLOR_SUCCESS))

            # Feedback
            QMessageBox.information(self, "Saved", "Evaluation committed to vault.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save JSON: {e}")

    def open_vault(self):
        d = QFileDialog.getExistingDirectory(self, "Open Vault", str(self.vault_path))
        if d:
            self.vault_path = Path(d)
            self.scan_vault()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = OrphioAuditor()
    win.show()
    sys.exit(app.exec())