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

# AGANCY/orphio_schema.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

# --- 1. SUB-MODELS ---

class Provenance(BaseModel):
    id: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    engine_uid: str = "HeartMuLa-Hybrid-OrphioAgency"
    project_root: str

class Configuration(BaseModel):
    seed: int
    cfg_scale: float = 1.5
    temperature: float = 1.0
    duration_sec: int
    input_prompt: Dict[str, Any]

class AutomatedMetrics(BaseModel):
    generation_time_sec: float
    audit_status: str = "PENDING"
    lyric_accuracy_score: Optional[float] = None
    raw_transcript: Optional[str] = None

class HumanEvaluation(BaseModel):
    # 1. JUDGMENT: Overall score (1-10)
    overall_score: Optional[int] = None

    # 2. ADHERENCE: How well it matched the prompt tags
    # Example: {"Rock": 9, "Sad": 2}
    prompt_adherence_scores: Dict[str, int] = Field(default_factory=dict)

    # 3. FEEDBACK: What the human actually heard
    # Example: ["Lo-Fi", "Guitar", "Sleepy"]
    perceived_tags: List[str] = Field(default_factory=list)

    # 4. TECHNICAL AUDIT: Matrix scores
    # Example: {"Mixing-Clarity": 1, "Clipping": -1}
    technical_audit_scores: Dict[str, int] = Field(default_factory=dict)

    qualitative_notes: Optional[str] = None
    status: str = "NOT_EVALUATED"


# --- 2. MASTER MODEL ---

class MasterLedger(BaseModel):
    provenance: Provenance
    configuration: Configuration
    automated_metrics: AutomatedMetrics
    human_evaluation: HumanEvaluation
    status: str = "PRODUCED"

    @classmethod
    def create_new(cls, topic, lyrics, tags, seed, duration, gen_time, root_path):
        ts = datetime.now()
        # Generate a unique ID for the song
        safe_id = f"ORPHIO_{ts.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        return cls(
            provenance=Provenance(id=safe_id, project_root=str(root_path)),
            configuration=Configuration(
                seed=seed,
                duration_sec=duration,
                input_prompt={"topic": topic, "lyrics": lyrics, "tags": tags}
            ),
            automated_metrics=AutomatedMetrics(generation_time_sec=gen_time),
            # This instantiates the HumanEvaluation class defined immediately above
            human_evaluation=HumanEvaluation()
        )