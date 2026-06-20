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
from pipeline import run_intent_expansion, run_structured_bullets, run_formal_requirements
from schemas import (
    CreateProjectRequest,
    CreateProjectResponse,
    ProjectResponse,
    StageResponse,
    RunStageResponse,
    ReviseRequest,
    ReviseResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Tracer API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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


# ── Revisions ─────────────────────────────────────────────────────────────────

@app.post("/stages/{stage_id}/revise", response_model=ReviseResponse)
def revise_stage_endpoint(stage_id: int, body: ReviseRequest):
    stage = get_stage(stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    update_stage_output(stage_id, body.edited_output)
    return ReviseResponse(ok=True)
