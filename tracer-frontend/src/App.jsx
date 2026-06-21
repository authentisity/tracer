import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import * as api from './api'

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
  { num: '01', label: 'Describe board',   screen: 'prompt' },
  { num: '02', label: 'Intent analysis',  screen: null },
  { num: '03', label: 'Requirements',     screen: 'requirements' },
  { num: '04', label: 'Components',       screen: 'components' },
  { num: '05', label: 'Netlist',          screen: 'netlist' },
  { num: '06', label: 'Placement',        screen: 'placement' },
  { num: '07', label: 'Validation',       screen: 'validation' },
  { num: '08', label: 'Remediation',      screen: 'remediation' },
  { num: '09', label: 'Report',           screen: 'report' },
]

const SCREEN_STAGE = {
  prompt:       1,
  analyzing:    2,
  requirements: 3,
  components:   4,
  netlist:      5,
  placement:    6,
  validation:   7,
  remediation:  8,
  report:       9,
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
  "design": "candidate",
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

const DEFAULT_BRIEF =
  'Small USB-C powered mux board. 9–36 V input, needs 5 V at 3 A out. Talks I²C to a host controller. Must fit a 50 × 35 mm enclosure and run up to 70 °C ambient.'

const STARTERS = {
  mux: DEFAULT_BRIEF,
  ble: 'Compact BLE sensor node. Coin-cell powered (CR2032), reads a BME280 over I²C, advertises every 2 s. Chip antenna on board, fits a 25 mm round PCB, indoor use.',
  motor: 'Brushed DC motor driver. 12 V supply, up to 5 A continuous. STM32 control over CAN, current sense and thermal shutdown. 60 × 40 mm board, automotive cabin.',
}

const STARTER_OPTIONS = [
  { key: 'mux',   label: 'USB-C power mux' },
  { key: 'ble',   label: 'BLE sensor node' },
  { key: 'motor', label: 'DC motor driver' },
]

const EXTRACT_TAGS = [
  'Power', 'Interfaces', 'Components', 'Signal Integrity', 'Thermal', 'Mechanical', 'Placement',
]

const ANALYZING_STEPS = [
  { label: 'Parsing description',       step: 1 },
  { label: 'Expanding intent',          step: 2 },
  { label: 'Classifying requirements',  step: 3 },
  { label: 'Formalizing spec',          step: 4 },
]

const COMP_CATEGORY_COLOR = {
  mcu:       '#4a7fcb',
  ldo:       '#c27830',
  capacitor: '#4fa852',
  resistor:  '#9050b0',
  sensor:    '#c04040',
  connector: '#3898c0',
  led:       '#b8a020',
  crystal:   '#30a898',
  diode:     '#c07040',
  header:    '#6888a0',
  inductor:  '#a04888',
}

const STATUS_GLYPH = { pass: '✓', warn: '!', fail: '✕' }
const STATUS_WORD  = { pass: 'PASS', warn: 'WARN', fail: 'FAIL' }

// ── Pure helpers ───────────────────────────────────────────────────────────────

function getConfidenceColor(conf) {
  if (conf >= 0.85) return '#3f7d57'
  if (conf >= 0.7)  return '#c2620e'
  return '#cf9134'
}

function getBarStyle(conf) {
  return { width: `${Math.round(conf * 100)}%`, background: getConfidenceColor(conf) }
}

function briefName(brief) {
  const words = brief.trim().split(/\s+/).slice(0, 6).join(' ')
  return words.slice(0, 60) || 'Untitled board'
}

function buildFormalSpec(projectName, requirements) {
  const now = new Date().toISOString().slice(0, 10)
  const grouped = {}
  requirements.forEach((req) => {
    if (!grouped[req.cat]) grouped[req.cat] = []
    grouped[req.cat].push({
      id: req.id, title: req.title, value: req.value,
      origin: req.kind, confidence: Number(req.conf.toFixed(2)),
    })
  })
  const output = {
    project:  projectName || 'untitled',
    generated: now,
    summary: {
      total:      requirements.length,
      stated:     requirements.filter((r) => r.kind === 'stated').length,
      inferred:   requirements.filter((r) => r.kind === 'inferred').length,
      confidence: requirements.length
        ? Number((requirements.reduce((s, r) => s + r.conf, 0) / requirements.length).toFixed(2))
        : 0,
    },
    requirements: {},
  }
  Object.keys(grouped).forEach((cat) => { output.requirements[cat] = grouped[cat] })
  return output
}

function buildReport(projectName, requirements, checks, applied) {
  const now   = new Date().toISOString().slice(0, 10)
  const pass  = checks.filter((c) => c.status === 'pass').length
  const warn  = checks.filter((c) => c.status === 'warn').length
  const fail  = checks.filter((c) => c.status === 'fail').length
  const issues   = checks.filter((c) => c.status !== 'pass')
  const resolved = issues.filter((c) => applied[c.id]).length
  const verdict  = fail > 0 ? '❌ FAILED' : warn > 0 ? '⚠️ PASSED WITH WARNINGS' : '✅ PASSED'

  const lines = []
  lines.push('# Tracer — Design Validation Report')
  lines.push('')
  lines.push(`**Project:** ${projectName || 'untitled'} &nbsp;·&nbsp; **Generated:** ${now}`)
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

// ── Backend → view-model mappers ───────────────────────────────────────────────

const CATEGORY_MAP = {
  power: 'power', interfaces: 'interfaces', components: 'components',
  signal_integrity: 'signal', signal: 'signal',
  thermal: 'thermal', mechanical: 'mechanical', placement: 'placement',
  other: 'components',
}

const OPERATOR_GLYPH = { '<=': '≤', '>=': '≥', '<': '<', '>': '>', '==': '=', '=': '' }

function constraintText(r) {
  if (r.value === null || r.value === undefined || r.value === '') return ''
  const op = OPERATOR_GLYPH[r.operator] ?? (r.operator || '')
  return [op, r.value, r.unit].filter((x) => x !== '' && x !== null && x !== undefined).join(' ').trim()
}

function mapFormalToRequirements(formal) {
  const reqs = (formal && formal.requirements) || []
  return reqs.map((r) => {
    const constraint = constraintText(r)
    return {
      id:    r.id,
      cat:   CATEGORY_MAP[r.category] || 'components',
      title: r.statement || r.parameter || r.id,
      value: constraint || r.parameter || '—',
      kind:  r.provenance === 'user_stated' ? 'stated' : 'inferred',
      conf:  typeof r.confidence === 'number' ? r.confidence : 0.7,
    }
  })
}

const VERDICT_TO_STATUS = { pass: 'pass', fail: 'fail', needs_review: 'warn' }

function mapValidationToChecks(validation) {
  const results = (validation && validation.results) || []
  return results.map((r) => {
    let actual = r.design_value
    if (actual === null || actual === undefined || actual === '') {
      actual = r.flagged_refs?.length ? 'unverified reference' : 'not specified'
    }
    return {
      id:       r.req_id,
      title:    r.statement || r.req_id,
      expected: String(constraintText(r) || r.statement || '—'),
      actual:   String(actual),
      status:   VERDICT_TO_STATUS[r.verdict] || 'warn',
    }
  })
}

const ERROR_BANNER_STYLE = {
  marginTop: 14, padding: '11px 15px', borderRadius: 10,
  background: '#fbe9e7', border: '1px solid #f1c4bd',
  color: '#9a2b1f', fontSize: 14, lineHeight: 1.4,
}

// ── PlacementBoard SVG ────────────────────────────────────────────────────────

function PlacementBoard({ board, components }) {
  const SCALE = 7
  const PAD   = 20
  const W = board.width_mm  * SCALE
  const H = board.height_mm * SCALE

  return (
    <div className="placement-svg-wrap">
      <svg
        viewBox={`${-PAD} ${-PAD} ${W + PAD * 2} ${H + PAD * 2}`}
        className="placement-svg"
      >
        <defs>
          <pattern id="pcb-dot" x="0" y="0" width={SCALE * 2.5} height={SCALE * 2.5} patternUnits="userSpaceOnUse">
            <circle cx="0" cy="0" r="0.8" fill="#2f5438" opacity="0.5" />
          </pattern>
        </defs>

        {/* PCB body */}
        <rect x="0" y="0" width={W} height={H} rx="5" fill="#1a3020" />
        <rect x="0" y="0" width={W} height={H} rx="5" fill="url(#pcb-dot)" />
        <rect x="0" y="0" width={W} height={H} rx="5" fill="none" stroke="#3a6a40" strokeWidth="2" />

        {/* Corner mounting holes */}
        {[[10,10],[W-10,10],[10,H-10],[W-10,H-10]].map(([cx, cy], i) => (
          <g key={i}>
            <circle cx={cx} cy={cy} r="5" fill="#1a3020" stroke="#4a8050" strokeWidth="1.5" />
            <circle cx={cx} cy={cy} r="2" fill="#3a6040" />
          </g>
        ))}

        {/* Components */}
        {components.map((comp) => {
          const x  = comp.x_mm * SCALE
          const y  = comp.y_mm * SCALE
          const sz = comp.category === 'mcu' ? 28 : comp.category === 'connector' ? 22 : 14
          const color = COMP_CATEGORY_COLOR[comp.category] || '#778899'
          const label = (comp.functional_role || '').slice(0, 7)
          return (
            <g key={comp.functional_role} transform={`rotate(${comp.rotation_deg},${x},${y})`}>
              <rect x={x - sz/2} y={y - sz/2} width={sz} height={sz} rx="2" fill={color} opacity="0.9" />
              <text x={x} y={y} textAnchor="middle" dominantBaseline="middle"
                fontSize="5" fill="#fff" fontFamily="monospace" fontWeight="600">
                {label}
              </text>
            </g>
          )
        })}

        {/* Dimensions label */}
        <text x={W / 2} y={H + PAD - 5} textAnchor="middle"
          fontSize="9" fill="#4a8050" fontFamily="monospace">
          {board.width_mm} mm × {board.height_mm} mm
        </text>
      </svg>
    </div>
  )
}

// ── App ────────────────────────────────────────────────────────────────────────

export default function App() {
  // ── state ──
  const [screen,          setScreen]          = useState('prompt')
  const [brief,           setBrief]           = useState(DEFAULT_BRIEF)
  const [projectId,       setProjectId]       = useState(null)
  const [projectName,     setProjectName]     = useState('')
  const [completedSteps,  setCompletedSteps]  = useState(0)

  // requirements screen
  const [requirements,    setRequirements]    = useState([])
  const [filter,          setFilter]          = useState('all')
  const [category,        setCategory]        = useState('all')
  const [copied,          setCopied]          = useState(false)

  // component selection
  const [componentSelection,  setComponentSelection]  = useState(null)
  const [componentSelecting,  setComponentSelecting]  = useState(false)

  // netlist
  const [netlistData,        setNetlistData]        = useState(null)
  const [netlistGenerating,  setNetlistGenerating]  = useState(false)
  const [kicadDownloaded,    setKicadDownloaded]    = useState(false)

  // placement
  const [placementData,       setPlacementData]       = useState(null)
  const [placementGenerating, setPlacementGenerating] = useState(false)

  // validation
  const [designSource,    setDesignSource]    = useState('ai')
  const [designText,      setDesignText]      = useState(CANDIDATE_DESIGN)
  const [validated,       setValidated]       = useState(false)
  const [checks,          setChecks]          = useState([])
  const [validating,      setValidating]      = useState(false)

  // remediation / report
  const [appliedFixes,    setAppliedFixes]    = useState({})
  const [reportDownloaded,setReportDownloaded]= useState(false)

  // shared
  const [error,           setError]           = useState(null)

  const timeoutRef  = useRef(null)
  const analyzeRef  = useRef(null)
  const validateRef = useRef(null)

  useEffect(() => () => {
    clearTimeout(timeoutRef.current)
    clearTimeout(analyzeRef.current)
    clearTimeout(validateRef.current)
  }, [])

  // ── derived ──
  const stage      = SCREEN_STAGE[screen] || 1
  const formalized = stage >= 7

  const statusText =
    screen === 'prompt'       ? 'draft'
    : screen === 'analyzing'  ? 'analyzing'
    : screen === 'requirements' ? 'structured'
    : screen === 'components' ? 'components'
    : screen === 'netlist'    ? 'netlist'
    : screen === 'placement'  ? 'placed'
    : screen === 'validation' ? (validated ? 'validated' : 'validating')
    : screen === 'remediation'? 'remediating'
    : 'complete'

  // ── requirements derived ──
  const total           = requirements.length
  const statedCount     = requirements.filter((r) => r.kind === 'stated').length
  const inferredCount   = total - statedCount
  const averageConf     = total ? requirements.reduce((a, r) => a + r.conf, 0) / total : 0
  const overallPct      = `${Math.round(averageConf * 100)}%`
  const overallBar      = { width: `${Math.round(averageConf * 100)}%`, background: getConfidenceColor(averageConf) }
  const summarySub      = `${total} extracted · ${statedCount} stated · ${inferredCount} inferred`
  const assumptions     = requirements.filter((r) => r.kind === 'inferred').slice(0, 6).map((r) => ({ text: r.title, tag: r.id }))
  const activeFilters   = [
    { key: 'all',      text: `All ${total}` },
    { key: 'stated',   text: `Stated ${statedCount}` },
    { key: 'inferred', text: `Inferred ${inferredCount}` },
  ]
  const categoryChips   = [
    { key: 'all', text: `All ${total}` },
    ...CATEGORY_ORDER.map((key) => ({
      key, text: `${CATEGORY_LABELS[key]} ${requirements.filter((r) => r.cat === key).length}`,
    })),
  ]
  const filteredReqs    = requirements.filter((req) => {
    if (filter !== 'all' && req.kind !== filter) return false
    if (category !== 'all' && req.cat !== category) return false
    return true
  })
  const groups = useMemo(() => {
    const cats = category === 'all' ? CATEGORY_ORDER : [category]
    return cats
      .map((cat) => ({ label: CATEGORY_LABELS[cat], count: 0, items: filteredReqs.filter((r) => r.cat === cat) }))
      .filter((g) => g.items.length)
      .map((g) => ({ ...g, count: g.items.length }))
  }, [category, filteredReqs])

  const spec     = useMemo(() => buildFormalSpec(projectName, requirements), [projectName, requirements])
  const jsonText = useMemo(() => JSON.stringify(spec, null, 2), [spec])

  // ── validation derived ──
  const passCount    = checks.filter((c) => c.status === 'pass').length
  const warnCount    = checks.filter((c) => c.status === 'warn').length
  const failCount    = checks.filter((c) => c.status === 'fail').length
  const issues       = checks.filter((c) => c.status !== 'pass')
  const resolvedCount= issues.filter((c) => appliedFixes[c.id]).length
  const verdict      = failCount > 0 ? 'failed' : warnCount > 0 ? 'passed-warn' : 'passed'

  const reportMarkdown = useMemo(
    () => buildReport(projectName, requirements, checks, appliedFixes),
    [projectName, requirements, checks, appliedFixes],
  )

  // ── handlers ──

  const handleAnalyze = async () => {
    if (!brief.trim()) return
    setError(null)
    setValidated(false)
    setChecks([])
    setComponentSelection(null)
    setNetlistData(null)
    setPlacementData(null)
    setCompletedSteps(0)
    setFilter('all')
    setCategory('all')
    setScreen('analyzing')
    try {
      const name = briefName(brief)
      setProjectName(name)
      const { project_id } = await api.createProject(name, brief)
      setProjectId(project_id)
      setCompletedSteps(1)
      await api.runStage(project_id, 'intent_expansion')
      setCompletedSteps(2)
      await api.runStage(project_id, 'structured_bullets')
      setCompletedSteps(3)
      const formal = await api.runStage(project_id, 'formal_requirements')
      setCompletedSteps(4)
      const mapped = mapFormalToRequirements(formal)
      if (!mapped.length) throw new Error('No requirements extracted — try a more detailed brief.')
      setRequirements(mapped)
      setScreen('requirements')
    } catch (err) {
      setError(String((err && err.message) || err))
      setScreen('prompt')
    }
  }

  const handleRunComponentSelection = async () => {
    if (!projectId) return
    setError(null)
    setComponentSelection(null)
    setNetlistData(null)
    setPlacementData(null)
    setComponentSelecting(true)
    setScreen('components')
    try {
      const result = await api.runStage(projectId, 'component_selection')
      setComponentSelection(result)
    } catch (err) {
      setError(String((err && err.message) || err))
    } finally {
      setComponentSelecting(false)
    }
  }

  const handleRunNetlist = async () => {
    if (!projectId) return
    setError(null)
    setNetlistData(null)
    setPlacementData(null)
    setNetlistGenerating(true)
    setScreen('netlist')
    try {
      const result = await api.runStage(projectId, 'netlist')
      setNetlistData(result)
    } catch (err) {
      if (err.detail?.erc_violations) {
        // 422 ERC failure — still show the netlist screen with violations
        setNetlistData({
          nets:           err.detail.partial_netlist?.nets || [],
          unconnected:    err.detail.partial_netlist?.unconnected || [],
          erc_passed:     false,
          erc_violations: err.detail.erc_violations,
          kicad_net_file: err.detail.partial_netlist?.kicad_net_file || null,
        })
      } else {
        setError(String((err && err.message) || err))
      }
    } finally {
      setNetlistGenerating(false)
    }
  }

  const handleRunPlacement = async () => {
    if (!projectId) return
    setError(null)
    setPlacementData(null)
    setPlacementGenerating(true)
    setScreen('placement')
    try {
      const result = await api.runStage(projectId, 'placement')
      setPlacementData(result)
    } catch (err) {
      setError(String((err && err.message) || err))
    } finally {
      setPlacementGenerating(false)
    }
  }

  const handleRunValidation = async () => {
    if (!projectId) {
      setError('Analyze a board first so there is a spec to validate against.')
      return
    }
    setError(null)
    setValidated(false)
    setValidating(true)
    try {
      let body
      if (designSource === 'json' && designText.trim()) {
        try {
          body = { artifact: JSON.parse(designText) }
        } catch {
          throw new Error('Design JSON is not valid — fix it or switch to the AI candidate.')
        }
      }
      const val = await api.runStage(projectId, 'validation', body)
      setChecks(mapValidationToChecks(val))
      setValidated(true)
    } catch (err) {
      setError(String((err && err.message) || err))
    } finally {
      setValidating(false)
    }
  }

  const handleRemediate = async () => {
    const open = checks.filter((c) => c.status !== 'pass')
    if (!open.length) { setScreen('report'); return }
    try {
      const rem = await api.runStage(projectId, 'remediation')
      const fixById = {}
      ;(rem.fixes || []).forEach((f) => { fixById[f.req_id] = f.suggestion })
      setChecks((cur) => cur.map((c) => (fixById[c.id] ? { ...c, fix: fixById[c.id] } : c)))
    } catch (err) {
      setError(String((err && err.message) || err))
    }
    setScreen('remediation')
  }

  const handleApplyFix = (id) => {
    setAppliedFixes((cur) => ({ ...cur, [id]: !cur[id] }))
  }

  const handleDownloadKicad = () => {
    if (!netlistData?.kicad_net_file) return
    try {
      const blob = new Blob([netlistData.kicad_net_file], { type: 'text/plain' })
      const url  = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${projectName || 'board'}.net`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      setKicadDownloaded(true)
      clearTimeout(timeoutRef.current)
      timeoutRef.current = setTimeout(() => setKicadDownloaded(false), 1800)
    } catch { /* ignore */ }
  }

  const handleDownloadReport = () => {
    try {
      const blob = new Blob([reportMarkdown], { type: 'text/markdown' })
      const url  = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${projectName || 'board'}.validation.md`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      setReportDownloaded(true)
      clearTimeout(timeoutRef.current)
      timeoutRef.current = setTimeout(() => setReportDownloaded(false), 1800)
    } catch { /* ignore */ }
  }

  const handleStageClick = (targetScreen) => {
    if (!targetScreen || screen === 'analyzing') return
    setScreen(targetScreen)
  }

  const handleStarter = (key) => { if (STARTERS[key]) setBrief(STARTERS[key]) }

  const handleNewBoard = () => {
    clearTimeout(analyzeRef.current)
    clearTimeout(validateRef.current)
    setBrief('')
    setFilter('all')
    setCategory('all')
    setValidated(false)
    setAppliedFixes({})
    setReportDownloaded(false)
    setRequirements([])
    setChecks([])
    setProjectId(null)
    setProjectName('')
    setError(null)
    setComponentSelection(null)
    setNetlistData(null)
    setPlacementData(null)
    setCompletedSteps(0)
    setScreen('prompt')
  }

  const handleSelectSource = (key) => {
    setDesignSource(key)
    setDesignText(key === 'ai' ? CANDIDATE_DESIGN : '')
    setValidated(false)
  }

  const copyJson = async () => {
    try {
      await navigator.clipboard.writeText(jsonText)
      setCopied(true)
      clearTimeout(timeoutRef.current)
      timeoutRef.current = setTimeout(() => setCopied(false), 1600)
    } catch { /* ignore */ }
  }

  const handleToggleKind = (id) => {
    setRequirements((cur) => cur.map((req) => {
      if (req.id !== id) return req
      if (req.kind === 'stated') return { ...req, kind: 'inferred', conf: Math.max(0.5, req.conf - 0.2) }
      return { ...req, kind: 'stated', conf: Math.min(0.99, req.conf + 0.2) }
    }))
  }

  const handleValueChange = (id, value) => {
    setRequirements((cur) => cur.map((req) => (req.id === id ? { ...req, value } : req)))
  }

  const footerNote = formalized
    ? 'Specification formalized · ready for export'
    : 'Regenerated live from current requirements'

  // ── render ──
  return (
    <div className="app">
      {/* background */}
      <div className="bg-layer" aria-hidden="true">
        <div className="bg-blob bg-blob--1" />
        <div className="bg-blob bg-blob--2" />
        <div className="bg-blob bg-blob--3" />
        <div className="bg-blob bg-blob--4" />
        <div className="bg-blob bg-blob--5" />
        <div className="bg-streak" />
      </div>

      {/* topbar */}
      <header className="topbar">
        <div className="brand-row">
          <div className="brand-mark">T</div>
          <div className="brand-wordmark">TRACER</div>
          <div className="brand-chip">v0.5</div>
        </div>

        <div className="project-row">
          <span className="project-label">PROJECT</span>
          <span className="project-name">{projectName || '—'}</span>
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
            <button
              className="btn btn-primary"
              onClick={handleRunComponentSelection}
              disabled={componentSelecting}
            >
              {componentSelecting ? 'Selecting…' : 'Select components →'}
            </button>
          </>
        )}

        {screen === 'components' && (
          <>
            <button className="btn btn-ghost" onClick={() => setScreen('requirements')}>
              ← Requirements
            </button>
            {componentSelection && !componentSelecting && (
              <button className="btn btn-primary" onClick={handleRunNetlist} disabled={netlistGenerating}>
                {netlistGenerating ? 'Generating…' : 'Generate netlist →'}
              </button>
            )}
          </>
        )}

        {screen === 'netlist' && (
          <>
            <button className="btn btn-ghost" onClick={() => setScreen('components')}>
              ← Components
            </button>
            {netlistData?.kicad_net_file && (
              <button className="btn btn-ghost" onClick={handleDownloadKicad}>
                {kicadDownloaded ? 'Downloaded ✓' : 'Download .net'}
              </button>
            )}
            {netlistData && !netlistGenerating && (
              <button className="btn btn-primary" onClick={handleRunPlacement} disabled={placementGenerating}>
                {placementGenerating ? 'Solving…' : 'Solve placement →'}
              </button>
            )}
          </>
        )}

        {screen === 'placement' && (
          <>
            <button className="btn btn-ghost" onClick={() => setScreen('netlist')}>
              ← Netlist
            </button>
            {placementData && !placementGenerating && (
              <button className="btn btn-primary" onClick={() => setScreen('validation')}>
                Validate design →
              </button>
            )}
          </>
        )}

        {screen === 'validation' && (
          <>
            <button className="btn btn-ghost" onClick={() => placementData ? setScreen('placement') : setScreen('requirements')}>
              ← {placementData ? 'Placement' : 'Requirements'}
            </button>
            {validated && (
              <button className="btn btn-primary" onClick={handleRemediate}>
                {issues.length ? 'Remediate →' : 'Export report →'}
              </button>
            )}
          </>
        )}

        {screen === 'remediation' && (
          <>
            <button className="btn btn-ghost" onClick={() => setScreen('validation')}>← Validation</button>
            <button className="btn btn-primary" onClick={() => setScreen('report')}>Export report →</button>
          </>
        )}

        {screen === 'report' && (
          <>
            <button className="btn btn-ghost" onClick={() => setScreen('remediation')}>← Remediation</button>
            <button className="btn btn-primary" onClick={handleDownloadReport}>
              {reportDownloaded ? 'Downloaded ✓' : 'Download .md'}
            </button>
          </>
        )}
      </header>

      {/* stage strip */}
      <div className="stage-strip">
        {STAGE_DEFS.map((stageDef, index) => {
          const isActive   = index + 1 === stage
          const isDone     = index + 1 < stage
          const isNavigable = Boolean(stageDef.screen) && screen !== 'analyzing'
          return (
            <div key={stageDef.num} className="stage-item">
              <div
                className={`stage-item-inner ${isNavigable ? 'stage-item-inner--clickable' : ''}`}
                onClick={() => handleStageClick(stageDef.screen)}
              >
                <div className={`stage-dot ${isActive ? 'stage-dot--active' : ''} ${isDone ? 'stage-dot--done' : ''}`}>
                  {isDone ? '✓' : stageDef.num}
                </div>
                <div className="stage-labels">
                  <span className="stage-pretitle">STAGE {stageDef.num}</span>
                  <span className={`stage-title ${isActive ? 'stage-title--active' : ''}`}>{stageDef.label}</span>
                </div>
              </div>
              {index < STAGE_DEFS.length - 1 && <span className="stage-separator">→</span>}
            </div>
          )
        })}
      </div>

      {/* ── Prompt ── */}
      {screen === 'prompt' && (
        <div className="prompt-screen">
          <div className="prompt-inner">
            <div className="prompt-eyebrow">STAGE 01 · DESCRIBE BOARD</div>
            <h1 className="prompt-title">Describe your board</h1>
            <p className="prompt-lede">
              Write what the board needs to do in plain language — voltages, interfaces, size, environment.
              Tracer extracts stated requirements, infers the gaps, then walks you through component
              selection, netlist generation, placement, and design validation.
            </p>

            <div className="prompt-card">
              <textarea
                className="prompt-textarea"
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                spellCheck={false}
                placeholder="e.g. Small USB-C powered mux board. 9–36 V input, needs 5 V at 3 A out. Talks I²C to a host controller. Must fit a 50 × 35 mm enclosure and run up to 70 °C ambient."
              />
              <div className="prompt-card-footer">
                <button type="button" className="prompt-attach">+ Attach datasheet / netlist</button>
                <div className="spacer" />
                <span className="prompt-count">{brief.length} chars</span>
                <button type="button" className="btn btn-primary" onClick={handleAnalyze} disabled={!brief.trim()}>
                  Analyze requirements →
                </button>
              </div>
            </div>

            {error && <div style={ERROR_BANNER_STYLE}>{error}</div>}

            <div className="prompt-section">
              <div className="prompt-section-label">TRY A STARTER</div>
              <div className="starter-row">
                {STARTER_OPTIONS.map((o) => (
                  <button key={o.key} type="button" className="starter-chip" onClick={() => handleStarter(o.key)}>
                    {o.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="prompt-section prompt-section--extract">
              <div className="prompt-section-label">TRACER WILL EXTRACT</div>
              <div className="extract-row">
                {EXTRACT_TAGS.map((tag) => <span key={tag} className="extract-tag">{tag}</span>)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Analyzing ── */}
      {screen === 'analyzing' && (
        <div className="analyzing-screen">
          <div className="analyzing-spinner" />
          <div className="analyzing-text">
            <div className="analyzing-title">Analyzing intent…</div>
            <div className="analyzing-sub">Running AI pipeline — this takes about 15–30 s</div>
          </div>
          <div className="analyzing-steps">
            {ANALYZING_STEPS.map(({ label, step }) => {
              const done   = completedSteps >= step
              const active = completedSteps === step - 1
              return (
                <div key={label} className={`analyzing-step ${done ? 'analyzing-step--done' : ''}`}>
                  <div
                    className={`analyzing-step-dot ${done ? 'analyzing-step-dot--done' : ''}`}
                    style={!done && active ? {} : !done ? { animationDelay: `${(step - 1) * 0.3}s` } : {}}
                  />
                  <span className="analyzing-step-label">{label}</span>
                  {done && <span className="analyzing-step-check">✓</span>}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Requirements ── */}
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
              <div className="stat-row"><span>Requirements extracted</span><span className="stat-value">{total}</span></div>
              <div className="stat-row"><span>Stated</span><span className="stat-value stat-value--green">{statedCount}</span></div>
              <div className="stat-row"><span>Inferred</span><span className="stat-value stat-value--amber">{inferredCount}</span></div>
            </div>

            <div className="confidence-block">
              <div className="confidence-label-row">
                <span>OVERALL CONFIDENCE</span><span>{overallPct}</span>
              </div>
              <div className="confidence-track">
                <div className="confidence-fill" style={overallBar} />
              </div>
            </div>

            <div className="divider" />

            <div className="section-label section-label--bottom">
              <span>INFERRED ASSUMPTIONS</span><span>{inferredCount}</span>
            </div>
            <div className="assumptions-list">
              {assumptions.map((item) => (
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
                    key={item.key} type="button"
                    className={`chip ${filter === item.key ? 'chip--active' : ''}`}
                    onClick={() => setFilter(item.key)}
                  >{item.text}</button>
                ))}
              </div>
            </div>

            <div className="chip-bar">
              {categoryChips.map((item) => (
                <button
                  key={item.key} type="button"
                  className={`chip ${category === item.key ? 'chip--active' : ''}`}
                  onClick={() => setCategory(item.key)}
                >{item.text}</button>
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
                      const isStated      = req.kind === 'stated'
                      const stripColor    = isStated ? '#9bbf9f' : '#d3ccbf'
                      const badgeBg       = isStated ? '#e7efe7' : '#fbeed8'
                      const badgeColor    = isStated ? '#3f6b50' : '#9a4d09'
                      const badgeBorder   = isStated ? '#cfe0d2' : '#f0dcb5'
                      return (
                        <div key={req.id} className="req-card">
                          <div className="req-strip" style={{ background: stripColor }} />
                          <div className="req-body">
                            <div className="req-top-row">
                              <span className="req-id">{req.id}</span>
                              <button
                                type="button" className="req-badge"
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
                              className="req-input" value={req.value}
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
                <span className="spec-filename">{projectName || 'spec'}.req.json</span>
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

      {/* ── Component Selection ── */}
      {screen === 'components' && (
        <div className="flow-screen">
          <div className="flow-inner">
            <div className="prompt-eyebrow">STAGE 04 · COMPONENT SELECTION</div>
            <h1 className="prompt-title">Selected components</h1>
            <p className="prompt-lede">
              Real catalog parts matched to your formal requirements. Every component is verified
              against the catalog — no invented part numbers.
            </p>

            {componentSelecting && (
              <div className="stage-loading">
                <div className="analyzing-spinner" />
                <span className="stage-loading-label">Searching component catalog…</span>
              </div>
            )}

            {!componentSelecting && componentSelection && (
              <>
                <div className="comp-summary-row">
                  <div className="comp-summary-stat">
                    <span className="comp-summary-value">{componentSelection.components?.length || 0}</span>
                    <span className="comp-summary-label">selected</span>
                  </div>
                  {componentSelection.unresolved?.length > 0 && (
                    <div className="comp-summary-stat comp-summary-stat--warn">
                      <span className="comp-summary-value">{componentSelection.unresolved.length}</span>
                      <span className="comp-summary-label">unresolved</span>
                    </div>
                  )}
                </div>

                <div className="comp-list">
                  {(componentSelection.components || []).map((comp, i) => (
                    <div key={comp.functional_role || i} className="comp-card">
                      <div className="comp-card-head">
                        <span
                          className="comp-cat-dot"
                          style={{ background: COMP_CATEGORY_COLOR[comp.category] || '#888' }}
                        />
                        <span className="comp-role">{comp.functional_role}</span>
                        <div className="req-spacer" />
                        <span className="comp-mpn">{comp.mpn}</span>
                        <span className="comp-cat-badge">{comp.category}</span>
                      </div>
                      <div className="comp-kicad-row">
                        <span className="comp-detail-label">Symbol</span>
                        <span className="comp-kicad-val">{comp.kicad_symbol}</span>
                      </div>
                      <div className="comp-kicad-row">
                        <span className="comp-detail-label">Footprint</span>
                        <span className="comp-kicad-val">{comp.kicad_footprint}</span>
                      </div>
                      <div className="comp-rationale">{comp.rationale}</div>
                      {comp.satisfies_requirement_ids?.length > 0 && (
                        <div className="comp-req-ids">
                          {comp.satisfies_requirement_ids.map((id) => (
                            <span key={id} className="comp-req-tag">{id}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {componentSelection.unresolved?.length > 0 && (
                  <div className="unresolved-section">
                    <div className="section-label" style={{ marginBottom: 10 }}>UNRESOLVED</div>
                    {componentSelection.unresolved.map((u, i) => (
                      <div key={i} className="unresolved-item">
                        <span className="unresolved-role">{u.functional_role}</span>
                        <span className="unresolved-reason">{u.reason}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {error && <div style={ERROR_BANNER_STYLE}>{error}</div>}
          </div>
        </div>
      )}

      {/* ── Netlist ── */}
      {screen === 'netlist' && (
        <div className="flow-screen">
          <div className="flow-inner">
            <div className="prompt-eyebrow">STAGE 05 · NETLIST GENERATION</div>
            <h1 className="prompt-title">Netlist</h1>
            <p className="prompt-lede">
              Proposed connectivity between components, verified by electrical rules check (ERC).
              Download the KiCad .net file to import directly into your layout tool.
            </p>

            {netlistGenerating && (
              <div className="stage-loading">
                <div className="analyzing-spinner" />
                <span className="stage-loading-label">Generating netlist and running ERC…</span>
              </div>
            )}

            {!netlistGenerating && netlistData && (
              <>
                {netlistData.erc_passed === false ? (
                  <div className="verdict-banner verdict-banner--failed">
                    <span className="verdict-mark">✕</span>
                    <div>
                      <div className="verdict-title">
                        ERC failed — {netlistData.erc_violations?.length || 0} violation{netlistData.erc_violations?.length !== 1 ? 's' : ''}
                      </div>
                      <div className="verdict-sub">
                        Review the violations below. You can still download the partial netlist and proceed to placement.
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="verdict-banner verdict-banner--passed">
                    <span className="verdict-mark">✓</span>
                    <div>
                      <div className="verdict-title">ERC passed</div>
                      <div className="verdict-sub">
                        {netlistData.nets?.length || 0} nets · {netlistData.unconnected?.length || 0} unconnected pins
                      </div>
                    </div>
                  </div>
                )}

                {netlistData.erc_violations?.length > 0 && (
                  <div className="erc-section">
                    <div className="section-label" style={{ marginBottom: 10 }}>ERC VIOLATIONS</div>
                    <div className="erc-list">
                      {netlistData.erc_violations.map((v, i) => (
                        <div key={i} className="erc-violation">
                          <span className="erc-rule">{v.rule || `violation ${i + 1}`}</span>
                          <span className="erc-message">{v.message || JSON.stringify(v)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="section-label" style={{ marginTop: 22, marginBottom: 10 }}>
                  NETS · {netlistData.nets?.length || 0}
                </div>
                <div className="net-list">
                  {(netlistData.nets || []).map((net, i) => (
                    <div key={net.name || i} className={`net-row net-row--${net.net_class}`}>
                      <span className={`net-class-badge net-class-badge--${net.net_class}`}>
                        {net.net_class}
                      </span>
                      <span className="net-name">{net.name}</span>
                      <div className="req-spacer" />
                      <span className="net-pin-count">{net.pins?.length || 0} pins</span>
                    </div>
                  ))}
                </div>

                {netlistData.unconnected?.length > 0 && (
                  <div className="unresolved-section" style={{ marginTop: 16 }}>
                    <div className="section-label" style={{ marginBottom: 8 }}>UNCONNECTED PINS</div>
                    {netlistData.unconnected.map((u, i) => (
                      <div key={i} className="unresolved-item">
                        <span className="unresolved-role">
                          {u.pin_ref?.component_role} pin {u.pin_ref?.pin_number}
                        </span>
                        <span className="unresolved-reason">{u.reason}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {error && <div style={ERROR_BANNER_STYLE}>{error}</div>}
          </div>
        </div>
      )}

      {/* ── Placement ── */}
      {screen === 'placement' && (
        <div className="flow-screen">
          <div className="flow-inner">
            <div className="prompt-eyebrow">STAGE 06 · COMPONENT PLACEMENT</div>
            <h1 className="prompt-title">Board layout</h1>
            <p className="prompt-lede">
              Constraint-driven placement solved from netlist topology and mechanical requirements.
              Proximity constraints from net connectivity are automatically enforced.
            </p>

            {placementGenerating && (
              <div className="stage-loading">
                <div className="analyzing-spinner" />
                <span className="stage-loading-label">Solving placement constraints…</span>
              </div>
            )}

            {!placementGenerating && placementData && (
              <>
                {placementData.status === 'placed' ? (
                  <>
                    <div className="verdict-banner verdict-banner--passed">
                      <span className="verdict-mark">✓</span>
                      <div>
                        <div className="verdict-title">Placement solved</div>
                        <div className="verdict-sub">
                          {placementData.components?.length || 0} components on{' '}
                          {placementData.board?.width_mm} mm × {placementData.board?.height_mm} mm
                        </div>
                      </div>
                    </div>
                    <PlacementBoard board={placementData.board} components={placementData.components} />
                    <div className="placement-legend">
                      {Object.entries(COMP_CATEGORY_COLOR).map(([cat, color]) => {
                        const hasComp = (placementData.components || []).some((c) => c.category === cat)
                        if (!hasComp) return null
                        return (
                          <div key={cat} className="legend-item">
                            <span className="legend-dot" style={{ background: color }} />
                            <span className="legend-label">{cat}</span>
                          </div>
                        )
                      })}
                    </div>
                  </>
                ) : (
                  <div className="verdict-banner verdict-banner--failed">
                    <span className="verdict-mark">✕</span>
                    <div>
                      <div className="verdict-title">
                        Placement {placementData.status === 'infeasible' ? 'infeasible' : 'timed out'}
                      </div>
                      <div className="verdict-sub">
                        {placementData.unsat_reason || 'Constraints could not be satisfied with the current board dimensions.'}
                      </div>
                    </div>
                  </div>
                )}

                {placementData.unsat_groups?.length > 0 && (
                  <div className="unresolved-section" style={{ marginTop: 16 }}>
                    <div className="section-label" style={{ marginBottom: 8 }}>CONFLICTING GROUPS</div>
                    {placementData.unsat_groups.map((g, i) => (
                      <div key={i} className="unresolved-item"><span>{g}</span></div>
                    ))}
                  </div>
                )}
              </>
            )}

            {error && <div style={ERROR_BANNER_STYLE}>{error}</div>}
          </div>
        </div>
      )}

      {/* ── Validation ── */}
      {screen === 'validation' && (
        <div className="flow-screen">
          <div className="flow-inner">
            <div className="prompt-eyebrow">STAGE 07 · DESIGN VALIDATION</div>
            <h1 className="prompt-title">Validate a design</h1>
            <p className="prompt-lede">
              Check a candidate design against the {requirements.length} structured requirements. Pick
              a source, then run validation to see what passes, what needs attention, and what fails.
            </p>

            <div className="source-grid">
              {DESIGN_SOURCES.map((source) => (
                <button
                  key={source.key} type="button"
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
                onChange={(e) => { setDesignText(e.target.value); setValidated(false) }}
                spellCheck={false}
                placeholder={
                  designSource === 'bom'     ? 'ref,part,value,qty\nU1,TPS54331,buck,1\n…'
                  : designSource === 'netlist' ? '(export (version "E")\n  (components …))'
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
                  type="button" className="btn btn-primary"
                  onClick={handleRunValidation}
                  disabled={!designText.trim() || validating}
                >
                  {validating ? 'Validating…' : 'Run validation →'}
                </button>
              </div>
            </div>

            {error && <div style={ERROR_BANNER_STYLE}>{error}</div>}

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

      {/* ── Remediation ── */}
      {screen === 'remediation' && (
        <div className="flow-screen">
          <div className="flow-inner">
            <div className="prompt-eyebrow">STAGE 08 · REMEDIATION</div>
            <h1 className="prompt-title">Suggested fixes</h1>
            <p className="prompt-lede">
              {issues.length
                ? `Tracer found ${issues.length} issue${issues.length === 1 ? '' : 's'}. Apply the suggested fixes below, then move on to the report.`
                : 'No failures or warnings — nothing to remediate. Head straight to the report.'}
            </p>

            {issues.length > 0 && (
              <div className="remediation-meta">
                <span className="remediation-progress">{resolvedCount} of {issues.length} resolved</span>
                <div className="remediation-track">
                  <div className="remediation-fill" style={{ width: `${issues.length ? (resolvedCount / issues.length) * 100 : 0}%` }} />
                </div>
              </div>
            )}

            <div className="fix-list">
              {issues.map((item) => {
                const isApplied = Boolean(appliedFixes[item.id])
                return (
                  <div key={item.id} className={`fix-card ${isApplied ? 'fix-card--applied' : ''}`}>
                    <div className="fix-head">
                      <span className={`check-tag check-tag--${item.status}`}>{STATUS_WORD[item.status]}</span>
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
                    <div className="fix-issue">Expected {item.expected} · got {item.actual}</div>
                    <div className="fix-suggestion">{item.fix}</div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── Report ── */}
      {screen === 'report' && (
        <div className="flow-screen">
          <div className="flow-inner">
            <div className="prompt-eyebrow">STAGE 09 · EXPORT REPORT</div>
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
                <span className="report-stat-value">{resolvedCount}/{issues.length}</span>
                <span className="report-stat-label">resolved</span>
              </div>
            </div>

            <div className="report-panel">
              <div className="report-panel-header">
                <div className="spec-dot" />
                <span className="spec-filename">{projectName || 'board'}.validation.md</span>
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
