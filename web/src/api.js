// Thin fetch wrapper over api.py. Every function throws an ApiError with
// the server's own error/message on non-2xx, so components can show the
// real "ServiceNow not configured" / "LLM not configured" text instead of
// a generic failure.

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function handle(resp) {
  const body = await resp.json().catch(() => ({}))
  if (!resp.ok) {
    throw new ApiError(resp.status, body.error || 'unknown_error', body.message || resp.statusText)
  }
  return body
}

export async function getAssessment(number, hours = 6) {
  const resp = await fetch(`/api/incident/${encodeURIComponent(number)}?hours=${hours}`)
  return handle(resp)
}

export async function getNarrative(number) {
  const resp = await fetch(`/api/incident/${encodeURIComponent(number)}/narrate`, { method: 'POST' })
  return handle(resp)
}

export async function askChat(number, question) {
  const resp = await fetch(`/api/incident/${encodeURIComponent(number)}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  return handle(resp)
}

export async function postNote(number, confirm) {
  const resp = await fetch(`/api/incident/${encodeURIComponent(number)}/post-note`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirm }),
  })
  return handle(resp)
}
