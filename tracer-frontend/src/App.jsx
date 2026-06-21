import { useState, useCallback, useEffect, useRef } from 'react'

const API = 'http://localhost:8000'

// ── API helpers ──────────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

const api = {
  createProject: (name, intent) =>
    apiFetch('/projects', { method: 'POST', body: JSON.stringify({ name, intent }) }),
  getProject: (id) => apiFetch(`/projects/${id}`),
  runStage: (projectId, stageName, body) =>
    apiFetch(`/projects/${projectId}/stage/${stageName}`, {
      method: 'POST',
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    }),
  revise: (stageId, editedOutput, note) =>
    apiFetch(`/stages/${stageId}/revise`, {
      method: 'POST',
      body: JSON.stringify({ edited_output: editedOutput, note }),
    }),
}

// ── Constants ────────────────────────────────────────────────────────────────

const STAGES = [
  {
    key: 'intent_expansion',
    label: 'Intent Analysis',
    shortLabel: 'Intent',
    description: 'Understand and expand your description',
  },
  {
    key: 'structured_bullets',
    label: 'Structured Requirements',
    shortLabel: 'Requirements',
    description: 'Organise into categories with provenance',
  },
  {
    key: 'formal_requirements',
    label: 'Formal Specification',
    shortLabel: 'Formal Spec',
    description: 'Machine-readable spec with test criteria',
  },
  {
    key: 'validation',
    label: 'Validation',
    shortLabel: 'Validation',
    description: 'Check a candidate design against the spec',
  },
]

const STAGE_ENDPOINT = {
  intent_expansion: 'intent_expansion',
  structured_bullets: 'structured_bullets',
  formal_requirements: 'formal_requirements',
  validation: 'validation',
}

const VERDICT_LABEL = { pass: 'Pass', fail: 'Fail', needs_review: 'Review' }
const METHOD_LABEL = {
  deterministic: 'math check',
  judgment: 'reviewer',
  unit_mismatch: 'unit mismatch',
  incomplete_value: 'needs value',
  unverified_reference: 'unverified ref',
}

const ARTIFACT_PLACEHOLDER = `{
  "components": [
    { "ref": "U1", "part": "ESP32-C3", "values": { "supply_voltage": "3.3 V" } }
  ],
  "nets": [
    { "name": "3V3", "pins": ["U1.VDD"] }
  ],
  "parameters": { "input_voltage": "5 V", "sleep_current": "40 uA" }
}`

const CATEGORY_LABELS = {
  power: 'Power',
  interfaces: 'Interfaces',
  components: 'Components',
  signal_integrity: 'Signal Integrity',
  thermal: 'Thermal',
  mechanical: 'Mechanical',
  placement: 'Placement',
  other: 'Other',
}

// ── Small primitives ─────────────────────────────────────────────────────────

function ProvenanceTag({ provenance }) {
  return (
    <span className={`provenance-tag provenance-${provenance}`}>
      {provenance === 'user_stated' ? 'stated' : 'inferred'}
    </span>
  )
}

function StatusDot({ status }) {
  return <span className={`status-dot status-${status}`} aria-label={status} />
}

function Spinner() {
  return <span className="spinner" aria-label="Running" />
}

function ErrorBanner({ message, onDismiss }) {
  return (
    <div className="error-banner" role="alert">
      <span className="error-icon">!</span>
      <span className="error-text">{message}</span>
      {onDismiss && (
        <button className="error-dismiss" onClick={onDismiss} aria-label="Dismiss error">
          ×
        </button>
      )}
    </div>
  )
}

// ── Stage rail ───────────────────────────────────────────────────────────────

