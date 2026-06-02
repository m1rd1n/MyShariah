/**
 * app/api/audit/start/route.ts — Start a new audit via FastAPI backend
 *
 * Flow:
 *  1. Create the audit record in Supabase (so the status page can poll immediately)
 *  2. Fire-and-forget POST to the FastAPI backend — it runs the real AI pipeline
 *     and writes results back to Supabase at each stage
 *  3. Return { contractId } to the frontend immediately (non-blocking)
 *
 * The frontend then polls /api/audit/[id] which reads from Supabase.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAudit, appendEvent } from '@/lib/db'

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const { contractId, contractText } = await request.json()

    if (!contractId || !contractText) {
      return NextResponse.json(
        { error: 'contractId and contractText are required' },
        { status: 400 }
      )
    }

    // 1. Create the initial audit record in Supabase
    await createAudit(contractId, contractText)
    await appendEvent(contractId, 'phase_change', { phase: 'queued' })

    // 2. Fire-and-forget — trigger the real AI pipeline on the Python backend
    fetch(`${BACKEND_URL}/audit/start`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        contract_id:   contractId,
        contract_text: contractText,
      }),
    }).catch((err) => {
      console.error('[api/audit/start] Failed to reach FastAPI backend:', err.message)
    })

    // 3. Return immediately — frontend polls for status
    return NextResponse.json({ contractId })

  } catch (err: any) {
    console.error('[api/audit/start]', err)
    return NextResponse.json(
      { error: err.message ?? 'Internal server error' },
      { status: 500 }
    )
  }
}
