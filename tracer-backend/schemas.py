from typing import Optional, Union
from pydantic import BaseModel, ConfigDict


# ── Stage output schemas ──────────────────────────────────────────────────────

class IntentExpansionOutput(BaseModel):
    restated_goal: str
    functional_description: str
    inferred_context: str
    open_questions: list[str] = []


class StructuredBullet(BaseModel):
    text: str
    category: str
    provenance: str
    rationale: Optional[str] = None


class StructuredBulletsOutput(BaseModel):
    bullets: list[StructuredBullet]


class FormalRequirement(BaseModel):
    id: str
    category: str
    statement: str
    provenance: str
    parameter: Optional[str] = None
    operator: Optional[str] = None
    value: Optional[Union[float, str]] = None
    unit: Optional[str] = None
    verification_method: Optional[str] = None


class FormalRequirementsOutput(BaseModel):
    requirements: list[FormalRequirement]


# ── API request / response schemas ────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str = 'Untitled board'
    intent: str


class CreateProjectResponse(BaseModel):
    project_id: int


class StageResponse(BaseModel):
    model_config = ConfigDict(extra='ignore')

    id: int
    stage_type: str
    status: str
    output_json: Optional[dict] = None
    error: Optional[str] = None
    created_at: str


class ProjectResponse(BaseModel):
    id: int
    name: str
    intent: str
    created_at: str
    stages: list[StageResponse]


class RunStageResponse(BaseModel):
    stage_id: int
    output: dict


class ReviseRequest(BaseModel):
    edited_output: dict
    note: Optional[str] = None


class ReviseResponse(BaseModel):
    ok: bool
