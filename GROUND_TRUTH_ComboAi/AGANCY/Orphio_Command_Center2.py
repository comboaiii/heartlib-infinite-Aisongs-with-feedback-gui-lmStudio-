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

"""
ORPHIO COMMAND CENTER 2.0 - Professional AI Music Production Suite
===================================================================
A PyQt6-based GUI for automated album generation using HeartMuLa + LM Studio

FEATURES:
- Producer Strategy Selection (Narrative, Hit Singles, Lo-Fi)
- Tag Strategy: AI, Manual, or Hybrid
- Draft → Render Pipeline
- Built-in Audio Player with Waveform
- Vault Management & Inspector
- Configurable CFG, Duration, Temperature

FIXES IN THIS VERSION:
- CFG slider defaults to 1.5 (was 2.5)
- Temperature defaults to 1.0
- Unicode emoji logging errors fixed (Windows cp1252)
- Proper output schema for human evaluation
"""

import sys
import os
import json
import threading
import random
import time
import logging
from pathlib import Path
from datetime import datetime

# === CRITICAL: TORCH MUST BE IMPORTED BEFORE PYQT6 ===
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Add current directory to path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Import engine components first
try:
    from orphio_config import conf
    from orphio_engine import OrphioEngine
    from Blueprint_Executor import ProducerBlueprintEngine
    import torch

    print("✅ Engine Loaded Successfully.")
except ImportError as e:
    print(f"❌ Critical Engine Import Error: {e}")
    sys.exit(1)

# Now import PyQt6
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QFrame,
    QProgressBar, QComboBox, QMessageBox, QSlider,
    QScrollArea, QCheckBox, QGridLayout, QListWidget, QListWidgetItem,
    QSplitter, QFileDialog, QPlainTextEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QUrl, QThread
from PyQt6.QtGui import QFont, QTextCursor, QPainter, QColor, QBrush
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# Import UI components
try:
    from agency_styles import MODERN_STYLES
    from tagSelector import TagSelectorDialog
except ImportError as e:
    print(f"❌ UI Component Import Error: {e}")
    sys.exit(1)


# ============================================================
# LOGGING SETUP - FIX UNICODE ERRORS ON WINDOWS
# ============================================================
class SafeFileHandler(logging.FileHandler):
    """Custom file handler that handles Unicode emojis safely on Windows"""

    def emit(self, record):
        try:
            # Remove emojis and problematic Unicode characters
            msg = self.format(record)
            # Strip emojis but keep the message
            safe_msg = msg.encode('ascii', errors='ignore').decode('ascii')

            # Write to file manually
            with open(self.baseFilename, 'a', encoding='utf-8') as f:
                f.write(safe_msg + '\n')
        except Exception:
            self.handleError(record)


# Setup logging with safe handler
log_file = CURRENT_DIR / "orphio_studio.log"
logger = logging.getLogger("OrphioStudio")
logger.setLevel(logging.INFO)

# Remove any existing handlers
logger.handlers.clear()

# Add safe file handler
file_handler = SafeFileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s',
                                            datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(file_handler)


