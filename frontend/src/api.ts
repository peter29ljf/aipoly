const BASE = ''

export interface Strategy {
  id: string
  name: string
  description: string
  created_at: string
}

export interface Position {
  token_id: string
  outcome: string
  shares: number
  cost_usdc: number
  note: string
}

export interface Alert {
  id: number
  sid: string
  token_id: string
  target: number
  direction: string
  status: string
  note: string
  created_at: string
  fired_at?: string
  fired_price?: number
}

export interface ScheduleJob {
  id: string
  next_run: string | null
  trigger: string
}

// ── Strategies ────────────────────────────────────────────────────────────────

export async function listStrategies(): Promise<Strategy[]> {
  const r = await fetch(`${BASE}/api/strategies`)
  return r.json()
}

export async function createStrategy(name: string, description = ''): Promise<Strategy> {
  const r = await fetch(`${BASE}/api/strategies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  })
  return r.json()
}

export async function getStrategy(sid: string): Promise<Strategy | null> {
  const r = await fetch(`${BASE}/api/strategies/${sid}`)
  if (!r.ok) return null
  return r.json()
}

export async function deleteStrategy(sid: string): Promise<void> {
  await fetch(`${BASE}/api/strategies/${sid}`, { method: 'DELETE' })
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export async function getChatHistory(sid: string, n = 50): Promise<any[]> {
  const r = await fetch(`${BASE}/api/strategies/${sid}/chat/history?n=${n}`)
  return r.json()
}

export async function runStrategy(sid: string): Promise<{ started: boolean }> {
  const r = await fetch(`${BASE}/api/strategies/${sid}/chat/run`, { method: 'POST' })
  return r.json()
}

export async function sendMessage(sid: string, message: string): Promise<{ started: boolean }> {
  const r = await fetch(`${BASE}/api/strategies/${sid}/chat/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  return r.json()
}

export function subscribeStream(sid: string, onEvent: (e: any) => void): EventSource {
  const es = new EventSource(`${BASE}/api/strategies/${sid}/chat/stream`)
  es.onmessage = (e) => {
    try { onEvent(JSON.parse(e.data)) } catch {}
  }
  return es
}

// ── Portfolio ─────────────────────────────────────────────────────────────────

export async function listPositions(sid: string): Promise<Position[]> {
  const r = await fetch(`${BASE}/api/strategies/${sid}/portfolio`)
  return r.json()
}

// ── Alerts ────────────────────────────────────────────────────────────────────

export async function listAlerts(sid: string): Promise<Alert[]> {
  const r = await fetch(`${BASE}/api/strategies/${sid}/alerts`)
  return r.json()
}

export async function createAlert(sid: string, token_id: string, target: number, direction: string, note = ''): Promise<Alert> {
  const r = await fetch(`${BASE}/api/strategies/${sid}/alerts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token_id, target, direction, note }),
  })
  return r.json()
}

export async function cancelAlert(sid: string, alertId: number): Promise<void> {
  await fetch(`${BASE}/api/strategies/${sid}/alerts/${alertId}`, { method: 'DELETE' })
}

// ── Schedules ─────────────────────────────────────────────────────────────────

export async function listSchedules(sid: string): Promise<ScheduleJob[]> {
  const r = await fetch(`${BASE}/api/strategies/${sid}/schedules`)
  return r.json()
}

// ── Strategy Doc ──────────────────────────────────────────────────────────────

export async function getStrategyDoc(sid: string): Promise<string> {
  const r = await fetch(`${BASE}/api/strategies/${sid}/doc`)
  const data = await r.json()
  return data.content || ''
}

export async function writeStrategyDoc(sid: string, content: string): Promise<void> {
  await fetch(`${BASE}/api/strategies/${sid}/doc`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
}

// ── Health ────────────────────────────────────────────────────────────────────

export interface McpServerStatus {
  status: 'ok' | 'error'
  detail?: string
  jobs?: number | null
}

export async function getMcpHealth(): Promise<Record<string, McpServerStatus>> {
  const r = await fetch(`${BASE}/api/health/mcp`)
  return r.json()
}
