/**
 * lib/store.ts — In-memory audit store for MVP
 *
 * WHY THIS EXISTS:
 * The Next.js API routes need to share state between requests
 * (e.g. start audit in POST /api/audit/start, read it in GET /api/audit/[id]).
 * For the MVP we use a module-level Map — it persists as long as the
 * Next.js dev server is running.
 *
 * REPLACE WITH SUPABASE in the next stage:
 *   import { createClient } from '@supabase/supabase-js'
 *   const supabase = createClient(url, key)
 *   await supabase.from('audits').insert({ ... })
 */

export type AuditPhase =
  | 'queued'
  | 'extraction'
  | 'compliance'
  | 'devils_advocate'
  | 'simulator'
  | 'hitl_required'
  | 'approved'
  | 'rejected'

export interface ClauseItem {
  clause_id: string
  clause_type: string
  text: string
}

export interface ComplianceResult {
  clause_id: string
  status: 'compliant' | 'non_compliant' | 'ambiguous'
  bnm_reference: string
  explanation: string
  confidence: number
}

export interface AdversarialFinding {
  clause_id: string
  risk_type: string
  severity: 'high' | 'medium' | 'low'
  finding: string
  loophole: string
}

export interface AuditRecord {
  contract_id: string
  contract_text: string
  phase: AuditPhase
  started_at: string
  completed_at?: string

  // Populated progressively as agents complete
  clauses?: ClauseItem[]
  compliance_report?: ComplianceResult[]
  adversarial_findings?: AdversarialFinding[]
  audit_report?: string        // JSON string from simulator
  risk_score?: number

  // HITL fields
  human_decision?: string
  officer_justification?: string
  officer_id?: string
}

// Module-level store — survives across requests within one server process
const audits = new Map<string, AuditRecord>()

export const store = {
  create: (record: AuditRecord) => {
    audits.set(record.contract_id, record)
  },
  get: (id: string): AuditRecord | undefined => audits.get(id),
  update: (id: string, patch: Partial<AuditRecord>) => {
    const existing = audits.get(id)
    if (existing) audits.set(id, { ...existing, ...patch })
  },
  all: (): AuditRecord[] =>
    Array.from(audits.values()).sort(
      (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
    ),
}

// ── Seed data for demo (shows a realistic audit log on first load) ────────────
const seedData: AuditRecord[] = [
  {
    contract_id: 'MUR-2024-0081',
    contract_text: '',
    phase: 'approved',
    started_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 2.8 * 60 * 60 * 1000).toISOString(),
    risk_score: 0.18,
    human_decision: 'AUTO_APPROVED',
  },
  {
    contract_id: 'MUR-2024-0082',
    contract_text: '',
    phase: 'rejected',
    started_at: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 5.5 * 60 * 60 * 1000).toISOString(),
    risk_score: 0.91,
    human_decision: 'REJECT',
    officer_justification: 'Clause 3 constitutes Riba. Variable profit rate tied to KLIBOR is non-compliant with SGF 2019 Para 7.1.',
    officer_id: 'Dr. Aminah binti Yusof',
  },
  {
    contract_id: 'MUR-2024-0085',
    contract_text: '',
    phase: 'approved',
    started_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 23.5 * 60 * 60 * 1000).toISOString(),
    risk_score: 0.42,
    human_decision: 'APPROVE',
    officer_justification: 'Concerns noted but bank confirmed constructive possession procedures. Approved with conditions.',
    officer_id: 'Ustaz Hafiz bin Rahman',
  },
]

seedData.forEach(store.create)
