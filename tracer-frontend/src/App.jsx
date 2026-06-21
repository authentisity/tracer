import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

const CATEGORY_LABELS = {
  power: 'Power',
  interfaces: 'Interfaces',
  components: 'Components',
  signal: 'Signal Integrity',
  thermal: 'Thermal',
  mechanical: 'Mechanical',
  placement: 'Placement',
}

const CATEGORY_ORDER = [
  'power',
  'interfaces',
  'components',
  'signal',
  'thermal',
  'mechanical',
  'placement',
]

const STAGE_DEFS = [
  { num: '01', label: 'Describe board', screen: 'prompt' },
  { num: '02', label: 'Intent analysis', screen: null },
  { num: '03', label: 'Structured requirements', screen: 'requirements' },
  { num: '04', label: 'Design validation', screen: 'validation' },
  { num: '05', label: 'Remediation', screen: 'remediation' },
  { num: '06', label: 'Export report', screen: 'report' },
]

const SCREEN_STAGE = {
  prompt: 1,
  analyzing: 2,
  requirements: 3,
  validation: 4,
  remediation: 5,
  report: 6,
}

const DESIGN_SOURCES = [
  {
    key: 'ai',
    label: 'AI-generated candidate',
    hint: 'Let Tracer synthesize a candidate design straight from the formal spec.',
  },
  {
    key: 'json',
    label: 'Paste JSON',
    hint: 'Paste a design description as a JSON object of populated parameters.',
  },
  {
    key: 'bom',
    label: 'BOM CSV',
    hint: 'Drop in a bill of materials — Tracer maps line items to requirements.',
  },
  {
    key: 'netlist',
    label: 'KiCad netlist',
    hint: 'Import a .net file exported from KiCad and validate against the spec.',
  },
]

const CANDIDATE_DESIGN = `{
  "design": "rev-c-power-mux candidate",
  "source": "tracer-synthesized",
  "input": { "range": "9-36 V", "connector": "USB-C" },
  "rails": [
    { "net": "VOUT", "v": 5.0, "i_max": 3.0 },
    { "net": "V3V3", "v": 3.3, "i_max": 1.0 }
  ],
  "protection": { "reverse_polarity": "P-FET", "iq_typ_uA": 68 },
  "interfaces": ["USB-C USB2.0 FS", "I2C @ 400kHz"],
  "thermal": { "ambient_max_c": 70, "junction_margin_c": 12 },
  "mechanical": { "outline_mm": "50 x 35", "debug": "none" }
}`

