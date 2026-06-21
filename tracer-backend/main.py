from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from db import (
    init_db,
    create_project,
    get_project,
    get_stages_for_project,
    get_stage,
    upsert_stage,
    update_stage_output,
)
from pipeline import (
    run_intent_expansion,
    run_structured_bullets,
    run_formal_requirements,
    run_validation,
    run_remediation,
    run_stage4_component_selection,
    run_stage5_netlist,
    run_stage6_placement,
    _ErcFailure,
)
from schemas import (
    CreateProjectRequest,
    CreateProjectResponse,
    ProjectResponse,
    StageResponse,
    RunStageResponse,
    ReviseRequest,
    ReviseResponse,
    ValidateRequest,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Tracer API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Projects ──────────────────────────────────────────────────────────────────

@app.post("/projects", response_model=CreateProjectResponse)
def create_project_endpoint(body: CreateProjectRequest):
    project_id = create_project(body.name, body.intent)
    return CreateProjectResponse(project_id=project_id)


@app.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project_endpoint(project_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    stages = get_stages_for_project(project_id)
    return ProjectResponse(
        id=project["id"],
        name=project["name"],
        intent=project["intent"],
        created_at=project["created_at"],
        stages=[StageResponse(**s) for s in stages],
    )


# ── Stage runners ─────────────────────────────────────────────────────────────

@app.post("/projects/{project_id}/stage/intent_expansion", response_model=RunStageResponse)
def run_intent_expansion_endpoint(project_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    input_data = {"intent": project["intent"]}
    stage_id = upsert_stage(project_id, "intent_expansion", "running", input_data=input_data)

    try:
        output = run_intent_expansion(project["intent"])
    except Exception as exc:
        upsert_stage(project_id, "intent_expansion", "failed",
                     input_data=input_data, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    upsert_stage(project_id, "intent_expansion", "complete",
                 input_data=input_data, output_data=output)
    return RunStageResponse(stage_id=stage_id, output=output)


@app.post("/projects/{project_id}/stage/structured_bullets", response_model=RunStageResponse)
def run_structured_bullets_endpoint(project_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stages_by_type = {s["stage_type"]: s for s in get_stages_for_project(project_id)}
    intent_stage = stages_by_type.get("intent_expansion")
    if not intent_stage or intent_stage["status"] != "complete":
        raise HTTPException(status_code=400, detail="Complete intent_expansion stage first")

    intent_expansion = intent_stage["output_json"]
    input_data = {"intent": project["intent"], "intent_expansion": intent_expansion}
    stage_id = upsert_stage(project_id, "structured_bullets", "running", input_data=input_data)

    try:
        output = run_structured_bullets(project["intent"], intent_expansion)
    except Exception as exc:
        upsert_stage(project_id, "structured_bullets", "failed",
                     input_data=input_data, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    upsert_stage(project_id, "structured_bullets", "complete",
                 input_data=input_data, output_data=output)
    return RunStageResponse(stage_id=stage_id, output=output)


@app.post("/projects/{project_id}/stage/formal_requirements", response_model=RunStageResponse)
def run_formal_requirements_endpoint(project_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stages_by_type = {s["stage_type"]: s for s in get_stages_for_project(project_id)}
    intent_stage = stages_by_type.get("intent_expansion")
    bullets_stage = stages_by_type.get("structured_bullets")

    if not intent_stage or intent_stage["status"] != "complete":
        raise HTTPException(status_code=400, detail="Complete intent_expansion stage first")
    if not bullets_stage or bullets_stage["status"] != "complete":
        raise HTTPException(status_code=400, detail="Complete structured_bullets stage first")

    intent_expansion = intent_stage["output_json"]
    structured_bullets = bullets_stage["output_json"]
    input_data = {
        "intent": project["intent"],
        "intent_expansion": intent_expansion,
        "structured_bullets": structured_bullets,
    }
    stage_id = upsert_stage(project_id, "formal_requirements", "running", input_data=input_data)

    try:
        output = run_formal_requirements(project["intent"], intent_expansion, structured_bullets)
    except Exception as exc:
        upsert_stage(project_id, "formal_requirements", "failed",
                     input_data=input_data, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    upsert_stage(project_id, "formal_requirements", "complete",
                 input_data=input_data, output_data=output)
    return RunStageResponse(stage_id=stage_id, output=output)


@app.post("/projects/{project_id}/stage/validation", response_model=RunStageResponse)
def run_validation_endpoint(project_id: int, body: ValidateRequest | None = None):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stages_by_type = {s["stage_type"]: s for s in get_stages_for_project(project_id)}
    intent_stage = stages_by_type.get("intent_expansion")
    formal_stage = stages_by_type.get("formal_requirements")

    if not formal_stage or formal_stage["status"] != "complete":
        raise HTTPException(status_code=400, detail="Complete formal_requirements stage first")

    intent_expansion = intent_stage["output_json"] if intent_stage else {}
    formal_requirements = formal_stage["output_json"]
    artifact = body.artifact if body else None
    if artifact is None:
        # Fall back to a previously persisted design_artifact stage.
        da_stage = stages_by_type.get("design_artifact")
        if da_stage and da_stage["status"] == "complete":
            artifact = da_stage["output_json"]
    input_data = {
        "intent": project["intent"],
        "formal_requirements": formal_requirements,
        "artifact": artifact,
    }
    stage_id = upsert_stage(project_id, "validation", "running", input_data=input_data)

    try:
        output = run_validation(
            project["intent"], intent_expansion, formal_requirements, artifact=artifact
        )
    except Exception as exc:
        upsert_stage(project_id, "validation", "failed",
                     input_data=input_data, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    upsert_stage(project_id, "validation", "complete",
                 input_data=input_data, output_data=output)
    return RunStageResponse(stage_id=stage_id, output=output)


@app.post("/projects/{project_id}/stage/remediation", response_model=RunStageResponse)
def run_remediation_endpoint(project_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stages_by_type = {s["stage_type"]: s for s in get_stages_for_project(project_id)}
    validation_stage = stages_by_type.get("validation")

    if not validation_stage or validation_stage["status"] != "complete":
        raise HTTPException(status_code=400, detail="Complete validation stage first")

    validation = validation_stage["output_json"]
    input_data = {"intent": project["intent"], "validation": validation}
    stage_id = upsert_stage(project_id, "remediation", "running", input_data=input_data)

    try:
        output = run_remediation(project["intent"], validation)
    except Exception as exc:
        upsert_stage(project_id, "remediation", "failed",
                     input_data=input_data, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    upsert_stage(project_id, "remediation", "complete",
                 input_data=input_data, output_data=output)
    return RunStageResponse(stage_id=stage_id, output=output)


@app.post("/projects/{project_id}/stage/component_selection", response_model=RunStageResponse)
def run_component_selection_endpoint(project_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stages_by_type = {s["stage_type"]: s for s in get_stages_for_project(project_id)}
    formal_stage = stages_by_type.get("formal_requirements")

    if not formal_stage or formal_stage["status"] != "complete":
        raise HTTPException(status_code=400, detail="Complete formal_requirements stage first")

    formal_requirements = formal_stage["output_json"]
    input_data = {
        "intent": project["intent"],
        "formal_requirements": formal_requirements,
    }
    stage_id = upsert_stage(project_id, "component_selection", "running", input_data=input_data)

    try:
        output = run_stage4_component_selection(formal_requirements)
    except Exception as exc:
        upsert_stage(project_id, "component_selection", "failed",
                     input_data=input_data, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    upsert_stage(project_id, "component_selection", "complete",
                 input_data=input_data, output_data=output)
    return RunStageResponse(stage_id=stage_id, output=output)


@app.post("/projects/{project_id}/stage/netlist", response_model=RunStageResponse)
def run_netlist_endpoint(project_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stages_by_type = {s["stage_type"]: s for s in get_stages_for_project(project_id)}
    comp_stage = stages_by_type.get("component_selection")
    formal_stage = stages_by_type.get("formal_requirements")

    if not formal_stage or formal_stage["status"] != "complete":
        raise HTTPException(status_code=400, detail="Complete formal_requirements stage first")
    if not comp_stage or comp_stage["status"] != "complete":
        raise HTTPException(status_code=400, detail="Complete component_selection stage first")

    component_selection = comp_stage["output_json"]
    formal_requirements = formal_stage["output_json"]
    input_data = {
        "intent": project["intent"],
        "component_selection": component_selection,
        "formal_requirements": formal_requirements,
    }
    stage_id = upsert_stage(project_id, "netlist", "running", input_data=input_data)

    try:
        output = run_stage5_netlist(component_selection, formal_requirements)
    except _ErcFailure as exc:
        # ERC violations are structured output — persist them and return 422 so the
        # client can display the rule failures rather than a generic 500.
        upsert_stage(
            project_id, "netlist", "failed",
            input_data=input_data,
            output_data=exc.partial_output,
            error=str(exc),
        )
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "erc_violations": exc.violations,
                "partial_netlist": exc.partial_output,
            },
        )
    except Exception as exc:
        upsert_stage(project_id, "netlist", "failed",
                     input_data=input_data, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    upsert_stage(project_id, "netlist", "complete",
                 input_data=input_data, output_data=output)
    return RunStageResponse(stage_id=stage_id, output=output)


@app.post("/projects/{project_id}/stage/placement", response_model=RunStageResponse)
def run_placement_endpoint(project_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stages_by_type = {s["stage_type"]: s for s in get_stages_for_project(project_id)}
    netlist_stage  = stages_by_type.get("netlist")
    comp_stage     = stages_by_type.get("component_selection")
    formal_stage   = stages_by_type.get("formal_requirements")

    if not formal_stage or formal_stage["status"] != "complete":
        raise HTTPException(status_code=400, detail="Complete formal_requirements stage first")
    if not comp_stage or comp_stage["status"] != "complete":
        raise HTTPException(status_code=400, detail="Complete component_selection stage first")
    if not netlist_stage or netlist_stage["status"] != "complete":
        raise HTTPException(status_code=400, detail="Complete netlist stage first")

    component_selection  = comp_stage["output_json"]
    formal_requirements  = formal_stage["output_json"]
    netlist              = netlist_stage["output_json"]

    input_data = {
        "intent":               project["intent"],
        "component_selection":  component_selection,
        "formal_requirements":  formal_requirements,
        "netlist":              netlist,
    }
    stage_id = upsert_stage(project_id, "placement", "running", input_data=input_data)

    try:
        output = run_stage6_placement(
            component_selection=component_selection,
            netlist=netlist,
            formal_requirements=formal_requirements,
        )
    except Exception as exc:
        upsert_stage(project_id, "placement", "failed",
                     input_data=input_data, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    # infeasible / timeout are complete stages, not failed ones
    upsert_stage(project_id, "placement", "complete",
                 input_data=input_data, output_data=output)
    return RunStageResponse(stage_id=stage_id, output=output)


@app.post("/projects/{project_id}/stage/design_artifact", response_model=RunStageResponse)
def save_design_artifact_endpoint(project_id: int, body: ValidateRequest):
    """Persist a user-provided design artifact as its own stage so it survives reloads
    and is reused by validation when no artifact is supplied in the request."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = body.artifact or {}
    stage_id = upsert_stage(
        project_id, "design_artifact", "complete",
        input_data={"intent": project["intent"]}, output_data=artifact,
    )
    return RunStageResponse(stage_id=stage_id, output=artifact)


# ── Revisions ─────────────────────────────────────────────────────────────────

@app.post("/stages/{stage_id}/revise", response_model=ReviseResponse)
def revise_stage_endpoint(stage_id: int, body: ReviseRequest):
    stage = get_stage(stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    update_stage_output(stage_id, body.edited_output)
    return ReviseResponse(ok=True)
