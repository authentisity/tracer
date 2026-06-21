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
    throw new Error(detail ? `${res.status} — ${detail}` : `${res.status} ${res.statusText}`)
  }
  return res.json()
}

// POST /projects  ->  { project_id }
export function createProject(name, intent) {
  return post('/projects', { name, intent })
}

// POST /projects/{id}/stage/{stage}  ->  { stage_id, output }
// `body` is optional: intent/structured/formal/remediation take none; validation
// accepts an optional { artifact }.
export async function runStage(projectId, stage, body) {
  const res = await post(`/projects/${projectId}/stage/${stage}`, body)
  return res.output
}
