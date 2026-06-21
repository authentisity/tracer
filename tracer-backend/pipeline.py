import json
import os
import re
from typing import Any, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel

import catalog as _catalog
import erc as _erc
import netlist_writer as _nw
import placement_constraints as _pc
import placement_solver as _ps

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
    cited_refs: list[str] = []            # component refs / net names the verdict relied on


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


def _design_from_artifact(artifact: dict) -> tuple[dict, str, str, str]:
    """Shape a user-provided design artifact into a design dict + prompt lines."""
    components = []
    for c in artifact.get("components") or []:
        values = c.get("values") or {}
        rationale = "; ".join(f"{k}: {v}" for k, v in values.items()) or "(provided)"
        components.append({"ref": c.get("ref", ""), "part": c.get("part", ""), "rationale": rationale})
    nets = [
        {"name": n.get("name", ""), "pins": n.get("pins") or []}
        for n in artifact.get("nets") or []
    ]
    params = artifact.get("parameters") or {}
    key_parameters = [
        {"name": k, "value": str(v), "unit": None, "rationale": "user-provided"}
        for k, v in params.items()
    ]
    param_summary = "; ".join(f"{k}: {v}" for k, v in params.items())
    design = {
        "summary": "User-provided design artifact" + (f" — {param_summary}" if param_summary else ""),
        "components": components,
        "nets": nets,
        "key_parameters": key_parameters,
    }
    comp_lines = "\n".join(f"  {c['ref']}: {c['part']} — {c['rationale']}" for c in components)
    net_lines = "\n".join(f"  {n['name']}: {', '.join(n['pins'])}" for n in nets)
    parameter_lines = "\n".join(f"  {p['name']}: {p['value']}" for p in key_parameters)
    return design, comp_lines, net_lines, parameter_lines


def run_validation(
    intent: str,
    intent_expansion: dict,
    formal_requirements: dict,
    artifact: Optional[dict] = None,
) -> dict:
    reqs = formal_requirements.get("requirements", [])
    source = "uploaded_artifact" if artifact else "ai_candidate"

    if artifact:
        # Validate the design the user actually provided.
        design, comp_lines, net_lines, parameter_lines = _design_from_artifact(artifact)
    else:
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
        net_lines = ""  # AI candidate design has no explicit nets
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
        "Given the design under review and the formal requirements, assess whether the design "
        "satisfies EACH requirement. For every requirement return: its req_id; the design_value — the "
        "concrete value or property the design exhibits for that requirement's parameter (a short "
        "string, or null if the design does not address it); a verdict of 'pass', 'fail', or "
        "'needs_review'; a one-sentence rationale; and cited_refs — the component reference "
        "designators or net names FROM THE DESIGN BELOW that you relied on (use only refs/nets that "
        "actually appear in the design; return an empty list if none). Be strict: if the design does "
        "not clearly address a requirement, use 'needs_review' or 'fail', never 'pass'. For "
        "quantitative checks, include a numeric design_value with units, for example '3.3 V' or "
        "'250 mA'.\n\n"
        f"Design under review:\n{design.get('summary', '')}\n\n"
        f"Components:\n{comp_lines}\n\n"
        f"Nets:\n{net_lines}\n\n"
        f"Key parameters:\n{parameter_lines}\n\n"
        f"Requirements:\n{req_detail}"
    )
    checks = _call_structured(_ChecksOutput, check_prompt).get("checks", [])
    checks_by_id = {c.get("req_id"): c for c in checks}

    # Anti-hallucination guardrail: the set of refs/nets the design actually contains.
    known_refs = {str(c.get("ref", "")).strip().lower() for c in design.get("components", [])}
    known_refs |= {str(n.get("name", "")).strip().lower() for n in design.get("nets", [])}
    known_refs.discard("")

    def _flagged(cited) -> list:
        flagged = []
        for ref in cited or []:
            tok = str(ref).strip().lower()
            if tok and tok not in known_refs and tok.split(".")[0] not in known_refs:
                flagged.append(ref)
        return flagged

    # 3) Resolve each verdict deterministically where the requirement is quantitative.
    results = []
    for r in reqs:
        c = checks_by_id.get(r.get("id"), {})
        design_value = c.get("design_value")
        verdict, method = _resolve_verdict(r, design_value, c.get("verdict", "needs_review"))
        flagged_refs = _flagged(c.get("cited_refs")) if known_refs else []
        # A "pass" justified by parts/nets that aren't in the design can't be trusted.
        if flagged_refs and verdict == "pass":
            verdict, method = "needs_review", "unverified_reference"
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
            "flagged_refs": flagged_refs,
        })

    summary = {
        "total": len(results),
        "pass": sum(1 for x in results if x["verdict"] == "pass"),
        "fail": sum(1 for x in results if x["verdict"] == "fail"),
        "needs_review": sum(1 for x in results if x["verdict"] == "needs_review"),
        "flagged": sum(1 for x in results if x["flagged_refs"]),
    }
    return {"design": design, "results": results, "summary": summary, "source": source}


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


