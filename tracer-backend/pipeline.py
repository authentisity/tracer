import json
import os
import re
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
    confidence: float    # 0.0 – 1.0
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
        "for every requirement. "
        "Assign a confidence score (0.0–1.0) to each requirement: "
        "use 0.90–0.99 for requirements explicitly stated in the description, "
        "and 0.50–0.85 for inferred requirements based on engineering judgement.\n\n"
        f"Original description:\n{intent}\n\n"
        f"Goal: {intent_expansion['restated_goal']}\n\n"
        f"Requirement bullets:\n{bullets_text}"
    )
    return _call_structured(_FormalOutput, prompt)


# ── Stage 4: Validation (generate a candidate design, then check it) ───────────

class _CandidateComponent(BaseModel):
    ref: str             # reference designator, e.g. U1, C1
    part: str            # specific part or part class, e.g. "AMS1117-3.3 LDO"
    rationale: str


class _CandidateParameter(BaseModel):
    name: str
    value: str
    unit: Optional[str] = None
    rationale: str


class _CandidateDesign(BaseModel):
    summary: str
    components: list[_CandidateComponent]
    key_parameters: list[_CandidateParameter]


class _ReqCheck(BaseModel):
    req_id: str
    design_value: Optional[str] = None   # value the design exhibits for this req's parameter
    verdict: str                          # pass | fail | needs_review
    rationale: str


class _ChecksOutput(BaseModel):
    checks: list[_ReqCheck]


