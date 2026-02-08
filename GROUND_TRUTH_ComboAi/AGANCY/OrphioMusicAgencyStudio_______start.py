import sys
import json
import threading
import os
from pathlib import Path

# --- BOILERPLATE: FIX PATHS & IMPORTS ---
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QFrame,
    QProgressBar, QComboBox, QMessageBox, QSlider, QDialog,
    QScrollArea, QCheckBox, QGridLayout, QListWidget, QListWidgetItem, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QUrl
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# Internal Imports
try:
    from agency_styles import MODERN_STYLES
    from orphio_config import conf
    from orphio_engine import OrphioEngine
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)


# ============================================================
# TAG LIBRARY DIALOG
# ============================================================
class TagLibraryDialog(QDialog):
    def __init__(self, current_tags_str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Global Tag Library")
        self.setMinimumSize(700, 600)
        self.setStyleSheet(MODERN_STYLES + "QDialog { background-color: #09090B; }")
        self.selected_tags = [t.strip().lower() for t in current_tags_str.split(",") if t.strip()]
        self.checkboxes = []
        self.init_ui()
        self.load_tags()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Filter tags...")
        layout.addWidget(self.search_bar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.container.setObjectName("TagContainer")
        self.grid = QGridLayout(self.container)
        scroll.setWidget(self.container)
        layout.addWidget(scroll)
        self.search_bar.textChanged.connect(
            lambda txt: [cb.setVisible(txt.lower() in cb.text().lower()) for cb in self.checkboxes])
        btn = QPushButton("APPLY TAGS", objectName="PrimaryBtn")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def load_tags(self):
        try:
            with open(conf.TAGS_FILE, 'r') as f:
                tags = json.load(f)
            tags.sort();
            r, c = 0, 0
            for t in tags:
                cb = QCheckBox(t);
                cb.setChecked(t.lower() in self.selected_tags)
                self.checkboxes.append(cb);
                self.grid.addWidget(cb, r, c)
                c += 1;
                if c > 3: c, r = 0, r + 1
        except:
            pass

    def get_result(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]


# ============================================================
# MAIN STUDIO CLASS
# ============================================================
class WorkerSignals(QObject):
    log = pyqtSignal(str)
    finished_draft = pyqtSignal(str, list)
    finished_decorate = pyqtSignal(str)
    finished_render = pyqtSignal(str)
    error = pyqtSignal(str)


class OrphioStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ORPHIO AGENCY STUDIO v2.5 - Inspector Pro")
        self.resize(1750, 950)
        self.setStyleSheet(MODERN_STYLES)

        self.signals = WorkerSignals()
        self.signals.log.connect(self.log_system)
        self.signals.finished_draft.connect(self.on_draft_complete)
        self.signals.finished_decorate.connect(self.on_decorate_complete)
        self.signals.finished_render.connect(self.on_render_complete)
        self.signals.error.connect(self.on_error)

        self.engine = OrphioEngine(log_callback=lambda m: self.signals.log.emit(m))
        self.ai_generated_tags = []

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        self.init_ui()
        self.refresh_playlist()

        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)

    def init_ui(self):
        central = QWidget();
        self.setCentralWidget(central)
        outer_layout = QVBoxLayout(central);
        outer_layout.setContentsMargins(0, 0, 0, 0);
        outer_layout.setSpacing(0)

        main_h_layout = QHBoxLayout()

        # --- SIDEBAR (LEFT) ---
        sidebar = QFrame(objectName="Sidebar");
        sidebar.setFixedWidth(360)
        side_lyt = QVBoxLayout(sidebar)

        side_lyt.addWidget(QLabel("ORPHIO AGENCY", styleSheet="color: #FF9F1A; font-weight: 900; font-size: 20px;"))

        side_lyt.addWidget(QLabel("SONG CONCEPT", objectName="SectionHeader"))
        self.input_topic = QLineEdit();
        self.input_topic.setPlaceholderText("Topic...")
        side_lyt.addWidget(self.input_topic)

        self.combo_strat = QComboBox();
        self.combo_strat.addItems(["AI GENERATED", "USER DEFINED", "MIXED"])
        side_lyt.addWidget(QLabel("TAG STRATEGY", objectName="SectionHeader"));
        side_lyt.addWidget(self.combo_strat)

        tag_row = QHBoxLayout()
        self.input_manual = QLineEdit();
        self.input_manual.setPlaceholderText("Manual tags...")
        lib_btn = QPushButton("LIB", objectName="SecondaryBtn");
        lib_btn.setFixedWidth(45)
        lib_btn.clicked.connect(self.open_tag_library)
        tag_row.addWidget(self.input_manual);
        tag_row.addWidget(lib_btn)
        side_lyt.addLayout(tag_row)

        self.btn_draft = QPushButton("1. DRAFT LYRICS", objectName="PrimaryBtn")
        self.btn_draft.clicked.connect(self.run_draft_thread);
        side_lyt.addWidget(self.btn_draft)

        # --- SPACE SAVER: PRODUCTION CONTROL STRIP ---
        side_lyt.addWidget(QLabel("PRODUCTION (TIME | CFG | TEMP)", objectName="SectionHeader"))
        strip_layout = QHBoxLayout()

        # Duration Strip
        v_dur = QVBoxLayout()
        self.sld_dur = QSlider(Qt.Orientation.Horizontal);
        self.sld_dur.setRange(10, 300);
        self.sld_dur.setValue(60)
        self.lbl_dur = QLabel("60s");
        self.lbl_dur.setStyleSheet("color: #FF9F1A; font-weight: bold; font-size: 10px;")
        self.sld_dur.valueChanged.connect(lambda v: self.lbl_dur.setText(f"{v}s"))
        v_dur.addWidget(self.lbl_dur, alignment=Qt.AlignmentFlag.AlignCenter);
        v_dur.addWidget(self.sld_dur)
        strip_layout.addLayout(v_dur)

        # CFG Strip
        v_cfg = QVBoxLayout()
        self.sld_cfg = QSlider(Qt.Orientation.Horizontal);
        self.sld_cfg.setRange(10, 40);
        self.sld_cfg.setValue(15)
        self.lbl_cfg = QLabel("1.5");
        self.lbl_cfg.setStyleSheet("color: #FF9F1A; font-weight: bold; font-size: 10px;")
        self.sld_cfg.valueChanged.connect(lambda v: self.lbl_cfg.setText(f"{v / 10.0}"))
        v_cfg.addWidget(self.lbl_cfg, alignment=Qt.AlignmentFlag.AlignCenter);
        v_cfg.addWidget(self.sld_cfg)
        strip_layout.addLayout(v_cfg)

        # Temp Strip
        v_tmp = QVBoxLayout()
        self.sld_temp = QSlider(Qt.Orientation.Horizontal);
        self.sld_temp.setRange(1, 15);
        self.sld_temp.setValue(10)
        self.lbl_temp = QLabel("1.0");
        self.lbl_temp.setStyleSheet("color: #FF9F1A; font-weight: bold; font-size: 10px;")
        self.sld_temp.valueChanged.connect(lambda v: self.lbl_temp.setText(f"{v / 10.0}"))
        v_tmp.addWidget(self.lbl_temp, alignment=Qt.AlignmentFlag.AlignCenter);
        v_tmp.addWidget(self.sld_temp)
        strip_layout.addLayout(v_tmp)

        side_lyt.addLayout(strip_layout)

        side_lyt.addWidget(QLabel("SONG VAULT", objectName="SectionHeader"))
        self.playlist_widget = QListWidget()
        self.playlist_widget.setStyleSheet(
            "QListWidget { background: #050505; border: 1px solid #27272A; color: #E4E4E7; } QListWidget::item:selected { background: #FF9F1A; color: black; }")
        self.playlist_widget.itemDoubleClicked.connect(self.play_track)
        side_lyt.addWidget(self.playlist_widget)

        self.btn_render = QPushButton("3. RENDER AUDIO", objectName="PrimaryBtn")
        self.btn_render.setStyleSheet("background-color: #2ECC71; color: black; font-weight: bold;")
        self.btn_render.clicked.connect(self.run_render_thread);
        side_lyt.addWidget(self.btn_render)

        main_h_layout.addWidget(sidebar)

        # --- CONTENT SPLITTER (Editor | Inspector) ---
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # EDITOR PANE
        editor_pane = QFrame(objectName="MainEditor");
        ed_lyt = QVBoxLayout(editor_pane)
        tool_row = QHBoxLayout();
        tool_row.addWidget(QLabel("ARCHITECT:", objectName="SectionHeader"))
        self.combo_dec = QComboBox();
        self.combo_dec.addItems(list(conf.DECORATOR_SCHEMAS.keys()))
        btn_dec = QPushButton("2. DECORATE", objectName="SecondaryBtn");
        btn_dec.clicked.connect(self.run_decorate_thread)
        tool_row.addWidget(self.combo_dec);
        tool_row.addWidget(btn_dec);
        tool_row.addStretch();
        ed_lyt.addLayout(tool_row)

        self.txt_lyrics = QTextEdit();
        self.txt_lyrics.setPlaceholderText("Lyrics appear here...");
        self.txt_lyrics.setFont(QFont("Inter", 13))
        ed_lyt.addWidget(self.txt_lyrics)

        self.prog = QProgressBar();
        self.prog.setTextVisible(False);
        self.prog.setFixedHeight(4)
        ed_lyt.addWidget(self.prog)

        self.txt_log = QTextEdit();
        self.txt_log.setReadOnly(True);
        self.txt_log.setFixedHeight(100)
        self.txt_log.setStyleSheet(
            "font-family: Consolas; background: #050505; color: #71717A; border-top: 1px solid #27272A;")
        ed_lyt.addWidget(self.txt_log);
        content_splitter.addWidget(editor_pane)

        # INSPECTOR PANE (PREVIEW DATA)
        inspector_pane = QFrame();
        inspector_pane.setMinimumWidth(450);
        inspector_pane.setStyleSheet("background-color: #0C0C0E; border-left: 1px solid #27272A;")
        ins_lyt = QVBoxLayout(inspector_pane)

        ins_lyt.addWidget(QLabel("GENERATION INSPECTOR", objectName="SectionHeader"))
        self.ins_title = QLabel("No Track Selected");
        self.ins_title.setStyleSheet("color: #FF9F1A; font-weight: bold; font-size: 16px; margin-bottom: 10px;")
        ins_lyt.addWidget(self.ins_title)

        ins_lyt.addWidget(QLabel("FROZEN LYRICS", styleSheet="color: #71717A; font-size: 9px; font-weight: 800;"))
        self.ins_lyrics = QTextEdit();
        self.ins_lyrics.setReadOnly(True);
        self.ins_lyrics.setStyleSheet("background: #050505; color: #A1A1AA; font-style: italic;")
        ins_lyt.addWidget(self.ins_lyrics)

        ins_lyt.addWidget(QLabel("SONIC TAGS", styleSheet="color: #71717A; font-size: 9px; font-weight: 800;"))
        self.ins_tags = QLabel("N/A");
        self.ins_tags.setWordWrap(True);
        self.ins_tags.setStyleSheet("color: #FF9F1A; background: #121217; padding: 10px; border-radius: 4px;")
        ins_lyt.addWidget(self.ins_tags)

        spec_grid = QGridLayout()
        self.spec_seed = QLabel("Seed: -");
        self.spec_cfg = QLabel("CFG: -")
        self.spec_dur = QLabel("Time: -");
        self.spec_temp = QLabel("Temp: -")
        for i, lbl in enumerate([self.spec_seed, self.spec_cfg, self.spec_dur, self.spec_temp]):
            lbl.setStyleSheet("color: #71717A; font-family: monospace; font-size: 11px;")
            spec_grid.addWidget(lbl, i // 2, i % 2)
        ins_lyt.addLayout(spec_grid)
        content_splitter.addWidget(inspector_pane)

        main_h_layout.addWidget(content_splitter)
        outer_layout.addLayout(main_h_layout)

        # --- PLAYER BAR ---
        player_bar = QFrame();
        player_bar.setFixedHeight(90);
        player_bar.setStyleSheet("background-color: #09090B; border-top: 2px solid #27272A;")
        p_lyt = QHBoxLayout(player_bar);
        p_lyt.setContentsMargins(25, 0, 25, 0)
        self.btn_play = QPushButton("▶");
        self.btn_play.setFixedSize(54, 54);
        self.btn_play.setStyleSheet("border-radius: 27px; background-color: #FF9F1A; color: black; font-size: 24px;")
        self.btn_play.clicked.connect(self.toggle_play);
        p_lyt.addWidget(self.btn_play)
        v_lyt = QVBoxLayout();
        v_lyt.setSpacing(5);
        self.lbl_track = QLabel("No track loaded");
        self.lbl_track.setStyleSheet("color: #71717A; font-weight: 800; text-transform: uppercase; font-size: 10px;")
        self.seek = QSlider(Qt.Orientation.Horizontal);
        self.seek.setStyleSheet(
            "QSlider::groove:horizontal { height: 6px; background: #18181B; } QSlider::handle:horizontal { background: #FF9F1A; width: 14px; height: 14px; margin: -4px 0; border-radius: 7px; }")
        self.seek.sliderMoved.connect(lambda v: self.player.setPosition(v))
        v_lyt.addStretch();
        v_lyt.addWidget(self.lbl_track);
        v_lyt.addWidget(self.seek);
        v_lyt.addStretch();
        p_lyt.addLayout(v_lyt, 1)
        self.lbl_time = QLabel("00:00 / 00:00");
        self.lbl_time.setStyleSheet("font-family: monospace; font-size: 14px; color: #E4E4E7;")
        p_lyt.addWidget(self.lbl_time);
        outer_layout.addWidget(player_bar)

    # --- LOGIC ---
    def load_audio(self, path):
        self.player.setSource(QUrl.fromLocalFile(path))
        self.lbl_track.setText(f"NOW PLAYING: {Path(path).name}");
        self.player.play();
        self.btn_play.setText("⏸")
        json_path = Path(path).with_suffix(".json")
        if json_path.exists():
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                prov = data.get("provenance", {});
                c_data = data.get("configuration", {})
                prompt = c_data.get("input_prompt", {})
                self.ins_title.setText(prov.get("title") or prov.get("id"))
                self.ins_lyrics.setPlainText(prompt.get("lyrics", ""))
                tags = prompt.get("tags", [])
                self.ins_tags.setText(", ".join(tags) if isinstance(tags, list) else str(tags))
                self.spec_seed.setText(f"Seed: {c_data.get('seed')}")
                self.spec_cfg.setText(f"CFG: {c_data.get('cfg_scale')}")
                self.spec_dur.setText(f"Time: {c_data.get('duration_sec')}s")
                self.spec_temp.setText(f"Temp: {c_data.get('temperature')}")
            except:
                pass

    def play_track(self, item):
        self.load_audio(item.data(Qt.ItemDataRole.UserRole))

    def refresh_playlist(self):
        self.playlist_widget.clear()
        if conf.OUTPUT_DIR.exists():
            for f in sorted(conf.OUTPUT_DIR.glob("*.wav"), key=os.path.getmtime, reverse=True):
                i = QListWidgetItem(f.name);
                i.setData(Qt.ItemDataRole.UserRole, str(f));
                self.playlist_widget.addItem(i)

    def log_system(self, msg):
        self.txt_log.append(f"> {msg}"); self.txt_log.moveCursor(QTextCursor.MoveOperation.End)

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause(); self.btn_play.setText("▶")
        else:
            self.player.play(); self.btn_play.setText("⏸")

    def update_position(self, pos):
        self.seek.setValue(pos); self.update_time_label()

    def update_duration(self, dur):
        self.seek.setRange(0, dur); self.update_time_label()

    def update_time_label(self):
        c, t = self.player.position() // 1000, self.player.duration() // 1000
        self.lbl_time.setText(f"{c // 60:02}:{c % 60:02} / {t // 60:02}:{t % 60:02}")

    def get_active_tags(self):
        strat = self.combo_strat.currentText();
        manual = [t.strip().lower() for t in self.input_manual.text().split(",") if t.strip()]
        if strat == "AI GENERATED": return self.ai_generated_tags
        return list(set(self.ai_generated_tags + manual)) if strat == "MIXED" else manual

    def open_tag_library(self):
        dlg = TagLibraryDialog(self.input_manual.text(), self);
        if dlg.exec(): self.input_manual.setText(", ".join(dlg.get_result()))

    def run_draft_thread(self):
        t = self.input_topic.text();
        if t: self.prog.setRange(0, 0); threading.Thread(target=self._bg_draft, args=(t,), daemon=True).start()

    def _bg_draft(self, t):
        try:
            l, tags = self.engine.generate_lyrics_stage(t); self.signals.finished_draft.emit(l, tags)
        except Exception as e:
            self.signals.error.emit(str(e))

    def on_draft_complete(self, l, t):
        self.txt_lyrics.setPlainText(l); self.ai_generated_tags = t; self.prog.setRange(0, 100)

    def run_decorate_thread(self):
        l = self.txt_lyrics.toPlainText();
        conf.CURRENT_DECORATOR_SCHEMA = self.combo_dec.currentText()
        if len(l) > 10: self.prog.setRange(0, 0); threading.Thread(target=self._bg_decorate,
                                                                   args=(l, self.get_active_tags()),
                                                                   daemon=True).start()

    def _bg_decorate(self, l, t):
        try:
            res = self.engine.decorate_lyrics_stage(l, t); self.signals.finished_decorate.emit(res)
        except Exception as e:
            self.signals.error.emit(str(e))

    def on_decorate_complete(self, res):
        self.txt_lyrics.setPlainText(res); self.prog.setRange(0, 100)

    def run_render_thread(self):
        topic = self.input_topic.text() or "Untitled";
        l = self.txt_lyrics.toPlainText();
        t = self.get_active_tags()
        d = self.sld_dur.value();
        cfg = self.sld_cfg.value() / 10.0;
        tmp = self.sld_temp.value() / 10.0
        self.prog.setRange(0, 0);
        threading.Thread(target=self._bg_render, args=(topic, l, t, d, cfg, tmp), daemon=True).start()

    def _bg_render(self, topic, lyrics, tags, duration, cfg, temp):
        try:
            path, ledger = self.engine.render_audio_stage(topic, lyrics, tags, duration, cfg,
                                                          temp); self.signals.finished_render.emit(path)
        except Exception as e:
            self.signals.error.emit(str(e))

    def on_render_complete(self, path):
        self.prog.setRange(0, 100); self.refresh_playlist(); self.load_audio(path)

    def on_error(self, e):
        self.prog.setRange(0, 100); QMessageBox.critical(self, "Error", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv);
    win = OrphioStudio();
    win.show();
    sys.exit(app.exec())