import anthropic

_client = anthropic.Anthropic()
_MODEL = "claude-opus-4-8"

# ── Tool definitions ──────────────────────────────────────────────────────────

_INTENT_TOOL = {
    "name": "record_intent_expansion",
    "description": "Record the expanded intent analysis for a PCB design project.",
    "input_schema": {
        "type": "object",
        "properties": {
            "restated_goal": {
                "type": "string",
                "description": "One-sentence restatement of the board's core purpose.",
            },
            "functional_description": {
                "type": "string",
                "description": (
                    "2–4 sentences describing what the board does, its key subsystems, "
                    "and main data/power flows."
                ),
            },
            "inferred_context": {
                "type": "string",
                "description": (
                    "2–4 sentences on context not explicitly stated: target environment, "
                    "likely regulatory applicability, production scale, technology maturity."
                ),
            },
            "open_questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Specific unanswered questions whose answers would materially change "
                    "the design. Limit to the most impactful ones."
                ),
            },
        },
        "required": ["restated_goal", "functional_description", "inferred_context", "open_questions"],
    },
}

_BULLETS_TOOL = {
    "name": "record_structured_bullets",
    "description": "Record structured design requirement bullets organised by category.",
    "input_schema": {
        "type": "object",
        "properties": {
            "bullets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The requirement in plain engineering language.",
                        },
                        "category": {
                            "type": "string",
                            "enum": [
                                "power", "interfaces", "components", "signal_integrity",
                                "thermal", "mechanical", "placement", "other",
                            ],
                        },
                        "provenance": {
                            "type": "string",
                            "enum": ["user_stated", "inferred"],
                            "description": "Whether the designer stated this or it was inferred.",
                        },
                        "rationale": {
                            "type": "string",
                            "description": (
                                "Brief AI reasoning explaining why this was inferred. "
                                "Omit for user_stated requirements."
                            ),
                        },
                    },
                    "required": ["text", "category", "provenance"],
                },
            }
        },
        "required": ["bullets"],
    },
}

_FORMAL_TOOL = {
    "name": "record_formal_requirements",
    "description": "Record formal, machine-readable requirements with quantitative constraints.",
    "input_schema": {
        "type": "object",
        "properties": {
            "requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": (
                                "Unique ID with category prefix, e.g. PWR-001, MECH-003, "
                                "INTF-002, SIG-001, COMP-004, THERM-001, PLAC-002."
                            ),
                        },
                        "category": {
                            "type": "string",
                            "enum": [
                                "power", "interfaces", "components", "signal_integrity",
                                "thermal", "mechanical", "placement", "other",
                            ],
                        },
                        "statement": {
                            "type": "string",
                            "description": "The requirement as a single declarative sentence.",
                        },
                        "provenance": {
                            "type": "string",
                            "enum": ["user_stated", "inferred"],
                        },
                        "parameter": {
                            "type": "string",
                            "description": "The specific parameter being constrained, e.g. 'supply_voltage'.",
                        },
                        "operator": {
                            "type": "string",
                            "enum": ["<=", ">=", "==", "<", ">", "in"],
                        },
                        "value": {
                            "description": "Numeric or enumerated value for the constraint.",
                            "oneOf": [{"type": "number"}, {"type": "string"}],
                        },
                        "unit": {
                            "type": "string",
                            "description": "SI unit or standard abbreviation, e.g. 'V', 'mA', 'mm', '°C'.",
                        },
                        "verification_method": {
                            "type": "string",
                            "description": "How to verify this requirement: simulation, measurement, inspection, analysis, test.",
                        },
                    },
                    "required": ["id", "category", "statement", "provenance"],
                },
            }
        },
        "required": ["requirements"],
    },
}


# ── Internal helper ───────────────────────────────────────────────────────────

def _call_structured(tool: dict, messages: list[dict]) -> dict:
    response = _client.messages.create(
        model=_MODEL,
        max_tokens=4096,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=messages,
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == tool["name"]:
            return block.input
    raise RuntimeError(f"Model did not return expected tool call '{tool['name']}'")


# ── Stage runners ─────────────────────────────────────────────────────────────

def run_intent_expansion(intent: str) -> dict:
    messages = [
        {
            "role": "user",
            "content": (
                "You are a senior PCB/electronics engineer. "
                "Analyse the following board description and expand the designer's intent. "
                "Be precise and draw on standard electronics engineering knowledge.\n\n"
                f"Board description:\n{intent}"
            ),
        }
    ]
    return _call_structured(_INTENT_TOOL, messages)


def run_structured_bullets(intent: str, intent_expansion: dict) -> dict:
    messages = [
        {
            "role": "user",
            "content": (
                "You are a senior PCB/electronics engineer. "
                "Using the original description and intent analysis below, generate a comprehensive "
                "set of design requirement bullets organised by category. "
                "Mark each as user_stated (explicitly from the description) or inferred "
                "(your expert engineering judgement). For inferred items include a brief rationale.\n\n"
                f"Original description:\n{intent}\n\n"
                "Intent analysis:\n"
                f"Goal: {intent_expansion['restated_goal']}\n"
                f"Functional: {intent_expansion['functional_description']}\n"
                f"Context: {intent_expansion['inferred_context']}"
            ),
        }
    ]
    return _call_structured(_BULLETS_TOOL, messages)


def run_formal_requirements(intent: str, intent_expansion: dict, structured_bullets: dict) -> dict:
    bullets_text = "\n".join(
        f"  [{b['category']}][{b['provenance']}] {b['text']}"
        for b in structured_bullets.get("bullets", [])
    )
    messages = [
        {
            "role": "user",
            "content": (
                "You are a senior PCB/electronics engineer. "
                "Convert the requirement bullets below into formal, machine-readable requirements. "
                "Assign each a unique ID using prefix codes matching the category "
                "(PWR-, INTF-, COMP-, SIG-, THERM-, MECH-, PLAC-, OTH-). "
                "Write a declarative statement for every requirement. "
                "Where a requirement is quantifiable, add parameter, operator, value, and unit. "
                "Add a verification_method (simulation / measurement / inspection / analysis / test) "
                "for every requirement.\n\n"
                f"Original description:\n{intent}\n\n"
                f"Goal: {intent_expansion['restated_goal']}\n\n"
                f"Requirement bullets:\n{bullets_text}"
            ),
        }
    ]
    return _call_structured(_FORMAL_TOOL, messages)
