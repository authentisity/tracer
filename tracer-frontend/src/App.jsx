import { useEffect, useMemo, useRef, useState } from 'react'

// ── API layer ──────────────────────────────────────────────────────────────────

const API = 'http://localhost:8000'

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
  runStage: (projectId, stageName) =>
    apiFetch(`/projects/${projectId}/stage/${stageName}`, { method: 'POST' }),
}

// ── Constants ─────────────────────────────────────────────────────────────────

const CATEGORY_LABELS = {
  power: 'Power',
  interfaces: 'Interfaces',
  components: 'Components',
  signal: 'Signal Integrity',
  thermal: 'Thermal',
  mechanical: 'Mechanical',
  placement: 'Placement',
}

const CATEGORY_ORDER = ['power', 'interfaces', 'components', 'signal', 'thermal', 'mechanical', 'placement']

const STAGE_DEFS = [
  { num: '01', label: 'Describe board', screen: 'prompt' },
  { num: '02', label: 'Intent analysis', screen: null },
  { num: '03', label: 'Structured requirements', screen: 'requirements' },
  { num: '04', label: 'Formal specification', screen: null },
]

const DEFAULT_BRIEF =
  'Small USB-C powered mux board. 9–36 V input, needs 5 V at 3 A out. Talks I²C to a host controller. Must fit a 50 × 35 mm enclosure and run up to 70 °C ambient.'

const STARTERS = {
  mux: DEFAULT_BRIEF,
  ble: 'Compact BLE sensor node. Coin-cell powered (CR2032), reads a BME280 over I²C, advertises every 2 s. Chip antenna on board, fits a 25 mm round PCB, indoor use.',
  motor: 'Brushed DC motor driver. 12 V supply, up to 5 A continuous. STM32 control over CAN, current sense and thermal shutdown. 60 × 40 mm board, automotive cabin.',
}

const STARTER_OPTIONS = [
  { key: 'mux', label: 'USB-C power mux' },
  { key: 'ble', label: 'BLE sensor node' },
  { key: 'motor', label: 'DC motor driver' },
]

const EXTRACT_TAGS = ['Power', 'Interfaces', 'Components', 'Signal Integrity', 'Thermal', 'Mechanical', 'Placement']

const ANALYZING_STEPS = [
  'Parsing description',
  'Classifying by domain',
  'Extracting stated values',
  'Inferring gaps',
]

// ── Data helpers ──────────────────────────────────────────────────────────────

const CAT_KEY_MAP = { signal_integrity: 'signal' }

function mapCatKey(cat) {
  return CAT_KEY_MAP[cat] ?? cat
}

function deriveProjectName(brief) {
  const slug = brief
    .trim()
    .split(/\s+/)
    .slice(0, 5)
    .join('-')
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
  return slug || 'untitled'
}

function buildValueString(req) {
  const parts = []
  if (req.parameter) parts.push(req.parameter)
  if (req.operator) parts.push(req.operator)
  if (req.value != null) parts.push(String(req.value))
  if (req.unit) parts.push(req.unit)
  return parts.length > 0 ? parts.join(' ') : req.statement
}

function mapRequirements(formalReqs) {
  return (formalReqs ?? []).map((req) => ({
    id: req.id,
    cat: mapCatKey(req.category),
    title: req.statement,
    value: buildValueString(req),
    kind: req.provenance === 'user_stated' ? 'stated' : 'inferred',
    conf: req.confidence ?? (req.provenance === 'user_stated' ? 0.93 : 0.68),
  }))
}

function getConfidenceColor(conf) {
  if (conf >= 0.85) return '#3f7d57'
  if (conf >= 0.7) return '#c2620e'
  return '#cf9134'
}

function getBarStyle(conf) {
  return {
    width: `${Math.round(conf * 100)}%`,
    background: getConfidenceColor(conf),
  }
}

