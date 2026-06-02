/**
 * components/RiskMeter.tsx — Visual risk score display
 * Server component.
 */

interface RiskMeterProps {
  score: number   // 0.0 – 1.0
  size?: 'sm' | 'lg'
}

function getRiskLevel(score: number) {
  if (score < 0.3) return { label: 'Low Risk',      color: 'text-emerald-600', bar: 'bg-emerald-500', bg: 'bg-emerald-50 border-emerald-200' }
  if (score < 0.6) return { label: 'Moderate Risk', color: 'text-amber-600',   bar: 'bg-amber-500',   bg: 'bg-amber-50 border-amber-200' }
  if (score < 0.8) return { label: 'High Risk',     color: 'text-orange-600',  bar: 'bg-orange-500',  bg: 'bg-orange-50 border-orange-200' }
  return             { label: 'Critical Risk',  color: 'text-red-600',    bar: 'bg-red-500',    bg: 'bg-red-50 border-red-200' }
}

export default function RiskMeter({ score, size = 'sm' }: RiskMeterProps) {
  const { label, color, bar, bg } = getRiskLevel(score)
  const pct = Math.round(score * 100)

  if (size === 'lg') {
    return (
      <div className={`rounded-xl border p-6 ${bg}`}>
        <p className="text-sm font-medium text-gray-500 mb-1">Overall Risk Score</p>
        <div className="flex items-end gap-3 mb-4">
          <span className={`text-5xl font-bold ${color}`}>{pct}</span>
          <span className={`text-2xl font-medium ${color} mb-1`}>/100</span>
          <span className={`text-sm font-semibold ${color} mb-1.5 ml-1`}>{label}</span>
        </div>
        <div className="w-full bg-white rounded-full h-3 overflow-hidden border border-gray-200">
          <div
            className={`h-3 rounded-full transition-all duration-700 ${bar}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>0 — Low</span>
          <span>60 — Escalate</span>
          <span>100 — Critical</span>
        </div>
      </div>
    )
  }

  // Small inline version (for tables and cards)
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 bg-gray-200 rounded-full h-1.5">
        <div className={`h-1.5 rounded-full ${bar}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-medium ${color}`}>{pct}/100</span>
    </div>
  )
}
