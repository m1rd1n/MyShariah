/**
 * app/api/audit/start/route.ts — Start a new audit (Supabase-backed)
 *
 * CHANGES: Creates the audit record in Supabase instead of the in-memory store.
 * The simulation still fires in the background (replace with FastAPI call in prod).
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAudit, updateAudit, appendEvent } from '@/lib/db'

export async function POST(request: NextRequest) {
  try {
    const { contractId, contractText } = await request.json()

    if (!contractId || !contractText) {
      return NextResponse.json(
        { error: 'contractId and contractText are required' },
        { status: 400 }
      )
    }

    // Create the audit record in Supabase
    await createAudit(contractId, contractText)
    await appendEvent(contractId, 'phase_change', { phase: 'queued' })

    /* PRODUCTION: Fire-and-forget call to FastAPI backend:
    fetch(`${process.env.BACKEND_URL}/audit/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contract_id: contractId, contract_text: contractText }),
    }).catch(console.error)
    */

    // MVP: simulate pipeline progression in background
    simulateAuditRun(contractId, contractText)

    return NextResponse.json({ contractId })
  } catch (err: any) {
    console.error('[api/audit/start]', err)
    return NextResponse.json({ error: err.message ?? 'Internal server error' }, { status: 500 })
  }
}

// ── MVP simulation (replace with FastAPI call in production) ──────────────────

async function simulateAuditRun(contractId: string, text: string) {
  const delay = (ms: number) => new Promise(res => setTimeout(res, ms))

  const steps = [
    { wait: 2000, phase: 'extraction', patch: {
      phase: 'extraction',
      clauses: [
        { clause_id: 'C001', clause_type: 'pricing',            text: text.slice(0, 120) },
        { clause_id: 'C002', clause_type: 'tenure',             text: text.slice(120, 240) },
        { clause_id: 'C003', clause_type: 'penalty',            text: text.slice(240, 360) },
        { clause_id: 'C004', clause_type: 'ownership_transfer', text: text.slice(360, 480) },
        { clause_id: 'C005', clause_type: 'governing_law',      text: text.slice(480, 600) },
      ]
    }},
    { wait: 3000, phase: 'compliance', patch: {
      phase: 'compliance',
      compliance_report: [
        { clause_id: 'C001', status: 'non_compliant', bnm_reference: 'SGF 2019, Para 7.1', explanation: 'Profit rate is KLIBOR-linked. Must be fixed at inception.', confidence: 0.92 },
        { clause_id: 'C002', status: 'compliant',     bnm_reference: 'SGF 2019, Para 8.1', explanation: 'Payment schedule clearly defined.', confidence: 0.95 },
        { clause_id: 'C003', status: 'non_compliant', bnm_reference: 'BNM/RH/PD 029-7',   explanation: 'Late payment income to bank violates ta\'widh rules.', confidence: 0.97 },
        { clause_id: 'C004', status: 'ambiguous',     bnm_reference: 'SGF 2019, Para 8.2', explanation: 'Direct delivery before execution raises ownership concerns.', confidence: 0.71 },
        { clause_id: 'C005', status: 'ambiguous',     bnm_reference: 'AAOIFI SS No. 8',    explanation: 'Dual jurisdiction may conflict with Shariah governance.', confidence: 0.68 },
      ]
    }},
    { wait: 3500, phase: 'devils_advocate', patch: {
      phase: 'devils_advocate',
      adversarial_findings: [
        { clause_id: 'C001', risk_type: 'riba',           severity: 'high',   finding: 'KLIBOR-linked profit constitutes disguised interest.', loophole: 'Bank could argue KLIBOR adjustment is a "review", not a change.' },
        { clause_id: 'C003', risk_type: 'riba',           severity: 'high',   finding: 'Late payment income to bank is undisclosed profit.', loophole: 'No cap on charges — unlimited income extraction possible.' },
        { clause_id: 'C004', risk_type: 'gharar',         severity: 'high',   finding: 'Bank never holds constructive possession before delivery.', loophole: 'Invalidates the Murabaha structure entirely.' },
        { clause_id: 'C005', risk_type: 'jurisdictional', severity: 'medium', finding: 'Unilateral forum election creates Shariah oversight gap.', loophole: 'Bank could elect DIFC to escape BNM Shariah oversight.' },
      ],
      devils_advocate_iterations: 1,
    }},
    { wait: 2000, phase: 'simulator', patch: {
      phase: 'hitl_required',
      audit_report: JSON.stringify({
        audit_summary: 'This contract contains three high-severity Shariah violations and cannot be approved in its current form.',
        key_concerns: [
          'Variable profit rate (KLIBOR) violates SGF 2019 Para 7.1 fixed-profit requirement',
          'Late payment income to bank contravenes ta\'widh rules (BNM/RH/PD 029-7)',
          'Direct delivery before execution creates bay\' al-ma\'dum risk (ownership gap)',
        ],
        risk_score: 0.87,
        recommendation: 'ESCALATE',
        reasoning: 'Multiple fundamental Shariah principles violated. Material amendments required.',
        conditions: [
          'Fix profit rate at inception — remove KLIBOR reference',
          'Redirect late payment charges to charity',
          'Bank must take constructive possession before delivery',
        ],
      }),
      risk_score: 0.87,
      needs_human_review: true,
    }},
  ]

  for (const step of steps) {
    await delay(step.wait)
    await updateAudit(contractId, step.patch as any)
    await appendEvent(contractId, 'agent_complete', { phase: step.phase })
  }
}
