'use client'

/**
 * app/review/[id]/page.tsx — HITL Officer Review Screen
 *
 * This is the most critical page: the Shariah officer sees the full dossier
 * (risk score, audit summary, key concerns, adversarial findings) and
 * submits a decision with a mandatory written justification.
 *
 * On submit, it calls POST /api/review/[id] which resumes the paused
 * LangGraph pipeline with the officer's decision.
 */

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'
import RiskMeter from '@/components/RiskMeter'
import AuditPhaseTracker from '@/components/AuditPhaseTracker'

const fetcher = (url: string) => fetch(url).then(r => r.json())

export default function ReviewPage({ params }: { params: { id: string } }) {
  const { id } = params
  const router  = useRouter()

  const { data: audit, error } = useSWR(`/api/audit/${id}`, fetcher)

  const [officerName,    setOfficerName]    = useState('')
  const [decision,       setDecision]       = useState<'APPROVE' | 'REJECT' | ''>('')
  const [justification,  setJustification]  = useState('')
  const [isSubmitting,   setIsSubmitting]   = useState(false)
  const [submitError,    setSubmitError]    = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!decision)              return setSubmitError('Please select a decision.')
    if (!justification.trim()) return setSubmitError('Written justification is mandatory.')
    if (!officerName.trim())   return setSubmitError('Officer name is required for audit trail.')

    setIsSubmitting(true)
    setSubmitError('')

    try {
      const res = await fetch(`/api/review/${id}`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ decision, justification, officerName }),
      })

      if (!res.ok) throw new Error('Submission failed')

      // Navigate back to audit status to see the recorded outcome
      router.push(`/audit/${id}`)
    } catch {
      setSubmitError('Failed to submit decision. Please try again.')
      setIsSubmitting(false)
    }
  }

  if (error) return (
    <div className="p-8 text-red-500">Failed to load review data for contract {id}</div>
  )

  if (!audit) return (
    <div className="p-8 text-gray-400 text-sm">Loading review dossier...</div>
  )

  // Parse board report JSON
  let boardReport: any = {}
  try { boardReport = audit.audit_report ? JSON.parse(audit.audit_report) : {} } catch {}

  const highFindings = (audit.adversarial_findings ?? []).filter(
    (f: any) => f.severity === 'high'
  )

  return (
    <div className="p-8 max-w-3xl">

      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-amber-600 font-medium mb-2">
          <span>⚠</span>
          <span>ESCALATED — Shariah Officer Review Required</span>
        </div>
        <h1 className="text-2xl font-semibold text-gray-900 font-mono">{audit.contract_id}</h1>
        <p className="text-sm text-gray-500 mt-1">
          The audit system has flagged this contract. Your review and decision are required.
        </p>
      </div>

      {/* Phase tracker (all complete) */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 mb-5">
        <AuditPhaseTracker currentPhase="hitl_required" />
      </div>

      {/* Risk score — prominently displayed */}
      {audit.risk_score != null && (
        <div className="mb-5">
          <RiskMeter score={audit.risk_score} size="lg" />
        </div>
      )}

      {/* Audit summary */}
      {boardReport.audit_summary && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 mb-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
            Board Simulator Summary
          </p>
          <p className="text-sm text-gray-700 leading-relaxed">{boardReport.audit_summary}</p>
        </div>
      )}

      {/* Key concerns */}
      {boardReport.key_concerns?.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 mb-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Key Concerns
          </p>
          <ul className="space-y-2">
            {boardReport.key_concerns.map((c: string, i: number) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-amber-500 mt-0.5">•</span>
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* High-severity adversarial findings */}
      {highFindings.length > 0 && (
        <div className="bg-red-50 border border-red-100 rounded-xl p-5 mb-4">
          <p className="text-xs font-semibold text-red-400 uppercase tracking-wide mb-3">
            High-Severity Flags ({highFindings.length})
          </p>
          <div className="space-y-3">
            {highFindings.map((f: any, i: number) => (
              <div key={i} className="bg-white rounded-lg border border-red-100 p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-bold text-red-700 bg-red-100 px-2 py-0.5 rounded">
                    {f.risk_type.toUpperCase()}
                  </span>
                  <span className="text-xs text-gray-500">{f.clause_id}</span>
                </div>
                <p className="text-xs text-gray-700">{f.finding}</p>
                {f.loophole && (
                  <p className="text-xs text-red-500 mt-1">↳ {f.loophole}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Approval conditions */}
      {boardReport.conditions?.length > 0 && (
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-5 mb-6">
          <p className="text-xs font-semibold text-blue-400 uppercase tracking-wide mb-2">
            Conditions for Approval
          </p>
          <ul className="space-y-1">
            {boardReport.conditions.map((c: string, i: number) => (
              <li key={i} className="text-sm text-blue-700 flex gap-2">
                <span>✦</span>{c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Decision form ── */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <p className="text-sm font-semibold text-gray-900 mb-5">
          🕌 Your Decision
        </p>

        <form onSubmit={handleSubmit} className="space-y-5">

          {/* Officer name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Officer Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={officerName}
              onChange={e => setOfficerName(e.target.value)}
              placeholder="e.g. Dr. Aminah binti Yusof"
              className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          {/* Decision buttons */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Decision <span className="text-red-500">*</span>
            </label>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setDecision('APPROVE')}
                className={`flex-1 py-3 rounded-xl border-2 text-sm font-semibold transition-all ${
                  decision === 'APPROVE'
                    ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                    : 'border-gray-200 text-gray-500 hover:border-gray-300'
                }`}
              >
                ✓ Approve
              </button>
              <button
                type="button"
                onClick={() => setDecision('REJECT')}
                className={`flex-1 py-3 rounded-xl border-2 text-sm font-semibold transition-all ${
                  decision === 'REJECT'
                    ? 'border-red-500 bg-red-50 text-red-700'
                    : 'border-gray-200 text-gray-500 hover:border-gray-300'
                }`}
              >
                ✗ Reject
              </button>
            </div>
          </div>

          {/* Justification */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Written Justification <span className="text-red-500">*</span>
            </label>
            <textarea
              value={justification}
              onChange={e => setJustification(e.target.value)}
              rows={4}
              placeholder="Provide a detailed rationale for your decision. This will be recorded in the permanent audit trail."
              className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <p className="text-xs text-gray-400 mt-1">
              {justification.length} characters — minimum 20 recommended
            </p>
          </div>

          {/* Error */}
          {submitError && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {submitError}
            </p>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={isSubmitting || !decision}
            className={`w-full py-3 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              decision === 'APPROVE'
                ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                : decision === 'REJECT'
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-gray-200 text-gray-400'
            }`}
          >
            {isSubmitting
              ? 'Recording decision...'
              : decision
              ? `Confirm ${decision === 'APPROVE' ? 'Approval' : 'Rejection'}`
              : 'Select a decision above'
            }
          </button>

          <p className="text-xs text-center text-gray-400">
            This decision will be permanently logged with your name, timestamp, and justification.
          </p>
        </form>
      </div>
    </div>
  )
}
