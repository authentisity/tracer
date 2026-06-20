import json
import os
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel

_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
_MODEL = "gemini-2.5-flash"

# ── Structured output schemas (Gemini-compatible) ─────────────────────────────
# Kept separate from schemas.py to avoid Union types that Gemini can't represent.

class _IntentOutput(BaseModel):
    restated_goal: str
    functional_description: str
    inferred_context: str
    open_questions: list[str]


class _Bullet(BaseModel):
    text: str
    category: str        # power | interfaces | components | signal_integrity | thermal | mechanical | placement | other
    provenance: str      # user_stated | inferred
    rationale: Optional[str] = None


class _BulletsOutput(BaseModel):
    bullets: list[_Bullet]


class _FormalReq(BaseModel):
    id: str
    category: str
    statement: str
    provenance: str      # user_stated | inferred
    parameter: Optional[str] = None
    operator: Optional[str] = None   # <= >= == < > in
    value: Optional[str] = None      # str covers both numeric and enumerated values
    unit: Optional[str] = None
    verification_method: Optional[str] = None


class _FormalOutput(BaseModel):
    requirements: list[_FormalReq]


# ── Internal helper ───────────────────────────────────────────────────────────

def _call_structured(schema: type, prompt: str) -> dict:
    response = _client.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    return json.loads(response.text)


# ── Stage runners ─────────────────────────────────────────────────────────────

def run_intent_expansion(intent: str) -> dict:
    prompt = (
        "You are a senior PCB/electronics engineer. "
        "Analyse the following board description and expand the designer's intent. "
        "Be precise and draw on standard electronics engineering knowledge.\n\n"
        f"Board description:\n{intent}"
    )
    return _call_structured(_IntentOutput, prompt)


def run_structured_bullets(intent: str, intent_expansion: dict) -> dict:
    prompt = (
        "You are a senior PCB/electronics engineer. "
        "Using the original description and intent analysis below, generate a comprehensive "
        "set of design requirement bullets organised by category. "
        "Mark each as user_stated (explicitly from the description) or inferred "
        "(your expert engineering judgement). For inferred items include a brief rationale. "
        "Valid categories: power, interfaces, components, signal_integrity, thermal, mechanical, placement, other.\n\n"
        f"Original description:\n{intent}\n\n"
        "Intent analysis:\n"
        f"Goal: {intent_expansion['restated_goal']}\n"
        f"Functional: {intent_expansion['functional_description']}\n"
        f"Context: {intent_expansion['inferred_context']}"
    )
    return _call_structured(_BulletsOutput, prompt)


def run_formal_requirements(intent: str, intent_expansion: dict, structured_bullets: dict) -> dict:
    bullets_text = "\n".join(
        f"  [{b['category']}][{b['provenance']}] {b['text']}"
        for b in structured_bullets.get("bullets", [])
    )
    prompt = (
        "You are a senior PCB/electronics engineer. "
        "Convert the requirement bullets below into formal, machine-readable requirements. "
        "Assign each a unique ID using prefix codes matching the category "
        "(PWR-, INTF-, COMP-, SIG-, THERM-, MECH-, PLAC-, OTH-). "
        "Write a declarative statement for every requirement. "
        "Where a requirement is quantifiable, add parameter, operator, value (as a string), and unit. "
        "Valid operators: <=, >=, ==, <, >, in. "
        "Add a verification_method (simulation / measurement / inspection / analysis / test) "
        "for every requirement.\n\n"
        f"Original description:\n{intent}\n\n"
        f"Goal: {intent_expansion['restated_goal']}\n\n"
        f"Requirement bullets:\n{bullets_text}"
    )
    return _call_structured(_FormalOutput, prompt)