# ── Stage 4: Component selection ──────────────────────────────────────────────
# The LLM never invents part numbers. It emits parametric search criteria;
# catalog.search() returns real matches; the LLM (or score) picks from those.

class _ConstraintSpec(BaseModel):
    name: str      # parameter key matching catalog.CatalogPart.parameters
    operator: str  # eq | min | max | in
    value: str     # string representation; "in" uses comma-separated values


class _SearchCriteria(BaseModel):
    functional_role: str
    category: str   # mcu|ldo|resistor|capacitor|sensor|connector|led|diode|crystal|header|inductor
    constraints: list[_ConstraintSpec]
    satisfies_requirement_ids: list[str]


class _SearchCriteriaList(BaseModel):
    criteria: list[_SearchCriteria]


class _PickedPart(BaseModel):
    part_id: str
    rationale: str


# Parameter names the LLM should use, communicated in the decompose prompt.
_CATALOG_SCHEMA_HINT = """
Available catalog parameter names by category (use exact names in constraints):
  mcu:       cpu, freq_mhz, flash_kb, ram_kb, gpio_count, i2c_count, spi_count, uart_count, usb_fs, package
  ldo:       output_voltage_v, max_current_a, dropout_v, input_voltage_max_v, quiescent_current_ma, package
  capacitor: capacitance_uf, voltage_v, dielectric, package
  resistor:  resistance_ohm, tolerance_pct, power_w, package
  sensor:    interface, measures, supply_v_min, supply_v_max, package
  connector: connector_type, usb_version, mounting, current_rating_a
  led:       color, package, vf_v, if_ma
  crystal:   frequency_mhz, load_capacitance_pf, package
  diode:     type, package, vf_v, vr_v
  header:    pins, pitch_mm, rows, gender, mounting
  inductor:  impedance_ohm_at_100mhz, current_rating_a, package
""".strip()


def _constraints_to_criteria(constraints: list[dict[str, str]]) -> dict[str, Any]:
    """Convert list of {name, operator, value} dicts to catalog.search() criteria dict."""
    result: dict[str, Any] = {}
    for c in constraints:
        name = c.get("name", "")
        op = c.get("operator", "eq")
        raw = c.get("value", "")
        if not name:
            continue
        try:
            num: Any = float(raw)
        except (TypeError, ValueError):
            num = None

        entry = result.setdefault(name, {})
        if op == "eq":
            result[name] = {"eq": num if num is not None else raw}
        elif op == "min":
            entry["min"] = num if num is not None else raw
        elif op == "max":
            entry["max"] = num if num is not None else raw
        elif op == "in":
            result[name] = {"in": [v.strip() for v in raw.split(",")]}
    return result


