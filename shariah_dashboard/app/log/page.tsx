'use client'

/**
 * app/log/page.tsx — Full Audit History Log
 */

import { useState } from 'react'
import Link from 'next/link'
import useSWR from 'swr'
import StatusBadge from '@/components/StatusBadge'
import RiskMeter from '@/components/RiskMeter'

const fetcher = (url: string) => fetch(url).then(r => r.json())

const FILTERS = ['All', 'Awaiting Review', 'Approved', 'Rejected'] as const

export default function LogPage() {
  const [filter, setFilter] = useState<typeof FILTERS[number]>('All')
  const { data, error } = useSWR('/api/audit/list', fetcher, { refreshInterval: 5000 })

  const audits: any[] = data?.audits ?? []

  const filtered = audits.filter(a => {
    if (filter === 'All')              return true
    if (filter === 'Awaiting Review')  return a.phase === 'hitl_required'
    if (filter === 'Approved')         return ['APPROVE', 'AUTO_APPROVED'].includes(a.human_decision)
    if (filter === 'Rejected')         return a.human_decision === 'REJECT'
    return true
  })

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Audit Log</h1>
          <p className="text-sm text-gray-500 mt-1">Complete history of all Shariah contract audits</p>
        </div>
        <Link
          href="/upload"
          className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-emerald-700"
        >
          + New Audit
        </Link>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-5">
        {FILTERS.map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              filter === f
                ? 'bg-emerald-600 text-white'
                : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-300'
            }`}
          >
            {f}
          </button>
        ))}
        <span className="ml-2 self-center text-xs text-gray-400">
          {filtered.length} result{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
        {error ? (
          <p className="p-8 text-center text-red-400 text-sm">Failed to load audit log</p>
        ) : !data ? (
          <p className="p-8 text-center text-gray-400 text-sm">Loading...</p>
        ) : filtered.length === 0 ? (
          <p className="p-8 text-center text-gray-400 text-sm">No audits found for this filter</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-50">
                {['Contract ID', 'Started', 'Risk Score', 'Status', 'Officer', 'Action'].map(h => (
                  <th key={h} className="text-left px-5 py-3 text-xs font-medium text-gray-400 uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map((audit: any) => (
                <tr key={audit.contract_id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-3.5 font-mono text-gray-800 font-medium text-xs">
                    {audit.contract_id}
                  </td>
                  <td className="px-5 py-3.5 text-gray-500 text-xs">
                    {new Date(audit.started_at).toLocaleString('en-MY', {
                      dateStyle: 'medium', timeStyle: 'short'
                    })}
                  </td>
                  <td className="px-5 py-3.5">
                    {audit.risk_score != null
                      ? <RiskMeter score={audit.risk_score} />
                      : <span className="text-gray-300 text-xs">—</span>
                    }
                  </td>
                  <td className="px-5 py-3.5">
                    <StatusBadge status={audit.human_decision ?? audit.phase} />
                  </td>
                  <td className="px-5 py-3.5 text-xs text-gray-500">
                    {audit.officer_id ?? '—'}
                  </td>
                  <td className="px-5 py-3.5">
                    {audit.phase === 'hitl_required' ? (
                      <Link
                        href={`/review/${audit.contract_id}`}
                        className="text-xs font-medium text-amber-600 hover:underline"
                      >
                        Review →
                      </Link>
                    ) : (
                      <Link
                        href={`/audit/${audit.contract_id}`}
                        className="text-xs text-gray-400 hover:text-gray-600 hover:underline"
                      >
                        View →
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