function StageRail({ stages, activeStageKey, onSelectStage, isMobile }) {
  return (
    <nav className={`stage-rail ${isMobile ? 'stage-rail--mobile' : ''}`} aria-label="Pipeline stages">
      {STAGES.map((stageDef, idx) => {
        const stage = stages.find((s) => s.stage_type === stageDef.key)
        const status = stage?.status ?? 'pending'
        const isActive = stageDef.key === activeStageKey
        const isClickable = !!stage

        return (
          <div key={stageDef.key} className="rail-item-wrapper">
            {idx > 0 && <div className={`rail-trace ${status !== 'pending' ? 'rail-trace--lit' : ''}`} aria-hidden="true" />}
            <button
              className={`rail-node ${isActive ? 'rail-node--active' : ''} ${isClickable ? 'rail-node--clickable' : ''}`}
              onClick={() => isClickable && onSelectStage(stageDef.key)}
              disabled={!isClickable}
              aria-current={isActive ? 'step' : undefined}
            >
              <div className="rail-node-circle">
                {status === 'running' ? (
                  <Spinner />
                ) : status === 'complete' ? (
                  <span className="rail-check" aria-hidden="true">✓</span>
                ) : status === 'failed' ? (
                  <span className="rail-fail" aria-hidden="true">✕</span>
                ) : (
                  <span className="rail-index" aria-hidden="true">{idx + 1}</span>
                )}
              </div>
              <div className="rail-node-label">
                <span className="rail-label-main">{isMobile ? stageDef.shortLabel : stageDef.label}</span>
                {!isMobile && <span className="rail-label-sub">{stageDef.description}</span>}
              </div>
            </button>
          </div>
        )
      })}
    </nav>
  )
}

// ── Stage 1: Intent Expansion ────────────────────────────────────────────────