// status: 'pass' | 'warn' | 'fail'. fix only present on warn/fail.
const VALIDATION_CHECKS = [
  { id: 'PWR-01', title: 'Input voltage range', expected: '9 – 36 V DC', actual: '9 – 36 V', status: 'pass' },
  { id: 'PWR-02', title: 'Primary output rail', expected: '5.0 V @ 3.0 A', actual: '5.0 V @ 3.0 A', status: 'pass' },
  {
    id: 'PWR-03',
    title: 'Logic rail',
    expected: '3.3 V @ 1.5 A',
    actual: '3.3 V @ 1.0 A',
    status: 'warn',
    fix: 'Raise the buck inductor saturation rating to ≥ 2 A so V3V3 meets the 1.5 A spec.',
  },
  { id: 'PWR-04', title: 'Reverse-polarity protection', expected: 'Required · P-FET', actual: 'P-FET present', status: 'pass' },
  {
    id: 'PWR-05',
    title: 'Quiescent current',
    expected: '< 50 µA',
    actual: '68 µA',
    status: 'fail',
    fix: 'Swap the always-on LDO for a TPS7A02 (25 nA Iq) to bring quiescent draw under 50 µA.',
  },
  { id: 'IF-01', title: 'Host link', expected: 'USB-C · USB 2.0 FS', actual: 'USB-C USB2.0 FS', status: 'pass' },
  { id: 'IF-02', title: 'Control bus', expected: 'I²C @ 400 kHz', actual: 'I²C @ 400 kHz', status: 'pass' },
  {
    id: 'IF-03',
    title: 'Debug port',
    expected: 'SWD · 10-pin 1.27 mm',
    actual: 'not populated',
    status: 'warn',
    fix: 'Add a 10-pin 1.27 mm SWD header at the board edge for programming and debug.',
  },
  {
    id: 'CMP-01',
    title: 'Buck converter',
    expected: 'Sync · ≥ 90% eff',
    actual: '88% eff @ 3 A',
    status: 'warn',
    fix: 'Select a sync buck rated ≥ 90% efficiency at 3 A (e.g. TPS62932).',
  },
  { id: 'SI-01', title: 'USB differential impedance', expected: '90 Ω ± 10%', actual: '90 Ω', status: 'pass' },
  { id: 'TH-01', title: 'Max ambient', expected: '70 °C', actual: '70 °C rated', status: 'pass' },
  {
    id: 'TH-02',
    title: 'Junction margin',
    expected: '≥ 20 °C',
    actual: '12 °C',
    status: 'fail',
    fix: 'Add a copper pour with thermal vias under U2 (or derate to 60 °C ambient) to recover ≥ 20 °C margin.',
  },
  { id: 'MEC-01', title: 'Board outline', expected: '50 × 35 mm', actual: '50 × 35 mm', status: 'pass' },
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

const EXTRACT_TAGS = [
  'Power',
  'Interfaces',
  'Components',
  'Signal Integrity',
  'Thermal',
  'Mechanical',
  'Placement',
]

const ANALYZING_STEPS = [
  'Parsing description',
  'Classifying by domain',
  'Extracting stated values',
  'Inferring gaps',
]

const INITIAL_REQUIREMENTS = [
  { id: 'PWR-01', cat: 'power', title: 'Input voltage range', value: '9 – 36 V DC', kind: 'stated', conf: 0.98 },
  { id: 'PWR-02', cat: 'power', title: 'Primary output rail', value: '5.0 V @ 3.0 A', kind: 'stated', conf: 0.97 },
  { id: 'PWR-03', cat: 'power', title: 'Logic rail', value: '3.3 V @ 1.5 A', kind: 'inferred', conf: 0.74 },
  { id: 'PWR-04', cat: 'power', title: 'Reverse-polarity protection', value: 'Required · P-FET', kind: 'inferred', conf: 0.69 },
  { id: 'PWR-05', cat: 'power', title: 'Quiescent current', value: '< 50 µA', kind: 'inferred', conf: 0.58 },
  { id: 'IF-01', cat: 'interfaces', title: 'Host link', value: 'USB-C · USB 2.0 FS', kind: 'stated', conf: 0.95 },
  { id: 'IF-02', cat: 'interfaces', title: 'Control bus', value: 'I²C @ 400 kHz', kind: 'stated', conf: 0.96 },
  { id: 'IF-03', cat: 'interfaces', title: 'Debug port', value: 'SWD · 10-pin 1.27 mm', kind: 'inferred', conf: 0.71 },
  { id: 'CMP-01', cat: 'components', title: 'Buck converter', value: 'Sync · ≥ 90% eff', kind: 'inferred', conf: 0.66 },
  { id: 'CMP-02', cat: 'components', title: 'Microcontroller', value: 'Cortex-M0+ class', kind: 'inferred', conf: 0.62 },
  { id: 'SI-01', cat: 'signal', title: 'USB differential impedance', value: '90 Ω ± 10%', kind: 'inferred', conf: 0.78 },
  { id: 'SI-02', cat: 'signal', title: 'I²C pull-ups', value: '2.2 kΩ to 3V3', kind: 'inferred', conf: 0.64 },
  { id: 'TH-01', cat: 'thermal', title: 'Max ambient', value: '70 °C', kind: 'stated', conf: 0.94 },
  { id: 'TH-02', cat: 'thermal', title: 'Junction margin', value: '≥ 20 °C', kind: 'inferred', conf: 0.60 },
  { id: 'MEC-01', cat: 'mechanical', title: 'Board outline', value: '50 × 35 mm', kind: 'stated', conf: 0.99 },
  { id: 'MEC-02', cat: 'mechanical', title: 'Mounting', value: '4 × M2.5', kind: 'inferred', conf: 0.67 },
  { id: 'PLC-01', cat: 'placement', title: 'USB-C connector', value: 'Board edge · south', kind: 'inferred', conf: 0.63 },
  { id: 'PLC-02', cat: 'placement', title: 'Connectors', value: 'Top side only', kind: 'inferred', conf: 0.61 },
]

const ASSUMPTIONS = [
  { text: '3.3 V logic rail assumed from I²C bus and MCU presence.', tag: 'PWR-03' },
  { text: 'Reverse-polarity FET added for wide 9–36 V input.', tag: 'PWR-04' },
  { text: 'USB 2.0 full-speed — no high-speed cue in the brief.', tag: 'IF-01' },
  { text: 'Enclosure fit implies 4 × M2.5 mounting holes.', tag: 'MEC-02' },
  { text: 'Edge-mounted USB-C for connector access through the case.', tag: 'PLC-01' },
]

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

function buildFormalSpec(requirements) {
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
    project: 'rev-c-power-mux',
    revision: 'C',
    generated: now,
    summary: {
      total: requirements.length,
      stated: requirements.filter((r) => r.kind === 'stated').length,
      inferred: requirements.filter((r) => r.kind === 'inferred').length,
      confidence: Number(
        (
          requirements.reduce((sum, r) => sum + r.conf, 0) / requirements.length
        ).toFixed(2)
      ),
    },
    requirements: {},
  }

  Object.keys(grouped).forEach((cat) => {
    output.requirements[cat] = grouped[cat]
  })

  return output
}

