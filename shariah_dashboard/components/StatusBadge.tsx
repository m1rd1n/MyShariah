/**
 * components/StatusBadge.tsx — Reusable status pill
 * Server component (no hooks needed).
 */

type Status =
  | 'queued' | 'extraction' | 'compliance' | 'devils_advocate'
  | 'simulator' | 'hitl_required' | 'approved' | 'rejected' | 'AUTO_APPROVED'

const config: Record<string, { label: string; classes: string }> = {
  queued:          { label: 'Queued',          classes: 'bg-slate-100 text-slate-600' },
  extraction:      { label: 'Extracting',      classes: 'bg-blue-100 text-blue-700' },
  compliance:      { label: 'Compliance',      classes: 'bg-blue-100 text-blue-700' },
  devils_advocate: { label: 'Probing',         classes: 'bg-purple-100 text-purple-700' },
  simulator:       { label: 'Simulating',      classes: 'bg-purple-100 text-purple-700' },
  hitl_required:   { label: 'Awaiting Review', classes: 'bg-amber-100 text-amber-700' },
  approved:        { label: 'Approved',        classes: 'bg-emerald-100 text-emerald-700' },
  AUTO_APPROVED:   { label: 'Auto-Approved',   classes: 'bg-emerald-100 text-emerald-700' },
  rejected:        { label: 'Rejected',        classes: 'bg-red-100 text-red-700' },
  APPROVE:         { label: 'Approved',        classes: 'bg-emerald-100 text-emerald-700' },
  REJECT:          { label: 'Rejected',        classes: 'bg-red-100 text-red-700' },
}

export default function StatusBadge({ status }: { status: string }) {
  const { label, classes } = config[status] ?? {
    label: status,
    classes: 'bg-gray-100 text-gray-600',
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${classes}`}>
      {label}
    </span>
  )
}