def run_stage4_component_selection(formal_requirements: dict) -> dict:
    """Select real catalog parts for every functional block implied by the requirements.

    Flow:
    1. LLM emits parametric search criteria per functional block (no part numbers).
    2. catalog.search() returns matching real parts for each criterion.
    3. If one match: select it. If multiple: LLM ranks and picks from real candidates only.
       If zero: record in unresolved so failures are explicit.
    """
    reqs = formal_requirements.get("requirements", [])
    req_summary = "\n".join(
        f"  [{r.get('id', '?')}] {r.get('statement', '')}"
        + (
            f" ({r.get('parameter', '')} {r.get('operator', '')} "
            f"{r.get('value', '')} {r.get('unit', '') or ''})"
            if r.get("parameter")
            else ""
        )
        for r in reqs
    )

    # Step 1 — LLM decomposes requirements into parametric search criteria.
    decompose_prompt = (
        "You are a senior PCB/electronics engineer designing a microcontroller breakout board. "
        "Analyse the formal requirements below and decompose the board into functional blocks. "
        "For each functional block emit parametric search criteria to find a suitable component.\n\n"
        "Include all mandatory blocks for an MCU breakout: the MCU itself, an LDO 3.3 V regulator, "
        "at least one I²C sensor matched to the requirements, decoupling capacitors (100 nF per "
        "supply pin, bulk 10 µF at LDO output), I²C pull-up resistors (4.7 kΩ), LED(s) with "
        "current-limit resistors, a USB-C connector, a crystal oscillator if the MCU needs an "
        "external clock, ESD protection on USB data lines, and breakout pin headers.\n\n"
        "Rules:\n"
        "  - DO NOT invent part numbers — emit only search criteria.\n"
        "  - operator must be one of: eq, min, max, in\n"
        "  - value is always a string; for 'in' use comma-separated items, e.g. 'SOT-223,SOT-23-5'\n"
        "  - satisfies_requirement_ids must reference IDs from the requirements list below.\n\n"
        f"{_CATALOG_SCHEMA_HINT}\n\n"
        f"Formal requirements:\n{req_summary}"
    )
    criteria_output = _call_structured(_SearchCriteriaList, decompose_prompt)
    criteria_list = criteria_output.get("criteria", [])

    selected: list[dict] = []
    unresolved: list[dict] = []

    for criterion in criteria_list:
        role: str = criterion.get("functional_role", "unknown")
        category: str = criterion.get("category", "")
        raw_constraints: list[dict] = criterion.get("constraints", [])
        req_ids: list[str] = criterion.get("satisfies_requirement_ids", [])

        criteria_dict = _constraints_to_criteria(raw_constraints)
        candidates = _catalog.search(category, criteria_dict)

        if not candidates:
            # Relax to category-only match so narrow constraints don't silently swallow blocks.
            candidates = _catalog.search(category, {})

        if not candidates:
            unresolved.append({
                "functional_role": role,
                "reason": (
                    f"No catalog parts in category '{category}'. "
                    "Constraints: "
                    + "; ".join(
                        f"{c.get('name')} {c.get('operator')} {c.get('value')}"
                        for c in raw_constraints
                    )
                ),
            })
            continue

        if len(candidates) == 1:
            part = candidates[0]
            selected.append(_make_selected(role, part, req_ids,
                                           f"Only catalog match: {part.description}"))
            continue

        # Step 3 — LLM picks one from the real candidate list.
        candidates_lines = "\n".join(
            f"  part_id={p.part_id}  mpn={p.mpn}  desc={p.description}  params={p.parameters}"
            for p in candidates
        )
        constraints_summary = "\n".join(
            f"  {c.get('name')} {c.get('operator')} {c.get('value')}"
            for c in raw_constraints
        )
        pick_prompt = (
            f"You are a senior PCB/electronics engineer selecting a component for: {role!r}.\n\n"
            f"Search constraints:\n{constraints_summary}\n\n"
            f"Catalog candidates (choose ONLY a part_id from this list):\n{candidates_lines}\n\n"
            "Return the part_id of the best-fit component and a concise rationale. "
            "You MUST return a part_id that appears verbatim in the candidate list above."
        )
        pick_result = _call_structured(_PickedPart, pick_prompt)

        picked_id: str = pick_result.get("part_id", "")
        rationale: str = pick_result.get("rationale", "")

        # Anti-hallucination guard: verify the returned part_id is real.
        part = next((p for p in candidates if p.part_id == picked_id), None)
        if part is None:
            part = candidates[0]
            rationale = (
                f"[fallback — model returned unknown part_id {picked_id!r}] {rationale}"
            )

        selected.append(_make_selected(role, part, req_ids, rationale))

    return {"components": selected, "unresolved": unresolved}


def _make_selected(
    role: str,
    part: "_catalog.CatalogPart",
    req_ids: list[str],
    rationale: str,
) -> dict:
    return {
        "functional_role": role,
        "part_id": part.part_id,
        "mpn": part.mpn,
        "kicad_symbol": part.kicad_symbol,
        "kicad_footprint": part.kicad_footprint,
        "category": part.category,
        "satisfies_requirement_ids": req_ids,
        "provenance": "catalog_search",
        "rationale": rationale,
    }


# ── Stage 5: Netlist generation ───────────────────────────────────────────────
# The LLM proposes connectivity; deterministic ERC gates persistence.

