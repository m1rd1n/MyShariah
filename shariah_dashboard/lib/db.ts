/**
 * lib/db.ts — Supabase database operations
 *
 * This replaces lib/store.ts (the in-memory Map).
 * All API routes now call these functions instead of store.create/get/update.
 *
 * Every function returns typed data or throws — callers wrap in try/catch.
 *
 * TYPE NOTE: The AuditRecord type mirrors the Supabase 'audits' table schema.
 * Keep these in sync if you add columns to the SQL schema.
 */

import { supabase } from './supabase'

// ── Types (mirror the Supabase schema) ────────────────────────────────────────

export type AuditPhase =
  | 'queued' | 'extraction' | 'compliance' | 'devils_advocate'
  | 'simulator' | 'hitl_required' | 'approved' | 'rejected'

export interface AuditRecord {
  id?:                        string
  contract_id:                string
  contract_text?:             string
  phase:                      AuditPhase
  started_at?:                string
  completed_at?:              string
  clauses?:                   any[]
  compliance_report?:         any[]
  adversarial_findings?:      any[]
  devils_advocate_iterations?: number
  audit_report?:              string
  risk_score?:                number
  needs_human_review?:        boolean
  human_decision?:            string
  officer_justification?:     string
  officer_id?:                string
}

// ── Read operations ────────────────────────────────────────────────────────────

export async function getAudit(contractId: string): Promise<AuditRecord | null> {
  const { data, error } = await supabase
    .from('audits')
    .select('*')
    .eq('contract_id', contractId)
    .single()

  if (error) {
    if (error.code === 'PGRST116') return null   // row not found — not an error
    throw new Error(`getAudit failed: ${error.message}`)
  }
  return data
}

export async function listAudits(limit = 50): Promise<AuditRecord[]> {
  const { data, error } = await supabase
    .from('audits')
    .select('contract_id, phase, started_at, completed_at, risk_score, human_decision, officer_id')
    .order('started_at', { ascending: false })
    .limit(limit)

  if (error) throw new Error(`listAudits failed: ${error.message}`)
  return data ?? []
}

// ── Write operations ───────────────────────────────────────────────────────────

export async function createAudit(
  contractId: string,
  contractText: string
): Promise<AuditRecord> {
  const { data, error } = await supabase
    .from('audits')
    .insert({
      contract_id:   contractId,
      contract_text: contractText,
      phase:         'queued',
    })
    .select()
    .single()

  if (error) throw new Error(`createAudit failed: ${error.message}`)
  return data
}

export async function updateAudit(
  contractId: string,
  patch: Partial<AuditRecord>
): Promise<void> {
  const { error } = await supabase
    .from('audits')
    .update(patch)
    .eq('contract_id', contractId)

  if (error) throw new Error(`updateAudit failed: ${error.message}`)
}

export async function recordDecision(
  contractId: string,
  decision: string,
  justification: string,
  officerId: string
): Promise<void> {
  const now = new Date().toISOString()

  // Update the audit row
  await updateAudit(contractId, {
    human_decision:        decision,
    officer_justification: justification,
    officer_id:            officerId,
    phase:                 decision === 'APPROVE' ? 'approved' : 'rejected',
    completed_at:          now,
  })

  // Append an immutable event to the audit trail
  await appendEvent(contractId, 'hitl_decision', {
    decision, justification, timestamp: now,
  }, officerId)
}

// ── Audit trail ────────────────────────────────────────────────────────────────

export async function appendEvent(
  contractId: string,
  eventType: string,
  data: Record<string, any>,
  actor = 'system'
): Promise<void> {
  const { error } = await supabase
    .from('audit_events')
    .insert({ contract_id: contractId, event_type: eventType, event_data: data, actor })

  if (error) {
    // Non-fatal: log but don't throw — event logging should never block the pipeline
    console.error(`[db] appendEvent failed: ${error.message}`)
  }
}

export async function getAuditEvents(contractId: string) {
  const { data, error } = await supabase
    .from('audit_events')
    .select('*')
    .eq('contract_id', contractId)
    .order('created_at', { ascending: true })

  if (error) throw new Error(`getAuditEvents failed: ${error.message}`)
  return data ?? []
}
