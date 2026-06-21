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
    confidence: Optional[float] = None
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


class ValidateRequest(BaseModel):
    # Optional user-provided design artifact to validate against.
    # When omitted, validation falls back to an AI-generated candidate design.
    artifact: Optional[dict] = None


# ── Component selection stage schemas ─────────────────────────────────────────

class ComponentSearchCriteria(BaseModel):
    """What the LLM emits per functional block — parametric search spec, not a part number."""
    functional_role: str
    category: str
    parameters: dict           # parametric constraints in catalog.search() format
    satisfies_requirement_ids: list[str]


class SelectedComponent(BaseModel):
    functional_role: str
    part_id: str               # catalog part_id — never LLM-invented
    mpn: str
    kicad_symbol: str
    kicad_footprint: str
    category: str
    satisfies_requirement_ids: list[str]
    provenance: str            # always "catalog_search"
    rationale: str


class ComponentSelection(BaseModel):
    components: list[SelectedComponent]
    unresolved: list[dict]     # {"functional_role": str, "reason": str}


# ── Netlist stage schemas ─────────────────────────────────────────────────────

class PinRef(BaseModel):
    component_role: str
    part_id: str
    pin_number: str


class Net(BaseModel):
    name: str
    pins: list[PinRef]
    net_class: str              # power | ground | signal | bus
    satisfies_requirement_ids: list[str]
    provenance: str
    rationale: str


class Netlist(BaseModel):
    nets: list[Net]
    unconnected: list[dict]     # {"pin_ref": PinRef-like dict, "reason": str}


# ── Placement stage schemas ───────────────────────────────────────────────────

class BoardOutline(BaseModel):
    width_mm: float
    height_mm: float


class PlacedComponent(BaseModel):
    functional_role: str
    part_id: str
    x_mm: float
    y_mm: float
    rotation_deg: int           # 0 / 90 / 180 / 270
    satisfies_requirement_ids: list[str]


class Placement(BaseModel):
    board: BoardOutline
    components: list[PlacedComponent]
    status: str                 # "placed" | "infeasible"
    unsat_reason: Optional[str] = None
    unsat_groups: list[str] = []
    objective_value: Optional[float] = None