function formatCurrency(value) {
  return value.toString()
}

const STATUS_GLYPH = { pass: '✓', warn: '!', fail: '✕' }
const STATUS_WORD = { pass: 'PASS', warn: 'WARN', fail: 'FAIL' }

function buildReport(requirements, checks, applied) {
  const now = new Date().toISOString().slice(0, 10)
  const pass = checks.filter((c) => c.status === 'pass').length
  const warn = checks.filter((c) => c.status === 'warn').length
  const fail = checks.filter((c) => c.status === 'fail').length
  const issues = checks.filter((c) => c.status !== 'pass')
  const resolved = issues.filter((c) => applied[c.id]).length
  const verdict = fail > 0 ? '❌ FAILED' : warn > 0 ? '⚠️ PASSED WITH WARNINGS' : '✅ PASSED'

  const lines = []
  lines.push('# Tracer — Design Validation Report')
  lines.push('')
  lines.push(`**Project:** rev-c-power-mux &nbsp;·&nbsp; **Revision:** C &nbsp;·&nbsp; **Generated:** ${now}`)
  lines.push('')
  lines.push(`**Verdict:** ${verdict}`)
  lines.push('')
  lines.push('## Summary')
  lines.push('')
  lines.push('| Metric | Count |')
  lines.push('| --- | --- |')
  lines.push(`| Requirements checked | ${checks.length} |`)
  lines.push(`| Passed | ${pass} |`)
  lines.push(`| Warnings | ${warn} |`)
  lines.push(`| Failed | ${fail} |`)
  lines.push(`| Issues resolved | ${resolved} / ${issues.length} |`)
  lines.push('')
  lines.push('## Validation Results')
  lines.push('')
  lines.push('| ID | Requirement | Expected | Actual | Result |')
  lines.push('| --- | --- | --- | --- | --- |')
  checks.forEach((c) => {
    lines.push(`| ${c.id} | ${c.title} | ${c.expected} | ${c.actual} | ${STATUS_WORD[c.status]} |`)
  })
  lines.push('')
  if (issues.length) {
    lines.push('## Remediation')
    lines.push('')
    issues.forEach((c) => {
      const mark = applied[c.id] ? '[x]' : '[ ]'
      lines.push(`- ${mark} **${c.id} — ${c.title}** (${STATUS_WORD[c.status]})`)
      lines.push(`  - Issue: expected ${c.expected}, got ${c.actual}.`)
      if (c.fix) lines.push(`  - Fix: ${c.fix}`)
    })
    lines.push('')
  }
  lines.push('## Requirements Baseline')
  lines.push('')
  lines.push('| ID | Title | Value | Origin | Confidence |')
  lines.push('| --- | --- | --- | --- | --- |')
  requirements.forEach((r) => {
    lines.push(`| ${r.id} | ${r.title} | ${r.value} | ${r.kind} | ${Math.round(r.conf * 100)}% |`)
  })
  lines.push('')
  lines.push('---')
  lines.push('_Generated by Tracer · requirements workbench_')
  return lines.join('\n')
}

