/**
 * app/api/review/[id]/route.ts — Submit HITL officer decision
 * Updated to persist to Supabase (audit row + immutable event log).
 */

import { NextRequest, NextResponse } from 'next/server'
import { getAudit, recordDecision } from '@/lib/db'

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id } = params

  try {
    const { decision, justification, officerName } = await request.json()

    if (!decision || !['APPROVE', 'REJECT'].includes(decision)) {
      return NextResponse.json({ error: 'Decision must be APPROVE or REJECT' }, { status: 400 })
    }
    if (!justification?.trim()) {
      return NextResponse.json({ error: 'Justification is required' }, { status: 400 })
    }
    if (!officerName?.trim()) {
      return NextResponse.json({ error: 'Officer name is required' }, { status: 400 })
    }

    const audit = await getAudit(id)
    if (!audit) {
      return NextResponse.json({ error: `Audit not found: ${id}` }, { status: 404 })
    }
    if (audit.phase !== 'hitl_required') {
      return NextResponse.json({ error: 'Audit is not awaiting review' }, { status: 409 })
    }

    // Persist decision + append immutable event to audit trail
    await recordDecision(id, decision, justification, officerName)

    return NextResponse.json({
      success:    true,
      contractId: id,
      decision,
      recordedAt: new Date().toISOString(),
    })
  } catch (err: any) {
    console.error('[api/review]', err)
    return NextResponse.json({ error: err.message ?? 'Internal server error' }, { status: 500 })
  }
}