function buildFormalSpec(requirements, projectName) {
  const now = new Date().toISOString().slice(0, 10)
  const grouped = {}
  requirements.forEach((req) => {
    if (!grouped[req.cat]) grouped[req.cat] = []
    grouped[req.cat].push({
      id: req.id,
      title: req.title,
      value: req.value,
      origin: req.kind,
      confidence: Number(req.conf.toFixed(2)),
    })
  })

  const output = {
    project: projectName || 'untitled',
    revision: 'A',
    generated: now,
    summary: {
      total: requirements.length,
      stated: requirements.filter((r) => r.kind === 'stated').length,
      inferred: requirements.filter((r) => r.kind === 'inferred').length,
      confidence: Number(
        (requirements.reduce((sum, r) => sum + r.conf, 0) / (requirements.length || 1)).toFixed(2)
      ),
    },
    requirements: {},
  }

  CATEGORY_ORDER.forEach((cat) => {
    if (grouped[cat]) output.requirements[cat] = grouped[cat]
  })

  return output
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [screen, setScreen] = useState('prompt')
  const [brief, setBrief] = useState(DEFAULT_BRIEF)
  const [projectName, setProjectName] = useState('')
  const [requirements, setRequirements] = useState([])
  const [completedSteps, setCompletedSteps] = useState(0)
  const [analyzeError, setAnalyzeError] = useState(null)
  const [filter, setFilter] = useState('all')
  const [category, setCategory] = useState('all')
  const [formalized, setFormalized] = useState(false)
  const [copied, setCopied] = useState(false)
  const timeoutRef = useRef(null)

  useEffect(() => () => clearTimeout(timeoutRef.current), [])

  const stage = screen === 'prompt' ? 1 : screen === 'analyzing' ? 2 : formalized ? 4 : 3
  const statusText =
    screen === 'prompt'
      ? 'draft'
      : screen === 'analyzing'
      ? 'analyzing'
      : formalized
      ? 'formalized'
      : 'structured'

  const handleAnalyze = async () => {
    if (!brief.trim()) return
    setScreen('analyzing')
    setCompletedSteps(0)
    setAnalyzeError(null)
    setFormalized(false)
    setFilter('all')
    setCategory('all')

    try {
      const name = deriveProjectName(brief)
      setProjectName(name)

      const { project_id } = await api.createProject(name, brief)
      setCompletedSteps(1)

      await api.runStage(project_id, 'intent_expansion')
      setCompletedSteps(2)

      await api.runStage(project_id, 'structured_bullets')
      setCompletedSteps(3)

      const { output: formalOut } = await api.runStage(project_id, 'formal_requirements')
      setCompletedSteps(4)

      setRequirements(mapRequirements(formalOut.requirements))
      setScreen('requirements')
    } catch (err) {
      setAnalyzeError(err.message)
      setScreen('prompt')
    }
  }

  const handleStageClick = (targetScreen) => {
    if (!targetScreen || screen === 'analyzing') return
    if (targetScreen === 'requirements' && requirements.length === 0) return
    setScreen(targetScreen)
  }

  const handleToggleKind = (id) => {
    setRequirements((current) =>
      current.map((req) => {
        if (req.id !== id) return req
        if (req.kind === 'stated') {
          return { ...req, kind: 'inferred', conf: Math.max(0.5, req.conf - 0.2) }
        }
        return { ...req, kind: 'stated', conf: Math.min(0.99, req.conf + 0.2) }
      })
    )
  }

  const handleValueChange = (id, value) => {
    setRequirements((current) => current.map((req) => (req.id === id ? { ...req, value } : req)))
  }

  const total = requirements.length
  const statedCount = requirements.filter((r) => r.kind === 'stated').length
  const inferredCount = total - statedCount
  const averageConfidence =
    total > 0 ? requirements.reduce((acc, req) => acc + req.conf, 0) / total : 0
  const overallPct = `${Math.round(averageConfidence * 100)}%`
  const overallBar = {
    width: `${Math.round(averageConfidence * 100)}%`,
    background: getConfidenceColor(averageConfidence),
  }
  const summarySub = `${total} extracted · ${statedCount} stated · ${inferredCount} inferred`

  const activeFilters = [
    { key: 'all', text: `All ${total}` },
    { key: 'stated', text: `Stated ${statedCount}` },
    { key: 'inferred', text: `Inferred ${inferredCount}` },
  ]

  const categoryChips = useMemo(() => {
    const chips = [{ key: 'all', text: `All ${total}` }]
    CATEGORY_ORDER.forEach((key) => {
      const count = requirements.filter((r) => r.cat === key).length
      if (count > 0) chips.push({ key, text: `${CATEGORY_LABELS[key]} ${count}` })
    })
    return chips
  }, [requirements, total])

  const groups = useMemo(() => {
    const filtered = requirements.filter((req) => {
      if (filter !== 'all' && req.kind !== filter) return false
      if (category !== 'all' && req.cat !== category) return false
      return true
    })
    const result = []
    const categories = category === 'all' ? CATEGORY_ORDER : [category]
    categories.forEach((cat) => {
      const items = filtered.filter((req) => req.cat === cat)
      if (items.length > 0) result.push({ label: CATEGORY_LABELS[cat] ?? cat, count: items.length, items })
    })
    return result
  }, [requirements, filter, category])

  const inferredAssumptions = useMemo(
    () => requirements.filter((r) => r.kind === 'inferred').slice(0, 5),
    [requirements]
  )

  const spec = useMemo(() => buildFormalSpec(requirements, projectName), [requirements, projectName])
  const jsonText = useMemo(() => JSON.stringify(spec, null, 2), [spec])

  const copyJson = async () => {
    try {
      await navigator.clipboard.writeText(jsonText)
      setCopied(true)
      clearTimeout(timeoutRef.current)
      timeoutRef.current = setTimeout(() => setCopied(false), 1600)
    } catch {
      // ignore clipboard failure
    }
  }

  const footerNote = formalized
    ? 'Specification formalized · ready for export'
    : 'Regenerated live from current requirements'

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand-row">
          <div className="brand-mark">T</div>
          <div className="brand-wordmark">TRACER</div>
          <div className="brand-chip">v0.4</div>
        </div>

        <div className="topbar-divider" />

        <div className="project-row">
          <span className="project-label">PROJECT</span>
          <span className="project-name">{projectName || 'new-project'}</span>
          <span className="project-chip">REV A</span>
        </div>

        <div className="status-pill">
          <span className="status-dot" />
          <span className="status-text">{statusText}</span>
        </div>

        <div className="spacer" />

        {screen === 'requirements' && (
          <>
            <button className="btn btn-ghost" onClick={copyJson}>
              {copied ? 'Copied ✓' : 'Export JSON'}
            </button>
            <button className="btn btn-primary" onClick={() => setFormalized(true)}>
              Formalize spec →
            </button>
          </>
        )}
      </header>

      <div className="stage-strip">
        {STAGE_DEFS.map((stageDef, index) => {
          const isActive = index + 1 === stage
          const isDone = index + 1 < stage
          const isPending = index + 1 > stage
          const isNavigable = Boolean(stageDef.screen) && screen !== 'analyzing'
          return (
            <div key={stageDef.num} className="stage-item">
              <div
                className={`stage-item-inner ${isNavigable ? 'stage-item-inner--clickable' : ''}`}
                onClick={() => handleStageClick(stageDef.screen)}
              >
                <div
                  className={`stage-dot ${isActive ? 'stage-dot--active' : ''} ${
                    isDone ? 'stage-dot--done' : ''
                  } ${isPending ? 'stage-dot--pending' : ''}`}
                >
                  {isDone ? '✓' : stageDef.num}
                </div>
                <div className="stage-labels">
                  <span className="stage-pretitle">STAGE {stageDef.num}</span>
                  <span className={`stage-title ${isActive ? 'stage-title--active' : ''}`}>
                    {stageDef.label}
                  </span>
                </div>
              </div>
              {index < STAGE_DEFS.length - 1 && <span className="stage-separator">→</span>}
            </div>
          )
        })}
      </div>

      {screen === 'prompt' && (
        <div className="prompt-screen">
          <div className="prompt-inner">
            <div className="prompt-eyebrow">STAGE 01 · DESCRIBE BOARD</div>
            <h1 className="prompt-title">Describe your board</h1>
            <p className="prompt-lede">
              Write what the board needs to do in plain language — voltages, interfaces, size,
              environment. Tracer extracts the stated requirements, infers the gaps, and formalizes
              them into a spec you can review.
            </p>

            {analyzeError && (
              <div className="analyze-error">
                <span className="analyze-error-icon">!</span>
                <span>
                  Analysis failed: {analyzeError}
                  {!analyzeError.includes('localhost') &&
                    ' — Make sure the backend is running at localhost:8000.'}
                </span>
              </div>
            )}

            <div className="prompt-card">
              <textarea
                className="prompt-textarea"
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                spellCheck={false}
                placeholder="e.g. Small USB-C powered mux board. 9–36 V input, needs 5 V at 3 A out. Talks I²C to a host controller. Must fit a 50 × 35 mm enclosure and run up to 70 °C ambient."
              />
              <div className="prompt-card-footer">
                <button type="button" className="prompt-attach">
                  + Attach datasheet / netlist
                </button>
                <div className="spacer" />
                <span className="prompt-count">{brief.length} chars</span>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleAnalyze}
                  disabled={!brief.trim()}
                >
                  Analyze requirements →
                </button>
              </div>
            </div>

            <div className="prompt-section">
              <div className="prompt-section-label">TRY A STARTER</div>
              <div className="starter-row">
                {STARTER_OPTIONS.map((option) => (
                  <button
                    key={option.key}
                    type="button"
                    className="starter-chip"
                    onClick={() => setBrief(STARTERS[option.key])}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="prompt-section prompt-section--extract">
              <div className="prompt-section-label">TRACER WILL EXTRACT</div>
              <div className="extract-row">
                {EXTRACT_TAGS.map((tag) => (
                  <span key={tag} className="extract-tag">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {screen === 'analyzing' && (
        <div className="analyzing-screen">
          <div className="analyzing-spinner" />
          <div className="analyzing-text">
            <div className="analyzing-title">Analyzing intent…</div>
            <div className="analyzing-sub">Extracting requirements from your description</div>
          </div>
          <div className="analyzing-steps">
            {ANALYZING_STEPS.map((label, index) => {
              const isDone = index < completedSteps
              return (
                <div key={label} className={`analyzing-step ${isDone ? 'analyzing-step--done' : ''}`}>
                  <div
                    className={`analyzing-step-dot ${isDone ? 'analyzing-step-dot--done' : ''}`}
                    style={{ animationDelay: `${index * 0.2}s` }}
                  />
                  <span className="analyzing-step-label">{label}</span>
                  {isDone && <span className="analyzing-step-check">✓</span>}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {screen === 'requirements' && (
        <div className="layout">
          <aside className="rail-left">
            <div className="input-label-row">
              <span className="input-badge">INPUT</span>
              <span className="input-caption">plain language</span>
            </div>
            <div className="input-box">{brief}</div>

            <div className="divider" />

            <div className="section-label">INTENT ANALYSIS</div>
            <div className="stat-list">
              <div className="stat-row">
                <span>Requirements extracted</span>
                <span className="stat-value">{total}</span>
              </div>
              <div className="stat-row">
                <span>Stated</span>
                <span className="stat-value stat-value--green">{statedCount}</span>
              </div>
              <div className="stat-row">
                <span>Inferred</span>
                <span className="stat-value stat-value--amber">{inferredCount}</span>
              </div>
            </div>

            <div className="confidence-block">
              <div className="confidence-label-row">
                <span>OVERALL CONFIDENCE</span>
                <span>{overallPct}</span>
              </div>
              <div className="confidence-track">
                <div className="confidence-fill" style={overallBar} />
              </div>
            </div>

            <div className="divider" />

            <div className="section-label section-label--bottom">
              <span>INFERRED ASSUMPTIONS</span>
              <span>{inferredCount}</span>
            </div>
            <div className="assumptions-list">
              {inferredAssumptions.map((req) => (
                <div key={req.id} className="assumption-row">
                  <div className="assumption-dot" />
                  <div>
                    <span className="assumption-text">{req.title}</span>
                    <span className="assumption-tag">→ {req.id}</span>
                  </div>
                </div>
              ))}
            </div>
          </aside>

          <main className="main-content">
            <div className="content-header">
              <div>
                <div className="content-title">Structured requirements</div>
                <div className="content-subtitle">{summarySub}</div>
              </div>
              <div className="filter-row">
                {activeFilters.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    className={`chip ${filter === item.key ? 'chip--active' : ''}`}
                    onClick={() => setFilter(item.key)}
                  >
                    {item.text}
                  </button>
                ))}
              </div>
            </div>

            <div className="chip-bar">
              {categoryChips.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  className={`chip ${category === item.key ? 'chip--active' : ''}`}
                  onClick={() => setCategory(item.key)}
                >
                  {item.text}
                </button>
              ))}
            </div>

            <div className="groups-column">
              {groups.map((group) => (
                <section key={group.label} className="group-section">
                  <div className="group-header">
                    <span className="group-title">{group.label}</span>
                    <span className="group-count">{group.count}</span>
                    <div className="group-spacer" />
                  </div>
                  <div className="group-items">
                    {group.items.map((req) => {
                      const isStated = req.kind === 'stated'
                      const stripColor = isStated ? '#9bbf9f' : '#d3ccbf'
                      const badgeBg = isStated ? '#e7efe7' : '#fbeed8'
                      const badgeColor = isStated ? '#3f6b50' : '#9a4d09'
                      const badgeBorder = isStated ? '#cfe0d2' : '#f0dcb5'
                      return (
                        <div key={req.id} className="req-card">
                          <div className="req-strip" style={{ background: stripColor }} />
                          <div className="req-body">
                            <div className="req-top-row">
                              <span className="req-id">{req.id}</span>
                              <button
                                type="button"
                                className="req-badge"
                                onClick={() => handleToggleKind(req.id)}
                                style={{
                                  background: badgeBg,
                                  color: badgeColor,
                                  borderColor: badgeBorder,
                                }}
                              >
                                {isStated ? 'STATED' : 'INFERRED'}
                              </button>
                              <div className="req-spacer" />
                              <div className="req-confidence">
                                <span className="req-conf-label">CONF</span>
                                <div className="req-conf-track">
                                  <div className="req-conf-fill" style={getBarStyle(req.conf)} />
                                </div>
                                <span className="req-conf-text">
                                  {Math.round(req.conf * 100)}%
                                </span>
                              </div>
                            </div>
                            <div className="req-title">{req.title}</div>
                            <input
                              className="req-input"
                              value={req.value}
                              onChange={(e) => handleValueChange(req.id, e.target.value)}
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </section>
              ))}
            </div>
          </main>

          <aside className="rail-right">
            <div className="spec-header">
              <span className="spec-label">FORMAL SPECIFICATION</span>
              <span className="spec-tab">JSON</span>
            </div>
            <div className="spec-panel">
              <div className="spec-panel-header">
                <div className="spec-dot" />
                <span className="spec-filename">{projectName || 'project'}.req.json</span>
                <div className="req-spacer" />
                <button type="button" className="spec-copy" onClick={copyJson}>
                  {copied ? 'copied ✓' : 'copy'}
                </button>
              </div>
              <pre className="spec-pre">{jsonText}</pre>
            </div>
            <div className="spec-footer">
              <div className="footer-dot" />
              <span className="footer-note">{footerNote}</span>
            </div>
          </aside>
        </div>
      )}
    </div>
  )
}
