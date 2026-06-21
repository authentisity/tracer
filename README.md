# Tracer

Tracer is an AI-assisted PCB requirements and validation workbench.

It turns a plain-English board idea into structured requirements, converts those
requirements into a formal spec, validates a candidate or real design against
that spec, suggests fixes, and exports the review as a Markdown report.

```text
Describe board -> intent -> requirements -> formal spec -> validate design -> suggest fixes -> export report
```

## Why

PCB projects often start as vague intent:

> I need a low-power ESP32 sensor board with USB-C charging.

Before a design can be trusted, that idea has to become checkable engineering
requirements: voltage limits, sleep current, battery life, interfaces, thermal
constraints, component choices, and verification methods.

Tracer helps close that gap. It gives engineers and students a review pipeline
for moving from natural language to requirements, then from requirements to
design validation.

## What It Does

- **Intent Analysis**: restates the goal, expands context, and surfaces open
  questions.
- **Structured Requirements**: groups requirements by category and marks each as
  user-stated or inferred.
- **Formal Specification**: converts requirements into machine-readable records
  with optional `parameter / operator / value / unit` constraints and a
  verification method.
- **Validation**: checks a candidate or real design against every formal
  requirement.
- **Real Design Inputs**: accepts pasted JSON, BOM CSV, or KiCad netlist input.
- **Design Artifact Persistence**: saves the provided design as its own stage so
  it survives reloads and can be reused.
- **Reference Guardrails**: flags validation claims that rely on parts or nets
  not present in the design artifact.
- **Remediation**: suggests concrete fixes for failed or unclear checks.
- **Markdown Export**: downloads the completed pipeline as a shareable report.

## Tech Stack

- Backend: FastAPI, Python, Pydantic, SQLite
- AI: Gemini via the Google GenAI SDK
- Frontend: React, Vite, JavaScript, CSS
- Design artifact support: JSON, BOM CSV, KiCad netlist parsing

## Requirements

- Python 3.11+
- Node.js 18+
- A [Google AI Studio API key](https://aistudio.google.com/apikey)

The backend expects this environment variable:

```sh
GOOGLE_API_KEY=your_gemini_api_key
```

Do not commit API keys. `.env` is ignored by Git.

## Backend Setup

```sh
cd tracer-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `tracer-backend/.env`:

```env
GOOGLE_API_KEY=your_gemini_api_key
```

Start the API:

```sh
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The API runs at `http://127.0.0.1:8000`.

FastAPI docs are available at:

```text
http://127.0.0.1:8000/docs
```

A local SQLite database is created automatically as `tracer-backend/tracer.db`.

## Frontend Setup

```sh
cd tracer-frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

If Vite starts on another port, such as `5174`, use the URL printed in the
terminal. The backend allows both `5173` and `5174` for local development.

## Demo Flow

1. Create a project with a plain-English board description.
2. Run **Intent Analysis**.
3. Run **Structured Requirements**.
4. Run **Formal Specification**.
5. Open **Validation**.
6. Either leave the artifact box empty to validate an AI-generated candidate, or
   provide a real design artifact.
7. Run validation and review pass, fail, and needs-review results.
8. Run **Remediation** to get suggested fixes.
9. Click **Export report** to download the Markdown report.

## Design Artifact Inputs

Validation can use an AI-generated candidate design or a user-provided artifact.

### JSON Artifact

```json
{
  "components": [
    {
      "ref": "U1",
      "part": "ESP32-C3",
      "values": {
        "supply_voltage": "3.3 V"
      }
    }
  ],
  "nets": [
    {
      "name": "3V3",
      "pins": ["U1.VDD"]
    }
  ],
  "parameters": {
    "input_voltage": "5 V",
    "sleep_current": "40 uA"
  }
}
```

### BOM CSV

Paste a bill of materials with columns such as `Reference`, `Part`, and `Value`.
Multi-reference cells like `C1, C2, C3` are expanded into separate components.

```csv
Reference,Part,Value
U1,ESP32-C3,MCU
R1,Resistor,10k
C1,Capacitor,100nF
```

### KiCad Netlist

Paste a standard KiCad `.net` export. Tracer extracts components and nets into
the design artifact shape.

```scheme
(export
  (components
    (comp (ref "U1") (value "ESP32-C3")))
  (nets
    (net (name "3V3")
      (node (ref "U1") (pin "1")))))
```

Plain English:

- BOM tells Tracer what parts are used.
- KiCad netlist tells Tracer how those parts are connected.

## Validation Behavior

Tracer uses a mix of deterministic checks and AI review:

- Numeric constraints such as `sleep_current < 50 uA` are checked in code with
  unit-aware comparisons.
- Requirements that cannot be checked numerically are reviewed by Gemini.
- Claims that cite missing parts or nets are flagged as unverified instead of
  silently passing.

This keeps the validation output more grounded than a pure AI judgment.

## Running Tests

Backend tests:

```sh
cd tracer-backend
python3 -m pytest test_pipeline.py
```

Frontend production build:

```sh
cd tracer-frontend
npm run build
```

Production dependency audit:

```sh
cd tracer-frontend
npm audit --omit=dev
```

## Notes

- AI stages require `GOOGLE_API_KEY`.
- Frontend build, BOM parsing, KiCad parsing, Markdown export, and backend unit
  tests do not require a live Gemini call.
- Full `npm audit` may report Vite/esbuild development-tool warnings. Production
  dependencies can be checked with `npm audit --omit=dev`.
