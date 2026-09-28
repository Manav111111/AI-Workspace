# AVTAAR — FINAL DESIGN SYSTEM & UI/UX SPECIFICATION

## Aesthetic Identity: Warm Editorial SaaS

The Avtaar design system departs entirely from the generic blue-themed AI dashboard look, implementing a bespoke, warm editorial visual identity built for high-trust enterprise B2B workflows.

---

### 1. Color Palette Tokens

```css
/* Core Brand & Forest Accents */
--forest-50:  #f0fdf4;
--forest-100: #dcfce7;
--forest-400: #34d399;
--forest-500: #10b981;
--forest-600: #059669;
--forest-800: #065f46;
--forest-950: #022c22;

/* Warm Amber & Sand Highlights */
--amber-400:  #fbbf24;
--amber-500:  #f59e0b;
--sand-300:   #fde68a;
--sand-400:   #fcd34d;

/* Layered Charcoal & Dark Surface Containers */
--surface-50:  #2d3345;
--surface-100: #262b3a;
--surface-200: #1f2330;
--surface-300: #1a1e29;
--surface-400: #13161f;
--surface-500: #0e1017;
--surface-bg:  #0b0d13;
--surface-border: #262b3a;
--surface-borderLight: #333a4d;
```

---

### 2. Typography & Hierarchy

- **Primary Font**: `Plus Jakarta Sans` — Geometric sans-serif with excellent legibility at micro-scales.
- **Monospace Font**: `JetBrains Mono` / System monospace — Used for token metrics, trace IDs, latency values, timestamps, and JSON payloads.
- **Hierarchy Tokens**:
  - `Display / H1`: 24px–28px, Bold, tracking tight (`tracking-tight text-slate-100`)
  - `Section / H2`: 16px–18px, Bold (`font-bold text-white`)
  - `Card Header`: 13px–14px, SemiBold (`font-semibold text-slate-200`)
  - `Body / Metadata`: 11px–12px, Regular/Medium (`text-slate-400 leading-relaxed`)
  - `Micro / Code`: 10px–11px, Monospace (`font-mono text-[11px]`)

---

### 3. Shared Primitive Components

| Component | Location | Variants / Capabilities |
|---|---|---|
| `Button` | `src/components/ui/Button.tsx` | `forest`, `secondary`, `outline`, `ghost`, `danger`, `amber` with loading states and icon slots. |
| `Card` | `src/components/ui/Card.tsx` | `CardHeader`, `CardTitle`, `CardContent`, `CardFooter` with optional hover lift and subtle borders. |
| `Badge` | `src/components/ui/Badge.tsx` | `forest`, `amber`, `rose`, `neutral`, `sky`, `sand` with optional live pulse dot. |
| `PageHeader` | `src/components/ui/PageHeader.tsx` | Title, description, action buttons slot, status badge slot. |
| `EmptyState` | `src/components/ui/EmptyState.tsx` | Icon container, title, description, primary action trigger. |
| `Tabs` | `src/components/ui/Tabs.tsx` | Underline and pill tab switches with responsive overflow. |

---

### 4. Application Shell & Navigation Structure

```text
Workspace
├── Overview (Dashboard)          → /dashboard
├── AI Employees                  → /ai-employees
├── Knowledge Bases               → /knowledge
└── Conversations                 → /conversations

Build & Test
├── AI Playground                 → /playground
└── Evaluation Benchmarks         → /evaluations

Operations
├── Observability & Traces        → /observability
├── Cost & Budget Governance      → /usage
└── Audit Logs                    → /audit

Configuration
└── Settings & Organization       → /settings
```

---

### 5. Verified Redesigned Routes

All 16 routes in the application have been completely redesigned according to this specification:
1. `/` (Public Homepage / Control Plane Landing)
2. `/login` (Authentication)
3. `/signup` (Registration & Workspace Provisioning)
4. `/dashboard` (Executive KPI Dashboard)
5. `/ai-employees` (AI Employee Directory & Builder Drawer)
6. `/ai-employees/[id]/chat` (Dedicated AI Employee Session View)
7. `/knowledge` (Knowledge Base & Async Document Ingestion)
8. `/conversations` (Enterprise Conversation History)
9. `/playground` (Interactive Control Plane Testing & Inspection)
10. `/evaluations` (Golden Benchmark Matrix & Regression Reporting)
11. `/observability` (Distributed Trace Waterfall & Telemetry)
12. `/usage` (Decimal-Safe Spend Ledger & Budget Governance)
13. `/audit` (PII-Redacted Immutable Audit Explorer)
14. `/settings` (Company Identity & Membership Management)
15. `/preview/[public_id]` (Standalone Embed Preview & Widget Test)
16. `/_not-found` (Custom Editorial 404 Route)