class _NetPin(BaseModel):
    component_role: str
    pin_number: str


class _Net5(BaseModel):
    name: str
    pins: list[_NetPin]
    net_class: str                   # power | ground | signal | bus
    satisfies_requirement_ids: list[str]
    provenance: str
    rationale: str


class _UnconnectedPin(BaseModel):
    component_role: str
    pin_number: str
    reason: str


class _NetlistProposal(BaseModel):
    nets: list[_Net5]
    unconnected: list[_UnconnectedPin]


def _build_pin_context(components: list[dict]) -> tuple[str, dict[str, dict]]:
    """Return (LLM pin table, catalog_pins dict) for all selected components."""
    catalog_pins: dict[str, dict] = {}
    lines: list[str] = ["Component pin reference (role → part_id → pin# → name [type]):"]
    for comp in components:
        role = comp["functional_role"]
        part_id = comp["part_id"]
        pins = _catalog.get_pins(part_id)
        catalog_pins[part_id] = pins
        if not pins:
            lines.append(f"  {role} ({part_id}): [no pin data]")
            continue
        pin_strs = ", ".join(
            f"{num}:{info.get('name', num)}[{info.get('type', '?')}]"
            for num, info in sorted(pins.items(), key=lambda kv: kv[0])
        )
        lines.append(f"  {role} ({part_id}): {pin_strs}")
    return "\n".join(lines), catalog_pins


def run_stage5_netlist(
    component_selection: dict,
    formal_requirements: dict,
) -> dict:
    """Generate a netlist from selected components and requirements.

    Flow:
    1. Build a pin context table from the catalog for every selected component.
    2. Prompt the LLM to propose nets (connectivity), honouring ERC constraints.
    3. Run deterministic ERC on the proposal.
    4. On pass: persist and emit KiCad .net text.
       On fail: raise ValueError with structured violations so the caller can
                persist a failed stage and return them to the client.
    """
    components: list[dict] = component_selection.get("components", [])
    if not components:
        raise ValueError("component_selection has no components — run stage 4 first.")

    reqs = formal_requirements.get("requirements", [])
    req_summary = "\n".join(
        f"  [{r.get('id', '?')}] {r.get('statement', '')}"
        + (
            f" ({r.get('parameter', '')} {r.get('operator', '')} "
            f"{r.get('value', '')} {r.get('unit', '') or ''})"
            if r.get("parameter")
            else ""
        )
        for r in reqs
    )

    pin_context, catalog_pins = _build_pin_context(components)

    comp_summary = "\n".join(
        f"  {c['functional_role']} — {c['mpn']} ({c['category']})"
        for c in components
    )

    prompt = (
        "You are a senior PCB/electronics engineer. Produce a complete netlist for the MCU breakout "
        "board described by the components and requirements below.\n\n"
        "Rules:\n"
        "  1. Every pin listed in the component reference MUST appear in exactly one net OR in the "
        "     unconnected list. Pins typed 'nc' may be omitted from unconnected.\n"
        "  2. Ground pins (type=ground) must go on a net with net_class='ground'.\n"
        "  3. Power_in pins of ICs must go on a net with net_class='power'.\n"
        "  4. Power_out pins of regulators/MCU 3.3 V output go on a net_class='power' net.\n"
        "  5. Nets with SDA or SCL pins must also include a passive pin from a pull-up resistor.\n"
        "  6. Each VDD net of an IC must include at least one capacitor passive pin.\n"
        "  7. No two power_out or output pins may share the same net.\n"
        "  8. Use descriptive net names: GND, VDD_3V3, VBUS, I2C_SDA, I2C_SCL, USB_DM, USB_DP, "
        "     LED1, NRST, etc.\n"
        "  9. satisfies_requirement_ids must reference IDs from the requirements list.\n"
        " 10. Use ONLY pin numbers that appear in the component reference below.\n\n"
        f"Selected components:\n{comp_summary}\n\n"
        f"{pin_context}\n\n"
        f"Formal requirements:\n{req_summary}"
    )

    raw = _call_structured(_NetlistProposal, prompt)
    nets_raw: list[dict] = raw.get("nets", [])
    unc_raw: list[dict] = raw.get("unconnected", [])

    # Normalise unconnected into {pin_ref: {...}, reason: str} shape
    unconnected: list[dict] = []
    for u in unc_raw:
        unconnected.append({
            "pin_ref": {
                "component_role": u.get("component_role", ""),
                "pin_number": u.get("pin_number", ""),
                "part_id": next(
                    (c["part_id"] for c in components
                     if c["functional_role"] == u.get("component_role")),
                    "?",
                ),
            },
            "reason": u.get("reason", ""),
        })

    # Normalise nets: embed part_id in each pin
    role_to_part: dict[str, str] = {
        c["functional_role"]: c["part_id"] for c in components
    }
    nets: list[dict] = []
    for n in nets_raw:
        pins_out = []
        for p in n.get("pins", []):
            role = p.get("component_role", "")
            pins_out.append({
                "component_role": role,
                "part_id": role_to_part.get(role, "?"),
                "pin_number": p.get("pin_number", ""),
            })
        nets.append({
            "name": n.get("name", ""),
            "pins": pins_out,
            "net_class": n.get("net_class", "signal"),
            "satisfies_requirement_ids": n.get("satisfies_requirement_ids", []),
            "provenance": n.get("provenance", "llm_proposed"),
            "rationale": n.get("rationale", ""),
        })

    # ── ERC ──────────────────────────────────────────────────────────────────
    violations = _erc.run_erc(nets, unconnected, components, catalog_pins)
    erc_passed = len(violations) == 0

    # ── KiCad .net output ─────────────────────────────────────────────────────
    kicad_net = _nw.write_kicad_net(components, nets, unconnected)

    result: dict = {
        "nets": nets,
        "unconnected": unconnected,
        "erc_passed": erc_passed,
        "erc_violations": violations,
        "kicad_net_file": kicad_net,
    }

    if not erc_passed:
        raise _ErcFailure(violations, result)

    return result


