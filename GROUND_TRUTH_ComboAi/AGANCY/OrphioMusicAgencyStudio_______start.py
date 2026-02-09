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
import os
import json
import threading
import random
from pathlib import Path

# --- CRITICAL FIX FOR WINDOWS DLL ERRORS (WinError 1114) ---
# PyTorch MUST be imported BEFORE PyQt6 to initialize CUDA/C++ DLLs correctly.
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# --- FIX: SYSTEM PATHS ---
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# --- IMPORT ENGINE & CONFIG FIRST (Pre-loads Torch) ---
try:
    from orphio_config import conf
    from orphio_engine import OrphioEngine
    # We verify torch loaded successfully
    import torch
    print(f"✅ PyTorch loaded successfully. CUDA Available: {torch.cuda.is_available()}")
except ImportError as e:
    print(f"❌ Critical Engine Import Error: {e}")
    sys.exit(1)
except OSError as e:
    print(f"❌ DLL Error (Visual C++ Redistributable might be missing): {e}")
    sys.exit(1)

# --- IMPORT PYQT6 AFTER TORCH ---
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QFrame,
    QProgressBar, QComboBox, QMessageBox, QSlider,
    QScrollArea, QCheckBox, QGridLayout, QListWidget, QListWidgetItem,
    QSplitter, QFileDialog, QPlainTextEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QUrl
from PyQt6.QtGui import QFont, QTextCursor, QPainter, QColor, QBrush
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# --- INTERNAL IMPORTS ---
try:
    from agency_styles import MODERN_STYLES
    from tagSelector import TagSelectorDialog
except ImportError as e:
    print(f"❌ UI Component Import Error: {e}")
    sys.exit(1)


# ============================================================
# 1. CUSTOM WIDGETS
# ============================================================