export default function App() {
  const [requirements, setRequirements] = useState(INITIAL_REQUIREMENTS)
  const [filter, setFilter] = useState('all')
  const [category, setCategory] = useState('all')
  const [screen, setScreen] = useState('prompt')
  const [brief, setBrief] = useState(DEFAULT_BRIEF)
  const [copied, setCopied] = useState(false)
  const [designSource, setDesignSource] = useState('ai')
  const [designText, setDesignText] = useState(CANDIDATE_DESIGN)
  const [validated, setValidated] = useState(false)
  const [appliedFixes, setAppliedFixes] = useState({})
  const [reportDownloaded, setReportDownloaded] = useState(false)
  const timeoutRef = useRef(null)
  const analyzeRef = useRef(null)
  const validateRef = useRef(null)

  useEffect(() => {
    return () => {
      clearTimeout(timeoutRef.current)
      clearTimeout(analyzeRef.current)
      clearTimeout(validateRef.current)
    }
  }, [])

  const stage = SCREEN_STAGE[screen] || 1
  const formalized = stage >= 4
  const statusText =
    screen === 'prompt'
      ? 'draft'
      : screen === 'analyzing'
      ? 'analyzing'
      : screen === 'requirements'
      ? 'structured'
      : screen === 'validation'
      ? validated
        ? 'validated'
        : 'validating'
      : screen === 'remediation'
      ? 'remediating'
      : 'complete'

  const handleAnalyze = () => {
    setScreen('analyzing')
    clearTimeout(analyzeRef.current)
    analyzeRef.current = setTimeout(() => setScreen('requirements'), 1700)
  }

  const handleStageClick = (targetScreen) => {
    if (!targetScreen || screen === 'analyzing') return
    setScreen(targetScreen)
  }

  const handleStarter = (key) => {
    if (STARTERS[key]) setBrief(STARTERS[key])
  }

  const handleNewBoard = () => {
    clearTimeout(analyzeRef.current)
    clearTimeout(validateRef.current)
    setBrief('')
    setFilter('all')
    setCategory('all')
    setValidated(false)
    setAppliedFixes({})
    setReportDownloaded(false)
    setScreen('prompt')
  }

  const handleSelectSource = (key) => {
    setDesignSource(key)
    setDesignText(key === 'ai' ? CANDIDATE_DESIGN : '')
    setValidated(false)
  }

  const handleRunValidation = () => {
    setValidated(false)
    clearTimeout(validateRef.current)
    validateRef.current = setTimeout(() => setValidated(true), 900)
  }

  const handleApplyFix = (id) => {
    setAppliedFixes((current) => ({ ...current, [id]: !current[id] }))
  }

  const handleDownloadReport = () => {
    try {
      const blob = new Blob([reportMarkdown], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'rev-c-power-mux.validation.md'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      setReportDownloaded(true)
      clearTimeout(timeoutRef.current)
      timeoutRef.current = setTimeout(() => setReportDownloaded(false), 1800)
    } catch {
      // ignore download failure
    }
  }

  const total = requirements.length
  const statedCount = requirements.filter((r) => r.kind === 'stated').length
  const inferredCount = total - statedCount
  const averageConfidence = requirements.reduce((acc, req) => acc + req.conf, 0) / total
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

  const categoryChips = [
    { key: 'all', text: `All ${total}` },
    ...CATEGORY_ORDER.map((key) => ({
      key,
      text: `${CATEGORY_LABELS[key]} ${requirements.filter((r) => r.cat === key).length}`,
    })),
  ]

  const filteredRequirements = requirements.filter((req) => {
    if (filter !== 'all' && req.kind !== filter) return false
    if (category !== 'all' && req.cat !== category) return false
    return true
  })

  const groups = useMemo(() => {
    const grouped = []
    const categories = category === 'all' ? CATEGORY_ORDER : [category]
    categories.forEach((cat) => {
      const items = filteredRequirements.filter((req) => req.cat === cat)
      if (items.length === 0) return
      grouped.push({
        label: CATEGORY_LABELS[cat],
        count: items.length,
        items,
      })
    })
    return grouped
  }, [category, filteredRequirements])

  const spec = useMemo(() => buildFormalSpec(requirements), [requirements])
  const jsonText = useMemo(() => JSON.stringify(spec, null, 2), [spec])

  const checks = VALIDATION_CHECKS
  const passCount = checks.filter((c) => c.status === 'pass').length
  const warnCount = checks.filter((c) => c.status === 'warn').length
  const failCount = checks.filter((c) => c.status === 'fail').length
  const issues = checks.filter((c) => c.status !== 'pass')
  const resolvedCount = issues.filter((c) => appliedFixes[c.id]).length
  const verdict =
    failCount > 0 ? 'failed' : warnCount > 0 ? 'passed-warn' : 'passed'

  const reportMarkdown = useMemo(
    () => buildReport(requirements, checks, appliedFixes),
    [requirements, checks, appliedFixes]
  )

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

  const footerNote = formalized
    ? 'Specification formalized · ready for export'
    : 'Regenerated live from current requirements'

  return (
    <div className="app">
      <div className="bg-layer" aria-hidden="true">
        <div className="bg-blob bg-blob--1" />
        <div className="bg-blob bg-blob--2" />
        <div className="bg-blob bg-blob--3" />
        <div className="bg-blob bg-blob--4" />
        <div className="bg-blob bg-blob--5" />
        <div className="bg-streak" />
      </div>

      <header className="topbar">
        <div className="brand-row">
          <div className="brand-mark">T</div>
          <div className="brand-wordmark">TRACER</div>
          <div className="brand-chip">v0.4</div>
        </div>

        <div className="project-row">
          <span className="project-label">PROJECT</span>
          <span className="project-name">rev-c-power-mux</span>
          <span className="project-chip">REV C</span>
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
            <button className="btn btn-primary" onClick={() => setScreen('validation')}>
              Validate design →
            </button>
          </>
        )}

        {screen === 'validation' && (
          <>
            <button className="btn btn-ghost" onClick={() => setScreen('requirements')}>
              ← Requirements
            </button>
            {validated && (
              <button
                className="btn btn-primary"
                onClick={() => setScreen(issues.length ? 'remediation' : 'report')}
              >
                {issues.length ? 'Remediate →' : 'Export report →'}
              </button>
            )}
          </>
        )}

        {screen === 'remediation' && (
          <>
            <button className="btn btn-ghost" onClick={() => setScreen('validation')}>
              ← Validation
            </button>
            <button className="btn btn-primary" onClick={() => setScreen('report')}>
              Export report →
            </button>
          </>
        )}

        {screen === 'report' && (
          <>
            <button className="btn btn-ghost" onClick={() => setScreen('remediation')}>
              ← Remediation
            </button>
            <button className="btn btn-primary" onClick={handleDownloadReport}>
              {reportDownloaded ? 'Downloaded ✓' : 'Download .md'}
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

            <div className="prompt-card">
              <textarea
                className="prompt-textarea"
                value={brief}
                onChange={(event) => setBrief(event.target.value)}
                spellCheck={false}
                placeholder="e.g. Small USB-C powered mux board. 9–36 V input, needs 5 V at 3 A out. Talks I²C to a host controller. Must fit a 50 × 35 mm enclosure and run up to 70 °C ambient."
              />
              <div className="prompt-card-footer">
                <button type="button" className="prompt-attach">
                  + Attach datasheet / netlist
                </button>
                <div className="spacer" />
                <span className="prompt-count">{brief.length} chars</span>
                <button type="button" className="btn btn-primary" onClick={handleAnalyze}>
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
                    onClick={() => handleStarter(option.key)}
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
            {ANALYZING_STEPS.map((label, index) => (
              <div key={label} className="analyzing-step">
                <div className="analyzing-step-dot" style={{ animationDelay: `${index * 0.2}s` }} />
                <span className="analyzing-step-label">{label}</span>
              </div>
            ))}
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
          <button type="button" className="new-board-btn" onClick={handleNewBoard}>
            + Describe a new board
          </button>

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
            {ASSUMPTIONS.map((item) => (
              <div key={item.tag} className="assumption-row">
                <div className="assumption-dot" />
                <div>
                  <span className="assumption-text">{item.text}</span>{' '}
                  <span className="assumption-tag">→ {item.tag}</span>
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
                              style={{ background: badgeBg, color: badgeColor, borderColor: badgeBorder }}
                            >
                              {isStated ? 'STATED' : 'INFERRED'}
                            </button>
                            <div className="req-spacer" />
                            <div className="req-confidence">
                              <span className="req-conf-label">CONF</span>
                              <div className="req-conf-track">
                                <div className="req-conf-fill" style={getBarStyle(req.conf)} />
                              </div>
                              <span className="req-conf-text">{Math.round(req.conf * 100)}%</span>
                            </div>
                          </div>
                          <div className="req-title">{req.title}</div>
                          <input
                            className="req-input"
                            value={req.value}
                            onChange={(event) => handleValueChange(req.id, event.target.value)}
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
              <span className="spec-filename">rev-c-power-mux.req.json</span>
              <div className="req-spacer" />
              <button type="button" className="spec-copy" onClick={copyJson}>
                {copied ? 'Copied ✓' : 'copy'}
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

      {screen === 'validation' && (
        <div className="flow-screen">
          <div className="flow-inner">
            <div className="prompt-eyebrow">STAGE 04 · DESIGN VALIDATION</div>
            <h1 className="prompt-title">Validate a design</h1>
            <p className="prompt-lede">
              Check a candidate design against the {checks.length} structured requirements. Pick a
              source, then run validation to see what passes, what needs attention, and what fails.
            </p>

            <div className="source-grid">
              {DESIGN_SOURCES.map((source) => (
                <button
                  key={source.key}
                  type="button"
                  className={`source-card ${designSource === source.key ? 'source-card--active' : ''}`}
                  onClick={() => handleSelectSource(source.key)}
                >
                  <span className="source-card-label">{source.label}</span>
                  <span className="source-card-hint">{source.hint}</span>
                </button>
              ))}
            </div>

            <div className="prompt-card">
              <textarea
                className="prompt-textarea"
                value={designText}
                onChange={(event) => {
                  setDesignText(event.target.value)
                  setValidated(false)
                }}
                spellCheck={false}
                placeholder={
                  designSource === 'bom'
                    ? 'ref,part,value,qty\nU1,TPS54331,buck,1\n…'
                    : designSource === 'netlist'
                    ? '(export (version "E")\n  (components …))'
                    : 'Paste the candidate design here…'
                }
              />
              <div className="prompt-card-footer">
                <span className="prompt-count">
                  Source: {DESIGN_SOURCES.find((s) => s.key === designSource)?.label}
                </span>
                <div className="spacer" />
                <span className="prompt-count">{designText.length} chars</span>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleRunValidation}
                  disabled={!designText.trim()}
                >
                  Run validation →
                </button>
              </div>
            </div>

            {validated && (
              <div className="validation-results">
                <div className={`verdict-banner verdict-banner--${verdict}`}>
                  <span className="verdict-mark">
                    {verdict === 'passed' ? '✓' : verdict === 'failed' ? '✕' : '!'}
                  </span>
                  <div>
                    <div className="verdict-title">
                      {verdict === 'passed'
                        ? 'All requirements satisfied'
                        : verdict === 'failed'
                        ? `${failCount} requirement${failCount === 1 ? '' : 's'} failed`
                        : `Passed with ${warnCount} warning${warnCount === 1 ? '' : 's'}`}
                    </div>
                    <div className="verdict-sub">
                      {passCount} passed · {warnCount} warnings · {failCount} failed
                    </div>
                  </div>
                </div>

                <div className="check-list">
                  {checks.map((check) => (
                    <div key={check.id} className={`check-row check-row--${check.status}`}>
                      <span className={`check-icon check-icon--${check.status}`}>
                        {STATUS_GLYPH[check.status]}
                      </span>
                      <div className="check-body">
                        <div className="check-top">
                          <span className="check-id">{check.id}</span>
                          <span className="check-title">{check.title}</span>
                        </div>
                        <div className="check-compare">
                          <span className="check-expected">expected {check.expected}</span>
                          <span className="check-arrow">→</span>
                          <span className="check-actual">got {check.actual}</span>
                        </div>
                      </div>
                      <span className={`check-tag check-tag--${check.status}`}>
                        {STATUS_WORD[check.status]}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {screen === 'remediation' && (
        <div className="flow-screen">
          <div className="flow-inner">
            <div className="prompt-eyebrow">STAGE 05 · REMEDIATION</div>
            <h1 className="prompt-title">Suggested fixes</h1>
            <p className="prompt-lede">
              {issues.length
                ? `Tracer found ${issues.length} issue${issues.length === 1 ? '' : 's'}. Apply the suggested fixes below, then move on to the report.`
                : 'No failures or warnings — nothing to remediate. Head straight to the report.'}
            </p>

            {issues.length > 0 && (
              <div className="remediation-meta">
                <span className="remediation-progress">
                  {resolvedCount} of {issues.length} resolved
                </span>
                <div className="remediation-track">
                  <div
                    className="remediation-fill"
                    style={{ width: `${issues.length ? (resolvedCount / issues.length) * 100 : 0}%` }}
                  />
                </div>
              </div>
            )}

            <div className="fix-list">
              {issues.map((item) => {
                const isApplied = Boolean(appliedFixes[item.id])
                return (
                  <div key={item.id} className={`fix-card ${isApplied ? 'fix-card--applied' : ''}`}>
                    <div className="fix-head">
                      <span className={`check-tag check-tag--${item.status}`}>
                        {STATUS_WORD[item.status]}
                      </span>
                      <span className="check-id">{item.id}</span>
                      <span className="fix-title">{item.title}</span>
                      <div className="spacer" />
                      <button
                        type="button"
                        className={`fix-btn ${isApplied ? 'fix-btn--applied' : ''}`}
                        onClick={() => handleApplyFix(item.id)}
                      >
                        {isApplied ? 'Applied ✓' : 'Apply fix'}
                      </button>
                    </div>
                    <div className="fix-issue">
                      Expected {item.expected} · got {item.actual}
                    </div>
                    <div className="fix-suggestion">{item.fix}</div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {screen === 'report' && (
        <div className="flow-screen">
          <div className="flow-inner">
            <div className="prompt-eyebrow">STAGE 06 · EXPORT REPORT</div>
            <h1 className="prompt-title">Validation report</h1>
            <p className="prompt-lede">
              The full result — requirements, validation outcomes, and remediation — as a Markdown
              report you can download and share.
            </p>

            <div className="report-stats">
              <div className="report-stat">
                <span className="report-stat-value">{checks.length}</span>
                <span className="report-stat-label">checked</span>
              </div>
              <div className="report-stat">
                <span className="report-stat-value report-stat-value--green">{passCount}</span>
                <span className="report-stat-label">passed</span>
              </div>
              <div className="report-stat">
                <span className="report-stat-value report-stat-value--amber">{warnCount}</span>
                <span className="report-stat-label">warnings</span>
              </div>
              <div className="report-stat">
                <span className="report-stat-value report-stat-value--red">{failCount}</span>
                <span className="report-stat-label">failed</span>
              </div>
              <div className="report-stat">
                <span className="report-stat-value">
                  {resolvedCount}/{issues.length}
                </span>
                <span className="report-stat-label">resolved</span>
              </div>
            </div>

            <div className="report-panel">
              <div className="report-panel-header">
                <div className="spec-dot" />
                <span className="spec-filename">rev-c-power-mux.validation.md</span>
                <div className="spacer" />
                <button type="button" className="btn btn-primary report-dl" onClick={handleDownloadReport}>
                  {reportDownloaded ? 'Downloaded ✓' : 'Download .md'}
                </button>
              </div>
              <pre className="report-pre">{reportMarkdown}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
