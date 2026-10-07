// Thin typed client for the CodeAtreus backend.
// Base URL is configurable via VITE_API_URL; defaults to the local FastAPI dev server.

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000/api'

const TOKEN_KEY = 'ca_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

function authHeaders(): Record<string, string> {
  const t = getToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// Obtain a fresh dev token. Deduped so concurrent 401s trigger one login, not N.
let reauthInFlight: Promise<boolean> | null = null
async function reauthenticate(): Promise<boolean> {
  if (!reauthInFlight) {
    reauthInFlight = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/dev-login`, { method: 'POST' })
        if (!res.ok) return false
        const pair = (await res.json()) as TokenPair
        setToken(pair.access_token)
        return true
      } catch {
        return false
      } finally {
        reauthInFlight = null
      }
    })()
  }
  return reauthInFlight
}

async function request<T>(method: string, path: string, body?: unknown, _retried = false): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...authHeaders(),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    // A 401 usually means a stale/expired token in localStorage. Drop it, grab a
    // fresh dev token, and retry once so the app recovers instead of silently
    // falling back to mock data. (dev-login itself is excluded to avoid a loop.)
    if (res.status === 401 && !_retried && !path.startsWith('/auth/')) {
      setToken(null)
      if (await reauthenticate()) {
        return request<T>(method, path, body, true)
      }
    }
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = (data && (data.detail || data.message)) || detail
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  get: <T,>(p: string) => request<T>('GET', p),
  post: <T,>(p: string, body?: unknown) => request<T>('POST', p, body),
  del: <T,>(p: string) => request<T>('DELETE', p),
}

// ── Types (mirror the backend response shapes) ───────────────────────────────
export interface TokenPair { access_token: string; refresh_token: string; token_type: string; expires_in: number }
export interface RepoCard {
  id: string; name: string; language: string; framework: string; stars: number
  lastIndexed: string; health: number; description: string; color: string
  files: number; size: string; status: string
}
export interface ImportResponse { repo_id: string; status: string; job_id: string | null }
export interface IndexStatus { status: string; step: number; total: number; label: string; logs: string[]; error: string | null }
export interface LangSlice { name: string; value: number; color: string }
export interface Overview {
  language_dist: LangSlice[]; framework: string; file_count: number; size: string
  health: number; entry_points: string[]; key_files: string[]
}
export interface ChatResponse { answer: string; files: string[] }
export interface ChatMessage { role: string; content: string; files: string[]; created_at: string }
export interface GraphNode { id: string; label: string; type: string; x: number; y: number }
export interface GraphData { nodes: GraphNode[]; edges: [string, string][]; colors: Record<string, string> }
export interface FlowStep { label: string; type: string; detail: string }
export interface SequenceData { mermaid: string; plantuml: string }
export interface SearchResult { file: string; path: string; line: number; relevance: number; snippet: string }
export interface RoadmapDay { day: number; title: string; tasks: string[]; resources: string[]; complete: number }
export interface ArchitectureModule { layer: string; responsibility: string; files: string[]; count: number }
export interface Architecture { summary: string; modules: ArchitectureModule[]; generated_by: string }
export interface ImportantFile { path: string; tags: string[] }
export interface DashboardStats { repos_indexed: number; questions_asked: number; tokens_used: number }
export interface ActivityPoint { date: string; repos: number; questions: number }

// ── Endpoint wrappers ─────────────────────────────────────────────────────────
export const Auth = {
  devLogin: () => api.post<TokenPair>('/auth/dev-login'),
  github: (code: string, redirect_uri?: string) => api.post<TokenPair>('/auth/github', { code, redirect_uri }),
  me: () => api.get('/auth/me'),
}

export const Repos = {
  list: () => api.get<RepoCard[]>('/repos'),
  get: (id: string) => api.get<RepoCard>(`/repos/${id}`),
  import: (github_url: string) => api.post<ImportResponse>('/repos/import', { github_url }),
  del: (id: string) => api.del<void>(`/repos/${id}`),
  status: (id: string) => api.get<IndexStatus>(`/repos/${id}/status`),
  overview: (id: string) => api.get<Overview>(`/repos/${id}/overview`),
  chat: (id: string, message: string) => api.post<ChatResponse>(`/repos/${id}/chat`, { message }),
  chatHistory: (id: string) => api.get<ChatMessage[]>(`/repos/${id}/chat/history`),
  graph: (id: string) => api.get<GraphData>(`/repos/${id}/graph`),
  flow: (id: string, entrypoint?: string) => api.post<{ steps: FlowStep[] }>(`/repos/${id}/flow`, { entrypoint }),
  sequence: (id: string, entrypoint?: string) => api.post<SequenceData>(`/repos/${id}/sequence`, { entrypoint }),
  search: (id: string, q: string) => api.get<SearchResult[]>(`/repos/${id}/search?q=${encodeURIComponent(q)}`),
  roadmap: (id: string) => api.get<{ days: RoadmapDay[] }>(`/repos/${id}/roadmap`),
  architecture: (id: string) => api.post<Architecture>(`/repos/${id}/architecture-summary`),
  importantFiles: (id: string) => api.get<ImportantFile[]>(`/repos/${id}/important-files`),
  apiDocs: (id: string) => api.get<{ openapi: string; info: unknown; paths: Record<string, unknown> }>(`/repos/${id}/api-docs`),
}

export const Dashboard = {
  stats: () => api.get<DashboardStats>('/dashboard/stats'),
  activity: () => api.get<ActivityPoint[]>('/dashboard/activity'),
}

// ── SSE chat streaming ────────────────────────────────────────────────────────
export interface ChatStreamHandlers {
  onSources?: (files: string[]) => void
  onToken?: (text: string) => void
  onDone?: (files: string[]) => void
}

// Streams POST /repos/{id}/chat/stream. EventSource can't do POST+auth, so we
// read the response body ourselves and parse the `event:`/`data:` SSE frames.
export async function chatStream(
  repoId: string,
  message: string,
  handlers: ChatStreamHandlers,
): Promise<void> {
  const open = () =>
    fetch(`${API_BASE}/repos/${repoId}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ message }),
    })
  let res = await open()
  // Recover from a stale token the same way request() does: reauth and retry once.
  if (res.status === 401) {
    setToken(null)
    if (await reauthenticate()) res = await open()
  }
  if (!res.ok || !res.body) {
    throw new ApiError(res.status, res.statusText || 'stream failed')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const dispatch = (frame: string) => {
    let event = 'message'
    const dataLines: string[] = []
    for (const line of frame.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
    }
    if (!dataLines.length) return
    let payload: { text?: string; files?: string[] }
    try {
      payload = JSON.parse(dataLines.join('\n'))
    } catch {
      return
    }
    if (event === 'sources') handlers.onSources?.(payload.files ?? [])
    else if (event === 'token') handlers.onToken?.(payload.text ?? '')
    else if (event === 'done') handlers.onDone?.(payload.files ?? [])
  }

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let sep: number
    // SSE frames are separated by a blank line.
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      if (frame.trim()) dispatch(frame)
    }
  }
  if (buffer.trim()) dispatch(buffer)
}

// WebSocket URL for live indexing progress.
export function indexingWsUrl(repoId: string): string {
  const base = API_BASE.replace(/\/api$/, '').replace(/^http/, 'ws')
  return `${base}/ws/indexing/${repoId}`
}
