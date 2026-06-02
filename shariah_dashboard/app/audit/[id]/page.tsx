'use client'

/**
 * app/audit/[id]/page.tsx — Live audit status
 *
 * NEXT.JS NOTE: The folder name [id] creates a dynamic route.
 * The contract ID comes from params.id — e.g. /audit/MUR-2024-0087
 * sets params.id = "MUR-2024-0087".
 *
 * We use SWR for polling: it automatically re-fetches /api/audit/[id]
 * every 2 seconds while the audit is running, then stops once done.
 */

import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import useSWR from 'swr'
import AuditPhaseTracker from '@/components/AuditPhaseTracker'
import StatusBadge from '@/components/StatusBadge'
import RiskMeter from '@/components/RiskMeter'

const fetcher = (url: string) => fetch(url).then(r => r.json())

const RUNNING_PHASES = ['queued', 'extraction', 'compliance', 'devils_advocate', 'simulator']

export default function AuditStatusPage({ params }: { params: { id: string } }) {
  const { id } = params
  const router  = useRouter()

  // Poll every 2s while audit is running; stop when terminal phase reached
  const { data: audit, error } = useSWR(
    `/api/audit/${id}`,
    fetcher,
    {
      refreshInterval: (data) =>
        data && RUNNING_PHASES.includes(data.phase) ? 2000 : 0,
    }
  )

  // Auto-redirect to HITL review page when flagged
  useEffect(() => {
    if (audit?.phase === 'hitl_required') {
      router.push(`/review/${id}`)
    }
  }, [audit?.phase, id, router])

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700 font-medium">Failed to load audit status</p>
          <p className="text-red-500 text-sm mt-1">Contract ID: {id}</p>
        </div>
      </div>
    )
  }

  if (!audit) {
    return (
      <div className="p-8 flex items-center gap-3 text-gray-400">
        <div className="w-4 h-4 border-2 border-gray-300 border-t-emerald-500 rounded-full animate-spin" />
        Loading audit status...
      </div>
    )
  }

  const isRunning  = RUNNING_PHASES.includes(audit.phase)
  const isApproved = ['approved', 'AUTO_APPROVED'].includes(audit.human_decision ?? '')
  const isRejected = audit.human_decision === 'REJECT'

  return (
    <div className="p-8 max-w-3xl">

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-semibold text-gray-900 font-mono">{audit.contract_id}</h1>
            <StatusBadge status={audit.human_decision ?? audit.phase} />
            {isRunning && (
              <div className="w-4 h-4 border-2 border-gray-200 border-t-emerald-500 rounded-full animate-spin" />
            )}
          </div>
          <p className="text-sm text-gray-500">
            Started {new Date(audit.started_at).toLocaleString('en-MY')}
          </p>
        </div>
      </div>

      {/* Phase tracker */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 mb-6">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-6">
          Audit Pipeline
        </p>
        <AuditPhaseTracker currentPhase={audit.phase} />
      </div>

      {/* Outcome banner */}
      {isApproved && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 mb-6 flex items-center gap-4">
          <span className="text-3xl">✅</span>
          <div>
            <p className="font-semibold text-emerald-800">Contract Approved</p>
            <p className="text-sm text-emerald-600 mt-0.5">
              {audit.human_decision === 'AUTO_APPROVED'
                ? `Auto-approved — risk score ${Math.round((audit.risk_score ?? 0) * 100)}/100 (below threshold)`
                : `Approved by ${audit.officer_id ?? 'Shariah Officer'}`
              }
            </p>
          </div>
        </div>
      )}

      {isRejected && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-5 mb-6 flex items-center gap-4">
          <span className="text-3xl">❌</span>
          <div>
            <p className="font-semibold text-red-800">Contract Rejected</p>
            {audit.officer_justification && (
              <p className="text-sm text-red-600 mt-0.5">{audit.officer_justification}</p>
            )}
          </div>
        </div>
      )}

      {/* Risk score (shown once simulator completes) */}
      {audit.risk_score != null && (
        <div className="mb-6">
          <RiskMeter score={audit.risk_score} size="lg" />
        </div>
      )}

      {/* Compliance results */}
      {audit.compliance_report?.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm mb-4">
          <div className="px-5 py-3 border-b border-gray-50">
            <p className="text-sm font-semibold text-gray-700">⚖️ Compliance Report</p>
          </div>
          <div className="divide-y divide-gray-50">
            {audit.compliance_report.map((r: any) => (
              <div key={r.clause_id} className="px-5 py-3 flex items-start gap-4">
                <span className={`mt-0.5 text-xs font-bold px-2 py-0.5 rounded ${
                  r.status === 'compliant'     ? 'bg-emerald-100 text-emerald-700'
                  : r.status === 'ambiguous'   ? 'bg-amber-100 text-amber-700'
                  : 'bg-red-100 text-red-700'
                }`}>
                  {r.clause_id}
                </span>
                <div className="flex-1">
                  <p className="text-xs text-gray-700">{r.explanation}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{r.bnm_reference}</p>
                </div>
                <StatusBadge status={r.status} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Adversarial findings */}
      {audit.adversarial_findings?.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
          <div className="px-5 py-3 border-b border-gray-50">
            <p className="text-sm font-semibold text-gray-700">😈 Devil's Advocate Findings</p>
          </div>
          <div className="divide-y divide-gray-50">
            {audit.adversarial_findings.map((f: any, i: number) => (
              <div key={i} className="px-5 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                    f.severity === 'high'   ? 'bg-red-100 text-red-700'
                    : f.severity === 'medium' ? 'bg-amber-100 text-amber-700'
                    : 'bg-gray-100 text-gray-600'
                  }`}>
                    {f.severity.toUpperCase()}
                  </span>
                  <span className="text-xs font-medium text-gray-500 uppercase">{f.risk_type}</span>
                  <span className="text-xs text-gray-400">— {f.clause_id}</span>
                </div>
                <p className="text-xs text-gray-700">{f.finding}</p>
                {f.loophole && (
                  <p className="text-xs text-gray-400 mt-0.5">↳ {f.loophole}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