class AgencyWaveform(QWidget):
    seek_requested = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setFixedHeight(65)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bars = []
        self.progress = 0.0
        self.duration_ms = 1
        self.generate_random_shape(12345)

    def generate_random_shape(self, seed):
        random.seed(seed)
        self.bars = [random.uniform(0.15, 0.95) for _ in range(120)]
        self.update()

    def set_progress(self, current_ms, total_ms):
        if total_ms > 0:
            self.progress = current_ms / total_ms
            self.duration_ms = total_ms
        else:
            self.progress = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(self.rect(), QColor("#050505"))
        if not self.bars: return
        bar_width = w / len(self.bars)
        for i, h_factor in enumerate(self.bars):
            bar_h = h * h_factor * 0.8
            is_active = i <= int(self.progress * len(self.bars))
            painter.setBrush(QBrush(QColor("#00FF7F") if is_active else QColor("#1F2937")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(int(i * bar_width), int((h - bar_h) / 2), int(bar_width - 1), int(bar_h), 2, 2)

    def mousePressEvent(self, event):
        if self.duration_ms <= 0: return
        ratio = event.pos().x() / self.width()
        self.seek_requested.emit(int(ratio * self.duration_ms))


class WorkerSignals(QObject):
    log = pyqtSignal(str)
    finished_draft = pyqtSignal(str, list)
    finished_decorate = pyqtSignal(str)
    finished_render = pyqtSignal(str)
    error = pyqtSignal(str)


# ============================================================
# 2. MAIN STUDIO ENGINE
# ============================================================

class OrphioStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ORPHIO AGENCY STUDIO v3.0")
        self.resize(1750, 950)
        self.setStyleSheet(MODERN_STYLES)

        self.signals = WorkerSignals()
        self.signals.log.connect(self.log_system)
        self.signals.finished_draft.connect(self.on_draft_complete)
        self.signals.finished_decorate.connect(self.on_decorate_complete)
        self.signals.finished_render.connect(self.on_render_complete)
        self.signals.error.connect(self.on_error)

        self.engine = OrphioEngine(log_callback=lambda m: self.signals.log.emit(m))
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.playbackStateChanged.connect(self.update_play_btn_icon)

        self.init_ui()
        self.refresh_playlist()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        main_h_layout = QHBoxLayout()

        # --- SIDEBAR (LEFT) ---
        sidebar = QFrame(objectName="Sidebar")
        sidebar.setFixedWidth(360)
        side_lyt = QVBoxLayout(sidebar)
        side_lyt.addWidget(QLabel("ORPHIO AGENCY", styleSheet="color: #FF9F1A; font-weight: 900; font-size: 20px;"))

        side_lyt.addWidget(QLabel("SONG CONCEPT", objectName="SectionHeader"))
        self.input_topic = QPlainTextEdit(objectName="TopicInput")
        self.input_topic.setPlaceholderText("Enter detailed story (7 Rows)...")
        self.input_topic.setFixedHeight(160)
        side_lyt.addWidget(self.input_topic)

        side_lyt.addWidget(QLabel("TAG STRATEGY", objectName="SectionHeader"))
        self.combo_strat = QComboBox()
        self.combo_strat.addItems(["AI GENERATED", "USER DEFINED", "MIXED"])
        side_lyt.addWidget(self.combo_strat)

        tag_row = QHBoxLayout()
        self.input_manual = QLineEdit(placeholderText="Manual tags...")
        btn_lib = QPushButton("LIB", objectName="SecondaryBtn")
        btn_lib.setFixedWidth(50);
        btn_lib.clicked.connect(self.open_tag_library)
        tag_row.addWidget(self.input_manual);
        tag_row.addWidget(btn_lib)
        side_lyt.addLayout(tag_row)

        self.btn_draft = QPushButton("1. DRAFT LYRICS", objectName="PrimaryBtn")
        self.btn_draft.clicked.connect(self.run_draft_thread)
        side_lyt.addWidget(self.btn_draft)

        # Params
        side_lyt.addWidget(QLabel("PRODUCTION CONTROLS", objectName="SectionHeader"))
        self.sld_dur = QSlider(Qt.Orientation.Horizontal);
        self.sld_dur.setRange(10, 300);
        self.sld_dur.setValue(60)
        self.lbl_dur = QLabel("Duration: 60s");
        self.sld_dur.valueChanged.connect(lambda v: self.lbl_dur.setText(f"Duration: {v}s"))
        side_lyt.addWidget(self.lbl_dur);
        side_lyt.addWidget(self.sld_dur)

        self.sld_cfg = QSlider(Qt.Orientation.Horizontal);
        self.sld_cfg.setRange(10, 50);
        self.sld_cfg.setValue(25)
        self.lbl_cfg = QLabel("CFG Scale: 2.5");
        self.sld_cfg.valueChanged.connect(lambda v: self.lbl_cfg.setText(f"CFG Scale: {v / 10.0}"))
        side_lyt.addWidget(self.lbl_cfg);
        side_lyt.addWidget(self.sld_cfg)

        self.sld_temp = QSlider(Qt.Orientation.Horizontal);
        self.sld_temp.setRange(1, 15);
        self.sld_temp.setValue(10)
        self.lbl_temp = QLabel("Temp: 1.0");
        self.sld_temp.valueChanged.connect(lambda v: self.lbl_temp.setText(f"Temp: {v / 10.0}"))
        side_lyt.addWidget(self.lbl_temp);
        side_lyt.addWidget(self.sld_temp)

        vault_header = QHBoxLayout()
        vault_header.addWidget(QLabel("SONG VAULT", objectName="SectionHeader"))
        btn_browse = QPushButton("📁", objectName="FolderBtn")
        btn_browse.setFixedSize(35, 30);
        btn_browse.clicked.connect(self.browse_vault_location)
        vault_header.addWidget(btn_browse)
        side_lyt.addLayout(vault_header)

        self.playlist_widget = QListWidget()
        self.playlist_widget.itemDoubleClicked.connect(self.play_track)
        side_lyt.addWidget(self.playlist_widget)

        self.btn_render = QPushButton("3. RENDER AUDIO", objectName="PrimaryBtn")
        self.btn_render.clicked.connect(self.run_render_thread)
        side_lyt.addWidget(self.btn_render)

        main_h_layout.addWidget(sidebar)

        # --- CENTER / RIGHT SPLITTER ---
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- EDITOR (CENTER) ---
        editor_pane = QFrame(objectName="MainEditor")
        ed_lyt = QVBoxLayout(editor_pane)

        arch_row = QHBoxLayout()
        arch_row.addWidget(QLabel("ARCHITECT:", objectName="SectionHeader"))
        self.combo_dec = QComboBox();
        self.combo_dec.addItems(list(conf.DECORATOR_SCHEMAS.keys()))
        btn_dec = QPushButton("2. DECORATE", objectName="SecondaryBtn");
        btn_dec.clicked.connect(self.run_decorate_thread)
        arch_row.addWidget(self.combo_dec);
        arch_row.addWidget(btn_dec);
        arch_row.addStretch()
        ed_lyt.addLayout(arch_row)

        # THE MISSING EDITABLE TAGS FIELD
        ed_lyt.addWidget(QLabel("LIVE TAGS (EDITABLE - SENT TO RENDERER)", objectName="SectionHeader"))
        self.txt_live_tags = QLineEdit()
        self.txt_live_tags.setObjectName("LiveTags")  # NEW: Match the CSS
        self.txt_live_tags.setPlaceholderText("AI tags will appear here after drafting...")
        self.txt_live_tags.setStyleSheet(
            "background: #050505; color: #FF9F1A; font-weight: bold; border: 1px solid #27272A; padding: 10px;")
        ed_lyt.addWidget(self.txt_live_tags)

        ed_lyt.addWidget(QLabel("ACTIVE LYRIC CANVAS", objectName="SectionHeader"))
        self.txt_lyrics = QTextEdit();
        self.txt_lyrics.setFont(QFont("Inter", 13))
        ed_lyt.addWidget(self.txt_lyrics)

        self.prog = QProgressBar();
        self.prog.setTextVisible(False);
        self.prog.setFixedHeight(4)
        ed_lyt.addWidget(self.prog)
        self.txt_log = QTextEdit(readOnly=True);
        self.txt_log.setFixedHeight(100)
        ed_lyt.addWidget(self.txt_log)
        content_splitter.addWidget(editor_pane)

        # --- INSPECTOR (RIGHT) ---
        inspector_pane = QFrame()
        inspector_pane.setMinimumWidth(450)
        inspector_pane.setStyleSheet("background-color: #0C0C0E; border-left: 1px solid #18181B;")
        ins_lyt = QVBoxLayout(inspector_pane)
        ins_lyt.addWidget(QLabel("VAULT INSPECTOR", objectName="SectionHeader"))
        self.ins_title = QLabel("Select a track...");
        self.ins_title.setStyleSheet("color: #FF9F1A; font-weight: bold; font-size: 16px;")
        ins_lyt.addWidget(self.ins_title)

        self.ins_lyrics = QTextEdit(readOnly=True)  # Second window for Vault lyrics
        ins_lyt.addWidget(self.ins_lyrics)

        self.ins_tags = QLabel("N/A");
        self.ins_tags.setWordWrap(True);
        self.ins_tags.setStyleSheet("color: #FF9F1A; background: #050505; padding: 10px; border-radius: 4px;")
        ins_lyt.addWidget(self.ins_tags)

        spec_grid = QGridLayout()
        self.spec_seed = QLabel("Seed: -");
        self.spec_cfg = QLabel("CFG: -")
        self.spec_dur = QLabel("Time: -");
        self.spec_temp = QLabel("Temp: -")
        for i, lbl in enumerate([self.spec_seed, self.spec_cfg, self.spec_dur, self.spec_temp]):
            lbl.setStyleSheet("color: #00FF7F; font-family: monospace; border-bottom: 1px solid #1A1A1A; padding: 5px;")
            spec_grid.addWidget(lbl, i // 2, i % 2)
        ins_lyt.addLayout(spec_grid)

        content_splitter.addWidget(inspector_pane)
        main_h_layout.addWidget(content_splitter)
        outer_layout.addLayout(main_h_layout)

        # Player
        player_bar = QFrame();
        player_bar.setFixedHeight(100)
        p_lyt = QHBoxLayout(player_bar)
        self.btn_play = QPushButton("▶");
        self.btn_play.setFixedSize(60, 60);
        self.btn_play.clicked.connect(self.toggle_play)
        self.waveform = AgencyWaveform();
        self.waveform.seek_requested.connect(self.player.setPosition)
        self.lbl_time = QLabel("00:00 / 00:00");
        self.lbl_time.setFixedWidth(120)
        p_lyt.addWidget(self.btn_play);
        p_lyt.addWidget(self.waveform, 1);
        p_lyt.addWidget(self.lbl_time)
        outer_layout.addWidget(player_bar)

    def log_system(self, msg):
        self.txt_log.append(f"> {msg}");
        self.txt_log.moveCursor(QTextCursor.MoveOperation.End)

    def refresh_playlist(self):
        self.playlist_widget.clear()
        if not conf.OUTPUT_DIR.exists(): return
        for f in sorted(conf.OUTPUT_DIR.glob("*.wav"), key=os.path.getmtime, reverse=True):
            i = QListWidgetItem(f.name);
            i.setData(Qt.ItemDataRole.UserRole, str(f.absolute()))
            self.playlist_widget.addItem(i)

    def browse_vault_location(self):
        path = QFileDialog.getExistingDirectory(self, "Select Vault", str(conf.OUTPUT_DIR))
        if path: conf.set_output_dir(path); self.refresh_playlist()

    def load_audio(self, path_str):
        path = Path(path_str)
        if not path.exists() or path.stat().st_size < 1000: return
        self.player.setSource(QUrl.fromLocalFile(str(path.absolute())))
        self.player.play()
        json_path = path.with_suffix(".json")
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                config = data.get("configuration", {})
                prompt = config.get("input_prompt", {})
                self.ins_lyrics.setStyleSheet("line-height: 140%; padding: 15px; background: #070708;")
                self.ins_title.setText(data.get("provenance", {}).get("id", "Unknown"))
                self.ins_lyrics.setPlainText(prompt.get("lyrics", ""))
                self.ins_tags.setText(", ".join(prompt.get("tags", [])))
                self.spec_seed.setText(f"Seed: {config.get('seed')}")
                self.spec_cfg.setText(f"CFG: {config.get('cfg_scale')}")
                self.spec_dur.setText(f"Time: {config.get('duration_sec')}s")
                self.spec_temp.setText(f"Temp: {config.get('temperature')}")
                self.waveform.generate_random_shape(config.get('seed', 12345))
            except:
                pass

    def play_track(self, item):
        self.load_audio(item.data(Qt.ItemDataRole.UserRole))

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def update_play_btn_icon(self, state):
        self.btn_play.setText("⏸" if state == QMediaPlayer.PlaybackState.PlayingState else "▶")

    def update_position(self, pos):
        dur = self.player.duration()
        self.waveform.set_progress(pos, dur)
        cur, tot = pos // 1000, dur // 1000
        self.lbl_time.setText(f"{cur // 60:02}:{cur % 60:02} / {tot // 60:02}:{tot % 60:02}")

    def update_duration(self, dur):
        self.update_position(self.player.position())

    def open_tag_library(self):
        dlg = TagSelectorDialog(self.input_manual.text(), self)
        if dlg.exec(): self.input_manual.setText(", ".join(dlg.get_selected_tags()))

    def get_active_tags(self):
        # We now pull from the LIVE EDITABLE box above the lyrics
        return [t.strip().lower() for t in self.txt_live_tags.text().split(",") if t.strip()]

    def run_draft_thread(self):
        topic = self.input_topic.toPlainText()
        if topic: self.prog.setRange(0, 0); threading.Thread(target=self._bg_draft, args=(topic,), daemon=True).start()

    def _bg_draft(self, t):
        try:
            l, tags = self.engine.generate_lyrics_stage(t);
            self.signals.finished_draft.emit(l, tags)
        except Exception as e:
            self.signals.error.emit(str(e))

    def on_draft_complete(self, l, t):
        self.txt_lyrics.setPlainText(l)
        self.txt_live_tags.setText(", ".join(t))  # FILL THE EDITABLE BOX
        self.prog.setRange(0, 100)

    def run_decorate_thread(self):
        l = self.txt_lyrics.toPlainText()
        conf.CURRENT_DECORATOR_SCHEMA = self.combo_dec.currentText()
        self.prog.setRange(0, 0);
        threading.Thread(target=self._bg_decorate, args=(l, self.get_active_tags()), daemon=True).start()

    def _bg_decorate(self, l, t):
        try:
            res = self.engine.decorate_lyrics_stage(l, t);
            self.signals.finished_decorate.emit(res)
        except Exception as e:
            self.signals.error.emit(str(e))

    def on_decorate_complete(self, res):
        self.txt_lyrics.setPlainText(res);
        self.prog.setRange(0, 100)

    def run_render_thread(self):
        topic = self.input_topic.toPlainText()[:30] or "Untitled"
        lyrics = self.txt_lyrics.toPlainText()
        # GET TAGS FROM THE LIVE EDITABLE FIELD
        tags = self.get_active_tags()
        dur, cfg, tmp = self.sld_dur.value(), self.sld_cfg.value() / 10.0, self.sld_temp.value() / 10.0
        self.prog.setRange(0, 0);
        threading.Thread(target=self._bg_render, args=(topic, lyrics, tags, dur, cfg, tmp), daemon=True).start()

    def _bg_render(self, topic, lyrics, tags, duration, cfg, temp):
        try:
            path, ledger = self.engine.render_audio_stage(topic, lyrics, tags, duration, cfg, temp)
            self.signals.finished_render.emit(path)
        except Exception as e:
            self.signals.error.emit(str(e))

    def on_render_complete(self, path):
        self.prog.setRange(0, 100);
        self.refresh_playlist();
        self.load_audio(path)

    def on_error(self, e):
        self.prog.setRange(0, 100);
        QMessageBox.critical(self, "Error", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = OrphioStudio()
    win.show()
    sys.exit(app.exec())