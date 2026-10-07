import { useState, useEffect, useRef, createContext, useContext } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Auth, Repos, Dashboard, chatStream, setToken, getToken,
  type RepoCard, type Overview as OverviewData,
  type GraphData, type GraphNode, type FlowStep, type SearchResult, type RoadmapDay,
  type SequenceData, type DashboardStats,
} from './api'
import {
  LayoutDashboard, GitBranch, MessageSquare, Search, Settings,
  Plus, RefreshCw, Trash2, ExternalLink, Copy, Download,
  CheckCircle2, Clock, Loader2, Sun, Moon, ChevronRight,
  FileCode, Database, Server, Globe, Package, GitBranchIcon, Star,
  Zap, Network, BookOpen, Terminal, Code2, ArrowRight,
  BarChart3, Activity, User, Key, Palette, LogOut, ChevronDown,
  AlertCircle, Shield, Cpu, Layers, Hash, TrendingUp,
  MoreHorizontal, Eye, Play, GitCommit, Send, Box,
  ArrowUpRight, Info, GitFork, Map, GitMerge, Braces,
  Gauge, Radio, PanelLeft, Filter, FolderOpen, Workflow,
  Command, Upload, List, Columns, Inbox, X
} from 'lucide-react'

// lucide-react no longer ships brand icons, so GitHub is a small inline SVG
function Github({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 .5C5.73.5.5 5.73.5 12c0 5.08 3.29 9.39 7.86 10.91.57.1.78-.25.78-.55 0-.27-.01-1.16-.02-2.11-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.28-1.68-1.28-1.68-1.04-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.76 2.7 1.25 3.36.96.1-.75.4-1.25.73-1.54-2.56-.29-5.26-1.28-5.26-5.7 0-1.26.45-2.29 1.19-3.09-.12-.29-.52-1.47.11-3.06 0 0 .97-.31 3.18 1.18.92-.26 1.9-.38 2.88-.39.98.01 1.96.13 2.88.39 2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.77.11 3.06.74.8 1.19 1.83 1.19 3.09 0 4.43-2.7 5.41-5.28 5.69.42.36.78 1.08.78 2.18 0 1.57-.01 2.84-.01 3.23 0 .3.2.66.79.55A10.52 10.52 0 0 0 23.5 12C23.5 5.73 18.27.5 12 .5Z" />
    </svg>
  )
}
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts'

// ── Types ──────────────────────────────────────────────────────────────────

type Page =
  | 'landing' | 'login' | 'dashboard' | 'import' | 'indexing'
  | 'overview' | 'chat' | 'graph' | 'flow' | 'sequence'
  | 'roadmap' | 'search' | 'settings'

interface Repo {
  id: string; name: string; language: string; framework: string
  stars: number; lastIndexed: string; health: number; description: string
  color: string; files: number; size: string
}

// ── Mock Data ──────────────────────────────────────────────────────────────

const REPOS: Repo[] = [
  { id: '1', name: 'NextCommerce', language: 'TypeScript', framework: 'Next.js', stars: 2341, lastIndexed: '2h ago', health: 98, description: 'Full-stack e-commerce platform with Stripe integration', color: '#3b82f6', files: 847, size: '12.4 MB' },
  { id: '2', name: 'FinTrack API', language: 'Python', framework: 'FastAPI', stars: 891, lastIndexed: '1d ago', health: 92, description: 'Financial analytics REST API with real-time WebSocket support', color: '#10b981', files: 312, size: '4.1 MB' },
  { id: '3', name: 'CodeAtreus', language: 'TypeScript', framework: 'Next.js', stars: 4120, lastIndexed: '3h ago', health: 97, description: 'AI-powered repository onboarding and exploration platform', color: '#8b5cf6', files: 1203, size: '28.7 MB' },
  { id: '4', name: 'HospitalMS', language: 'Java', framework: 'Spring Boot', stars: 567, lastIndexed: '3d ago', health: 84, description: 'Hospital management system with patient records and scheduling', color: '#f59e0b', files: 1891, size: '45.2 MB' },
  { id: '5', name: 'OpenCRM', language: 'Go', framework: 'Gin', stars: 1654, lastIndexed: '5h ago', health: 95, description: 'Open-source CRM with pipeline management and analytics', color: '#ef4444', files: 423, size: '7.8 MB' },
]

const DASH_ACTIVITY = [
  { date: 'Jan', repos: 2, questions: 45 },
  { date: 'Feb', repos: 3, questions: 78 },
  { date: 'Mar', repos: 3, questions: 112 },
  { date: 'Apr', repos: 4, questions: 167 },
  { date: 'May', repos: 5, questions: 234 },
  { date: 'Jun', repos: 5, questions: 289 },
  { date: 'Jul', repos: 5, questions: 341 },
]

const LANG_DIST = [
  { name: 'TypeScript', value: 42, color: '#3b82f6' },
  { name: 'Python', value: 23, color: '#10b981' },
  { name: 'Java', value: 18, color: '#f59e0b' },
  { name: 'Go', value: 17, color: '#ef4444' },
]

const PIPELINE_STEPS = [
  { id: 1, label: 'Git Clone', desc: 'Fetching repository from GitHub', icon: GitCommit },
  { id: 2, label: 'AST Parsing', desc: 'Building abstract syntax tree', icon: Braces },
  { id: 3, label: 'Metadata Extraction', desc: 'Extracting file structure and exports', icon: FileCode },
  { id: 4, label: 'Embedding Generation', desc: 'Creating semantic vector embeddings', icon: Cpu },
  { id: 5, label: 'Dependency Analysis', desc: 'Mapping module dependencies', icon: Network },
  { id: 6, label: 'Knowledge Graph', desc: 'Building relational knowledge graph', icon: Box },
  { id: 7, label: 'Ready', desc: 'Repository indexed and ready', icon: CheckCircle2 },
]

const CHAT_MESSAGES = [
  { role: 'user', content: 'Explain the authentication flow in this repository.' },
  { role: 'assistant', content: 'The authentication system uses **JWT tokens** with a refresh token strategy.\n\n1. User submits credentials to `POST /api/auth/login`\n2. `AuthController` validates the request and delegates to `AuthService`\n3. `AuthService` verifies the password hash via `bcrypt` and queries `UserRepository`\n4. On success, `JWTService` generates an access token (15min expiry) and refresh token (7d expiry)\n5. Refresh tokens are stored in Redis with user binding\n\nKey files: `auth.controller.ts`, `auth.service.ts`, `jwt.service.ts`', files: ['src/auth/auth.controller.ts', 'src/auth/auth.service.ts', 'src/auth/jwt.service.ts'] },
  { role: 'user', content: 'Which files connect to PostgreSQL?' },
  { role: 'assistant', content: 'PostgreSQL connections are managed through **TypeORM** with these key files:\n\n- `src/database/database.module.ts` — connection pool configuration\n- `src/database/migrations/` — 23 migration files\n- `src/users/user.entity.ts` — User table definition\n- `src/auth/refresh-token.entity.ts` — Token storage\n- `src/products/product.entity.ts` — Product catalogue\n\nConnection config lives in `.env` as `DATABASE_URL`. The app uses connection pooling via `pg` driver with max 20 connections.', files: ['src/database/database.module.ts', 'src/users/user.entity.ts', 'src/products/product.entity.ts'] },
  { role: 'user', content: 'How does payment processing work?' },
  { role: 'assistant', content: 'Payment processing is handled via **Stripe** with webhook verification:\n\n1. `PaymentController` receives `POST /api/payments/intent`\n2. `StripeService` creates a `PaymentIntent` with amount and currency\n3. Client confirms via Stripe.js\n4. Stripe sends webhook to `POST /api/webhooks/stripe`\n5. `WebhookService` verifies signature and updates `OrderRepository`\n\nIdempotency keys prevent duplicate charges. Failed payments trigger `PaymentFailedEvent` consumed by the notification system.', files: ['src/payments/payment.controller.ts', 'src/payments/stripe.service.ts', 'src/webhooks/webhook.service.ts'] },
]

const GRAPH_NODES = [
  { id: 'fe', label: 'Next.js Frontend', type: 'frontend', x: 400, y: 60 },
  { id: 'gw', label: 'API Gateway', type: 'api', x: 400, y: 160 },
  { id: 'ac', label: 'AuthController', type: 'controller', x: 160, y: 280 },
  { id: 'pc', label: 'ProductController', type: 'controller', x: 400, y: 280 },
  { id: 'oc', label: 'OrderController', type: 'controller', x: 640, y: 280 },
  { id: 'as', label: 'AuthService', type: 'service', x: 80, y: 400 },
  { id: 'ps', label: 'ProductService', type: 'service', x: 260, y: 400 },
  { id: 'os', label: 'OrderService', type: 'service', x: 440, y: 400 },
  { id: 'ss', label: 'StripeService', type: 'service', x: 620, y: 400 },
  { id: 'ur', label: 'UserRepo', type: 'repo', x: 120, y: 520 },
  { id: 'pr', label: 'ProductRepo', type: 'repo', x: 320, y: 520 },
  { id: 'or', label: 'OrderRepo', type: 'repo', x: 520, y: 520 },
  { id: 'pg', label: 'PostgreSQL', type: 'db', x: 280, y: 640 },
  { id: 'rd', label: 'Redis', type: 'db', x: 520, y: 640 },
]

const GRAPH_EDGES = [
  ['fe', 'gw'], ['gw', 'ac'], ['gw', 'pc'], ['gw', 'oc'],
  ['ac', 'as'], ['pc', 'ps'], ['oc', 'os'], ['oc', 'ss'],
  ['as', 'ur'], ['ps', 'pr'], ['os', 'or'],
  ['ur', 'pg'], ['pr', 'pg'], ['or', 'pg'], ['as', 'rd'],
]

const NODE_COLORS: Record<string, string> = {
  frontend: '#3b82f6', api: '#8b5cf6', controller: '#06b6d4',
  service: '#10b981', repo: '#f59e0b', db: '#ef4444',
}

const FLOW_STEPS = [
  { label: 'POST /api/auth/login', type: 'request', detail: 'HTTP request with email + password' },
  { label: 'AuthController', type: 'controller', detail: 'Validates body schema, rate-limits by IP' },
  { label: 'AuthService', type: 'service', detail: 'Calls UserRepository, verifies bcrypt hash' },
  { label: 'JWTService', type: 'service', detail: 'Signs access token (15min) + refresh token (7d)' },
  { label: 'UserRepository', type: 'repo', detail: 'SELECT * FROM users WHERE email = $1' },
  { label: 'PostgreSQL', type: 'db', detail: '~2ms query, returns user row with hashed password' },
  { label: '200 OK + tokens', type: 'response', detail: 'Sets httpOnly cookie, returns access token in body' },
]

const ROADMAP_DAYS = [
  { day: 1, title: 'Project Structure', tasks: ['Explore directory layout', 'Read package.json and dependencies', 'Understand Vite/Next.js config', 'Set up local environment'], resources: ['Next.js 14 App Router docs', 'Project README.md', 'CONTRIBUTING.md'], complete: 100 },
  { day: 2, title: 'Authentication System', tasks: ['Trace login flow', 'Understand JWT strategy', 'Review middleware chain', 'Test auth endpoints'], resources: ['NextAuth.js documentation', 'JWT.io introduction', 'OWASP Authentication Cheatsheet'], complete: 75 },
  { day: 3, title: 'Database Layer', tasks: ['Study entity definitions', 'Review migrations', 'Understand repository pattern', 'Query with TypeORM'], resources: ['Prisma ORM docs', 'PostgreSQL 15 release notes', 'pgvector README'], complete: 45 },
  { day: 4, title: 'API Layer', tasks: ['Map all REST endpoints', 'Understand DTOs and validation', 'Review error handling', 'Study interceptors'], resources: ['OpenAPI specification', 'REST API design guide', 'NestJS documentation'], complete: 20 },
  { day: 5, title: 'Deployment & CI/CD', tasks: ['Review Docker setup', 'Understand GitHub Actions', 'Study environment configs', 'Review monitoring setup'], resources: ['Docker Compose reference', 'GitHub Actions docs', 'Vercel deployment guide'], complete: 0 },
]

const SEARCH_RESULTS = [
  { file: 'src/auth/auth.service.ts', path: 'src/auth/', line: 42, relevance: 98, snippet: `async validateUser(email: string, password: string) {\n  const user = await this.userRepo.findByEmail(email);\n  if (!user || !bcrypt.compareSync(password, user.password)) {\n    throw new UnauthorizedException();\n  }\n  return user;\n}` },
  { file: 'src/auth/jwt.service.ts', path: 'src/auth/', line: 18, relevance: 94, snippet: `sign(payload: JwtPayload): string {\n  return this.jwtService.sign(payload, {\n    secret: this.config.get('JWT_SECRET'),\n    expiresIn: '15m',\n  });\n}` },
  { file: 'src/auth/guards/jwt-auth.guard.ts', path: 'src/auth/guards/', line: 7, relevance: 89, snippet: `@Injectable()\nexport class JwtAuthGuard extends AuthGuard('jwt') {\n  canActivate(context: ExecutionContext) {\n    return super.canActivate(context);\n  }\n}` },
  { file: 'src/middleware/auth.middleware.ts', path: 'src/middleware/', line: 23, relevance: 82, snippet: `export function authMiddleware(req: Request, res: Response, next: NextFunction) {\n  const token = req.headers.authorization?.split(' ')[1];\n  if (!token) throw new UnauthorizedException('No token provided');\n  // verify and attach user\n}` },
  { file: 'src/users/user.entity.ts', path: 'src/users/', line: 1, relevance: 76, snippet: `@Entity('users')\nexport class User {\n  @PrimaryGeneratedColumn('uuid') id: string;\n  @Column({ unique: true }) email: string;\n  @Column() passwordHash: string;\n  @Column({ default: 'user' }) role: string;\n}` },
]

// ── Fade variants ──────────────────────────────────────────────────────────

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.22, ease: 'easeOut' as const } },
}
const fadeIn = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.18 } },
}

// ── Shared UI primitives ───────────────────────────────────────────────────

function Badge({ children, color = 'blue' }: { children: React.ReactNode; color?: string }) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    green: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
    purple: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
    slate: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium border font-mono ${colors[color] || colors.blue}`}>
      {children}
    </span>
  )
}

function HealthBar({ value }: { value: number }) {
  const color = value >= 95 ? '#10b981' : value >= 80 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-white/5 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${value}%`, background: color }} />
      </div>
      <span className="text-[11px] font-mono" style={{ color }}>{value}%</span>
    </div>
  )
}

function Btn({
  children, onClick, variant = 'primary', size = 'md', className = '', disabled = false
}: {
  children: React.ReactNode; onClick?: () => void
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'; className?: string; disabled?: boolean
}) {
  const sizes = { sm: 'px-3 py-1.5 text-xs', md: 'px-4 py-2 text-sm', lg: 'px-6 py-3 text-base' }
  const variants = {
    primary: 'bg-blue-600 hover:bg-blue-500 text-white border border-blue-500/50',
    secondary: 'bg-white/5 hover:bg-white/10 text-white/80 border border-white/10',
    ghost: 'bg-transparent hover:bg-white/5 text-white/60 hover:text-white/80 border border-transparent',
    danger: 'bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20',
  }
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-2 rounded-md font-medium transition-all ${sizes[size]} ${variants[variant]} ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'} ${className}`}
    >
      {children}
    </button>
  )
}

// ── Sidebar ────────────────────────────────────────────────────────────────

