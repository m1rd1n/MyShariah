/**
 * app/api/audit/[id]/route.ts — Get audit by ID or list all
 * Updated to read from Supabase instead of in-memory store.
 */

import { NextRequest, NextResponse } from 'next/server'
import { getAudit, listAudits } from '@/lib/db'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params

  // Special route: /api/audit/list
  if (id === 'list') {
    try {
      const audits = await listAudits()
      return NextResponse.json({ audits })
    } catch (err: any) {
      return NextResponse.json({ error: err.message }, { status: 500 })
    }
  }

  try {
    const audit = await getAudit(id)
    if (!audit) {
      return NextResponse.json({ error: `Audit not found: ${id}` }, { status: 404 })
    }
    return NextResponse.json(audit)
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 })
  }
}