# ============================================================
# CUSTOM WIDGETS
# ============================================================
class AgencyWaveform(QWidget):
    """Interactive waveform display with seek capability"""
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

        if not self.bars:
            return

        bar_width = w / len(self.bars)
        for i, h_factor in enumerate(self.bars):
            bar_h = h * h_factor * 0.8
            is_active = i <= int(self.progress * len(self.bars))
            painter.setBrush(QBrush(QColor("#00FF7F") if is_active else QColor("#1F2937")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(
                int(i * bar_width),
                int((h - bar_h) / 2),
                int(bar_width - 1),
                int(bar_h),
                2, 2
            )

    def mousePressEvent(self, event):
        if self.duration_ms <= 0:
            return
        ratio = event.pos().x() / self.width()
        self.seek_requested.emit(int(ratio * self.duration_ms))


# ============================================================
# WORKER THREADS
# ============================================================
class WorkerSignals(QObject):
    """Signals for background workers"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)


class DraftThread(QThread):
    """Background thread for drafting lyrics"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)  # album_dir path
    error_signal = pyqtSignal(str)

    def __init__(self, executor, blueprint, topic, track_count, tag_mode, manual_tags):
        super().__init__()
        self.executor = executor
        self.blueprint = blueprint
        self.topic = topic
        self.track_count = track_count
        self.tag_mode = tag_mode
        self.manual_tags = manual_tags

    def run(self):
        try:
            self.log_signal.emit("Starting draft generation...")
            album_dir = self.executor.stage_1_draft_content(
                self.blueprint,
                self.topic,
                self.track_count,
                self.tag_mode,
                self.manual_tags
            )

            if album_dir:
                # Count drafts
                drafts = list(Path(album_dir).glob("*_DRAFT.json"))
                self.log_signal.emit(f"Found {len(drafts)} drafts")
                self.log_signal.emit(f"Draft generation complete: {Path(album_dir).name}")
                self.finished_signal.emit(str(album_dir))
            else:
                self.error_signal.emit("Failed to generate album drafts")

        except Exception as e:
            self.error_signal.emit(f"Draft error: {str(e)}")


class RenderThread(QThread):
    """Background thread for batch rendering"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, executor, album_dir, duration, cfg):
        super().__init__()
        self.executor = executor
        self.album_dir = album_dir
        self.duration = duration
        self.cfg = cfg

    def run(self):
        try:
            album_path = Path(self.album_dir)
            drafts = sorted(list(album_path.glob("*_DRAFT.json")))

            if not drafts:
                self.error_signal.emit("No draft files found to render")
                return

            self.log_signal.emit(f"Starting render queue: {len(drafts)} jobs")

            for idx, json_file in enumerate(drafts):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    params = data.get("parameters", {})
                    title = data.get("title", f"Track {idx + 1}")
                    lyrics = params.get("lyrics", "")
                    tags = params.get("tags", [])

                    self.log_signal.emit(f"[{idx + 1}/{len(drafts)}] Rendering: {title}")
                    self.progress_signal.emit(idx + 1, len(drafts))

                    # Free memory before rendering
                    self.executor.engine.free_memory()

                    # Render with CFG 1.5, Temp 1.0
                    self.log_signal.emit(f"Offloading LLM... Duration: {self.duration}s, CFG: {self.cfg}")

                    wav_path, ledger = self.executor.engine.render_audio_stage(
                        topic=title,
                        lyrics=lyrics,
                        tags=tags,
                        duration_s=self.duration,
                        cfg=self.cfg,
                        temp=1.0  # Fixed at 1.0
                    )

                    # Move to album directory with clean name
                    dest_wav = json_file.with_suffix('.wav').name.replace("_DRAFT", "")
                    dest_path = album_path / dest_wav

                    if Path(wav_path).exists():
                        Path(wav_path).rename(dest_path)

                    # Save ledger
                    final_ledger_path = dest_path.with_suffix('.json')
                    with open(final_ledger_path, 'w', encoding='utf-8') as f:
                        f.write(ledger.model_dump_json(indent=4))

                    # Remove draft file
                    os.remove(json_file)

                    self.log_signal.emit(f"   Saved: {dest_path.name}")

                except Exception as e:
                    self.log_signal.emit(f"Failed to render {json_file.name}: {e}")
                    continue

            # Final cleanup
            drafts_remaining = list(album_path.glob("*_DRAFT.json"))
            self.log_signal.emit(f"Found {len(drafts_remaining)} drafts")
            self.log_signal.emit("Rendering complete!")
            self.finished_signal.emit()

        except Exception as e:
            self.error_signal.emit(f"Render error: {str(e)}")


# ============================================================
# MAIN APPLICATION
# ============================================================
class OrphioCommandCenter(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ORPHIO COMMAND CENTER PRO v2.0")
        self.resize(1750, 950)
        self.setStyleSheet(MODERN_STYLES)

        # Initialize executor
        self.executor = ProducerBlueprintEngine()

        # Load strategies
        self.strategies = self.executor.list_producers()
        logger.info(f"Loaded {len(self.strategies)} strategies")

        # Audio player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        # State
        self.current_album_dir = None
        self.draft_thread = None
        self.render_thread = None

        # Build UI
        self.init_ui()

        # Connect player signals
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.playbackStateChanged.connect(self.update_play_btn_icon)

        # Load vault
        self.refresh_vault()

        # Check LM Studio connection
        self.check_lms_connection()

        logger.info("Orphio Command Center PRO initialized")

    def init_ui(self):
        """Build the user interface"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # === TOP SPLIT: SIDEBAR | CONTENT ===
        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- LEFT SIDEBAR ---
        sidebar = self.build_sidebar()
        top_splitter.addWidget(sidebar)

        # --- RIGHT CONTENT AREA ---
        content = self.build_content_area()
        top_splitter.addWidget(content)

        top_splitter.setSizes([400, 1350])
        main_layout.addWidget(top_splitter)

        # === BOTTOM PLAYER BAR ===
        player_bar = self.build_player_bar()
        main_layout.addWidget(player_bar)

    def build_sidebar(self):
        """Build left sidebar with controls"""
        sidebar = QFrame(objectName="Sidebar")
        sidebar.setFixedWidth(400)
        layout = QVBoxLayout(sidebar)

        # Header
        header = QLabel("ORPHIO COMMAND CENTER")
        header.setStyleSheet("color: #FF9F1A; font-weight: 900; font-size: 20px; margin-bottom: 10px;")
        layout.addWidget(header)

        # === PRODUCER STRATEGY ===
        layout.addWidget(QLabel("PRODUCER STRATEGY", objectName="SectionHeader"))
        self.combo_strategy = QComboBox()
        for s in self.strategies:
            self.combo_strategy.addItem(s['name'])
        layout.addWidget(self.combo_strategy)

        # === ALBUM CONCEPT ===
        layout.addWidget(QLabel("ALBUM CONCEPT", objectName="SectionHeader"))
        self.input_topic = QPlainTextEdit(objectName="TopicInput")
        self.input_topic.setPlaceholderText("Describe the album theme or story...")
        self.input_topic.setFixedHeight(120)
        layout.addWidget(self.input_topic)

        # === TAG STRATEGY ===
        layout.addWidget(QLabel("TAG STRATEGY", objectName="SectionHeader"))
        self.combo_tag_mode = QComboBox()
        self.combo_tag_mode.addItems(["AI", "MANUAL", "HYBRID"])
        layout.addWidget(self.combo_tag_mode)

        # Manual tags input
        tag_row = QHBoxLayout()
        self.input_manual_tags = QLineEdit(placeholderText="e.g., pop, electronic, female")
        btn_tag_lib = QPushButton("LIB", objectName="SecondaryBtn")
        btn_tag_lib.setFixedWidth(50)
        btn_tag_lib.clicked.connect(self.open_tag_library)
        tag_row.addWidget(self.input_manual_tags)
        tag_row.addWidget(btn_tag_lib)
        layout.addLayout(tag_row)

        # === TRACK COUNT ===
        layout.addWidget(QLabel("TRACK COUNT", objectName="SectionHeader"))
        track_row = QHBoxLayout()
        self.spin_track_count = QLineEdit("5")
        self.spin_track_count.setFixedWidth(60)
        track_row.addWidget(self.spin_track_count)
        track_row.addWidget(QLabel("songs"))
        track_row.addStretch()
        layout.addLayout(track_row)

        # === DRAFT BUTTON ===
        self.btn_draft = QPushButton("1. DRAFT ALBUM", objectName="PrimaryBtn")
        self.btn_draft.clicked.connect(self.start_draft_generation)
        layout.addWidget(self.btn_draft)

        layout.addWidget(QLabel("", objectName="SectionHeader"))  # Spacer

        # === PRODUCTION CONTROLS ===
        layout.addWidget(QLabel("PRODUCTION CONTROLS", objectName="SectionHeader"))

        # Duration Slider
        dur_layout = QVBoxLayout()
        self.lbl_duration = QLabel("Duration: 60s")
        self.sld_duration = QSlider(Qt.Orientation.Horizontal)
        self.sld_duration.setRange(30, 180)
        self.sld_duration.setValue(60)
        self.sld_duration.valueChanged.connect(
            lambda v: self.lbl_duration.setText(f"Duration: {v}s")
        )
        dur_layout.addWidget(self.lbl_duration)
        dur_layout.addWidget(self.sld_duration)
        layout.addLayout(dur_layout)

        # CFG Scale Slider - FIXED DEFAULT TO 1.5
        cfg_layout = QVBoxLayout()
        self.lbl_cfg = QLabel("CFG Scale: 1.5")  # ✅ CHANGED FROM 2.5
        self.sld_cfg = QSlider(Qt.Orientation.Horizontal)
        self.sld_cfg.setRange(10, 50)
        self.sld_cfg.setValue(15)  # ✅ CHANGED FROM 25 (15/10 = 1.5)
        self.sld_cfg.valueChanged.connect(
            lambda v: self.lbl_cfg.setText(f"CFG Scale: {v / 10.0:.1f}")
        )
        cfg_layout.addWidget(self.lbl_cfg)
        cfg_layout.addWidget(self.sld_cfg)
        layout.addLayout(cfg_layout)

        # Temperature Slider (already correct at 1.0)
        temp_layout = QVBoxLayout()
        self.lbl_temp = QLabel("Temperature: 1.0")
        self.sld_temp = QSlider(Qt.Orientation.Horizontal)
        self.sld_temp.setRange(5, 15)
        self.sld_temp.setValue(10)  # ✅ CORRECT (10/10 = 1.0)
        self.sld_temp.valueChanged.connect(
            lambda v: self.lbl_temp.setText(f"Temperature: {v / 10.0:.1f}")
        )
        temp_layout.addWidget(self.lbl_temp)
        temp_layout.addWidget(self.sld_temp)
        layout.addLayout(temp_layout)

        # === RENDER BUTTON ===
        self.btn_render = QPushButton("2. RENDER AUDIO", objectName="PrimaryBtn")
        self.btn_render.clicked.connect(self.start_batch_render)
        self.btn_render.setEnabled(False)
        layout.addWidget(self.btn_render)

        layout.addStretch()
        return sidebar

    def build_content_area(self):
        """Build center/right content area"""
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # === CENTER: DRAFT EDITOR ===
        editor_frame = QFrame()
        editor_layout = QVBoxLayout(editor_frame)

        editor_layout.addWidget(QLabel("DRAFT EDITOR", objectName="SectionHeader"))

        self.list_drafts = QListWidget()
        self.list_drafts.setMaximumHeight(200)
        self.list_drafts.itemClicked.connect(self.load_draft_for_editing)
        editor_layout.addWidget(self.list_drafts)

        editor_layout.addWidget(QLabel("LYRICS", objectName="SectionHeader"))
        self.txt_lyrics = QTextEdit()
        self.txt_lyrics.setFont(QFont("Consolas", 11))
        editor_layout.addWidget(self.txt_lyrics)

        editor_layout.addWidget(QLabel("TAGS (EDITABLE)", objectName="SectionHeader"))
        self.txt_tags = QLineEdit()
        self.txt_tags.setObjectName("LiveTags")
        editor_layout.addWidget(self.txt_tags)

        # Save draft button
        self.btn_save_draft = QPushButton("SAVE DRAFT", objectName="SecondaryBtn")
        self.btn_save_draft.clicked.connect(self.save_current_draft)
        editor_layout.addWidget(self.btn_save_draft)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        editor_layout.addWidget(self.progress_bar)

        # Log console
        editor_layout.addWidget(QLabel("SYSTEM LOG", objectName="SectionHeader"))
        self.txt_log = QTextEdit(readOnly=True)
        self.txt_log.setFixedHeight(150)
        self.txt_log.setFont(QFont("Consolas", 9))
        editor_layout.addWidget(self.txt_log)

        content_splitter.addWidget(editor_frame)

        # === RIGHT: VAULT INSPECTOR ===
        inspector_frame = QFrame()
        inspector_frame.setStyleSheet("background-color: #0C0C0E; border-left: 1px solid #18181B;")
        inspector_layout = QVBoxLayout(inspector_frame)

        vault_header = QHBoxLayout()
        vault_header.addWidget(QLabel("SONG VAULT", objectName="SectionHeader"))
        btn_vault_folder = QPushButton("📁", objectName="FolderBtn")
        btn_vault_folder.setFixedSize(35, 30)
        btn_vault_folder.clicked.connect(self.browse_vault_folder)
        vault_header.addWidget(btn_vault_folder)
        inspector_layout.addLayout(vault_header)

        self.list_vault = QListWidget()
        self.list_vault.itemDoubleClicked.connect(self.play_vault_track)
        self.list_vault.itemClicked.connect(self.load_vault_inspector)
        inspector_layout.addWidget(self.list_vault)

        inspector_layout.addWidget(QLabel("INSPECTOR", objectName="SectionHeader"))

        self.lbl_inspector_title = QLabel("Select a track...")
        self.lbl_inspector_title.setStyleSheet("color: #FF9F1A; font-weight: bold; font-size: 14px;")
        inspector_layout.addWidget(self.lbl_inspector_title)

        self.txt_inspector_lyrics = QTextEdit(readOnly=True)
        self.txt_inspector_lyrics.setMaximumHeight(200)
        inspector_layout.addWidget(self.txt_inspector_lyrics)

        self.lbl_inspector_tags = QLabel("Tags: N/A")
        self.lbl_inspector_tags.setWordWrap(True)
        self.lbl_inspector_tags.setStyleSheet("color: #00FF7F; padding: 8px; background: #050505; border-radius: 4px;")
        inspector_layout.addWidget(self.lbl_inspector_tags)

        # Specs grid
        spec_grid = QGridLayout()
        self.lbl_seed = QLabel("Seed: -")
        self.lbl_cfg_spec = QLabel("CFG: -")
        self.lbl_dur_spec = QLabel("Duration: -")
        self.lbl_temp_spec = QLabel("Temp: -")

        for i, lbl in enumerate([self.lbl_seed, self.lbl_cfg_spec, self.lbl_dur_spec, self.lbl_temp_spec]):
            lbl.setStyleSheet("color: #00FF7F; font-family: monospace; padding: 5px; background: #050505;")
            spec_grid.addWidget(lbl, i // 2, i % 2)

        inspector_layout.addLayout(spec_grid)
        inspector_layout.addStretch()

        content_splitter.addWidget(inspector_frame)
        content_splitter.setSizes([700, 450])

        return content_splitter

    def build_player_bar(self):
        """Build bottom audio player bar"""
        player_bar = QFrame()
        player_bar.setFixedHeight(100)
        player_bar.setStyleSheet("background-color: #0D0D0F; border-top: 1px solid #18181B;")

        layout = QHBoxLayout(player_bar)

        # Play button
        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(60, 60)
        self.btn_play.setStyleSheet("""
            QPushButton {
                background-color: #FF9F1A;
                color: #000000;
                font-size: 24px;
                font-weight: bold;
                border-radius: 30px;
            }
            QPushButton:hover {
                background-color: #FFB020;
            }
        """)
        self.btn_play.clicked.connect(self.toggle_playback)
        layout.addWidget(self.btn_play)

        # Waveform
        self.waveform = AgencyWaveform()
        self.waveform.seek_requested.connect(self.player.setPosition)
        layout.addWidget(self.waveform, 1)

        # Time label
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setFixedWidth(120)
        self.lbl_time.setStyleSheet("color: #A1A1AA; font-family: monospace; font-size: 12px;")
        layout.addWidget(self.lbl_time)

        return player_bar

    # ============================================================
    # LOGGING
    # ============================================================
    def log(self, msg, level="INFO"):
        """Thread-safe logging with emoji stripping for Windows"""
        # Strip emojis for display
        safe_msg = msg.encode('ascii', errors='ignore').decode('ascii').strip()

        # Log to file (safe handler will strip emojis)
        logger.log(getattr(logging, level, logging.INFO), msg)

        # Display in UI
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_log.append(f"[{timestamp}] {safe_msg}")
        self.txt_log.moveCursor(QTextCursor.MoveOperation.End)

    # ============================================================
    # LM STUDIO CONNECTION CHECK
    # ============================================================
    def check_lms_connection(self):
        """Verify LM Studio connection on startup"""
        ok, msg = self.executor.lms.check_connection()
        if ok:
            self.log(f"LM Studio: {msg}", "INFO")
        else:
            self.log(f"LM Studio: {msg}", "WARNING")
            QMessageBox.warning(self, "LM Studio Warning",
                                f"Cannot connect to LM Studio:\n{msg}\n\nMake sure it's running on port 1234.")

    # ============================================================
    # DRAFT GENERATION
    # ============================================================
    def start_draft_generation(self):
        """Start background draft generation"""
        # Validate inputs
        topic = self.input_topic.toPlainText().strip()
        if not topic:
            QMessageBox.warning(self, "Input Required", "Please enter an album concept.")
            return

        # Get selected strategy
        strategy_idx = self.combo_strategy.currentIndex()
        if strategy_idx < 0:
            QMessageBox.warning(self, "Strategy Required", "Please select a producer strategy.")
            return

        blueprint = self.executor.load_blueprint(self.strategies[strategy_idx]['path'])

        # Get track count
        try:
            track_count = int(self.spin_track_count.text())
        except ValueError:
            track_count = 5

        # Get tag mode
        tag_mode = self.combo_tag_mode.currentText()
        manual_tags = [t.strip() for t in self.input_manual_tags.text().split(",") if t.strip()]

        # Start thread
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.btn_draft.setEnabled(False)

        self.draft_thread = DraftThread(
            self.executor,
            blueprint,
            topic,
            track_count,
            tag_mode,
            manual_tags
        )

        self.draft_thread.log_signal.connect(lambda msg: self.log(msg, "INFO"))
        self.draft_thread.finished_signal.connect(self.on_draft_complete)
        self.draft_thread.error_signal.connect(self.on_draft_error)
        self.draft_thread.start()

    def on_draft_complete(self, album_dir):
        """Handle draft completion"""
        self.current_album_dir = album_dir
        self.progress_bar.setRange(0, 100)
        self.btn_draft.setEnabled(True)
        self.btn_render.setEnabled(True)

        # Load drafts into editor
        self.load_drafts_list()

        QMessageBox.information(self, "Drafts Ready",
                                f"Album drafts generated successfully!\n\nYou can now edit them or proceed to rendering.")

    def on_draft_error(self, error_msg):
        """Handle draft errors"""
        self.progress_bar.setRange(0, 100)
        self.btn_draft.setEnabled(True)
        self.log(f"Draft Error: {error_msg}", "ERROR")
        QMessageBox.critical(self, "Draft Failed", error_msg)

    def load_drafts_list(self):
        """Load draft files into list widget"""
        self.list_drafts.clear()

        if not self.current_album_dir:
            return

        album_path = Path(self.current_album_dir)
        drafts = sorted(list(album_path.glob("*_DRAFT.json")))

        for draft in drafts:
            try:
                with open(draft, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    title = data.get("title", draft.stem)

                item = QListWidgetItem(title)
                item.setData(Qt.ItemDataRole.UserRole, str(draft))
                self.list_drafts.addItem(item)
                self.log(f"Loaded: {draft.name}", "INFO")

            except Exception as e:
                self.log(f"Failed to load {draft.name}: {e}", "ERROR")

    def load_draft_for_editing(self, item):
        """Load a draft into the editor"""
        draft_path = item.data(Qt.ItemDataRole.UserRole)

        try:
            with open(draft_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            params = data.get("parameters", {})
            self.txt_lyrics.setPlainText(params.get("lyrics", ""))
            self.txt_tags.setText(", ".join(params.get("tags", [])))

            self.current_draft_path = draft_path

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load draft:\n{e}")

    def save_current_draft(self):
        """Save edited draft back to file"""
        if not hasattr(self, 'current_draft_path'):
            QMessageBox.warning(self, "No Draft Selected", "Please select a draft to save.")
            return

        try:
            with open(self.current_draft_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Update with edited content
            data["parameters"]["lyrics"] = self.txt_lyrics.toPlainText()
            data["parameters"]["tags"] = [t.strip() for t in self.txt_tags.text().split(",") if t.strip()]

            with open(self.current_draft_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)

            self.log("Draft saved successfully", "INFO")

        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save draft:\n{e}")

    # ============================================================
    # BATCH RENDERING
    # ============================================================
    def start_batch_render(self):
        """Start background batch rendering"""
        if not self.current_album_dir:
            QMessageBox.warning(self, "No Album", "Please generate drafts first.")
            return

        # Get render settings
        duration = self.sld_duration.value()
        cfg = self.sld_cfg.value() / 10.0

        # Confirm with user
        album_path = Path(self.current_album_dir)
        drafts = list(album_path.glob("*_DRAFT.json"))

        reply = QMessageBox.question(
            self,
            "Start Rendering?",
            f"Ready to render {len(drafts)} tracks.\n\nDuration: {duration}s\nCFG: {cfg}\n\nThis will take approximately {len(drafts) * 3} minutes.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Start render thread
        self.progress_bar.setRange(0, len(drafts))
        self.btn_render.setEnabled(False)
        self.btn_draft.setEnabled(False)

        self.render_thread = RenderThread(
            self.executor,
            self.current_album_dir,
            duration,
            cfg
        )

        self.render_thread.log_signal.connect(lambda msg: self.log(msg, "INFO"))
        self.render_thread.progress_signal.connect(self.update_render_progress)
        self.render_thread.finished_signal.connect(self.on_render_complete)
        self.render_thread.error_signal.connect(self.on_render_error)
        self.render_thread.start()

    def update_render_progress(self, current, total):
        """Update progress bar during rendering"""
        self.progress_bar.setValue(current)

    def on_render_complete(self):
        """Handle render completion"""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.btn_render.setEnabled(True)
        self.btn_draft.setEnabled(True)

        # Refresh vault
        self.refresh_vault()

        QMessageBox.information(self, "Rendering Complete",
                                "All tracks have been rendered successfully!\n\nCheck the Song Vault.")

    def on_render_error(self, error_msg):
        """Handle render errors"""
        self.progress_bar.setRange(0, 100)
        self.btn_render.setEnabled(True)
        self.btn_draft.setEnabled(True)
        self.log(f"Render Error: {error_msg}", "ERROR")
        QMessageBox.critical(self, "Render Failed", error_msg)

    # ============================================================
    # VAULT MANAGEMENT
    # ============================================================
    def refresh_vault(self):
        """Refresh song vault list"""
        self.list_vault.clear()

        if not conf.OUTPUT_DIR.exists():
            return

        # Get all WAV files, sorted by modification time
        wav_files = sorted(
            conf.OUTPUT_DIR.glob("*.wav"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for wav in wav_files:
            item = QListWidgetItem(wav.name)
            item.setData(Qt.ItemDataRole.UserRole, str(wav))
            self.list_vault.addItem(item)

    def browse_vault_folder(self):
        """Let user select a different vault directory"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Vault Directory",
            str(conf.OUTPUT_DIR)
        )

        if folder:
            conf.set_output_dir(folder)
            self.refresh_vault()

    def load_vault_inspector(self, item):
        """Load track metadata into inspector"""
        wav_path = Path(item.data(Qt.ItemDataRole.UserRole))
        json_path = wav_path.with_suffix('.json')

        if not json_path.exists():
            self.lbl_inspector_title.setText(wav_path.name)
            self.txt_inspector_lyrics.setPlainText("No metadata available")
            return

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract info
            provenance = data.get("provenance", {})
            config = data.get("configuration", {})
            prompt = config.get("input_prompt", {})

            # Update inspector
            self.lbl_inspector_title.setText(provenance.get("id", wav_path.stem))
            self.txt_inspector_lyrics.setPlainText(prompt.get("lyrics", "N/A"))
            self.lbl_inspector_tags.setText("Tags: " + ", ".join(prompt.get("tags", [])))

            # Update specs
            self.lbl_seed.setText(f"Seed: {config.get('seed', 'N/A')}")
            self.lbl_cfg_spec.setText(f"CFG: {config.get('cfg_scale', 'N/A')}")
            self.lbl_dur_spec.setText(f"Duration: {config.get('duration_sec', 'N/A')}s")
            self.lbl_temp_spec.setText(f"Temp: {config.get('temperature', 'N/A')}")

            # Update waveform
            seed = config.get('seed', 12345)
            self.waveform.generate_random_shape(seed)

        except Exception as e:
            self.log(f"Failed to load metadata: {e}", "ERROR")

    def play_vault_track(self, item):
        """Play selected track from vault"""
        wav_path = item.data(Qt.ItemDataRole.UserRole)

        if Path(wav_path).exists():
            self.player.setSource(QUrl.fromLocalFile(wav_path))
            self.player.play()

    # ============================================================
    # AUDIO PLAYER
    # ============================================================
    def toggle_playback(self):
        """Toggle play/pause"""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def update_play_btn_icon(self, state):
        """Update play button icon based on state"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText("⏸")
        else:
            self.btn_play.setText("▶")

    def update_position(self, position):
        """Update waveform and time display"""
        duration = self.player.duration()
        self.waveform.set_progress(position, duration)

        cur_sec = position // 1000
        dur_sec = duration // 1000

        self.lbl_time.setText(
            f"{cur_sec // 60:02}:{cur_sec % 60:02} / {dur_sec // 60:02}:{dur_sec % 60:02}"
        )

    def update_duration(self, duration):
        """Update when duration changes"""
        self.update_position(self.player.position())

    # ============================================================
    # TAG LIBRARY
    # ============================================================
    def open_tag_library(self):
        """Open tag selector dialog"""
        dialog = TagSelectorDialog(self.input_manual_tags.text(), self)
        if dialog.exec():
            selected = dialog.get_selected_tags()
            self.input_manual_tags.setText(", ".join(selected))


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================
if __name__ == "__main__":
    print("🔌 Initializing Audio Engine & CUDA...")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = OrphioCommandCenter()
    window.show()

    sys.exit(app.exec())