_NUM_UNIT_RE = re.compile(r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([A-Za-zµμΩΩ°/%]+)?")

_UNIT_FACTORS = {
    # Voltage
    "v": ("voltage", 1.0),
    "mv": ("voltage", 1e-3),
    "kv": ("voltage", 1e3),
    # Current
    "a": ("current", 1.0),
    "ma": ("current", 1e-3),
    "ua": ("current", 1e-6),
    # Resistance
    "ohm": ("resistance", 1.0),
    "kohm": ("resistance", 1e3),
    "mohm": ("resistance", 1e6),
    # Capacitance
    "f": ("capacitance", 1.0),
    "mf": ("capacitance", 1e-3),
    "uf": ("capacitance", 1e-6),
    "nf": ("capacitance", 1e-9),
    "pf": ("capacitance", 1e-12),
    # Frequency
    "hz": ("frequency", 1.0),
    "khz": ("frequency", 1e3),
    "mhz": ("frequency", 1e6),
    "ghz": ("frequency", 1e9),
    # Time
    "s": ("time", 1.0),
    "ms": ("time", 1e-3),
    "us": ("time", 1e-6),
    "min": ("time", 60.0),
    "h": ("time", 3600.0),
    "day": ("time", 86400.0),
    "year": ("time", 365.0 * 86400.0),
    # Length / board dimensions
    "m": ("length", 1.0),
    "cm": ("length", 1e-2),
    "mm": ("length", 1e-3),
    "um": ("length", 1e-6),
    "mil": ("length", 2.54e-5),
    "in": ("length", 0.0254),
    # Data rates
    "bps": ("data_rate", 1.0),
    "kbps": ("data_rate", 1e3),
    "mbps": ("data_rate", 1e6),
    "gbps": ("data_rate", 1e9),
    # Common unitless-ish values
    "%": ("percent", 1.0),
    "c": ("temperature_c", 1.0),
}

_UNIT_ALIASES = {
    "volt": "v",
    "volts": "v",
    "amp": "a",
    "amps": "a",
    "ua": "ua",
    "microamp": "ua",
    "microamps": "ua",
    "ohms": "ohm",
    "k": "kohm",
    "kohms": "kohm",
    "megohm": "mohm",
    "megohms": "mohm",
    "second": "s",
    "seconds": "s",
    "sec": "s",
    "secs": "s",
    "minute": "min",
    "minutes": "min",
    "hour": "h",
    "hours": "h",
    "hr": "h",
    "hrs": "h",
    "days": "day",
    "yr": "year",
    "yrs": "year",
    "years": "year",
    "inch": "in",
    "inches": "in",
    "degc": "c",
}


def _clean_unit(unit) -> Optional[str]:
    if unit is None:
        return None
    cleaned = str(unit).strip()
    if not cleaned:
        return None
    cleaned = (
        cleaned.replace("Ω", "ohm")
        .replace("Ω", "ohm")
        .replace("µ", "u")
        .replace("μ", "u")
        .replace("°", "")
        .replace(" ", "")
        .lower()
        .rstrip(".")
    )
    return _UNIT_ALIASES.get(cleaned, cleaned)


def _quantity(value, unit_hint=None) -> Optional[tuple[float, Optional[str], Optional[str]]]:
    if value is None:
        return None
    m = _NUM_UNIT_RE.search(str(value))
    if not m:
        return None
    number = float(m.group(1))
    unit = _clean_unit(m.group(2) or unit_hint)
    if unit in _UNIT_FACTORS:
        dimension, factor = _UNIT_FACTORS[unit]
        return number * factor, dimension, unit
    if unit is None:
        return number, None, None
    return number, "unknown", unit


def _normalized_verdict(verdict: str) -> str:
    verdict = str(verdict or "").strip().lower().replace("-", "_").replace(" ", "_")
    return verdict if verdict in {"pass", "fail", "needs_review"} else "needs_review"


def _resolve_verdict(req: dict, design_value, llm_verdict: str) -> tuple[str, str]:
    """Prefer a deterministic numeric comparison; fall back to the model's judgement.

    Returns (verdict, method) for UI display and traceability.
    """
    op = req.get("operator")
    expected = _quantity(req.get("value"), req.get("unit"))
    actual = _quantity(design_value)

    if op in {"<=", ">=", "<", ">", "=="} and (expected is None or actual is None):
        return "needs_review", "incomplete_value"

    if op in {"<=", ">=", "<", ">", "=="} and expected and actual:
        expected_value, expected_dimension, _ = expected
        actual_value, actual_dimension, _ = actual

        if expected_dimension != actual_dimension:
            return "needs_review", "unit_mismatch"

        ok = {
            "<=": actual_value <= expected_value,
            ">=": actual_value >= expected_value,
            "<": actual_value < expected_value,
            ">": actual_value > expected_value,
            "==": abs(actual_value - expected_value) <= 1e-9 + 1e-6 * abs(expected_value),
        }[op]
        return ("pass" if ok else "fail", "deterministic")

    return _normalized_verdict(llm_verdict), "judgment"


def run_validation(intent: str, intent_expansion: dict, formal_requirements: dict) -> dict:
    reqs = formal_requirements.get("requirements", [])

    # 1) Generate a concrete candidate design from the requirements.
    req_lines = "\n".join(f"  [{r.get('id', '?')}] {r.get('statement', '')}" for r in reqs)
    design_prompt = (
        "You are a senior PCB/electronics engineer. Propose ONE concrete candidate board design "
        "that attempts to satisfy the requirements below. List the key components you would choose "
        "(reference designator, a specific real part or part family, and a one-line rationale), "
        "plus key design parameters with concrete values and units where applicable. Pick realistic "
        "parts and concrete values.\n\n"
        f"Board goal:\n{intent_expansion.get('restated_goal', intent)}\n\n"
        f"Requirements:\n{req_lines}"
    )
    design = _call_structured(_CandidateDesign, design_prompt)

    # 2) Review the candidate design against each requirement.
    comp_lines = "\n".join(
        f"  {c.get('ref', '?')}: {c.get('part', '')} — {c.get('rationale', '')}"
        for c in design.get("components", [])
    )
    parameter_lines = "\n".join(
        f"  {p.get('name', '')}: {p.get('value', '')} {p.get('unit') or ''} — {p.get('rationale', '')}"
        for p in design.get("key_parameters", [])
    )
    req_detail = "\n".join(
        f"  [{r.get('id', '?')}] {r.get('statement', '')}"
        + (
            f"  (constraint: {r.get('parameter', '')} {r.get('operator', '')} "
            f"{r.get('value', '')} {r.get('unit', '') or ''})"
            if r.get("parameter")
            else ""
        )
        for r in reqs
    )
    check_prompt = (
        "You are a senior PCB/electronics engineer acting as a design reviewer. "
        "Given the candidate design and the formal requirements, assess whether the design satisfies "
        "EACH requirement. For every requirement return: its req_id; the design_value — the concrete "
        "value or property the candidate design exhibits for that requirement's parameter (a short "
        "string, or null if the design does not address it); a verdict of 'pass', 'fail', or "
        "'needs_review'; and a one-sentence rationale. Be strict: if the design does not clearly "
        "address a requirement, use 'needs_review' or 'fail', never 'pass'. For quantitative checks, "
        "include a numeric design_value with units, for example '3.3 V' or '250 mA'.\n\n"
        f"Candidate design:\n{design.get('summary', '')}\n\n"
        f"Components:\n{comp_lines}\n\n"
        f"Key parameters:\n{parameter_lines}\n\n"
        f"Requirements:\n{req_detail}"
    )
    checks = _call_structured(_ChecksOutput, check_prompt).get("checks", [])
    checks_by_id = {c.get("req_id"): c for c in checks}

    # 3) Resolve each verdict deterministically where the requirement is quantitative.
    results = []
    for r in reqs:
        c = checks_by_id.get(r.get("id"), {})
        design_value = c.get("design_value")
        verdict, method = _resolve_verdict(r, design_value, c.get("verdict", "needs_review"))
        results.append({
            "req_id": r.get("id"),
            "category": r.get("category", "other"),
            "statement": r.get("statement", ""),
            "parameter": r.get("parameter"),
            "operator": r.get("operator"),
            "value": r.get("value"),
            "unit": r.get("unit"),
            "design_value": design_value,
            "verdict": verdict,
            "method": method,
            "rationale": c.get("rationale", ""),
        })

    summary = {
        "total": len(results),
        "pass": sum(1 for x in results if x["verdict"] == "pass"),
        "fail": sum(1 for x in results if x["verdict"] == "fail"),
        "needs_review": sum(1 for x in results if x["verdict"] == "needs_review"),
    }
    return {"design": design, "results": results, "summary": summary}


# ── Stage 5: Remediation (turn failed checks into concrete fixes) ──────────────

class _Fix(BaseModel):
    req_id: str
    issue: str           # why the requirement isn't satisfied
    suggestion: str      # the concrete change to make it pass
    change_type: str     # add_component | change_value | swap_part | add_constraint | clarify


class _RemediationOutput(BaseModel):
    fixes: list[_Fix]


def run_remediation(intent: str, validation: dict) -> dict:
    """Propose a concrete fix for each requirement that failed or needs review.

    Reads everything it needs from the validation output (each result already
    carries the requirement's constraint, the design value, and the reviewer note).
    """
    failing = [
        r for r in validation.get("results", [])
        if r.get("verdict") in ("fail", "needs_review")
    ]
    if not failing:
        return {"fixes": [], "all_clear": True}

    design_summary = (validation.get("design") or {}).get("summary", "")
    issues = "\n".join(
        f"  [{f.get('req_id')}] {f.get('statement', '')}"
        + (
            f" (constraint: {f.get('parameter', '')} {f.get('operator', '')} "
            f"{f.get('value', '')} {f.get('unit', '') or ''})"
            if f.get("parameter")
            else ""
        )
        + f" — verdict: {f.get('verdict')}; design value: {f.get('design_value') or 'n/a'}; "
        + f"reviewer note: {f.get('rationale', '')}"
        for f in failing
    )
    prompt = (
        "You are a senior PCB/electronics engineer. A design was validated against a spec and some "
        "requirements did not pass. For EACH failing requirement below, propose ONE concrete, "
        "actionable remediation: the issue (why it's not satisfied), a suggestion (the exact change "
        "to make — add/swap a part, change a value, add a constraint), and a change_type from: "
        "add_component, change_value, swap_part, add_constraint, clarify. Name specific parts or "
        "values where possible.\n\n"
        f"Board goal:\n{intent}\n\n"
        f"Design under review:\n{design_summary}\n\n"
        f"Failing requirements:\n{issues}"
    )
    output = _call_structured(_RemediationOutput, prompt)
    output["all_clear"] = False
    return output