function Sidebar({ page, setPage, isDark }: { page: Page; setPage: (p: Page) => void; isDark: boolean }) {
  const nav = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'import', label: 'Import Repo', icon: Plus },
    { id: 'overview', label: 'Overview', icon: Eye },
    { id: 'chat', label: 'AI Chat', icon: MessageSquare },
    { id: 'graph', label: 'Dependency Graph', icon: Network },
    { id: 'flow', label: 'Flow Visualizer', icon: Workflow },
    { id: 'sequence', label: 'Sequence Diagrams', icon: Layers },
    { id: 'roadmap', label: 'Learning Roadmap', icon: Map },
    { id: 'search', label: 'Search', icon: Search },
  ] as const

  const bottom = [
    { id: 'settings', label: 'Settings', icon: Settings },
  ] as const

  const activeRepo = REPOS[2]

  return (
    <aside className={`w-56 shrink-0 flex flex-col border-r h-screen sticky top-0 ${isDark ? 'bg-[#1e2544] border-white/[0.06]' : 'bg-white border-black/[0.06]'}`}>
      {/* Logo */}
      <div className="px-4 py-4 border-b border-inherit flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center shrink-0">
          <GitBranch className="w-4 h-4 text-white" />
        </div>
        <span className={`font-semibold text-sm tracking-tight ${isDark ? 'text-white' : 'text-gray-900'}`}>CodeAtreus</span>
        <Badge color="blue">Beta</Badge>
      </div>

      {/* Repo selector */}
      <div className={`mx-3 mt-3 mb-1 px-3 py-2.5 rounded-md border cursor-pointer transition-colors ${isDark ? 'bg-[#2D355C] border-white/[0.08] hover:bg-white/5' : 'bg-gray-50 border-black/[0.06] hover:bg-gray-100'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-2 h-2 rounded-full shrink-0" style={{ background: activeRepo.color }} />
            <span className={`text-xs font-medium truncate ${isDark ? 'text-white/90' : 'text-gray-800'}`}>{activeRepo.name}</span>
          </div>
          <ChevronDown className={`w-3 h-3 shrink-0 ${isDark ? 'text-white/30' : 'text-gray-400'}`} />
        </div>
        <div className={`mt-1 text-[10px] font-mono ${isDark ? 'text-white/30' : 'text-gray-400'}`}>{activeRepo.language} · {activeRepo.framework}</div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-2 overflow-y-auto">
        <div className={`text-[10px] font-semibold uppercase tracking-widest px-2 mb-1.5 ${isDark ? 'text-white/20' : 'text-gray-400'}`}>Navigation</div>
        {nav.map(({ id, label, icon: Icon }) => {
          const active = page === id
          return (
            <button
              key={id}
              onClick={() => setPage(id as Page)}
              className={`w-full flex items-center gap-2.5 px-2 py-2 rounded-md text-xs transition-all mb-0.5 ${
                active
                  ? isDark ? 'bg-blue-600/15 text-blue-400 border border-blue-500/20' : 'bg-blue-50 text-blue-600 border border-blue-100'
                  : isDark ? 'text-white/45 hover:text-white/70 hover:bg-white/5' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'
              }`}
            >
              <Icon className="w-3.5 h-3.5 shrink-0" />
              <span className="font-medium">{label}</span>
            </button>
          )
        })}
      </nav>

      {/* Bottom */}
      <div className="px-2 pb-3 border-t border-inherit pt-2">
        {bottom.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setPage(id as Page)}
            className={`w-full flex items-center gap-2.5 px-2 py-2 rounded-md text-xs transition-all ${
              page === id
                ? isDark ? 'bg-white/10 text-white/80' : 'bg-gray-100 text-gray-800'
                : isDark ? 'text-white/40 hover:text-white/70 hover:bg-white/5' : 'text-gray-400 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            <span className="font-medium">{label}</span>
          </button>
        ))}
        <div className={`mt-2 px-2 py-2 rounded-md flex items-center gap-2 ${isDark ? 'bg-white/3' : 'bg-gray-50'}`}>
          <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center shrink-0">
            <span className="text-[10px] font-bold text-white">JS</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className={`text-[11px] font-medium truncate ${isDark ? 'text-white/70' : 'text-gray-700'}`}>John Smith</div>
            <div className={`text-[10px] truncate ${isDark ? 'text-white/30' : 'text-gray-400'}`}>Pro Plan</div>
          </div>
        </div>
      </div>
    </aside>
  )
}

// ── TopBar ─────────────────────────────────────────────────────────────────

