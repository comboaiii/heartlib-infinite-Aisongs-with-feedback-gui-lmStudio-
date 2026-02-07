# AGANCY/orphio_schema.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


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
    input_prompt: Dict[str, Any]  # Holds tags and lyrics


class AutomatedMetrics(BaseModel):
    generation_time_sec: float
    audit_status: str = "PENDING"
    lyric_accuracy_score: Optional[float] = None
    raw_transcript: Optional[str] = None


class HumanEvaluation(BaseModel):
    overall_score: Optional[int] = None
    qualitative_notes: Optional[str] = None
    status: str = "NOT_EVALUATED"


class MasterLedger(BaseModel):
    """
    The Unified Ground Truth Schema.
    Compatible with GT_02_Transcription_Validator.
    """
    provenance: Provenance
    configuration: Configuration
    automated_metrics: AutomatedMetrics
    human_evaluation: HumanEvaluation
    status: str = "PRODUCED"

    @classmethod
    def create_new(cls, topic, lyrics, tags, seed, duration, gen_time, root_path):
        ts = datetime.now()
        # Create a safe ID like GT_01
        safe_id = f"ORPHIO_{ts.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        return cls(
            provenance=Provenance(id=safe_id, project_root=str(root_path)),
            configuration=Configuration(
                seed=seed,
                duration_sec=duration,
                input_prompt={"topic": topic, "lyrics": lyrics, "tags": tags}
            ),
            automated_metrics=AutomatedMetrics(generation_time_sec=gen_time),
            human_evaluation=HumanEvaluation()
        )