function IntentExpansionOutput({ output, onEdit }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const textareaRef = useRef(null)

  function startEdit() {
    setDraft(JSON.stringify(output, null, 2))
    setEditing(true)
  }

  function handleSave() {
    try {
      const parsed = JSON.parse(draft)
      onEdit(parsed)
      setEditing(false)
    } catch {
      // keep editing — parse error
    }
  }

  useEffect(() => {
    if (editing && textareaRef.current) textareaRef.current.focus()
  }, [editing])

  if (editing) {
    return (
      <div className="edit-block">
        <label className="edit-label" htmlFor="intent-edit">
          Edit analysis output (JSON)
        </label>
        <textarea
          id="intent-edit"
          ref={textareaRef}
          className="edit-textarea mono"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={20}
          spellCheck={false}
        />
        <div className="edit-actions">
          <button className="btn btn--primary" onClick={handleSave}>
            Save changes
          </button>
          <button className="btn btn--ghost" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="stage-output">
      <div className="output-field">
        <h3 className="output-field-label">Restated goal</h3>
        <p className="output-prose">{output.restated_goal}</p>
      </div>
      <div className="output-field">
        <h3 className="output-field-label">Functional description</h3>
        <p className="output-prose">{output.functional_description}</p>
      </div>
      <div className="output-field">
        <h3 className="output-field-label">Inferred context</h3>
        <p className="output-prose">{output.inferred_context}</p>
      </div>
      {output.open_questions?.length > 0 && (
        <div className="output-field">
          <h3 className="output-field-label output-field-label--warn">
            Open questions
            <span className="flag-count">{output.open_questions.length}</span>
          </h3>
          <ul className="open-questions">
            {output.open_questions.map((q, i) => (
              <li key={i} className="open-question">
                <span className="question-bullet" aria-hidden="true">?</span>
                <span>{q}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="output-actions">
        <button className="btn btn--ghost btn--sm" onClick={startEdit}>
          Edit assumptions
        </button>
      </div>
    </div>
  )
}

// ── Stage 2: Structured Bullets ──────────────────────────────────────────────

function StructuredBulletsOutput({ output, onEdit }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const textareaRef = useRef(null)

  function startEdit() {
    setDraft(JSON.stringify(output, null, 2))
    setEditing(true)
  }

  function handleSave() {
    try {
      const parsed = JSON.parse(draft)
      onEdit(parsed)
      setEditing(false)
    } catch {
      // keep editing
    }
  }

  useEffect(() => {
    if (editing && textareaRef.current) textareaRef.current.focus()
  }, [editing])

  if (editing) {
    return (
      <div className="edit-block">
        <label className="edit-label" htmlFor="bullets-edit">
          Edit structured requirements (JSON)
        </label>
        <textarea
          id="bullets-edit"
          ref={textareaRef}
          className="edit-textarea mono"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={24}
          spellCheck={false}
        />
        <div className="edit-actions">
          <button className="btn btn--primary" onClick={handleSave}>
            Save changes
          </button>
          <button className="btn btn--ghost" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </div>
      </div>
    )
  }

  const grouped = {}
  for (const bullet of output.bullets ?? []) {
    const cat = bullet.category ?? 'other'
    if (!grouped[cat]) grouped[cat] = []
    grouped[cat].push(bullet)
  }

  return (
    <div className="stage-output">
      {Object.entries(grouped).map(([category, bullets]) => (
        <div key={category} className="bullet-category">
          <h3 className="bullet-category-label">{CATEGORY_LABELS[category] ?? category}</h3>
          <ul className="bullet-list">
            {bullets.map((b, i) => (
              <li key={i} className="bullet-item">
                <div className="bullet-header">
                  <ProvenanceTag provenance={b.provenance} />
                  <span className="bullet-text">{b.text}</span>
                </div>
                {b.rationale && (
                  <p className="bullet-rationale">
                    <span className="rationale-label">AI reasoning:</span> {b.rationale}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
      <div className="output-actions">
        <button className="btn btn--ghost btn--sm" onClick={startEdit}>
          Edit requirements
        </button>
      </div>
    </div>
  )
}

// ── Stage 3: Formal Requirements ─────────────────────────────────────────────

function FormalRequirementsOutput({ output, onEdit }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const textareaRef = useRef(null)

  function startEdit() {
    setDraft(JSON.stringify(output, null, 2))
    setEditing(true)
  }

  function handleSave() {
    try {
      const parsed = JSON.parse(draft)
      onEdit(parsed)
      setEditing(false)
    } catch {
      // keep editing
    }
  }

  useEffect(() => {
    if (editing && textareaRef.current) textareaRef.current.focus()
  }, [editing])

  if (editing) {
    return (
      <div className="edit-block">
        <label className="edit-label" htmlFor="formal-edit">
          Edit formal specification (JSON)
        </label>
        <textarea
          id="formal-edit"
          ref={textareaRef}
          className="edit-textarea mono"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={28}
          spellCheck={false}
        />
        <div className="edit-actions">
          <button className="btn btn--primary" onClick={handleSave}>
            Save changes
          </button>
          <button className="btn btn--ghost" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </div>
      </div>
    )
  }

  const grouped = {}
  for (const req of output.requirements ?? []) {
    const cat = req.category ?? 'other'
    if (!grouped[cat]) grouped[cat] = []
    grouped[cat].push(req)
  }

  return (
    <div className="stage-output">
      {Object.entries(grouped).map(([category, reqs]) => (
        <div key={category} className="req-category">
          <h3 className="bullet-category-label">{CATEGORY_LABELS[category] ?? category}</h3>
          {reqs.map((req) => (
            <div key={req.id} className="req-card">
              <div className="req-card-header">
                <span className="mono req-id">{req.id}</span>
                <ProvenanceTag provenance={req.provenance} />
              </div>
              <p className="req-statement">{req.statement}</p>
              {(req.parameter || req.value != null) && (
                <div className="req-spec-row">
                  {req.parameter && <span className="mono req-spec-part">{req.parameter}</span>}
                  {req.operator && <span className="mono req-spec-op">{req.operator}</span>}
                  {req.value != null && <span className="mono req-spec-part">{req.value}</span>}
                  {req.unit && <span className="mono req-spec-unit">{req.unit}</span>}
                </div>
              )}
              {req.verification_method && (
                <div className="req-verify">
                  <span className="req-verify-label">Verify by:</span>
                  <span className="mono">{req.verification_method}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      ))}
      <div className="output-actions">
        <button className="btn btn--ghost btn--sm" onClick={startEdit}>
          Edit specification
        </button>
      </div>
    </div>
  )
}

// ── Stage 4: Validation ──────────────────────────────────────────────────────

function VerdictBadge({ verdict }) {
  return (
    <span className={`verdict-badge verdict-badge--${verdict}`}>
      {VERDICT_LABEL[verdict] ?? verdict}
    </span>
  )
}

function ValidationOutput({ output, onEdit }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const textareaRef = useRef(null)

  function startEdit() {
    setDraft(JSON.stringify(output, null, 2))
    setEditing(true)
  }

  function handleSave() {
    try {
      onEdit(JSON.parse(draft))
      setEditing(false)
    } catch {
      // keep editing — parse error
    }
  }

  useEffect(() => {
    if (editing && textareaRef.current) textareaRef.current.focus()
  }, [editing])

  if (editing) {
    return (
      <div className="edit-block">
        <label className="edit-label" htmlFor="validation-edit">
          Edit validation output (JSON)
        </label>
        <textarea
          id="validation-edit"
          ref={textareaRef}
          className="edit-textarea mono"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={28}
          spellCheck={false}
        />
        <div className="edit-actions">
          <button className="btn btn--primary" onClick={handleSave}>
            Save changes
          </button>
          <button className="btn btn--ghost" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </div>
      </div>
    )
  }

  const summary = output.summary ?? { pass: 0, fail: 0, needs_review: 0, total: 0 }
  const results = output.results ?? []
  const design = output.design ?? null
  const keyParameters = design?.key_parameters ?? []
  const source = output.source ?? 'ai_candidate'
  const fromArtifact = source === 'uploaded_artifact'

  return (
    <div className="stage-output">
      <div className="validation-summary">
        <span className="vsum-chip vsum-chip--pass">{summary.pass} pass</span>
        <span className="vsum-chip vsum-chip--fail">{summary.fail} fail</span>
        <span className="vsum-chip vsum-chip--review">{summary.needs_review} review</span>
        {summary.flagged > 0 && (
          <span className="vsum-chip vsum-chip--flagged">{summary.flagged} flagged</span>
        )}
        <span className="vsum-total">of {summary.total} requirements</span>
        <span className={`vsource vsource--${source}`}>
          {fromArtifact ? '✓ validated your artifact' : 'AI candidate'}
        </span>
      </div>

      {design && (
        <div className="output-field">
          <h3 className="output-field-label">
            {fromArtifact ? 'Your design artifact' : 'Candidate design (AI-generated)'}
          </h3>
          <p className="output-prose">{design.summary}</p>
          {design.components?.length > 0 && (
            <ul className="design-comp-list">
              {design.components.map((c, i) => (
                <li key={i} className="design-comp">
                  <span className="mono req-id">{c.ref}</span>
                  <span className="design-comp-part">{c.part}</span>
                  {c.rationale && <span className="design-comp-rationale">{c.rationale}</span>}
                </li>
              ))}
            </ul>
          )}
          {design.nets?.length > 0 && (
            <ul className="design-comp-list">
              {design.nets.map((n, i) => (
                <li key={`net-${i}`} className="design-comp">
                  <span className="mono req-id">{n.name}</span>
                  <span className="design-comp-rationale">{(n.pins ?? []).join(', ')}</span>
                </li>
              ))}
            </ul>
          )}
          {keyParameters.length > 0 && (
            <div className="design-param-grid">
              {keyParameters.map((p, i) => (
                <div key={`${p.name}-${i}`} className="design-param">
                  <span className="design-param-name">{p.name}</span>
                  <span className="mono design-param-value">
                    {p.value}{p.unit ? ` ${p.unit}` : ''}
                  </span>
                  {p.rationale && <span className="design-param-rationale">{p.rationale}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="output-field">
        <h3 className="output-field-label">Requirement checks</h3>
        {results.length === 0 && <p className="output-prose">No requirement checks returned.</p>}
        {results.map((r, i) => {
          const method = r.method ?? 'judgment'
          return (
            <div key={r.req_id ?? i} className="req-card">
              <div className="req-card-header">
                <span className="mono req-id">{r.req_id}</span>
                <VerdictBadge verdict={r.verdict} />
                <span className={`method-tag method-tag--${method}`}>
                  {METHOD_LABEL[method] ?? method}
                </span>
              </div>
              <p className="req-statement">{r.statement}</p>
              <div className="check-compare">
                {(r.parameter || r.value != null) && (
                  <span className="check-expected">
                    expected{' '}
                    <span className="mono">
                      {r.parameter ? `${r.parameter} ` : ''}
                      {r.operator} {r.value}
                      {r.unit ? ` ${r.unit}` : ''}
                    </span>
                  </span>
                )}
                {r.design_value != null && (
                  <span className="check-actual">
                    design <span className="mono">{r.design_value}</span>
                  </span>
                )}
              </div>
              {r.rationale && <p className="check-rationale">{r.rationale}</p>}
              {r.flagged_refs?.length > 0 && (
                <p className="check-flagged">
                  ⚠ references not in the design: {r.flagged_refs.join(', ')}
                </p>
              )}
            </div>
          )
        })}
      </div>

      <div className="output-actions">
        <button className="btn btn--ghost btn--sm" onClick={startEdit}>
          Edit results
        </button>
      </div>
    </div>
  )
}

// ── Design artifact input (Stage 4 — validate a real design) ─────────────────

function ArtifactInput({ value, onChange, candidate }) {
  function fillFromCandidate() {
    if (!candidate) return
    const artifact = {
      components: (candidate.components ?? []).map((c) => ({
        ref: c.ref,
        part: c.part,
        values: {},
      })),
      nets: candidate.nets ?? [],
      parameters: Object.fromEntries(
        (candidate.key_parameters ?? []).map((p) => [
          p.name,
          [p.value, p.unit].filter(Boolean).join(' '),
        ]),
      ),
    }
    onChange(JSON.stringify(artifact, null, 2))
  }

  return (
    <div className="artifact-input">
      <div className="artifact-input-head">
        <span className="output-field-label">
          Design to validate <span className="artifact-optional">— optional</span>
        </span>
        {candidate?.components?.length > 0 && (
          <button type="button" className="artifact-fill" onClick={fillFromCandidate}>
            Fill from AI candidate
          </button>
        )}
      </div>
      <p className="artifact-hint">
        Paste your board design as JSON to validate it. Leave blank to validate an AI-generated candidate.
      </p>
      <textarea
        className="edit-textarea mono"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={8}
        spellCheck={false}
        placeholder={ARTIFACT_PLACEHOLDER}
      />
    </div>
  )
}

// ── Stage panel ──────────────────────────────────────────────────────────────

function StagePanel({ stageDef, stage, projectId, onStageComplete, onRevise }) {
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)
  const [savingRevision, setSavingRevision] = useState(false)
  const [revisionSaved, setRevisionSaved] = useState(false)
  const [artifact, setArtifact] = useState('')
  const pendingEditRef = useRef(null)

  const status = stage?.status ?? 'pending'
  const output = stage?.output_json ?? null
  const stageError = stage?.error ?? null

  async function runStage() {
    setError(null)
    let body
    if (stageDef.key === 'validation') {
      const trimmed = artifact.trim()
      if (trimmed) {
        try {
          body = { artifact: JSON.parse(trimmed) }
        } catch {
          setError('Design artifact must be valid JSON — fix it or clear the box to use an AI candidate.')
          return
        }
      } else {
        body = {} // no artifact → validate an AI-generated candidate
      }
    }
    setRunning(true)
    try {
      const result = await api.runStage(projectId, STAGE_ENDPOINT[stageDef.key], body)
      onStageComplete(stageDef.key, result)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  async function handleEdit(editedOutput) {
    if (!stage?.id) {
      // stage not saved yet — shouldn't happen, but guard anyway
      return
    }
    pendingEditRef.current = editedOutput
    setSavingRevision(true)
    setRevisionSaved(false)
    try {
      await api.revise(stage.id, editedOutput, 'User override via UI')
      onRevise(stageDef.key, editedOutput)
      setRevisionSaved(true)
      setTimeout(() => setRevisionSaved(false), 3000)
    } catch (err) {
      setError(`Could not save revision: ${err.message}`)
    } finally {
      setSavingRevision(false)
    }
  }

  const isRunning = status === 'running' || running
  const canRun = status === 'pending' || status === 'failed' || status === 'complete'
  const runLabel = stageDef.key === 'validation' ? 'Run validation' : 'Run analysis'
  const rerunLabel = stageDef.key === 'validation' ? 'Re-run validation' : 'Re-run analysis'
  const runningLabel = stageDef.key === 'validation' ? 'Validating' : 'Analysing'

  return (
    <section className="stage-panel" aria-label={stageDef.label}>
      <div className="stage-panel-header">
        <div className="stage-panel-title-row">
          <StatusDot status={isRunning ? 'running' : status} />
          <h2 className="stage-panel-title">{stageDef.label}</h2>
        </div>
        <p className="stage-panel-desc">{stageDef.description}</p>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {(stageError && status === 'failed') && (
        <ErrorBanner
          message={`Analysis failed: ${stageError}. Check your board description and try again.`}
        />
      )}

      {savingRevision && (
        <div className="saving-banner">
          <Spinner /> Saving your changes…
        </div>
      )}

      {revisionSaved && (
        <div className="saved-banner" role="status">
          Changes saved — downstream stages will use your version.
        </div>
      )}

      {stageDef.key === 'validation' && !isRunning && (
        <ArtifactInput value={artifact} onChange={setArtifact} candidate={output?.design} />
      )}

      {status === 'pending' && !isRunning && (
        <div className="stage-empty">
          <div className="stage-empty-icon" aria-hidden="true">◈</div>
          <p className="stage-empty-text">
            {stageDef.key === 'intent_expansion'
              ? 'Ready to analyse your board description.'
              : stageDef.key === 'structured_bullets'
              ? 'Complete Intent Analysis first, then run this stage.'
              : stageDef.key === 'formal_requirements'
              ? 'Complete Structured Requirements first, then run this stage.'
              : 'Complete the Formal Specification first, then run this stage.'}
          </p>
          <button
            className="btn btn--primary"
            onClick={runStage}
            disabled={isRunning}
          >
            {runLabel}
          </button>
        </div>
      )}

      {isRunning && (
        <div className="stage-running">
          <Spinner />
          <p className="stage-running-text">{runningLabel} — this takes a few seconds…</p>
        </div>
      )}

      {status === 'complete' && output && (
        <>
          {stageDef.key === 'intent_expansion' && (
            <IntentExpansionOutput output={output} onEdit={handleEdit} />
          )}
          {stageDef.key === 'structured_bullets' && (
            <StructuredBulletsOutput output={output} onEdit={handleEdit} />
          )}
          {stageDef.key === 'formal_requirements' && (
            <FormalRequirementsOutput output={output} onEdit={handleEdit} />
          )}
          {stageDef.key === 'validation' && (
            <ValidationOutput output={output} onEdit={handleEdit} />
          )}
          {canRun && (
            <div className="output-actions">
              <button className="btn btn--ghost btn--sm" onClick={runStage} disabled={isRunning}>
                {rerunLabel}
              </button>
            </div>
          )}
        </>
      )}

      {status === 'failed' && !isRunning && (
        <div className="output-actions" style={{ marginTop: '1rem' }}>
          <button className="btn btn--primary" onClick={runStage}>
            Retry
          </button>
        </div>
      )}
    </section>
  )
}

// ── Project setup form ───────────────────────────────────────────────────────

function ProjectSetup({ onCreate }) {
  const [name, setName] = useState('')
  const [intent, setIntent] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!intent.trim()) return
    setError(null)
    setLoading(true)
    try {
      const { project_id } = await api.createProject(name.trim() || 'Untitled board', intent.trim())
      onCreate(project_id, intent.trim())
    } catch (err) {
      setError(`Could not create project: ${err.message}. Make sure the backend is running at localhost:8000.`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="setup-screen">
      <header className="setup-header">
        <div className="wordmark">
          <span className="wordmark-trace" aria-hidden="true">⬡</span>
          <span className="wordmark-text">Tracer</span>
        </div>
        <p className="setup-tagline">Describe your board. We'll build the spec.</p>
      </header>

      <form className="setup-form" onSubmit={handleSubmit} noValidate>
        <div className="form-field">
          <label className="form-label" htmlFor="project-name">
            Project name <span className="form-optional">(optional)</span>
          </label>
          <input
            id="project-name"
            className="form-input"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Wireless sensor node rev A"
            autoComplete="off"
          />
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="board-intent">
            Describe your board
          </label>
          <p className="form-hint">
            Write naturally — what it does, who uses it, any constraints you know about. The AI will
            infer the rest and flag its assumptions for you to review.
          </p>
          <textarea
            id="board-intent"
            className="form-textarea"
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            placeholder="e.g. A battery-powered environmental monitor that reads temperature, humidity, and CO₂, then sends readings over BLE every 30 seconds. It needs to run for at least a year on two AA batteries. The enclosure is outdoor-rated IP65."
            rows={6}
            required
          />
        </div>

        {error && <ErrorBanner message={error} />}

        <button
          className="btn btn--primary btn--lg"
          type="submit"
          disabled={loading || !intent.trim()}
        >
          {loading ? <><Spinner /> Starting…</> : 'Describe your board →'}
        </button>
      </form>

      <div className="setup-legend">
        <div className="legend-item">
          <ProvenanceTag provenance="user_stated" />
          <span className="legend-desc">From your description</span>
        </div>
        <div className="legend-item">
          <ProvenanceTag provenance="inferred" />
          <span className="legend-desc">AI expert inference — review these</span>
        </div>
      </div>
    </div>
  )
}

// ── Root App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [projectId, setProjectId] = useState(null)
  const [project, setProject] = useState(null)
  const [activeStageKey, setActiveStageKey] = useState('intent_expansion')
  const [loadError, setLoadError] = useState(null)
  const [isMobile, setIsMobile] = useState(window.innerWidth < 700)

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 700px)')
    const handler = (e) => setIsMobile(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  const refreshProject = useCallback(async (id) => {
    try {
      const p = await api.getProject(id)
      setProject(p)
    } catch (err) {
      setLoadError(err.message)
    }
  }, [])

  function handleCreate(id) {
    setProjectId(id)
    setActiveStageKey('intent_expansion')
    refreshProject(id)
  }

  function handleStageComplete(stageKey, result) {
    // Merge the new stage into local project state without full refetch
    setProject((prev) => {
      if (!prev) return prev
      const existing = prev.stages?.find((s) => s.stage_type === stageKey)
      const newStage = {
        id: result.stage_id ?? existing?.id,
        stage_type: stageKey,
        status: 'complete',
        output_json: result.output ?? result,
        error: null,
      }
      const stages = prev.stages
        ? prev.stages.map((s) => (s.stage_type === stageKey ? newStage : s))
        : [newStage]
      if (!stages.find((s) => s.stage_type === stageKey)) stages.push(newStage)
      return { ...prev, stages }
    })
  }

  function handleRevise(stageKey, editedOutput) {
    setProject((prev) => {
      if (!prev) return prev
      const stages = prev.stages?.map((s) =>
        s.stage_type === stageKey ? { ...s, output_json: editedOutput } : s
      )
      return { ...prev, stages }
    })
  }

  if (!projectId) {
    return <ProjectSetup onCreate={handleCreate} />
  }

  if (!project) {
    return (
      <div className="loading-screen">
        <Spinner />
        <p>Loading project…</p>
        {loadError && <ErrorBanner message={loadError} />}
      </div>
    )
  }

  const activeStageDef = STAGES.find((s) => s.key === activeStageKey)
  const activeStageData = project.stages?.find((s) => s.stage_type === activeStageKey)

  return (
    <div className="app">
      <header className="app-header">
        <div className="wordmark">
          <span className="wordmark-trace" aria-hidden="true">⬡</span>
          <span className="wordmark-text">Tracer</span>
        </div>
        <div className="app-header-right">
          <span className="project-name">{project.name ?? 'Untitled board'}</span>
          <button
            className="btn btn--ghost btn--sm"
            onClick={() => {
              setProjectId(null)
              setProject(null)
              setActiveStageKey('intent_expansion')
            }}
          >
            New project
          </button>
        </div>
      </header>

      <div className="app-body">
        <StageRail
          stages={project.stages ?? []}
          activeStageKey={activeStageKey}
          onSelectStage={setActiveStageKey}
          isMobile={isMobile}
        />

        <main className="main-panel" id="main-content">
          <StagePanel
            key={activeStageKey}
            stageDef={activeStageDef}
            stage={activeStageData}
            projectId={projectId}
            onStageComplete={handleStageComplete}
            onRevise={handleRevise}
          />

          {/* next-stage nudge */}
          {activeStageData?.status === 'complete' && (() => {
            const idx = STAGES.findIndex((s) => s.key === activeStageKey)
            const next = STAGES[idx + 1]
            if (!next) return null
            const nextStage = project.stages?.find((s) => s.stage_type === next.key)
            if (nextStage?.status === 'complete') return null
            return (
              <div className="next-stage-nudge">
                <span className="nudge-arrow" aria-hidden="true">↓</span>
                <span>Ready for the next stage —</span>
                <button
                  className="nudge-link"
                  onClick={() => setActiveStageKey(next.key)}
                >
                  {next.label}
                </button>
              </div>
            )
          })()}
        </main>
      </div>
    </div>
  )
}
