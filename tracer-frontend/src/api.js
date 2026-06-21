// Thin client for the Tracer pipeline backend.
//
// Base URL resolves to VITE_API_URL when set (e.g. on a deployed build), and
// otherwise to the relative "/api" prefix — which the Vite dev server proxies
// to the FastAPI backend (see vite.config.js) so the browser stays same-origin
// and never hits CORS.
const BASE = import.meta.env.VITE_API_URL || '/api'

async function post(path, body) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail
    try {
      detail = (await res.json()).detail
    } catch {
      /* response had no JSON body */
    }
    const msg =
      typeof detail === 'object' && detail?.message
        ? detail.message
        : typeof detail === 'string'
        ? `${res.status} — ${detail}`
        : `${res.status} ${res.statusText}`
    const err = new Error(msg)
    // Attach structured detail for callers that need it (e.g. ERC violations).
    if (typeof detail === 'object') err.detail = detail
    throw err
  }
  return res.json()
}

// POST /projects  ->  { project_id }
export function createProject(name, intent) {
  return post('/projects', { name, intent })
}

// POST /projects/{id}/stage/{stage}  ->  stage output object
// `body` is optional: intent/structured/formal/remediation/comp/netlist/placement take
// none; validation accepts an optional { artifact }.
// For the netlist stage a 422 ERC failure is rethrown with err.detail carrying
// { erc_violations, partial_netlist }.
export async function runStage(projectId, stage, body) {
  const res = await post(`/projects/${projectId}/stage/${stage}`, body)
  return res.output
}