class _ErcFailure(Exception):
    """Raised when ERC finds violations; carries both the violations and the partial output."""
    def __init__(self, violations: list[dict], partial_output: dict) -> None:
        super().__init__(f"ERC failed with {len(violations)} violation(s)")
        self.violations = violations
        self.partial_output = partial_output


# ── Stage 6: Component placement ─────────────────────────────────────────────
# Solver-driven, not LLM-driven.  Constraints compiled from netlist topology
# and formal requirements; Z3 finds a legal grid-quantised placement.

def run_stage6_placement(
    component_selection: dict,
    netlist: dict,
    formal_requirements: dict,
    board_outline: Optional[dict] = None,
    grid_mm: float = 0.5,
    optimize: bool = False,
    timeout_ms: int = 30_000,
) -> dict:
    """Compile placement constraints and solve with Z3.

    An infeasible solve is a valid outcome: it is returned as a successful dict
    with status="infeasible" and a structured unsat_reason.  The caller persists
    this as a complete stage (not failed) so the user can inspect the reason and
    adjust board size or requirements.

    Raises ValueError for configuration errors (missing geometry, empty
    component list) — those become failed stages in the endpoint.
    """
    components: list[dict] = component_selection.get("components", [])
    if not components:
        raise ValueError("component_selection has no components — run stage 4 first.")

    # Build catalog_pins for all selected parts
    catalog_pins: dict[str, dict] = {
        comp["part_id"]: _catalog.get_pins(comp["part_id"])
        for comp in components
    }

    # Compile — may raise ValueError listing parts with missing geometry
    compiled = _pc.compile_constraints(
        board_outline=board_outline,
        components=components,
        netlist=netlist,
        formal_requirements=formal_requirements,
        catalog_pins=catalog_pins,
        grid_mm=grid_mm,
        default_board_mm=(60.0, 60.0),
    )

    result = _ps.solve(compiled, optimize=optimize, timeout_ms=timeout_ms)

    board = {
        "width_mm":  compiled.board_w_units * grid_mm,
        "height_mm": compiled.board_h_units * grid_mm,
    }

    if result.status == "placed":
        return {
            "board": board,
            "components": list(result.positions.values()),
            "status": "placed",
            "unsat_reason": None,
            "unsat_groups": [],
            "objective_value": result.objective_value,
        }

    # infeasible or timeout — both are "complete" stages with an explanatory status
    return {
        "board": board,
        "components": [],
        "status": result.status,
        "unsat_reason": result.unsat_reason,
        "unsat_groups": result.unsat_groups,
        "objective_value": None,
    }