function TopBar({
  title, isDark, setIsDark, setPage, breadcrumbs = []
}: {
  title: string; isDark: boolean; setIsDark: (v: boolean) => void
  setPage: (p: Page) => void; breadcrumbs?: { label: string; page?: Page }[]
}) {
  return (
    <header className={`h-12 flex items-center justify-between px-6 border-b shrink-0 ${isDark ? 'bg-[#1e2544] border-white/[0.06]' : 'bg-white border-black/[0.06]'}`}>
      <div className="flex items-center gap-1.5">
        {breadcrumbs.map((b, i) => (
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && <ChevronRight className={`w-3 h-3 ${isDark ? 'text-white/20' : 'text-gray-300'}`} />}
            {b.page ? (
              <button onClick={() => setPage(b.page!)} className={`text-xs transition-colors ${isDark ? 'text-white/40 hover:text-white/70' : 'text-gray-400 hover:text-gray-700'}`}>{b.label}</button>
            ) : (
              <span className={`text-xs font-medium ${isDark ? 'text-white/80' : 'text-gray-800'}`}>{b.label}</span>
            )}
          </span>
        ))}
        {breadcrumbs.length === 0 && <span className={`text-sm font-medium ${isDark ? 'text-white/80' : 'text-gray-800'}`}>{title}</span>}
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => setIsDark(!isDark)}
          className={`w-7 h-7 flex items-center justify-center rounded-md transition-colors ${isDark ? 'text-white/40 hover:text-white/70 hover:bg-white/5' : 'text-gray-400 hover:text-gray-700 hover:bg-gray-100'}`}
        >
          {isDark ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
        </button>
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs ${isDark ? 'border-white/[0.06] text-white/30 bg-white/3' : 'border-black/[0.06] text-gray-400 bg-gray-50'}`}>
          <Command className="w-3 h-3" />
          <span>K</span>
        </div>
      </div>
    </header>
  )
}

// ── Page: Landing ──────────────────────────────────────────────────────────

function LandingPage({ setPage, isDark, setIsDark }: { setPage: (p: Page) => void; isDark: boolean; setIsDark: (v: boolean) => void }) {
  const features = [
    { icon: MessageSquare, label: 'Repository Chat', desc: 'Ask anything about your codebase in natural language' },
    { icon: Network, label: 'Dependency Graph', desc: 'Visualize module dependencies and architecture' },
    { icon: Workflow, label: 'Flow Visualizer', desc: 'Trace request lifecycle through your backend' },
    { icon: Map, label: 'Learning Roadmap', desc: 'Personal onboarding plan for every repository' },
    { icon: Layers, label: 'Sequence Diagrams', desc: 'Auto-generate UML diagrams from your code' },
    { icon: Search, label: 'Semantic Search', desc: 'Find code by meaning, not just keywords' },
  ]

  const logos = ['OpenAI', 'Stripe', 'Vercel', 'Supabase', 'Linear', 'Resend']

  // Animated graph nodes for hero
  const heroNodes = [
    { x: 120, y: 80, label: 'Frontend', color: '#3b82f6' },
    { x: 300, y: 40, label: 'API', color: '#8b5cf6' },
    { x: 480, y: 90, label: 'Auth', color: '#06b6d4' },
    { x: 200, y: 180, label: 'Service', color: '#10b981' },
    { x: 380, y: 200, label: 'DB', color: '#ef4444' },
    { x: 520, y: 220, label: 'Cache', color: '#f59e0b' },
  ]
  const heroEdges = [[0, 1], [1, 2], [0, 3], [1, 3], [1, 4], [2, 5], [3, 4]]

  return (
    <div className={`min-h-screen ${isDark ? 'bg-[#242C4D]' : 'bg-[#F8F9FC]'}`}>
      {/* Nav */}
      <nav className={`flex items-center justify-between px-10 py-4 border-b ${isDark ? 'border-white/[0.06]' : 'border-black/[0.05]'}`}>
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center">
            <GitBranch className="w-4 h-4 text-white" />
          </div>
          <span className={`font-semibold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>CodeAtreus</span>
          <Badge color="blue">Beta</Badge>
        </div>
        <div className="flex items-center gap-6">
          {['Features', 'Docs', 'Pricing'].map(l => (
            <button key={l} className={`text-sm transition-colors ${isDark ? 'text-white/40 hover:text-white/70' : 'text-gray-400 hover:text-gray-700'}`}>{l}</button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setIsDark(!isDark)} className={`p-2 rounded-md transition-colors ${isDark ? 'text-white/40 hover:bg-white/5' : 'text-gray-400 hover:bg-gray-100'}`}>
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <button onClick={() => setPage('login')} className={`px-4 py-1.5 text-sm rounded-md border transition-colors ${isDark ? 'border-white/10 text-white/60 hover:bg-white/5' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>Sign in</button>
          <button onClick={() => setPage('login')} className="px-4 py-1.5 text-sm rounded-md bg-blue-600 hover:bg-blue-500 text-white transition-colors">Get started</button>
        </div>
      </nav>

      {/* Hero */}
      <div className="max-w-6xl mx-auto px-10 pt-24 pb-16">
        <motion.div initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.08 } } }}>
          <motion.div variants={fadeUp} className="mb-4">
            <Badge color="blue">AI-Powered Repository Intelligence</Badge>
          </motion.div>
          <motion.h1 variants={fadeUp} className={`font-serif text-6xl leading-tight mb-6 max-w-3xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Understand Any Codebase<br />in Minutes.
          </motion.h1>
          <motion.p variants={fadeUp} className={`text-lg max-w-xl mb-10 leading-relaxed ${isDark ? 'text-white/50' : 'text-gray-500'}`}>
            AI-powered repository onboarding with architecture visualization, intelligent semantic search, and repository-aware chat.
          </motion.p>
          <motion.div variants={fadeUp} className="flex items-center gap-3">
            <button onClick={() => setPage('import')} className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-sm font-medium transition-colors">
              <Plus className="w-4 h-4" />
              Import Repository
            </button>
            <button onClick={() => setPage('overview')} className={`flex items-center gap-2 px-6 py-3 rounded-md text-sm font-medium border transition-colors ${isDark ? 'border-white/10 text-white/60 hover:bg-white/5' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
              <Play className="w-4 h-4" />
              View Demo
            </button>
          </motion.div>
        </motion.div>

        {/* Hero graph visualization */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4, duration: 0.4 }}
          className={`mt-20 rounded-xl border p-8 ${isDark ? 'bg-[#2D355C] border-white/[0.06]' : 'bg-white border-gray-100'}`}
        >
          <div className={`text-xs font-mono mb-4 ${isDark ? 'text-white/30' : 'text-gray-400'}`}>CodeAtreus / Architecture Preview — NextCommerce</div>
          <svg width="100%" viewBox="0 0 640 280" className="overflow-visible">
            {heroEdges.map(([a, b], i) => {
              const na = heroNodes[a], nb = heroNodes[b]
              return <line key={i} x1={na.x} y1={na.y} x2={nb.x} y2={nb.y} stroke={isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'} strokeWidth="1.5" />
            })}
            {heroNodes.map((n, i) => (
              <g key={i}>
                <circle cx={n.x} cy={n.y} r="28" fill={n.color + '18'} stroke={n.color + '60'} strokeWidth="1.5" />
                <text x={n.x} y={n.y + 1} textAnchor="middle" dominantBaseline="middle" fill={n.color} fontSize="9" fontWeight="600" fontFamily="JetBrains Mono, monospace">{n.label}</text>
              </g>
            ))}
          </svg>
        </motion.div>
      </div>

      {/* Logos */}
      <div className={`border-y py-8 ${isDark ? 'border-white/[0.06]' : 'border-gray-100'}`}>
        <div className={`text-center text-xs font-mono mb-6 ${isDark ? 'text-white/20' : 'text-gray-400'}`}>TRUSTED BY ENGINEERS AT</div>
        <div className="flex items-center justify-center gap-10 flex-wrap px-10">
          {logos.map(l => (
            <span key={l} className={`text-sm font-semibold ${isDark ? 'text-white/20' : 'text-gray-300'}`}>{l}</span>
          ))}
        </div>
      </div>

      {/* Features */}
      <div className="max-w-6xl mx-auto px-10 py-24">
        <h2 className={`font-serif text-3xl mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>Everything you need to ship faster.</h2>
        <p className={`text-sm mb-12 ${isDark ? 'text-white/40' : 'text-gray-400'}`}>From day one to fully productive in hours, not weeks.</p>
        <div className="grid grid-cols-3 gap-4">
          {features.map(({ icon: Icon, label, desc }) => (
            <div key={label} className={`p-5 rounded-xl border transition-colors ${isDark ? 'bg-[#2D355C] border-white/[0.06] hover:border-white/10' : 'bg-white border-gray-100 hover:border-gray-200'}`}>
              <div className="w-8 h-8 rounded-md bg-blue-600/10 flex items-center justify-center mb-3">
                <Icon className="w-4 h-4 text-blue-500" />
              </div>
              <div className={`text-sm font-medium mb-1 ${isDark ? 'text-white/80' : 'text-gray-800'}`}>{label}</div>
              <div className={`text-xs leading-relaxed ${isDark ? 'text-white/35' : 'text-gray-500'}`}>{desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <footer className={`border-t px-10 py-8 flex items-center justify-between ${isDark ? 'border-white/[0.06]' : 'border-gray-100'}`}>
        <div className={`text-xs ${isDark ? 'text-white/25' : 'text-gray-400'}`}>© 2025 CodeAtreus. All rights reserved.</div>
        <div className="flex items-center gap-6">
          {['GitHub', 'Docs', 'Privacy', 'Contact'].map(l => (
            <button key={l} className={`text-xs transition-colors ${isDark ? 'text-white/25 hover:text-white/50' : 'text-gray-400 hover:text-gray-600'}`}>{l}</button>
          ))}
        </div>
      </footer>
    </div>
  )
}

// ── Page: Login ────────────────────────────────────────────────────────────

function LoginPage({ setPage, isDark, setIsDark }: { setPage: (p: Page) => void; isDark: boolean; setIsDark: (v: boolean) => void }) {
  return (
    <div className={`min-h-screen flex ${isDark ? 'bg-[#242C4D]' : 'bg-[#F8F9FC]'}`}>
      {/* Left — illustration */}
      <div className="flex-1 hidden lg:flex flex-col items-center justify-center p-16 relative overflow-hidden">
        <div className="absolute inset-0" style={{ backgroundImage: isDark ? 'radial-gradient(circle at 50% 50%, #2D355C 0%, #242C4D 100%)' : 'radial-gradient(circle at 50% 50%, #e8edf8 0%, #F8F9FC 100%)' }} />
        <div className="relative z-10 w-full max-w-md">
          <svg viewBox="0 0 480 360" className="w-full">
            {/* Decorative graph */}
            {[[60,180,200,80],[200,80,340,160],[340,160,420,80],[200,80,200,260],[340,160,340,280],[200,260,340,280],[60,180,200,260]].map(([x1,y1,x2,y2], i) => (
              <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={isDark ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.12)'} strokeWidth="1.5" />
            ))}
            {[{x:60,y:180,c:'#3b82f6',r:22},{x:200,y:80,c:'#8b5cf6',r:28},{x:340,y:160,c:'#06b6d4',r:22},{x:420,y:80,c:'#10b981',r:18},{x:200,y:260,c:'#f59e0b',r:22},{x:340,y:280,c:'#ef4444',r:18}].map((n, i) => (
              <g key={i}>
                <circle cx={n.x} cy={n.y} r={n.r} fill={n.c + '18'} stroke={n.c + '50'} strokeWidth="1.5" />
                <circle cx={n.x} cy={n.y} r="4" fill={n.c} />
              </g>
            ))}
          </svg>
          <div className="text-center mt-4">
            <h2 className={`font-serif text-2xl mb-2 ${isDark ? 'text-white/70' : 'text-gray-600'}`}>Map Every Repository.</h2>
            <p className={`text-sm ${isDark ? 'text-white/30' : 'text-gray-400'}`}>AI-powered architecture understanding for engineering teams.</p>
          </div>
        </div>
      </div>

      {/* Right — login card */}
      <div className="w-full lg:w-[420px] flex items-center justify-center p-10">
        <motion.div initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.07 } } }} className="w-full max-w-sm">
          <motion.div variants={fadeUp} className="flex items-center gap-2 mb-10">
            <div className="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center">
              <GitBranch className="w-4 h-4 text-white" />
            </div>
            <span className={`font-semibold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>CodeAtreus</span>
          </motion.div>

          <motion.h1 variants={fadeUp} className={`font-serif text-3xl mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Welcome back.</motion.h1>
          <motion.p variants={fadeUp} className={`text-sm mb-8 ${isDark ? 'text-white/40' : 'text-gray-500'}`}>Sign in to your account to continue.</motion.p>

          <motion.div variants={fadeUp} className="space-y-3">
            <button onClick={() => setPage('dashboard')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-md border text-sm font-medium transition-all ${isDark ? 'bg-white/5 border-white/10 text-white/80 hover:bg-white/10' : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'}`}>
              <Github className="w-4 h-4" />
              Continue with GitHub
            </button>
            <button onClick={() => setPage('dashboard')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-md border text-sm font-medium transition-all ${isDark ? 'bg-white/5 border-white/10 text-white/80 hover:bg-white/10' : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'}`}>
              <svg className="w-4 h-4" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
              Continue with Google
            </button>
          </motion.div>

          <motion.div variants={fadeUp} className={`my-6 flex items-center gap-3 ${isDark ? 'text-white/15' : 'text-gray-200'}`}>
            <div className="flex-1 h-px bg-current" />
            <span className={`text-xs ${isDark ? 'text-white/25' : 'text-gray-400'}`}>or</span>
            <div className="flex-1 h-px bg-current" />
          </motion.div>

          <motion.div variants={fadeUp} className="space-y-3">
            <div>
              <label className={`text-xs font-medium block mb-1.5 ${isDark ? 'text-white/50' : 'text-gray-600'}`}>Email</label>
              <input type="email" placeholder="you@company.com" className={`w-full px-3 py-2.5 rounded-md border text-sm outline-none transition-colors ${isDark ? 'bg-white/5 border-white/10 text-white/80 placeholder-white/20 focus:border-blue-500/50' : 'bg-white border-gray-200 text-gray-800 placeholder-gray-300 focus:border-blue-300'}`} />
            </div>
            <div>
              <label className={`text-xs font-medium block mb-1.5 ${isDark ? 'text-white/50' : 'text-gray-600'}`}>Password</label>
              <input type="password" placeholder="••••••••" className={`w-full px-3 py-2.5 rounded-md border text-sm outline-none transition-colors ${isDark ? 'bg-white/5 border-white/10 text-white/80 placeholder-white/20 focus:border-blue-500/50' : 'bg-white border-gray-200 text-gray-800 placeholder-gray-300 focus:border-blue-300'}`} />
            </div>
            <button onClick={() => setPage('dashboard')} className="w-full py-2.5 rounded-md bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors">
              Sign in
            </button>
          </motion.div>

          <motion.div variants={fadeUp} className="mt-8 flex items-center justify-between">
            <span className={`text-xs ${isDark ? 'text-white/25' : 'text-gray-400'}`}>Don't have an account?</span>
            <button className="text-xs text-blue-500 hover:text-blue-400 transition-colors">Sign up free</button>
          </motion.div>

          <motion.div variants={fadeUp} className="mt-6 flex items-center justify-end">
            <button onClick={() => setIsDark(!isDark)} className={`flex items-center gap-1.5 text-xs transition-colors ${isDark ? 'text-white/25 hover:text-white/50' : 'text-gray-400 hover:text-gray-600'}`}>
              {isDark ? <Sun className="w-3 h-3" /> : <Moon className="w-3 h-3" />}
              {isDark ? 'Light mode' : 'Dark mode'}
            </button>
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}

// ── Page: Dashboard ────────────────────────────────────────────────────────

function DashboardPage({ setPage, isDark, setIsDark }: { setPage: (p: Page) => void; isDark: boolean; setIsDark: (v: boolean) => void }) {
  const { setRepoId, ensureAuth } = useAppState()
  const [repos, setRepos] = useState<RepoCard[]>(REPOS.map(r => ({ ...r, status: 'ready' })))
  const [activity, setActivity] = useState(DASH_ACTIVITY)
  const [statsData, setStatsData] = useState<DashboardStats | null>(null)
  const [live, setLive] = useState(false)

  useEffect(() => {
    let active = true
    ;(async () => {
      await ensureAuth()
      try {
        const [rs, st, act] = await Promise.all([
          Repos.list(), Dashboard.stats(), Dashboard.activity(),
        ])
        if (!active) return
        // Reflect the account's real library, even when empty (new user) — the
        // mock repos only stand in while the backend is unreachable.
        setRepos(rs)
        setStatsData(st)
        if (act.length) setActivity(act.map(a => ({ date: a.date, repos: a.repos, questions: a.questions })))
        setLive(true)
      } catch { /* keep mock data */ }
    })()
    return () => { active = false }
  }, [])

  const openRepo = (id: string) => { setRepoId(id); setPage('overview') }

  // Language distribution by repository count (falls back to mock LANG_DIST).
  const langDist = live && repos.length
    ? Object.values(repos.reduce((acc, r) => {
        const key = r.language || 'Unknown'
        acc[key] = acc[key] || { name: key, value: 0, color: r.color }
        acc[key].value += 1
        return acc
      }, {} as Record<string, { name: string; value: number; color: string }>))
    : LANG_DIST

  const stats = statsData
    ? [
        { label: 'Repositories', value: String(repos.length), icon: GitBranch, delta: `${statsData.repos_indexed} indexed` },
        { label: 'Questions Asked', value: statsData.questions_asked.toLocaleString(), icon: MessageSquare, delta: 'all time' },
        { label: 'Tokens Used', value: statsData.tokens_used.toLocaleString(), icon: Cpu, delta: 'LLM usage' },
        { label: 'Indexed Repos', value: String(statsData.repos_indexed), icon: Network, delta: 'ready' },
      ]
    : [
        { label: 'Repositories', value: '5', icon: GitBranch, delta: '+1 this month' },
        { label: 'Questions Asked', value: '1,247', icon: MessageSquare, delta: '+89 this week' },
        { label: 'Embeddings', value: '48.2K', icon: Cpu, delta: '4 repos indexed' },
        { label: 'Architecture Maps', value: '12', icon: Network, delta: '2 pending' },
      ]

  const c = isDark ? {
    bg: 'bg-[#242C4D]', surface: 'bg-[#2D355C]', border: 'border-white/[0.06]',
    text: 'text-white/80', muted: 'text-white/35', heading: 'text-white'
  } : {
    bg: 'bg-[#F8F9FC]', surface: 'bg-white', border: 'border-gray-100',
    text: 'text-gray-700', muted: 'text-gray-400', heading: 'text-gray-900'
  }

  return (
    <div className={`flex-1 overflow-y-auto ${c.bg}`}>
      <TopBar title="Dashboard" isDark={isDark} setIsDark={setIsDark} setPage={setPage}
        breadcrumbs={[{ label: 'Dashboard' }]} />
      <div className="p-6 max-w-7xl">
        <div className="mb-6">
          <h1 className={`font-serif text-2xl mb-1 ${c.heading}`}>Repository Library</h1>
          <p className={`text-sm ${c.muted}`}>Manage and explore your indexed repositories.</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {stats.map(({ label, value, icon: Icon, delta }) => (
            <motion.div key={label} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}
              className={`${c.surface} border ${c.border} rounded-xl p-4`}>
              <div className="flex items-start justify-between mb-3">
                <div className={`w-8 h-8 rounded-md flex items-center justify-center bg-blue-600/10`}>
                  <Icon className="w-4 h-4 text-blue-500" />
                </div>
                <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <div className={`text-2xl font-semibold mb-0.5 ${c.heading}`}>{value}</div>
              <div className={`text-xs ${c.muted}`}>{label}</div>
              <div className="text-[10px] text-emerald-400 mt-1 font-mono">{delta}</div>
            </motion.div>
          ))}
        </div>

        {/* Charts + Repos */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className={`col-span-2 ${c.surface} border ${c.border} rounded-xl p-5`}>
            <div className={`text-sm font-medium mb-1 ${c.heading}`}>Activity Overview</div>
            <div className={`text-xs mb-4 ${c.muted}`}>Questions asked over time</div>
            <ResponsiveContainer width="100%" height={140}>
              <AreaChart data={activity}>
                <defs>
                  <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke={isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)'} vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: isDark ? 'rgba(255,255,255,0.3)' : '#9ca3af' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: isDark ? 'rgba(255,255,255,0.3)' : '#9ca3af' }} axisLine={false} tickLine={false} width={30} />
                <Tooltip contentStyle={{ background: isDark ? '#2D355C' : '#fff', border: isDark ? '1px solid rgba(255,255,255,0.08)' : '1px solid #e5e7eb', borderRadius: 6, fontSize: 12 }} />
                <Area type="monotone" dataKey="questions" stroke="#3b82f6" strokeWidth={1.5} fill="url(#grad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className={`${c.surface} border ${c.border} rounded-xl p-5`}>
            <div className={`text-sm font-medium mb-1 ${c.heading}`}>Languages</div>
            <div className={`text-xs mb-4 ${c.muted}`}>By repository count</div>
            <ResponsiveContainer width="100%" height={100}>
              <PieChart>
                <Pie data={langDist} cx="50%" cy="50%" innerRadius={30} outerRadius={48} paddingAngle={2} dataKey="value">
                  {langDist.map((d, i) => <Cell key={i} fill={d.color} />)}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-3 space-y-1.5">
              {langDist.map(d => (
                <div key={d.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full" style={{ background: d.color }} />
                    <span className={`text-xs ${c.muted}`}>{d.name}</span>
                  </div>
                  <span className={`text-xs font-mono ${c.text}`}>{d.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Repo list */}
        <div className={`${c.surface} border ${c.border} rounded-xl overflow-hidden`}>
          <div className={`flex items-center justify-between px-5 py-3.5 border-b ${c.border}`}>
            <div className={`text-sm font-medium ${c.heading}`}>Repositories</div>
            <button onClick={() => setPage('import')} className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-md transition-colors">
              <Plus className="w-3 h-3" />
              Import
            </button>
          </div>
          <div>
            {live && repos.length === 0 && (
              <div className="flex flex-col items-center justify-center text-center px-6 py-16">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${isDark ? 'bg-white/5' : 'bg-gray-100'}`}>
                  <GitBranch className={`w-5 h-5 ${c.muted}`} />
                </div>
                <div className={`text-sm font-medium mb-1 ${c.heading}`}>No repositories yet</div>
                <div className={`text-xs mb-5 max-w-xs ${c.muted}`}>Import a GitHub repository to index it and start exploring its architecture, graph, and chat.</div>
                <button onClick={() => setPage('import')} className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-md transition-colors">
                  <Plus className="w-3 h-3" />
                  Import your first repository
                </button>
              </div>
            )}
            {repos.map((repo, i) => (
              <motion.div key={repo.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.05 }}
                className={`flex items-center px-5 py-4 border-b last:border-b-0 hover:bg-white/3 cursor-pointer transition-colors ${c.border}`}
                onClick={() => openRepo(repo.id)}
              >
                <div className="w-8 h-8 rounded-md flex items-center justify-center mr-4 shrink-0" style={{ background: repo.color + '18', border: `1px solid ${repo.color}30` }}>
                  <div className="w-2 h-2 rounded-full" style={{ background: repo.color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className={`text-sm font-medium ${c.heading}`}>{repo.name}</div>
                  <div className={`text-xs truncate ${c.muted}`}>{repo.description}</div>
                </div>
                <div className="hidden md:flex items-center gap-6 mx-6">
                  <div>
                    <div className={`text-[10px] ${c.muted} mb-0.5`}>Language</div>
                    <Badge color="blue">{repo.language}</Badge>
                  </div>
                  <div>
                    <div className={`text-[10px] ${c.muted} mb-0.5`}>Framework</div>
                    <span className={`text-xs font-mono ${c.text}`}>{repo.framework}</span>
                  </div>
                  <div className="w-28">
                    <div className={`text-[10px] ${c.muted} mb-1`}>Health</div>
                    <HealthBar value={repo.health} />
                  </div>
                  <div>
                    <div className={`text-[10px] ${c.muted} mb-0.5`}>Stars</div>
                    <div className="flex items-center gap-1">
                      <Star className="w-3 h-3 text-amber-400" />
                      <span className={`text-xs font-mono ${c.text}`}>{repo.stars.toLocaleString()}</span>
                    </div>
                  </div>
                  <div>
                    <div className={`text-[10px] ${c.muted} mb-0.5`}>Indexed</div>
                    <div className={`text-xs font-mono ${c.muted}`}>{repo.lastIndexed}</div>
                  </div>
                </div>
                <div className="flex items-center gap-1 ml-2">
                  <button onClick={(e) => { e.stopPropagation(); openRepo(repo.id) }} className={`p-1.5 rounded hover:bg-white/5 transition-colors ${c.muted}`}><Eye className="w-3.5 h-3.5" /></button>
                  <button className={`p-1.5 rounded hover:bg-white/5 transition-colors ${c.muted}`}><RefreshCw className="w-3.5 h-3.5" /></button>
                  <button
                    onClick={async (e) => {
                      e.stopPropagation()
                      try { await Repos.del(repo.id); setRepos(rs => rs.filter(r => r.id !== repo.id)) } catch { /* ignore */ }
                    }}
                    className={`p-1.5 rounded hover:bg-red-500/10 transition-colors text-red-400/50 hover:text-red-400`}><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Page: Import ───────────────────────────────────────────────────────────

function ImportPage({ setPage, isDark, setIsDark }: { setPage: (p: Page) => void; isDark: boolean; setIsDark: (v: boolean) => void }) {
  const { setRepoId, ensureAuth } = useAppState()
  const [url, setUrl] = useState('')
  const [previewing, setPreviewing] = useState(false)
  const [importing, setImporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleStart = async () => {
    setError(null)
    setImporting(true)
    try {
      await ensureAuth()
      const res = await Repos.import(url.trim())
      setRepoId(res.repo_id)
      setPage('indexing')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Import failed')
    } finally {
      setImporting(false)
    }
  }

  const c = isDark ? {
    bg: 'bg-[#242C4D]', surface: 'bg-[#2D355C]', border: 'border-white/[0.06]',
    text: 'text-white/80', muted: 'text-white/35', heading: 'text-white',
    input: 'bg-white/5 border-white/10 text-white/80 placeholder-white/20 focus:border-blue-500/40'
  } : {
    bg: 'bg-[#F8F9FC]', surface: 'bg-white', border: 'border-gray-100',
    text: 'text-gray-700', muted: 'text-gray-400', heading: 'text-gray-900',
    input: 'bg-white border-gray-200 text-gray-800 placeholder-gray-300 focus:border-blue-300'
  }

  const handlePreview = () => {
    if (url.trim()) setPreviewing(true)
  }

  const detected = {
    language: 'TypeScript', framework: 'Next.js', packageManager: 'pnpm',
    size: '28.7 MB', files: '1,203 files', estimatedTime: '~45 seconds',
  }

  return (
    <div className={`flex-1 overflow-y-auto ${c.bg}`}>
      <TopBar title="Import Repository" isDark={isDark} setIsDark={setIsDark} setPage={setPage}
        breadcrumbs={[{ label: 'Dashboard', page: 'dashboard' }, { label: 'Import Repository' }]} />
      <div className="p-6 max-w-3xl">
        <h1 className={`font-serif text-2xl mb-1 ${c.heading}`}>Import Repository</h1>
        <p className={`text-sm mb-8 ${c.muted}`}>Paste a GitHub URL to analyze and index your repository.</p>

        <div className={`${c.surface} border ${c.border} rounded-xl p-6 mb-4`}>
          <label className={`text-xs font-medium block mb-2 ${c.text}`}>GitHub Repository URL</label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Github className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${c.muted}`} />
              <input
                value={url}
                onChange={e => setUrl(e.target.value)}
                placeholder="https://github.com/owner/repository"
                className={`w-full pl-9 pr-4 py-3 rounded-md border text-sm outline-none transition-colors font-mono ${c.input}`}
              />
            </div>
            <button onClick={handlePreview} className="px-5 py-3 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-md transition-colors font-medium">
              Analyze
            </button>
          </div>
          <p className={`text-xs mt-2 ${c.muted}`}>Supports public and private repositories (requires GitHub OAuth)</p>
        </div>

        <AnimatePresence>
          {previewing && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className={`${c.surface} border ${c.border} rounded-xl p-6 mb-4`}>
              <div className="flex items-center gap-2 mb-5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className={`text-sm font-medium ${c.heading}`}>Repository detected</span>
              </div>
              <div className="grid grid-cols-3 gap-4 mb-6">
                {Object.entries(detected).map(([k, v]) => (
                  <div key={k} className={`p-3 rounded-lg border ${c.border} ${isDark ? 'bg-white/3' : 'bg-gray-50'}`}>
                    <div className={`text-[10px] uppercase tracking-wider mb-1 ${c.muted}`}>{k.replace(/([A-Z])/g, ' $1').trim()}</div>
                    <div className={`text-sm font-mono font-medium ${c.text}`}>{v}</div>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-3">
                <button onClick={handleStart} disabled={importing} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-60 text-white text-sm rounded-md transition-colors font-medium">
                  {importing ? 'Starting…' : 'Start Indexing'}
                </button>
                <button onClick={() => setPreviewing(false)} className={`px-5 py-2.5 text-sm rounded-md border transition-colors ${isDark ? 'border-white/10 text-white/50 hover:bg-white/5' : 'border-gray-200 text-gray-500 hover:bg-gray-50'}`}>
                  Cancel
                </button>
              </div>
              {error && <p className="text-xs mt-3 text-rose-400">{error}</p>}
            </motion.div>
          )}
        </AnimatePresence>

        <div className={`${c.surface} border ${c.border} rounded-xl p-5`}>
          <div className={`text-xs font-medium mb-3 ${c.heading}`}>Quick import</div>
          <div className="grid grid-cols-2 gap-2">
            {REPOS.slice(0, 4).map(r => (
              <button key={r.id} onClick={() => { setUrl(`https://github.com/example/${r.name.toLowerCase()}`); setPreviewing(true) }}
                className={`flex items-center gap-2.5 p-3 rounded-lg border text-left transition-colors ${isDark ? 'border-white/[0.06] hover:border-white/10 hover:bg-white/3' : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50'}`}>
                <div className="w-6 h-6 rounded flex items-center justify-center shrink-0" style={{ background: r.color + '18' }}>
                  <div className="w-1.5 h-1.5 rounded-full" style={{ background: r.color }} />
                </div>
                <div>
                  <div className={`text-xs font-medium ${c.heading}`}>{r.name}</div>
                  <div className={`text-[10px] font-mono ${c.muted}`}>{r.language}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Page: Indexing ─────────────────────────────────────────────────────────

function IndexingPage({ setPage, isDark, setIsDark }: { setPage: (p: Page) => void; isDark: boolean; setIsDark: (v: boolean) => void }) {
  const { repoId } = useAppState()
  const [step, setStep] = useState(0)
  const [logs, setLogs] = useState<string[]>([])

  const ALL_LOGS = [
    '$ git clone https://github.com/example/codeatreus.git',
    '✓ Repository cloned — 1,203 files, 28.7 MB',
    '$ ast-parser --lang typescript --target ./src',
    '✓ Parsed 847 TypeScript files, 23,419 nodes',
    '✓ Extracted 1,203 exports, 892 imports',
    '$ embed-gen --model text-embedding-3-small --batch 64',
    '✓ Generated 48,241 embeddings (4 batches)',
    '$ dep-analyzer --entry src/main.ts',
    '✓ Mapped 234 module dependencies',
    '✓ Detected 12 circular dependencies (auto-resolved)',
    '$ knowledge-graph --build --relations all',
    '✓ Knowledge graph built — 1,847 nodes, 3,219 edges',
    '✓ Repository ready. Indexing complete in 42.3s',
  ]

  useEffect(() => {
    // Offline/demo fallback: animate the mock pipeline when there's no repo.
    if (!repoId) {
      const ti = setInterval(() => {
        setStep(s => { if (s < PIPELINE_STEPS.length - 1) return s + 1; clearInterval(ti); return s })
      }, 1200)
      const tl = setInterval(() => {
        setLogs(l => { if (l.length >= ALL_LOGS.length) { clearInterval(tl); return l } return [...l, ALL_LOGS[l.length]] })
      }, 800)
      return () => { clearInterval(ti); clearInterval(tl) }
    }

    // Real indexing: poll the backend until the job reaches a terminal state.
    let active = true
    const poll = async () => {
      try {
        const s = await Repos.status(repoId)
        if (!active) return
        setStep(Math.max(0, s.step - 1))
        setLogs(s.logs)
        if (s.status === 'ready' || s.status === 'failed') return
      } catch {
        /* transient error — keep polling */
      }
      if (active) setTimeout(poll, 800)
    }
    poll()
    return () => { active = false }
  }, [repoId])

  const c = isDark ? {
    bg: 'bg-[#242C4D]', surface: 'bg-[#2D355C]', border: 'border-white/[0.06]',
    text: 'text-white/80', muted: 'text-white/35', heading: 'text-white',
    terminal: 'bg-[#151a2e]'
  } : {
    bg: 'bg-[#F8F9FC]', surface: 'bg-white', border: 'border-gray-100',
    text: 'text-gray-700', muted: 'text-gray-400', heading: 'text-gray-900',
    terminal: 'bg-gray-900'
  }

  const progress = Math.round((step / (PIPELINE_STEPS.length - 1)) * 100)

  return (
    <div className={`flex-1 overflow-y-auto ${c.bg}`}>
      <TopBar title="Indexing" isDark={isDark} setIsDark={setIsDark} setPage={setPage}
        breadcrumbs={[{ label: 'Dashboard', page: 'dashboard' }, { label: 'Import', page: 'import' }, { label: 'Indexing' }]} />
      <div className="p-6 max-w-4xl">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className={`font-serif text-2xl mb-1 ${c.heading}`}>Indexing Repository</h1>
            <div className={`text-sm font-mono ${c.muted}`}>github.com/example/codeatreus</div>
          </div>
          <div className={`text-right`}>
            <div className={`text-3xl font-semibold ${c.heading}`}>{progress}%</div>
            <div className={`text-xs ${c.muted}`}>complete</div>
          </div>
        </div>

        {/* Progress bar */}
        <div className={`h-1 rounded-full mb-8 overflow-hidden ${isDark ? 'bg-white/5' : 'bg-gray-100'}`}>
          <motion.div animate={{ width: `${progress}%` }} transition={{ duration: 0.5 }}
            className="h-full rounded-full bg-blue-600" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Pipeline */}
          <div className={`${c.surface} border ${c.border} rounded-xl p-5`}>
            <div className={`text-sm font-medium mb-4 ${c.heading}`}>Pipeline</div>
            <div className="space-y-1">
              {PIPELINE_STEPS.map((s, i) => {
                const Icon = s.icon
                const done = i < step
                const active = i === step
                return (
                  <div key={i} className={`flex items-center gap-3 p-2.5 rounded-lg transition-all ${active ? isDark ? 'bg-blue-600/10 border border-blue-500/20' : 'bg-blue-50 border border-blue-100' : ''}`}>
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition-all ${
                      done ? 'bg-emerald-500/15 border border-emerald-500/30' :
                      active ? 'bg-blue-500/15 border border-blue-500/30' :
                      isDark ? 'bg-white/5 border border-white/10' : 'bg-gray-100 border border-gray-200'
                    }`}>
                      {done ? <CheckCircle2 className="w-3 h-3 text-emerald-400" /> :
                       active ? <Loader2 className="w-3 h-3 text-blue-400 animate-spin" /> :
                       <Icon className={`w-3 h-3 ${c.muted}`} />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className={`text-xs font-medium ${done || active ? isDark ? 'text-white/80' : 'text-gray-800' : c.muted}`}>{s.label}</div>
                      {active && <div className={`text-[10px] ${c.muted} truncate`}>{s.desc}</div>}
                    </div>
                    {i > 0 && i < step && (
                      <div className="flex items-center gap-0.5">
                        {[...Array(5)].map((_, j) => (
                          <div key={j} className="w-0.5 h-3 rounded-full bg-emerald-500/30" style={{ height: `${8 + Math.random() * 8}px` }} />
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Terminal */}
          <div className={`${c.terminal} border ${c.border} rounded-xl p-5 overflow-hidden`}>
            <div className="flex items-center gap-1.5 mb-3">
              <div className="w-2.5 h-2.5 rounded-full bg-red-400/60" />
              <div className="w-2.5 h-2.5 rounded-full bg-amber-400/60" />
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-400/60" />
              <span className="text-[10px] text-white/20 ml-2 font-mono">indexing.log</span>
            </div>
            <div className="space-y-1 overflow-y-auto max-h-[340px]">
              {logs.map((log, i) => (
                <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.2 }}>
                  <span className={`text-[11px] font-mono block leading-relaxed ${
                    log.startsWith('✓') ? 'text-emerald-400' :
                    log.startsWith('$') ? 'text-blue-400' :
                    'text-white/40'
                  }`}>{log}</span>
                </motion.div>
              ))}
              {step < PIPELINE_STEPS.length - 1 && (
                <span className="text-[11px] font-mono text-white/20 animate-pulse">█</span>
              )}
            </div>
          </div>
        </div>

        {step >= PIPELINE_STEPS.length - 1 && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className={`mt-4 ${c.surface} border border-emerald-500/20 rounded-xl p-5 flex items-center justify-between`}>
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <div>
                <div className={`text-sm font-medium ${c.heading}`}>Repository indexed successfully</div>
                <div className={`text-xs ${c.muted}`}>1,203 files · 48,241 embeddings · 42.3s</div>
              </div>
            </div>
            <button onClick={() => setPage('overview')} className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-md transition-colors">
              View Overview
              <ArrowRight className="w-4 h-4" />
            </button>
          </motion.div>
        )}
      </div>
    </div>
  )
}

// ── Page: Overview ─────────────────────────────────────────────────────────

const TAG_ICONS: Record<string, typeof Package> = {
  config: Package, auth: Shield, routes: Server, database: Database,
  entry: Layers, ci: Server, env: Key,
}

function OverviewPage({ setPage, isDark, setIsDark }: { setPage: (p: Page) => void; isDark: boolean; setIsDark: (v: boolean) => void }) {
  const { repoId } = useAppState()
  const [repo, setRepo] = useState<RepoCard>({ ...REPOS[2], status: 'ready' })
  const [overview, setOverview] = useState<OverviewData | null>(null)
  const [arch, setArch] = useState<string | null>(null)
  const [impFiles, setImpFiles] = useState<{ path: string; tags: string[] }[] | null>(null)
  const [graph, setGraph] = useState<GraphData | null>(null)

  useEffect(() => {
    if (!repoId) return
    let active = true
    ;(async () => {
      try {
        const [r, ov] = await Promise.all([Repos.get(repoId), Repos.overview(repoId)])
        if (!active) return
        setRepo(r)
        setOverview(ov)
      } catch { /* keep mock */ }
      try {
        const a = await Repos.architecture(repoId)
        if (active) setArch(a.summary)
      } catch { /* keep mock */ }
      try {
        const f = await Repos.importantFiles(repoId)
        if (active) setImpFiles(f)
      } catch { /* keep mock */ }
      try {
        const g = await Repos.graph(repoId)
        if (active && g.nodes.length) setGraph(g)
      } catch { /* keep mock */ }
    })()
    return () => { active = false }
  }, [repoId])

  // Build a compact mini-graph from the real dependency graph: the highest-degree
  // nodes laid out in up to 4 columns. Falls back to a representative static sketch.
  const mini = (() => {
    if (!graph) return null
    const degree: Record<string, number> = {}
    for (const [a, b] of graph.edges) {
      degree[a] = (degree[a] ?? 0) + 1
      degree[b] = (degree[b] ?? 0) + 1
    }
    const top = [...graph.nodes]
      .sort((a, b) => (degree[b.id] ?? 0) - (degree[a.id] ?? 0))
      .slice(0, 8)
    if (!top.length) return null
    const ids = new Set(top.map(n => n.id))
    const cols = Math.min(4, top.length)
    const colW = 500 / (cols + 1)
    const byCol: string[][] = Array.from({ length: cols }, () => [])
    top.forEach((n, i) => byCol[i % cols].push(n.id))
    const pos: Record<string, { x: number; y: number; n: GraphNode }> = {}
    byCol.forEach((colIds, ci) => {
      const gap = 120 / (colIds.length + 1)
      colIds.forEach((id, ri) => {
        const n = top.find(t => t.id === id)!
        pos[id] = { x: colW * (ci + 1), y: gap * (ri + 1), n }
      })
    })
    const links = graph.edges.filter(([a, b]) => ids.has(a) && ids.has(b))
    return { pos, links, nodes: top }
  })()

  const mockImportantFiles = [
    { name: 'package.json', path: '/', desc: 'Dependencies and scripts', icon: Package },
    { name: '.env.example', path: '/', desc: 'Environment variables', icon: Key },
    { name: 'docker-compose.yml', path: '/', desc: 'Container configuration', icon: Server },
    { name: 'auth.service.ts', path: 'src/auth/', desc: 'Authentication logic', icon: Shield },
    { name: 'app.module.ts', path: 'src/', desc: 'Root application module', icon: Layers },
    { name: 'prisma/schema.prisma', path: 'prisma/', desc: 'Database schema', icon: Database },
  ]
  const importantFiles = impFiles
    ? impFiles.map(f => {
        const name = f.path.split('/').pop() || f.path
        const dir = f.path.includes('/') ? f.path.slice(0, f.path.lastIndexOf('/') + 1) : '/'
        return { name, path: dir, desc: f.tags.join(', '), icon: TAG_ICONS[f.tags[0]] || FileCode }
      })
    : mockImportantFiles

  // Derive the tech stack from real repo data, enriched by the overview when it
  // loads. No hardcoded product names — fall back to the repo card's own fields.
  const techStack = [
    { label: 'Project', value: repo.name },
    { label: 'Framework', value: overview?.framework || repo.framework || '—' },
    { label: 'Language', value: repo.language || '—' },
    { label: 'Files', value: overview ? String(overview.file_count) : String(repo.files ?? '—') },
    { label: 'Size', value: overview?.size || repo.size || '—' },
    { label: 'Health', value: `${overview?.health ?? repo.health}%` },
  ]

  const c = isDark ? {
    bg: 'bg-[#242C4D]', surface: 'bg-[#2D355C]', border: 'border-white/[0.06]',
    text: 'text-white/80', muted: 'text-white/35', heading: 'text-white'
  } : {
    bg: 'bg-[#F8F9FC]', surface: 'bg-white', border: 'border-gray-100',
    text: 'text-gray-700', muted: 'text-gray-400', heading: 'text-gray-900'
  }

  return (
    <div className={`flex-1 overflow-y-auto ${c.bg}`}>
      <TopBar title="Overview" isDark={isDark} setIsDark={setIsDark} setPage={setPage}
        breadcrumbs={[{ label: 'Dashboard', page: 'dashboard' }, { label: 'CodeAtreus' }, { label: 'Overview' }]} />
      <div className="p-6 max-w-6xl">
        {/* Header */}
        <div className={`${c.surface} border ${c.border} rounded-xl p-6 mb-4 flex items-start justify-between`}>
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0" style={{ background: repo.color + '18', border: `1px solid ${repo.color}30` }}>
              <GitBranch className="w-5 h-5" style={{ color: repo.color }} />
            </div>
            <div>
              <h1 className={`font-serif text-2xl mb-1 ${c.heading}`}>{repo.name}</h1>
              <p className={`text-sm mb-3 ${c.muted}`}>{repo.description}</p>
              <div className="flex items-center gap-3">
                <Badge color="blue">{repo.language}</Badge>
                <Badge color="purple">{repo.framework}</Badge>
                <div className="flex items-center gap-1">
                  <Star className="w-3 h-3 text-amber-400" />
                  <span className={`text-xs font-mono ${c.muted}`}>{repo.stars.toLocaleString()}</span>
                </div>
                <div className="flex items-center gap-1">
                  <GitFork className={`w-3 h-3 ${c.muted}`} />
                  <span className={`text-xs font-mono ${c.muted}`}>342</span>
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setPage('chat')} className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-md transition-colors">
              <MessageSquare className="w-3.5 h-3.5" />
              Ask AI
            </button>
            <button className={`p-2 rounded-md border transition-colors ${isDark ? 'border-white/10 text-white/40 hover:bg-white/5' : 'border-gray-200 text-gray-400 hover:bg-gray-50'}`}>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {/* Tech stack */}
          <div className={`${c.surface} border ${c.border} rounded-xl p-5`}>
            <div className={`text-sm font-medium mb-4 ${c.heading}`}>Tech Stack</div>
            <div className="space-y-2.5">
              {techStack.map(({ label, value }) => (
                <div key={label} className="flex items-center justify-between">
                  <span className={`text-xs ${c.muted}`}>{label}</span>
                  <span className={`text-xs font-mono font-medium ${c.text}`}>{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Architecture summary */}
          <div className={`col-span-2 ${c.surface} border ${c.border} rounded-xl p-5`}>
            <div className={`text-sm font-medium mb-3 ${c.heading}`}>Architecture Overview</div>
            {arch ? (
              <div className={`text-xs leading-relaxed mb-4 whitespace-pre-line ${c.text}`}>{arch}</div>
            ) : (
            <div className={`flex items-center gap-2 text-xs leading-relaxed mb-4 ${c.muted}`}>
              <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
              Generating architecture summary for <span className="font-mono">{repo.name}</span>…
            </div>
            )}
            {/* Mini graph */}
            <div className={`rounded-lg border p-3 ${isDark ? 'border-white/[0.06] bg-white/3' : 'border-gray-100 bg-gray-50'}`} onClick={() => setPage('graph')} style={{ cursor: 'pointer' }}>
              <svg viewBox="0 0 500 120" width="100%">
                {mini ? (
                  <>
                    {mini.links.map(([a, b], i) => {
                      const pa = mini.pos[a]; const pb = mini.pos[b]
                      if (!pa || !pb) return null
                      return <line key={i} x1={pa.x} y1={pa.y} x2={pb.x} y2={pb.y} stroke={isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'} strokeWidth="1" />
                    })}
                    {mini.nodes.map(n => {
                      const p = mini.pos[n.id]
                      const col = (graph!.colors[n.type]) || '#6474a8'
                      const label = n.label.length > 10 ? n.label.slice(0, 9) + '…' : n.label
                      return (
                        <g key={n.id}>
                          <circle cx={p.x} cy={p.y} r="16" fill={col + '15'} stroke={col + '50'} strokeWidth="1" />
                          <text x={p.x} y={p.y + 1} textAnchor="middle" dominantBaseline="middle" fill={col} fontSize="7" fontWeight="600" fontFamily="JetBrains Mono, monospace">{label}</text>
                        </g>
                      )
                    })}
                  </>
                ) : (
                  <>
                    {[['fe', 'gw'], ['gw', 'ac'], ['gw', 'pc'], ['ac', 'as'], ['pc', 'ps'], ['as', 'ur'], ['ur', 'pg']].map(([a, b], i) => {
                      const nodes: Record<string, [number, number]> = { fe: [50, 60], gw: [140, 60], ac: [230, 30], pc: [230, 90], as: [320, 30], ps: [320, 90], ur: [410, 30], pg: [470, 60] }
                      const [x1, y1] = nodes[a] || [0, 0]; const [x2, y2] = nodes[b] || [0, 0]
                      return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'} strokeWidth="1" />
                    })}
                    {[{ id: 'fe', x: 50, y: 60, l: 'Frontend', c: '#3b82f6' }, { id: 'gw', x: 140, y: 60, l: 'API', c: '#8b5cf6' }, { id: 'ac', x: 230, y: 30, l: 'Auth', c: '#06b6d4' }, { id: 'pc', x: 230, y: 90, l: 'Products', c: '#10b981' }, { id: 'as', x: 320, y: 30, l: 'Service', c: '#10b981' }, { id: 'ps', x: 320, y: 90, l: 'Service', c: '#10b981' }, { id: 'ur', x: 410, y: 30, l: 'Repo', c: '#f59e0b' }, { id: 'pg', x: 470, y: 60, l: 'PG', c: '#ef4444' }].map(n => (
                      <g key={n.id}>
                        <circle cx={n.x} cy={n.y} r="16" fill={n.c + '15'} stroke={n.c + '50'} strokeWidth="1" />
                        <text x={n.x} y={n.y + 1} textAnchor="middle" dominantBaseline="middle" fill={n.c} fontSize="7" fontWeight="600" fontFamily="JetBrains Mono, monospace">{n.l}</text>
                      </g>
                    ))}
                  </>
                )}
              </svg>
              <div className={`text-[10px] text-center mt-1 ${c.muted}`}>Click to explore full dependency graph →</div>
            </div>
          </div>
        </div>

        {/* Important files */}
        <div className={`mt-4 ${c.surface} border ${c.border} rounded-xl p-5`}>
          <div className={`text-sm font-medium mb-4 ${c.heading}`}>Key Files</div>
          <div className="grid grid-cols-3 gap-2">
            {importantFiles.map(({ name, path, desc, icon: Icon }) => (
              <div key={name} className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${isDark ? 'border-white/[0.06] hover:border-white/10 hover:bg-white/3' : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50'}`}>
                <Icon className={`w-4 h-4 shrink-0 ${c.muted}`} />
                <div className="min-w-0">
                  <div className={`text-xs font-mono font-medium truncate ${c.text}`}>{name}</div>
                  <div className={`text-[10px] truncate ${c.muted}`}>{path}{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick actions */}
        <div className="mt-4 grid grid-cols-4 gap-3">
          {[
            { label: 'AI Chat', icon: MessageSquare, page: 'chat' as Page, color: 'text-blue-400' },
            { label: 'Dependency Graph', icon: Network, page: 'graph' as Page, color: 'text-purple-400' },
            { label: 'Flow Visualizer', icon: Workflow, page: 'flow' as Page, color: 'text-cyan-400' },
            { label: 'Learning Roadmap', icon: Map, page: 'roadmap' as Page, color: 'text-emerald-400' },
          ].map(({ label, icon: Icon, page, color }) => (
            <button key={label} onClick={() => setPage(page)}
              className={`flex items-center gap-3 p-4 rounded-xl border text-left transition-colors ${isDark ? 'border-white/[0.06] hover:border-white/10 bg-white/3 hover:bg-white/5' : 'border-gray-100 hover:border-gray-200 bg-white'}`}>
              <Icon className={`w-4 h-4 shrink-0 ${color}`} />
              <span className={`text-sm font-medium ${c.text}`}>{label}</span>
              <ArrowRight className={`w-3.5 h-3.5 ml-auto ${c.muted}`} />
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Page: Chat ─────────────────────────────────────────────────────────────

function ChatPage({ isDark, setIsDark, setPage }: { isDark: boolean; setIsDark: (v: boolean) => void; setPage: (p: Page) => void }) {
  const { repoId } = useAppState()
  const [messages, setMessages] = useState<{ role: string; content: string; files?: string[] }[]>(CHAT_MESSAGES)
  const [input, setInput] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<string[]>([])
  const [sending, setSending] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load prior conversation for this repo, if any.
  useEffect(() => {
    if (!repoId) return
    let active = true
    Repos.chatHistory(repoId)
      .then(h => { if (active && h.length) setMessages(h.map(m => ({ role: m.role, content: m.content, files: m.files }))) })
      .catch(() => { /* keep seed */ })
    return () => { active = false }
  }, [repoId])

  const send = async () => {
    if (!input.trim() || sending) return
    const q = input
    setMessages(m => [...m, { role: 'user', content: q, files: [] }])
    setInput('')

    if (!repoId) {
      // Offline demo fallback.
      setTimeout(() => {
        setMessages(m => [...m, { role: 'assistant', content: 'Analyzing your question across 1,203 files...\n\nBased on the codebase, here\'s what I found:\n\n```typescript\n// src/auth/auth.service.ts:42\nasync validateUser(email: string, password: string) {\n  const user = await this.userRepo.findByEmail(email);\n  return bcrypt.compare(password, user.passwordHash) ? user : null;\n}\n```\n\nThis function is called from `AuthController.login()` and is the core validation step.', files: ['src/auth/auth.service.ts'] }])
      }, 1000)
      return
    }

    setSending(true)
    // Append a placeholder assistant message we stream tokens into.
    const assistantIdx = messages.length + 1
    setMessages(m => [...m, { role: 'assistant', content: '', files: [] }])
    const patchAssistant = (fn: (prev: { role: string; content: string; files?: string[] }) => { role: string; content: string; files?: string[] }) =>
      setMessages(m => m.map((msg, i) => (i === assistantIdx ? fn(msg) : msg)))

    try {
      let streamed = false
      await chatStream(repoId, q, {
        onToken: (text) => { streamed = true; patchAssistant(prev => ({ ...prev, content: prev.content + text })) },
        onSources: (files) => patchAssistant(prev => ({ ...prev, files })),
        onDone: (files) => patchAssistant(prev => ({ ...prev, files: files.length ? files : prev.files })),
      })
      if (!streamed) {
        // Nothing streamed (e.g. empty body) — fall back to a single request.
        const res = await Repos.chat(repoId, q)
        patchAssistant(() => ({ role: 'assistant', content: res.answer, files: res.files }))
      }
    } catch {
      // Streaming failed — try the non-streaming endpoint before giving up.
      try {
        const res = await Repos.chat(repoId, q)
        patchAssistant(() => ({ role: 'assistant', content: res.answer, files: res.files }))
      } catch {
        patchAssistant(() => ({ role: 'assistant', content: 'I could not reach the analysis backend. Please make sure the repository has finished indexing.', files: [] }))
      }
    } finally {
      setSending(false)
    }
  }

  const prompts = [
    'Explain the login flow', 'Where is authentication handled?',
    'Which files use PostgreSQL?', 'How does payment processing work?',
  ]

  const c = isDark ? {
    bg: 'bg-[#242C4D]', surface: 'bg-[#2D355C]', border: 'border-white/[0.06]',
    text: 'text-white/80', muted: 'text-white/35', heading: 'text-white',
    input: 'bg-white/5 border-white/10 text-white/80 placeholder-white/20',
    msg: 'bg-[#1a2040]'
  } : {
    bg: 'bg-[#F8F9FC]', surface: 'bg-white', border: 'border-gray-100',
    text: 'text-gray-700', muted: 'text-gray-400', heading: 'text-gray-900',
    input: 'bg-gray-50 border-gray-200 text-gray-800 placeholder-gray-300',
    msg: 'bg-gray-50'
  }

  return (
    <div className={`flex-1 flex flex-col ${c.bg}`} style={{ height: '100vh' }}>
      <TopBar title="AI Chat" isDark={isDark} setIsDark={setIsDark} setPage={setPage}
        breadcrumbs={[{ label: 'Dashboard', page: 'dashboard' }, { label: 'CodeAtreus' }, { label: 'AI Chat' }]} />
      <div className="flex-1 flex overflow-hidden">
        {/* Messages */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((msg, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
                {msg.role === 'user' ? (
                  <div className="flex justify-end">
                    <div className="max-w-lg px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm">
                      {msg.content}
                    </div>
                  </div>
                ) : (
                  <div className="flex gap-3">
                    <div className="w-7 h-7 rounded-full bg-blue-600/15 border border-blue-500/20 flex items-center justify-center shrink-0 mt-0.5">
                      <Zap className="w-3.5 h-3.5 text-blue-400" />
                    </div>
                    <div className="flex-1 max-w-2xl">
                      <div className={`text-xs font-medium mb-2 ${c.muted}`}>CodeAtreus AI</div>
                      <div className={`p-4 rounded-xl border text-sm leading-relaxed ${c.surface} ${c.border}`}>
                        <div className={`whitespace-pre-wrap font-sans ${c.text}`} style={{ fontFamily: 'inherit' }}>
                          {msg.content.split('```').map((part, j) => {
                            if (j % 2 === 1) {
                              const [lang, ...code] = part.split('\n')
                              return (
                                <pre key={j} className={`mt-2 mb-2 p-3 rounded-lg text-xs overflow-x-auto font-mono ${isDark ? 'bg-[#151a2e] text-emerald-300' : 'bg-gray-900 text-emerald-400'}`}>
                                  <code>{code.join('\n')}</code>
                                </pre>
                              )
                            }
                            return <span key={j}>{part.replace(/\*\*(.*?)\*\*/g, '$1')}</span>
                          })}
                        </div>
                        {msg.files && msg.files.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-inherit flex flex-wrap gap-1.5">
                            {msg.files.map(f => (
                              <span key={f} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono border ${isDark ? 'bg-white/5 border-white/10 text-white/50' : 'bg-gray-50 border-gray-200 text-gray-500'}`}>
                                <FileCode className="w-3 h-3" />
                                {f}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </motion.div>
            ))}
            <div ref={endRef} />
          </div>

          {/* Suggestions */}
          <div className={`px-6 pb-2 flex gap-2 flex-wrap`}>
            {prompts.map(p => (
              <button key={p} onClick={() => setInput(p)}
                className={`px-3 py-1.5 rounded-full text-xs border transition-colors ${isDark ? 'border-white/10 text-white/40 hover:text-white/70 hover:bg-white/5' : 'border-gray-200 text-gray-400 hover:text-gray-700 hover:bg-gray-50'}`}>
                {p}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className={`p-4 border-t ${c.border}`}>
            <div className={`flex gap-2 items-end rounded-xl border p-3 ${c.input}`}>
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
                placeholder="Ask anything about this codebase..."
                rows={1}
                className="flex-1 bg-transparent text-sm outline-none resize-none leading-relaxed"
                style={{ fontFamily: 'inherit' }}
              />
              <button onClick={send} className="p-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors shrink-0">
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className={`text-[10px] text-center mt-2 ${c.muted}`}>Press Enter to send · Shift+Enter for new line</div>
          </div>
        </div>

        {/* File panel */}
        <div className={`w-56 border-l ${c.border} ${c.surface} flex flex-col overflow-hidden`}>
          <div className={`px-4 py-3 border-b ${c.border}`}>
            <div className={`text-xs font-medium ${c.heading}`}>Referenced Files</div>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
            {['src/auth/auth.service.ts', 'src/auth/jwt.service.ts', 'src/auth/auth.controller.ts', 'src/users/user.entity.ts', 'src/database/database.module.ts', 'src/payments/stripe.service.ts'].map(f => {
              const parts = f.split('/')
              return (
                <div key={f} className={`p-2.5 rounded-lg border cursor-pointer transition-colors ${isDark ? 'border-white/[0.06] hover:border-white/10 hover:bg-white/3' : 'border-gray-100 hover:bg-gray-50'}`}>
                  <div className={`text-[11px] font-mono font-medium ${c.text} truncate`}>{parts[parts.length - 1]}</div>
                  <div className={`text-[10px] ${c.muted} truncate`}>{parts.slice(0, -1).join('/')}/</div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Page: Dependency Graph ─────────────────────────────────────────────────

function GraphPage({ isDark, setIsDark, setPage }: { isDark: boolean; setIsDark: (v: boolean) => void; setPage: (p: Page) => void }) {
  const { repoId } = useAppState()
  const [selected, setSelected] = useState<GraphNode | null>(null)
  const [nodes, setNodes] = useState<GraphNode[]>(GRAPH_NODES)
  const [edges, setEdges] = useState<string[][]>(GRAPH_EDGES)
  const [colors, setColors] = useState<Record<string, string>>(NODE_COLORS)

  useEffect(() => {
    if (!repoId) return
    let active = true
    Repos.graph(repoId)
      .then((g: GraphData) => {
        if (!active || !g.nodes.length) return
        setNodes(g.nodes)
        setEdges(g.edges)
        setColors(g.colors)
      })
      .catch(() => { /* keep mock graph */ })
    return () => { active = false }
  }, [repoId])

  const nodeDetails: Record<string, { responsibilities: string[]; files: string[]; ai: string }> = {
    fe: { responsibilities: ['SSR rendering', 'Route handling', 'API proxy'], files: ['src/pages/', 'src/components/', 'src/app/'], ai: 'Next.js 14 frontend with App Router. Handles all user-facing rendering with SSR. Proxies API calls to the FastAPI backend.' },
    gw: { responsibilities: ['Request routing', 'Rate limiting', 'Auth middleware'], files: ['src/middleware/', 'src/guards/'], ai: 'API Gateway layer built with NestJS. Handles authentication verification, rate limiting, and request routing to appropriate controllers.' },
    pg: { responsibilities: ['User data', 'Product catalog', 'Order records'], files: ['prisma/schema.prisma', 'src/database/'], ai: 'PostgreSQL 15 with pgvector extension for semantic search. Managed via Prisma ORM with 23 migrations.' },
  }

  const c = isDark ? {
    bg: 'bg-[#242C4D]', surface: 'bg-[#2D355C]', border: 'border-white/[0.06]',
    text: 'text-white/80', muted: 'text-white/35', heading: 'text-white'
  } : {
    bg: 'bg-[#F8F9FC]', surface: 'bg-white', border: 'border-gray-100',
    text: 'text-gray-700', muted: 'text-gray-400', heading: 'text-gray-900'
  }

  // Size the canvas to the actual node extents (nodes are 120x44) so the graph
  // never overflows or overlaps regardless of how the layout was persisted.
  const NODE_W = 120, NODE_H = 44, PAD = 48
  const canvasW = Math.max(740, ...nodes.map(n => n.x + NODE_W)) + PAD
  const canvasH = Math.max(500, ...nodes.map(n => n.y + NODE_H)) + PAD

  return (
    <div className={`flex-1 flex flex-col ${c.bg}`} style={{ height: '100vh' }}>
      <TopBar title="Dependency Graph" isDark={isDark} setIsDark={setIsDark} setPage={setPage}
        breadcrumbs={[{ label: 'Dashboard', page: 'dashboard' }, { label: 'CodeAtreus' }, { label: 'Dependency Graph' }]} />
      <div className="flex-1 flex overflow-hidden">
        {/* Canvas */}
        <div className="flex-1 overflow-auto p-6">
          <div className={`rounded-xl border ${c.border} ${c.surface} relative`} style={{ minHeight: '500px', minWidth: '100%', width: canvasW, height: canvasH }}>
            <div className={`absolute top-4 left-4 flex items-center gap-3 z-10`}>
              {Object.entries(colors).map(([type, color]) => (
                <div key={type} className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full" style={{ background: color }} />
                  <span className={`text-[10px] capitalize ${c.muted}`}>{type}</span>
                </div>
              ))}
            </div>
            <svg width={canvasW} height={canvasH} viewBox={`0 0 ${canvasW} ${canvasH}`} style={{ minHeight: '500px' }}>
              {/* Edges */}
              {edges.map(([a, b], i) => {
                const na = nodes.find(n => n.id === a)
                const nb = nodes.find(n => n.id === b)
                if (!na || !nb) return null
                return (
                  <line key={i}
                    x1={na.x + 60} y1={na.y + 22} x2={nb.x + 60} y2={nb.y + 22}
                    stroke={isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.08)'}
                    strokeWidth="1.5"
                  />
                )
              })}
              {/* Nodes */}
              {nodes.map(node => {
                const color = colors[node.type] || '#64748b'
                const isSelected = selected?.id === node.id
                return (
                  <g key={node.id} className="cursor-pointer" onClick={() => setSelected(isSelected ? null : node)}>
                    <rect x={node.x} y={node.y} width={120} height={44} rx={8}
                      fill={isSelected ? color + '25' : color + '12'}
                      stroke={isSelected ? color : color + '40'}
                      strokeWidth={isSelected ? 1.5 : 1}
                    />
                    <circle cx={node.x + 14} cy={node.y + 22} r="4" fill={color} />
                    <text x={node.x + 26} y={node.y + 18} fill={color} fontSize="9" fontWeight="600" fontFamily="JetBrains Mono, monospace">{node.label.split(' ')[0]}</text>
                    <text x={node.x + 26} y={node.y + 30} fill={isDark ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.35)'} fontSize="8" fontFamily="Inter, sans-serif">{node.type}</text>
                  </g>
                )
              })}
            </svg>
          </div>
        </div>

        {/* Side panel */}
        <AnimatePresence>
          {selected && (
            <motion.div initial={{ x: 300, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 300, opacity: 0 }} transition={{ duration: 0.2 }}
              className={`w-72 border-l ${c.border} ${c.surface} flex flex-col overflow-y-auto`}>
              <div className={`flex items-center justify-between px-5 py-4 border-b ${c.border}`}>
                <div>
                  <div className={`text-sm font-medium ${c.heading}`}>{selected.label}</div>
                  <Badge color="blue">{selected.type}</Badge>
                </div>
                <button onClick={() => setSelected(null)} className={`p-1.5 rounded ${c.muted} hover:text-white/70`}>
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
              {nodeDetails[selected.id] ? (
                <div className="p-5 space-y-4">
                  <div>
                    <div className={`text-xs font-medium mb-2 ${c.heading}`}>Responsibilities</div>
                    <ul className="space-y-1">
                      {nodeDetails[selected.id].responsibilities.map(r => (
                        <li key={r} className="flex items-center gap-2">
                          <div className="w-1 h-1 rounded-full bg-blue-400 shrink-0" />
                          <span className={`text-xs ${c.text}`}>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <div className={`text-xs font-medium mb-2 ${c.heading}`}>Key Files</div>
                    {nodeDetails[selected.id].files.map(f => (
                      <div key={f} className={`text-[11px] font-mono px-2 py-1 rounded ${isDark ? 'bg-white/5 text-white/50' : 'bg-gray-50 text-gray-500'} mb-1`}>{f}</div>
                    ))}
                  </div>
                  <div>
                    <div className={`text-xs font-medium mb-2 ${c.heading}`}>AI Explanation</div>
                    <p className={`text-xs leading-relaxed ${c.text}`}>{nodeDetails[selected.id].ai}</p>
                  </div>
                </div>
              ) : (
                <div className="p-5">
                  <div className={`text-xs leading-relaxed ${c.text}`}>
                    This node handles requests for the <strong>{selected.label}</strong> layer. Click "Ask AI" to get a detailed explanation.
                  </div>
                  <button onClick={() => setPage('chat')} className="mt-3 flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-md transition-colors">
                    <MessageSquare className="w-3 h-3" />
                    Ask AI about this node
                  </button>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

// ── Page: Flow Visualizer ──────────────────────────────────────────────────

function FlowPage({ isDark, setIsDark, setPage }: { isDark: boolean; setIsDark: (v: boolean) => void; setPage: (p: Page) => void }) {
  const { repoId } = useAppState()
  const [activeStep, setActiveStep] = useState<number | null>(null)
  const [playing, setPlaying] = useState(false)
  const [currentPlay, setCurrentPlay] = useState(-1)
  const [steps, setSteps] = useState<FlowStep[]>(FLOW_STEPS)

  const endpoints = ['POST /api/auth/login', 'GET /api/products', 'POST /api/orders', 'POST /api/payments/intent']
  const [endpoint, setEndpoint] = useState(0)

  useEffect(() => {
    if (!repoId) return
    let active = true
    Repos.flow(repoId, endpoints[endpoint])
      .then(r => { if (active && r.steps.length) setSteps(r.steps) })
      .catch(() => { /* keep mock flow */ })
    return () => { active = false }
  }, [repoId, endpoint])

  useEffect(() => {
    if (!playing) return
    setCurrentPlay(0)
    const interval = setInterval(() => {
      setCurrentPlay(p => {
        if (p >= steps.length - 1) { setPlaying(false); clearInterval(interval); return -1 }
        return p + 1
      })
    }, 600)
    return () => clearInterval(interval)
  }, [playing, steps.length])

  const c = isDark ? {
    bg: 'bg-[#242C4D]', surface: 'bg-[#2D355C]', border: 'border-white/[0.06]',
    text: 'text-white/80', muted: 'text-white/35', heading: 'text-white'
  } : {
    bg: 'bg-[#F8F9FC]', surface: 'bg-white', border: 'border-gray-100',
    text: 'text-gray-700', muted: 'text-gray-400', heading: 'text-gray-900'
  }

  const stepColors: Record<string, string> = { request: '#3b82f6', controller: '#06b6d4', service: '#10b981', repo: '#f59e0b', db: '#ef4444', response: '#8b5cf6' }

  const active = activeStep !== null ? activeStep : currentPlay

  return (
    <div className={`flex-1 flex flex-col overflow-hidden ${c.bg}`} style={{ height: '100vh' }}>
      <TopBar title="Flow Visualizer" isDark={isDark} setIsDark={setIsDark} setPage={setPage}
        breadcrumbs={[{ label: 'Dashboard', page: 'dashboard' }, { label: 'CodeAtreus' }, { label: 'Flow Visualizer' }]} />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className={`font-serif text-2xl mb-1 ${c.heading}`}>Backend Flow Visualizer</h1>
              <p className={`text-sm ${c.muted}`}>Trace request lifecycle through your backend architecture.</p>
            </div>
            <div className="flex items-center gap-2">
              <select value={endpoint} onChange={e => setEndpoint(Number(e.target.value))}
                className={`text-xs px-3 py-2 rounded-md border outline-none font-mono ${isDark ? 'bg-white/5 border-white/10 text-white/70' : 'bg-white border-gray-200 text-gray-700'}`}>
                {endpoints.map((e, i) => <option key={i} value={i}>{e}</option>)}
              </select>
              <button onClick={() => { setPlaying(true); setActiveStep(null) }}
                className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-md transition-colors">
                <Play className="w-3.5 h-3.5" />
                Animate
              </button>
            </div>
          </div>

          <div className="grid grid-cols-5 gap-4">
            {/* Flow */}
            <div className="col-span-3">
              <div className={`${c.surface} border ${c.border} rounded-xl p-6`}>
                <div className="relative">
                  {steps.map((step, i) => {
                    const color = stepColors[step.type]
                    const isActive = active === i
                    const isPast = active !== null && i < active
                    return (
                      <div key={i} className="relative">
                        <motion.div
                          animate={{ scale: isActive ? 1.02 : 1, opacity: (active !== null && !isActive && !isPast) ? 0.5 : 1 }}
                          className={`flex items-center gap-4 p-4 rounded-xl border cursor-pointer mb-1 transition-all ${
                            isActive ? (isDark ? 'border-blue-500/30 bg-blue-500/10' : 'border-blue-200 bg-blue-50') :
                            isPast ? (isDark ? 'border-white/5 bg-white/3' : 'border-gray-100 bg-gray-50') :
                            isDark ? 'border-white/[0.06] hover:border-white/10' : 'border-gray-100 hover:border-gray-200'
                          }`}
                          onClick={() => setActiveStep(isActive ? null : i)}
                        >
                          <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: color + '15', border: `1px solid ${color}30` }}>
                            {isPast ? <CheckCircle2 className="w-4 h-4" style={{ color }} /> :
                             isActive ? <Radio className="w-4 h-4 animate-pulse" style={{ color }} /> :
                             <div className="w-2 h-2 rounded-full" style={{ background: color }} />}
                          </div>
                          <div className="flex-1">
                            <div className={`text-sm font-mono font-medium ${isActive ? 'text-blue-400' : c.text}`}>{step.label}</div>
                            {isActive && <div className={`text-xs mt-0.5 ${c.muted}`}>{step.detail}</div>}
                          </div>
                          <div className={`text-[10px] font-mono px-2 py-0.5 rounded border capitalize ${isDark ? 'border-white/10 text-white/30' : 'border-gray-100 text-gray-400'}`}>{step.type}</div>
                        </motion.div>
                        {i < steps.length - 1 && (
                          <div className={`ml-8 w-px h-4 ${isPast || isActive ? '' : 'opacity-30'}`} style={{ background: color + '50' }} />
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>

            {/* Right panel */}
            <div className="col-span-2 space-y-4">
              <div className={`${c.surface} border ${c.border} rounded-xl p-5`}>
                <div className={`text-sm font-medium mb-3 ${c.heading}`}>Execution Details</div>
                {active !== null && active >= 0 && active < steps.length ? (
                  <div className="space-y-3">
                    <div>
                      <div className={`text-[10px] uppercase tracking-wider mb-1 ${c.muted}`}>Step</div>
                      <div className={`text-sm font-mono ${c.text}`}>{steps[active].label}</div>
                    </div>
                    <div>
                      <div className={`text-[10px] uppercase tracking-wider mb-1 ${c.muted}`}>Type</div>
                      <Badge color="blue">{steps[active].type}</Badge>
                    </div>
                    <div>
                      <div className={`text-[10px] uppercase tracking-wider mb-1 ${c.muted}`}>Detail</div>
                      <div className={`text-xs leading-relaxed ${c.text}`}>{steps[active].detail}</div>
                    </div>
                    <div>
                      <div className={`text-[10px] uppercase tracking-wider mb-1 ${c.muted}`}>Avg Latency</div>
                      <div className={`text-xs font-mono ${c.text}`}>{[2, 8, 14, 6, 18, 3, 1][active]}ms</div>
                    </div>
                  </div>
                ) : (
                  <p className={`text-xs ${c.muted}`}>Click a step or press Animate to trace the request lifecycle.</p>
                )}
              </div>

              <div className={`${c.surface} border ${c.border} rounded-xl p-5`}>
                <div className={`text-sm font-medium mb-3 ${c.heading}`}>Latency Breakdown</div>
                <div className="space-y-2">
                  {steps.map((step, i) => {
                    const lat = [2, 8, 14, 6, 18, 3, 1][i]
                    const color = stepColors[step.type]
                    return (
                      <div key={i} className="flex items-center gap-2">
                        <span className={`text-[10px] font-mono w-24 truncate ${c.muted}`}>{step.label.split(' ')[0]}</span>
                        <div className={`flex-1 h-1.5 rounded-full ${isDark ? 'bg-white/5' : 'bg-gray-100'}`}>
                          <div className="h-full rounded-full" style={{ width: `${(lat / 18) * 100}%`, background: color }} />
                        </div>
                        <span className={`text-[10px] font-mono w-8 text-right ${c.muted}`}>{lat}ms</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Page: Sequence Diagrams ────────────────────────────────────────────────

function SequencePage({ isDark, setIsDark, setPage }: { isDark: boolean; setIsDark: (v: boolean) => void; setPage: (p: Page) => void }) {
  const { repoId } = useAppState()
  const [tab, setTab] = useState<'mermaid' | 'plantuml'>('mermaid')
  const [copied, setCopied] = useState(false)

  const [diagrams, setDiagrams] = useState({
    mermaid: `sequenceDiagram
  participant U as User
  participant FE as Frontend
  participant AC as AuthController
  participant AS as AuthService
  participant UR as UserRepository
  participant DB as PostgreSQL
  participant RS as Redis

  U->>FE: Submit login form
  FE->>AC: POST /api/auth/login
  AC->>AC: Validate request body
  AC->>AS: validateUser(email, password)
  AS->>UR: findByEmail(email)
  UR->>DB: SELECT * FROM users WHERE email=$1
  DB-->>UR: User record
  UR-->>AS: User entity
  AS->>AS: bcrypt.compare(password, hash)
  AS->>AS: Generate JWT tokens
  AS->>RS: Store refresh token (7d TTL)
  RS-->>AS: OK
  AS-->>AC: { accessToken, refreshToken }
  AC-->>FE: 200 OK + tokens
  FE-->>U: Redirect to dashboard`,
    plantuml: `@startuml
actor User
participant Frontend
participant AuthController
participant AuthService
participant UserRepository
database PostgreSQL
database Redis

User -> Frontend: Submit login form
Frontend -> AuthController: POST /api/auth/login
AuthController -> AuthController: Validate body
AuthController -> AuthService: validateUser()
AuthService -> UserRepository: findByEmail()
UserRepository -> PostgreSQL: SELECT user
PostgreSQL --> UserRepository: User row
UserRepository --> AuthService: User entity
AuthService -> AuthService: verify bcrypt
AuthService -> AuthService: sign JWT
AuthService -> Redis: store refresh token
Redis --> AuthService: OK
AuthService --> AuthController: tokens
AuthController --> Frontend: 200 OK
Frontend --> User: dashboard redirect
@enduml`
  })

  useEffect(() => {
    if (!repoId) return
    let active = true
    Repos.sequence(repoId)
      .then((d: SequenceData) => { if (active && d.mermaid) setDiagrams({ mermaid: d.mermaid, plantuml: d.plantuml }) })
      .catch(() => { /* keep mock diagrams */ })
    return () => { active = false }
  }, [repoId])

  const copy = () => {
    navigator.clipboard?.writeText(diagrams[tab]).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const actors = ['User', 'Frontend', 'AuthController', 'AuthService', 'UserRepository', 'PostgreSQL', 'Redis']
  const messages = [
    { from: 0, to: 1, msg: 'Submit login form', ret: false },
    { from: 1, to: 2, msg: 'POST /api/auth/login', ret: false },
    { from: 2, to: 3, msg: 'validateUser(email, pwd)', ret: false },
    { from: 3, to: 4, msg: 'findByEmail(email)', ret: false },
    { from: 4, to: 5, msg: 'SELECT * FROM users', ret: false },
    { from: 5, to: 4, msg: 'User record', ret: true },
    { from: 4, to: 3, msg: 'User entity', ret: true },
    { from: 3, to: 6, msg: 'store refresh token', ret: false },
    { from: 6, to: 3, msg: 'OK', ret: true },
    { from: 3, to: 2, msg: '{ accessToken, refreshToken }', ret: true },
    { from: 2, to: 1, msg: '200 OK + tokens', ret: true },
    { from: 1, to: 0, msg: 'Redirect to dashboard', ret: true },
  ]

  const c = isDark ? {
    bg: 'bg-[#242C4D]', surface: 'bg-[#2D355C]', border: 'border-white/[0.06]',
    text: 'text-white/80', muted: 'text-white/35', heading: 'text-white',
    terminal: 'bg-[#151a2e]'
  } : {
    bg: 'bg-[#F8F9FC]', surface: 'bg-white', border: 'border-gray-100',
    text: 'text-gray-700', muted: 'text-gray-400', heading: 'text-gray-900',
    terminal: 'bg-gray-900'
  }

  const AW = 80; const gap = 90; const totalW = actors.length * gap

  return (
    <div className={`flex-1 overflow-y-auto ${c.bg}`}>
      <TopBar title="Sequence Diagrams" isDark={isDark} setIsDark={setIsDark} setPage={setPage}
        breadcrumbs={[{ label: 'Dashboard', page: 'dashboard' }, { label: 'CodeAtreus' }, { label: 'Sequence Diagrams' }]} />
      <div className="p-6 max-w-6xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className={`font-serif text-2xl mb-1 ${c.heading}`}>Sequence Diagrams</h1>
            <p className={`text-sm ${c.muted}`}>Auto-generated UML diagrams from repository analysis.</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={copy} className={`flex items-center gap-1.5 px-3 py-2 text-xs rounded-md border transition-colors ${isDark ? 'border-white/10 text-white/50 hover:bg-white/5' : 'border-gray-200 text-gray-500 hover:bg-gray-50'}`}>
              <Copy className="w-3 h-3" />
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button className={`flex items-center gap-1.5 px-3 py-2 text-xs rounded-md border transition-colors ${isDark ? 'border-white/10 text-white/50 hover:bg-white/5' : 'border-gray-200 text-gray-500 hover:bg-gray-50'}`}>
              <Download className="w-3 h-3" />
              Export SVG
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className={`flex gap-1 mb-4 p-1 rounded-lg border w-fit ${isDark ? 'border-white/[0.06] bg-white/3' : 'border-gray-200 bg-gray-50'}`}>
          {(['mermaid', 'plantuml'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-1.5 rounded-md text-xs font-medium transition-all ${tab === t ? isDark ? 'bg-white/10 text-white/80' : 'bg-white text-gray-800 shadow-sm' : c.muted}`}>
              {t === 'mermaid' ? 'Mermaid' : 'PlantUML'}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Preview */}
          <div className={`${c.surface} border ${c.border} rounded-xl p-5 overflow-x-auto`}>
            <div className={`text-xs font-medium mb-4 ${c.heading}`}>Rendered Preview</div>
            <svg width={totalW + 40} height={messages.length * 45 + 100} className="overflow-visible">
              {/* Actor headers */}
              {actors.map((actor, i) => (
                <g key={actor}>
                  <rect x={i * gap + 20} y={0} width={AW - 10} height={30} rx={6}
                    fill={isDark ? 'rgba(59,130,246,0.12)' : 'rgba(59,130,246,0.08)'}
                    stroke={isDark ? 'rgba(59,130,246,0.3)' : 'rgba(59,130,246,0.25)'}
                    strokeWidth="1" />
                  <text x={i * gap + 65} y={19} textAnchor="middle" fill={isDark ? 'rgba(255,255,255,0.7)' : '#374151'}
                    fontSize="8" fontWeight="600" fontFamily="JetBrains Mono, monospace">{actor.slice(0, 10)}</text>
                  <line x1={i * gap + 65} y1={30} x2={i * gap + 65} y2={messages.length * 45 + 60}
                    stroke={isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'} strokeWidth="1" strokeDasharray="3,3" />
                </g>
              ))}
              {/* Messages */}
              {messages.map((msg, i) => {
                const y = i * 45 + 65
                const x1 = msg.from * gap + 65; const x2 = msg.to * gap + 65
                const color = msg.ret ? (isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)') : (isDark ? 'rgba(59,130,246,0.5)' : 'rgba(59,130,246,0.6)')
                const dir = x2 > x1 ? 1 : -1
                return (
                  <g key={i}>
                    <line x1={x1} y1={y} x2={x2} y2={y} stroke={color} strokeWidth="1"
                      strokeDasharray={msg.ret ? '4,2' : 'none'} />
                    <polygon points={`${x2},${y} ${x2 - dir * 6},${y - 3} ${x2 - dir * 6},${y + 3}`} fill={color} />
                    <text x={(x1 + x2) / 2} y={y - 5} textAnchor="middle"
                      fill={isDark ? 'rgba(255,255,255,0.4)' : 'rgba(0,0,0,0.5)'} fontSize="7"
                      fontFamily="JetBrains Mono, monospace">{msg.msg.slice(0, 22)}</text>
                  </g>
                )
              })}
            </svg>
          </div>

          {/* Source */}
          <div className={`${c.terminal} border ${c.border} rounded-xl overflow-hidden`}>
            <div className={`flex items-center justify-between px-4 py-2.5 border-b ${isDark ? 'border-white/5' : 'border-gray-800'}`}>
              <span className="text-[11px] font-mono text-white/40">{tab === 'mermaid' ? 'login.mmd' : 'login.puml'}</span>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-red-400/40" />
                <div className="w-2 h-2 rounded-full bg-amber-400/40" />
                <div className="w-2 h-2 rounded-full bg-emerald-400/40" />
              </div>
            </div>
            <pre className="p-4 overflow-auto text-[10px] font-mono leading-relaxed text-emerald-300/80 max-h-[460px]">
              {diagrams[tab]}
            </pre>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Page: Roadmap ──────────────────────────────────────────────────────────

function RoadmapPage({ isDark, setIsDark, setPage }: { isDark: boolean; setIsDark: (v: boolean) => void; setPage: (p: Page) => void }) {
  const { repoId } = useAppState()
  const [selected, setSelected] = useState(0)
  const [days, setDays] = useState<RoadmapDay[]>(ROADMAP_DAYS)
  // Per-task completion, tracked client-side (keyed "dayIndex:taskIndex").
  const [checks, setChecks] = useState<Record<string, boolean>>({})

  useEffect(() => {
    if (!repoId) return
    let active = true
    Repos.roadmap(repoId)
      .then(r => { if (active && r.days.length) setDays(r.days) })
      .catch(() => { /* keep mock roadmap */ })
    return () => { active = false }
  }, [repoId])

  // Seed completion from each day's starting percentage whenever the plan loads.
  useEffect(() => {
    const seed: Record<string, boolean> = {}
    days.forEach((d, di) => {
      const doneCount = Math.round(d.tasks.length * (d.complete ?? 0) / 100)
      d.tasks.forEach((_, ti) => { seed[`${di}:${ti}`] = ti < doneCount })
    })
    setChecks(seed)
  }, [days])

  const isDone = (di: number, ti: number) => !!checks[`${di}:${ti}`]
  const toggleTask = (di: number, ti: number) =>
    setChecks(c => ({ ...c, [`${di}:${ti}`]: !c[`${di}:${ti}`] }))
  const dayPct = (di: number) => {
    const t = days[di]?.tasks ?? []
    if (!t.length) return 0
    const done = t.reduce((n, _, ti) => n + (isDone(di, ti) ? 1 : 0), 0)
    return Math.round((done / t.length) * 100)
  }
  const openReading = (title: string) =>
    window.open(`https://www.google.com/search?q=${encodeURIComponent(title)}`, '_blank', 'noopener,noreferrer')

  const c = isDark ? {
    bg: 'bg-[#242C4D]', surface: 'bg-[#2D355C]', border: 'border-white/[0.06]',
    text: 'text-white/80', muted: 'text-white/35', heading: 'text-white'
  } : {
    bg: 'bg-[#F8F9FC]', surface: 'bg-white', border: 'border-gray-100',
    text: 'text-gray-700', muted: 'text-gray-400', heading: 'text-gray-900'
  }

  const day = days[selected]

  return (
    <div className={`flex-1 overflow-y-auto ${c.bg}`}>
      <TopBar title="Learning Roadmap" isDark={isDark} setIsDark={setIsDark} setPage={setPage}
        breadcrumbs={[{ label: 'Dashboard', page: 'dashboard' }, { label: 'CodeAtreus' }, { label: 'Learning Roadmap' }]} />
      <div className="p-6 max-w-5xl">
        <div className="mb-6">
          <h1 className={`font-serif text-2xl mb-1 ${c.heading}`}>Your Learning Roadmap</h1>
          <p className={`text-sm ${c.muted}`}>Personalized onboarding plan — 5 days to full productivity.</p>
        </div>

        {/* Timeline */}
        <div className="flex gap-2 mb-6">
          {days.map((d, i) => (
            <button key={i} onClick={() => setSelected(i)}
              className={`flex-1 p-4 rounded-xl border text-left transition-all ${selected === i ?
                isDark ? 'border-blue-500/30 bg-blue-500/10' : 'border-blue-200 bg-blue-50'
                : isDark ? 'border-white/[0.06] bg-white/3 hover:border-white/10' : 'border-gray-100 bg-white hover:border-gray-200'
              }`}>
              <div className={`text-[10px] font-mono mb-1 ${selected === i ? 'text-blue-400' : c.muted}`}>Day {d.day}</div>
              <div className={`text-xs font-medium mb-2 ${selected === i ? isDark ? 'text-white' : 'text-gray-900' : c.text}`}>{d.title}</div>
              <div className={`h-1 rounded-full overflow-hidden ${isDark ? 'bg-white/5' : 'bg-gray-100'}`}>
                <div className="h-full rounded-full transition-all"
                  style={{ width: `${dayPct(i)}%`, background: dayPct(i) === 100 ? '#10b981' : dayPct(i) > 0 ? '#3b82f6' : '#4b5563' }} />
              </div>
              <div className={`text-[10px] mt-1 font-mono ${dayPct(i) === 100 ? 'text-emerald-400' : selected === i ? 'text-blue-400' : c.muted}`}>{dayPct(i)}%</div>
            </button>
          ))}
        </div>

        <div className="grid grid-cols-3 gap-4">
          {/* Tasks */}
          <div className={`col-span-2 ${c.surface} border ${c.border} rounded-xl p-5`}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className={`text-sm font-medium ${c.heading}`}>Day {day.day} — {day.title}</div>
                <div className={`text-xs ${c.muted}`}>{dayPct(selected)}% complete</div>
              </div>
              <Badge color={dayPct(selected) === 100 ? 'green' : dayPct(selected) > 0 ? 'blue' : 'slate'}>
                {dayPct(selected) === 100 ? 'Done' : dayPct(selected) > 0 ? 'In Progress' : 'Upcoming'}
              </Badge>
            </div>
            <div className="space-y-2">
              {day.tasks.map((task, i) => {
                const done = isDone(selected, i)
                return (
                  <button type="button" key={i} onClick={() => toggleTask(selected, i)}
                    className={`w-full text-left flex items-center gap-3 p-3 rounded-lg border transition-colors ${isDark ? 'border-white/[0.06] hover:bg-white/3' : 'border-gray-100 hover:bg-gray-50'}`}>
                    <div className={`w-5 h-5 rounded-full border flex items-center justify-center shrink-0 ${
                      done ? 'bg-emerald-500/15 border-emerald-500/30' : isDark ? 'border-white/10' : 'border-gray-200'
                    }`}>
                      {done && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                    </div>
                    <span className={`text-sm ${done ? c.muted + ' line-through' : c.text}`}>{task}</span>
                    {done && <span className="ml-auto"><Badge color="green">Done</Badge></span>}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Side info */}
          <div className="space-y-4">
            <div className={`${c.surface} border ${c.border} rounded-xl p-5`}>
              <div className={`text-sm font-medium mb-3 ${c.heading}`}>Recommended Reading</div>
              <div className="space-y-2">
                {(day.resources ?? []).map(r => (
                  <button type="button" key={r} onClick={() => openReading(r)}
                    className={`w-full text-left flex items-center gap-2 p-2 rounded-lg ${isDark ? 'hover:bg-white/3' : 'hover:bg-gray-50'} cursor-pointer transition-colors`}>
                    <BookOpen className={`w-3.5 h-3.5 shrink-0 ${c.muted}`} />
                    <span className={`text-xs ${c.text}`}>{r}</span>
                    <ArrowUpRight className={`w-3 h-3 ml-auto shrink-0 ${c.muted}`} />
                  </button>
                ))}
              </div>
            </div>

            <div className={`${c.surface} border ${c.border} rounded-xl p-5`}>
              <div className={`text-sm font-medium mb-3 ${c.heading}`}>Overall Progress</div>
              <div className="space-y-2.5">
                {days.map((d, di) => (
                  <div key={d.day} className="flex items-center gap-2">
                    <span className={`text-[10px] font-mono w-8 ${c.muted}`}>Day {d.day}</span>
                    <div className={`flex-1 h-1.5 rounded-full ${isDark ? 'bg-white/5' : 'bg-gray-100'}`}>
                      <div className="h-full rounded-full transition-all" style={{ width: `${dayPct(di)}%`, background: dayPct(di) === 100 ? '#10b981' : '#3b82f6' }} />
                    </div>
                    <span className={`text-[10px] font-mono w-8 text-right ${c.muted}`}>{dayPct(di)}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Page: Search ───────────────────────────────────────────────────────────

function SearchPage({ isDark, setIsDark, setPage }: { isDark: boolean; setIsDark: (v: boolean) => void; setPage: (p: Page) => void }) {
  const { repoId } = useAppState()
  const [query, setQuery] = useState('authentication')
  const [searching, setSearching] = useState(false)
  const [results, setResults] = useState<SearchResult[]>(SEARCH_RESULTS)

  const doSearch = async () => {
    if (!query.trim()) return
    setSearching(true)
    if (!repoId) {
      setTimeout(() => { setSearching(false); setResults(SEARCH_RESULTS) }, 800)
      return
    }
    try {
      const r = await Repos.search(repoId, query.trim())
      setResults(r)
    } catch {
      /* keep previous results */
    } finally {
      setSearching(false)
    }
  }

  const c = isDark ? {
    bg: 'bg-[#242C4D]', surface: 'bg-[#2D355C]', border: 'border-white/[0.06]',
    text: 'text-white/80', muted: 'text-white/35', heading: 'text-white',
    input: 'bg-white/5 border-white/10 text-white/80 placeholder-white/20'
  } : {
    bg: 'bg-[#F8F9FC]', surface: 'bg-white', border: 'border-gray-100',
    text: 'text-gray-700', muted: 'text-gray-400', heading: 'text-gray-900',
    input: 'bg-white border-gray-200 text-gray-800 placeholder-gray-300'
  }

  return (
    <div className={`flex-1 overflow-y-auto ${c.bg}`}>
      <TopBar title="Search" isDark={isDark} setIsDark={setIsDark} setPage={setPage}
        breadcrumbs={[{ label: 'Dashboard', page: 'dashboard' }, { label: 'CodeAtreus' }, { label: 'Search' }]} />
      <div className="p-6 max-w-4xl">
        <h1 className={`font-serif text-2xl mb-1 ${c.heading}`}>Semantic Search</h1>
        <p className={`text-sm mb-6 ${c.muted}`}>Search by meaning, not just keywords. Powered by vector embeddings.</p>

        {/* Search bar */}
        <div className={`flex gap-2 mb-6 p-3 rounded-xl border ${isDark ? 'border-white/[0.06] bg-white/3' : 'border-gray-200 bg-white'}`}>
          <Search className={`w-4 h-4 shrink-0 self-center ${c.muted}`} />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && doSearch()}
            placeholder="Search by concept, function, or behavior..."
            className={`flex-1 text-sm bg-transparent outline-none ${c.text}`}
            style={{ fontFamily: 'inherit' }}
          />
          {searching ? <Loader2 className="w-4 h-4 animate-spin text-blue-400 shrink-0 self-center" /> :
            <button onClick={doSearch} className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-md transition-colors">Search</button>}
        </div>

        {/* Quick searches */}
        <div className="flex flex-wrap gap-2 mb-6">
          {['authentication', 'payment processing', 'database queries', 'middleware', 'error handling'].map(s => (
            <button key={s} onClick={() => { setQuery(s); doSearch() }}
              className={`px-3 py-1 rounded-full text-xs border transition-colors ${isDark ? 'border-white/10 text-white/40 hover:border-white/20 hover:text-white/70' : 'border-gray-200 text-gray-400 hover:border-gray-300 hover:text-gray-600'}`}>
              {s}
            </button>
          ))}
        </div>

        {/* Results */}
        <div className={`text-xs mb-3 ${c.muted}`}>{results.length} results for "{query}" — 48,241 embeddings searched in 12ms</div>
        <div className="space-y-3">
          {results.map((r, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
              className={`${c.surface} border ${c.border} rounded-xl p-4 hover:border-blue-500/20 cursor-pointer transition-colors`}>
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <FileCode className={`w-3.5 h-3.5 ${c.muted}`} />
                  <span className={`text-xs font-mono font-medium ${c.heading}`}>{r.file}</span>
                  <span className={`text-[10px] font-mono ${c.muted}`}>:{r.line}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`flex items-center gap-1 text-[10px] font-mono ${c.muted}`}>
                    <span className="text-emerald-400">{r.relevance}%</span>
                    <span>match</span>
                  </div>
                  <Badge color={r.relevance >= 95 ? 'green' : r.relevance >= 85 ? 'blue' : 'slate'}>
                    {r.relevance >= 95 ? 'Best' : r.relevance >= 85 ? 'Good' : 'Fair'}
                  </Badge>
                </div>
              </div>
              <div className={`text-[10px] mb-2 font-mono ${c.muted}`}>{r.path}</div>
              <pre className={`text-[11px] font-mono leading-relaxed overflow-x-auto p-3 rounded-lg ${isDark ? 'bg-[#151a2e] text-emerald-300/80' : 'bg-gray-900 text-emerald-400'}`}>
                {r.snippet}
              </pre>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Page: Settings ─────────────────────────────────────────────────────────

function SettingsPage({ isDark, setIsDark, setPage }: { isDark: boolean; setIsDark: (v: boolean) => void; setPage: (p: Page) => void }) {
  const [activeSection, setActiveSection] = useState('profile')
  const [apiKey, setApiKey] = useState('sk-or-••••••••••••••••••••••••••••••••••••••••')

  const sections = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'theme', label: 'Appearance', icon: Palette },
    { id: 'apikeys', label: 'API Keys', icon: Key },
    { id: 'usage', label: 'Usage', icon: BarChart3 },
    { id: 'danger', label: 'Danger Zone', icon: AlertCircle },
  ]

  const c = isDark ? {
    bg: 'bg-[#242C4D]', surface: 'bg-[#2D355C]', border: 'border-white/[0.06]',
    text: 'text-white/80', muted: 'text-white/35', heading: 'text-white',
    input: 'bg-white/5 border-white/10 text-white/70',
    sidebar: 'bg-[#1e2544]'
  } : {
    bg: 'bg-[#F8F9FC]', surface: 'bg-white', border: 'border-gray-100',
    text: 'text-gray-700', muted: 'text-gray-400', heading: 'text-gray-900',
    input: 'bg-gray-50 border-gray-200 text-gray-700',
    sidebar: 'bg-white'
  }

  const usageData = [
    { month: 'May', questions: 167, tokens: 420 },
    { month: 'Jun', questions: 289, tokens: 710 },
    { month: 'Jul', questions: 341, tokens: 890 },
  ]

  return (
    <div className={`flex-1 flex flex-col overflow-hidden ${c.bg}`} style={{ height: '100vh' }}>
      <TopBar title="Settings" isDark={isDark} setIsDark={setIsDark} setPage={setPage}
        breadcrumbs={[{ label: 'Dashboard', page: 'dashboard' }, { label: 'Settings' }]} />
      <div className="flex-1 flex overflow-hidden">
        {/* Settings nav */}
        <div className={`w-48 border-r ${c.border} ${c.sidebar} p-3 flex flex-col shrink-0`}>
          <div className={`text-[10px] uppercase tracking-widest px-2 mb-2 ${c.muted}`}>Settings</div>
          {sections.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => setActiveSection(id)}
              className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs mb-0.5 transition-colors ${
                activeSection === id ?
                  isDark ? 'bg-white/8 text-white/80' : 'bg-gray-100 text-gray-800'
                  : isDark ? 'text-white/40 hover:text-white/60 hover:bg-white/5' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              } ${id === 'danger' ? 'text-red-400/70 hover:text-red-400' : ''}`}>
              <Icon className="w-3.5 h-3.5 shrink-0" />
              <span className="font-medium">{label}</span>
            </button>
          ))}
          <div className="flex-1" />
          <button className={`flex items-center gap-2 px-2.5 py-2 rounded-md text-xs transition-colors text-red-400/60 hover:text-red-400 hover:bg-red-500/10`}>
            <LogOut className="w-3.5 h-3.5" />
            Sign out
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8">
          <AnimatePresence mode="wait">
            <motion.div key={activeSection} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
              {activeSection === 'profile' && (
                <div className="max-w-lg space-y-6">
                  <div>
                    <h2 className={`font-serif text-xl mb-1 ${c.heading}`}>Profile</h2>
                    <p className={`text-xs ${c.muted}`}>Manage your account information.</p>
                  </div>
                  <div className={`${c.surface} border ${c.border} rounded-xl p-5 space-y-4`}>
                    <div className="flex items-center gap-4">
                      <div className="w-14 h-14 rounded-full bg-blue-600 flex items-center justify-center shrink-0">
                        <span className="text-xl font-bold text-white">JS</span>
                      </div>
                      <div>
                        <div className={`text-sm font-medium ${c.heading}`}>John Smith</div>
                        <div className={`text-xs ${c.muted}`}>john@company.com</div>
                        <button className="text-xs text-blue-500 hover:text-blue-400 mt-1">Change avatar</button>
                      </div>
                    </div>
                    {[{ label: 'Full Name', value: 'John Smith' }, { label: 'Email', value: 'john@company.com' }, { label: 'Company', value: 'Acme Corp' }].map(f => (
                      <div key={f.label}>
                        <label className={`text-xs font-medium block mb-1.5 ${c.muted}`}>{f.label}</label>
                        <input defaultValue={f.value} className={`w-full px-3 py-2 rounded-md border text-sm outline-none ${c.input}`} />
                      </div>
                    ))}
                    <button className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-md transition-colors">Save changes</button>
                  </div>

                  <div className={`${c.surface} border ${c.border} rounded-xl p-5`}>
                    <div className="flex items-center gap-3 mb-4">
                      <Github className={`w-4 h-4 ${c.muted}`} />
                      <div>
                        <div className={`text-sm font-medium ${c.heading}`}>GitHub Connection</div>
                        <div className={`text-xs ${c.muted}`}>Connected as @johnsmith</div>
                      </div>
                      <Badge color="green">Connected</Badge>
                    </div>
                    <button className={`text-xs border px-3 py-1.5 rounded-md transition-colors ${isDark ? 'border-white/10 text-white/40 hover:bg-white/5' : 'border-gray-200 text-gray-500 hover:bg-gray-50'}`}>Disconnect</button>
                  </div>
                </div>
              )}

              {activeSection === 'theme' && (
                <div className="max-w-lg space-y-6">
                  <div>
                    <h2 className={`font-serif text-xl mb-1 ${c.heading}`}>Appearance</h2>
                    <p className={`text-xs ${c.muted}`}>Customize how CodeAtreus looks.</p>
                  </div>
                  <div className={`${c.surface} border ${c.border} rounded-xl p-5`}>
                    <div className={`text-sm font-medium mb-4 ${c.heading}`}>Theme</div>
                    <div className="grid grid-cols-2 gap-3">
                      <button onClick={() => setIsDark(true)}
                        className={`p-4 rounded-xl border text-left transition-all ${isDark ? 'border-blue-500/40 bg-blue-500/10' : isDark ? 'border-white/10' : 'border-gray-200'}`}>
                        <div className="w-full h-12 rounded-lg bg-[#242C4D] mb-2 border border-white/10" />
                        <div className={`text-xs font-medium ${c.heading}`}>Dark</div>
                        <div className={`text-[10px] ${c.muted}`}>Navy blue</div>
                      </button>
                      <button onClick={() => setIsDark(false)}
                        className={`p-4 rounded-xl border text-left transition-all ${!isDark ? 'border-blue-500/40 bg-blue-50' : isDark ? 'border-white/10' : 'border-gray-200'}`}>
                        <div className="w-full h-12 rounded-lg bg-[#F8F9FC] mb-2 border border-gray-200" />
                        <div className={`text-xs font-medium ${c.heading}`}>Light</div>
                        <div className={`text-[10px] ${c.muted}`}>Clean white</div>
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {activeSection === 'apikeys' && (
                <div className="max-w-lg space-y-6">
                  <div>
                    <h2 className={`font-serif text-xl mb-1 ${c.heading}`}>API Keys</h2>
                    <p className={`text-xs ${c.muted}`}>Manage third-party API integrations.</p>
                  </div>
                  <div className={`${c.surface} border ${c.border} rounded-xl p-5 space-y-5`}>
                    {[
                      { label: 'OpenRouter API Key', desc: 'Used for AI chat and embeddings', prefix: 'sk-or-' },
                      { label: 'GitHub Personal Token', desc: 'Access private repositories', prefix: 'ghp_' },
                    ].map(k => (
                      <div key={k.label}>
                        <label className={`text-xs font-medium block mb-1 ${c.heading}`}>{k.label}</label>
                        <div className={`text-[10px] mb-2 ${c.muted}`}>{k.desc}</div>
                        <div className="flex gap-2">
                          <input type="password" defaultValue={`${k.prefix}••••••••••••••••••••••••••••••••••••`}
                            className={`flex-1 px-3 py-2 rounded-md border text-xs outline-none font-mono ${c.input}`} />
                          <button className={`px-3 py-2 rounded-md border text-xs transition-colors ${isDark ? 'border-white/10 text-white/50 hover:bg-white/5' : 'border-gray-200 text-gray-500 hover:bg-gray-50'}`}>
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                    <button className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-md transition-colors">Save API Keys</button>
                  </div>
                </div>
              )}

              {activeSection === 'usage' && (
                <div className="max-w-2xl space-y-6">
                  <div>
                    <h2 className={`font-serif text-xl mb-1 ${c.heading}`}>Usage Statistics</h2>
                    <p className={`text-xs ${c.muted}`}>Your activity and consumption metrics.</p>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { label: 'Repos Indexed', value: '5', icon: GitBranch, color: 'text-blue-400' },
                      { label: 'Questions Asked', value: '1,247', icon: MessageSquare, color: 'text-purple-400' },
                      { label: 'Tokens Used', value: '2.02M', icon: Cpu, color: 'text-emerald-400' },
                    ].map(s => (
                      <div key={s.label} className={`${c.surface} border ${c.border} rounded-xl p-4`}>
                        <s.icon className={`w-4 h-4 mb-2 ${s.color}`} />
                        <div className={`text-xl font-semibold ${c.heading}`}>{s.value}</div>
                        <div className={`text-xs ${c.muted}`}>{s.label}</div>
                      </div>
                    ))}
                  </div>
                  <div className={`${c.surface} border ${c.border} rounded-xl p-5`}>
                    <div className={`text-sm font-medium mb-4 ${c.heading}`}>Monthly Activity</div>
                    <ResponsiveContainer width="100%" height={150}>
                      <BarChart data={usageData}>
                        <CartesianGrid stroke={isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)'} vertical={false} />
                        <XAxis dataKey="month" tick={{ fontSize: 10, fill: isDark ? 'rgba(255,255,255,0.3)' : '#9ca3af' }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fontSize: 10, fill: isDark ? 'rgba(255,255,255,0.3)' : '#9ca3af' }} axisLine={false} tickLine={false} width={30} />
                        <Tooltip contentStyle={{ background: isDark ? '#2D355C' : '#fff', border: isDark ? '1px solid rgba(255,255,255,0.08)' : '1px solid #e5e7eb', borderRadius: 6, fontSize: 12 }} />
                        <Bar dataKey="questions" fill="#3b82f6" radius={[3, 3, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className={`${c.surface} border ${c.border} rounded-xl p-5`}>
                    <div className="flex items-center justify-between mb-2">
                      <div className={`text-sm font-medium ${c.heading}`}>Plan: Pro</div>
                      <Badge color="blue">Active</Badge>
                    </div>
                    <div className={`text-xs ${c.muted} mb-3`}>Renews August 19, 2025</div>
                    <div className="flex items-center gap-2 mb-1">
                      <div className={`flex-1 h-1.5 rounded-full ${isDark ? 'bg-white/5' : 'bg-gray-100'}`}>
                        <div className="h-full rounded-full bg-blue-600" style={{ width: '61%' }} />
                      </div>
                      <span className={`text-xs font-mono ${c.muted}`}>1.24M / 2M tokens</span>
                    </div>
                  </div>
                </div>
              )}

              {activeSection === 'danger' && (
                <div className="max-w-lg space-y-4">
                  <div>
                    <h2 className={`font-serif text-xl mb-1 text-red-400`}>Danger Zone</h2>
                    <p className={`text-xs ${c.muted}`}>These actions are irreversible. Proceed with caution.</p>
                  </div>
                  {[
                    { label: 'Delete Repository Index', desc: 'Remove all embeddings and knowledge graph for CodeAtreus. This cannot be undone.', btn: 'Delete Index' },
                    { label: 'Reset All Data', desc: 'Delete all repositories, chat history, and embeddings across your account.', btn: 'Reset Account' },
                    { label: 'Delete Account', desc: 'Permanently delete your account and all associated data.', btn: 'Delete Account' },
                  ].map(d => (
                    <div key={d.label} className={`${c.surface} border border-red-500/20 rounded-xl p-5 flex items-center justify-between`}>
                      <div>
                        <div className={`text-sm font-medium ${c.heading}`}>{d.label}</div>
                        <div className={`text-xs ${c.muted} max-w-xs`}>{d.desc}</div>
                      </div>
                      <button className="ml-4 shrink-0 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 text-xs rounded-md transition-colors font-medium">
                        {d.btn}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}

// ── App ────────────────────────────────────────────────────────────────────

// ── Shared app state (active repo + auth) ───────────────────────────────────
interface AppState {
  repoId: string | null
  setRepoId: (id: string | null) => void
  ensureAuth: () => Promise<void>
}
const AppStateCtx = createContext<AppState>({
  repoId: null,
  setRepoId: () => {},
  ensureAuth: async () => {},
})
export function useAppState() {
  return useContext(AppStateCtx)
}

export default function App() {
  const [page, setPage] = useState<Page>('landing')
  const [isDark, setIsDark] = useState(true)
  const [repoId, setRepoId] = useState<string | null>(null)

  // Lazily obtain a dev token so the frontend works before real GitHub OAuth.
  const ensureAuth = async () => {
    if (getToken()) return
    try {
      const pair = await Auth.devLogin()
      setToken(pair.access_token)
    } catch {
      /* backend offline — pages fall back to mock data */
    }
  }

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark)
  }, [isDark])

  const appPages: Page[] = ['dashboard', 'import', 'indexing', 'overview', 'chat', 'graph', 'flow', 'sequence', 'roadmap', 'search', 'settings']
  const isAppPage = appPages.includes(page)

  const renderPage = () => {
    const props = { isDark, setIsDark, setPage }
    switch (page) {
      case 'landing': return <LandingPage {...props} />
      case 'login': return <LoginPage {...props} />
      case 'dashboard': return <DashboardPage {...props} />
      case 'import': return <ImportPage {...props} />
      case 'indexing': return <IndexingPage {...props} />
      case 'overview': return <OverviewPage {...props} />
      case 'chat': return <ChatPage {...props} />
      case 'graph': return <GraphPage {...props} />
      case 'flow': return <FlowPage {...props} />
      case 'sequence': return <SequencePage {...props} />
      case 'roadmap': return <RoadmapPage {...props} />
      case 'search': return <SearchPage {...props} />
      case 'settings': return <SettingsPage {...props} />
    }
  }

  if (!isAppPage) {
    return (
      <AppStateCtx.Provider value={{ repoId, setRepoId, ensureAuth }}>
        <div className={isDark ? 'dark' : ''}>
          <AnimatePresence mode="wait">
            <motion.div key={page} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
              {renderPage()}
            </motion.div>
          </AnimatePresence>
        </div>
      </AppStateCtx.Provider>
    )
  }

  return (
    <AppStateCtx.Provider value={{ repoId, setRepoId, ensureAuth }}>
      <div className={`${isDark ? 'dark' : ''} flex h-screen overflow-hidden font-sans`} style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
        <Sidebar page={page} setPage={setPage} isDark={isDark} />
        <main className="flex-1 flex flex-col overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.div key={page} className="flex-1 flex flex-col overflow-hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.12 }}>
              {renderPage()}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </AppStateCtx.Provider>
  )
}
