/**
 * components/AuditPhaseTracker.tsx — Horizontal phase stepper
 * Server component — receives current phase as a prop.
 */

type Phase = string

const PHASES = [
  { key: 'extraction',      label: 'Extraction',       icon: '🔍', desc: 'Parsing clauses' },
  { key: 'compliance',      label: 'Compliance',        icon: '⚖️',  desc: 'BNM cross-check' },
  { key: 'devils_advocate', label: "Devil's Advocate",  icon: '😈', desc: 'Probing loopholes' },
  { key: 'simulator',       label: 'Board Simulator',   icon: '🕌', desc: 'Synthesising report' },
]

// Map terminal phases to the last completed step index
const PHASE_INDEX: Record<string, number> = {
  queued:          -1,
  extraction:       0,
  compliance:       1,
  devils_advocate:  2,
  simulator:        3,
  hitl_required:    3,
  approved:         3,
  AUTO_APPROVED:    3,
  rejected:         3,
  APPROVE:          3,
  REJECT:           3,
}

const isTerminal = (phase: string) =>
  ['hitl_required', 'approved', 'rejected', 'AUTO_APPROVED', 'APPROVE', 'REJECT'].includes(phase)

export default function AuditPhaseTracker({ currentPhase }: { currentPhase: Phase }) {
  const activeIdx = PHASE_INDEX[currentPhase] ?? -1
  const done = isTerminal(currentPhase)

  return (
    <div className="w-full">
      <div className="flex items-start">
        {PHASES.map((phase, idx) => {
          const isComplete = done ? true : idx < activeIdx
          const isActive   = !done && idx === activeIdx
          const isPending  = !done && idx > activeIdx

          return (
            <div key={phase.key} className="flex-1 flex flex-col items-center relative">
              {/* Connector line (not for last item) */}
              {idx < PHASES.length - 1 && (
                <div
                  className={`absolute top-5 left-1/2 w-full h-0.5 transition-colors duration-500 ${
                    isComplete ? 'bg-emerald-400' : 'bg-gray-200'
                  }`}
                />
              )}

              {/* Circle */}
              <div
                className={`relative z-10 w-10 h-10 rounded-full flex items-center justify-center text-lg border-2 transition-all duration-300 ${
                  isComplete
                    ? 'bg-emerald-500 border-emerald-500'
                    : isActive
                    ? 'bg-white border-blue-500 animate-pulse-slow'
                    : 'bg-white border-gray-200'
                }`}
              >
                {isComplete ? (
                  <span className="text-white text-sm">✓</span>
                ) : (
                  <span className={isPending ? 'opacity-30' : ''}>{phase.icon}</span>
                )}
              </div>

              {/* Label */}
              <div className="mt-2 text-center px-1">
                <p className={`text-xs font-medium ${
                  isComplete ? 'text-emerald-600'
                  : isActive  ? 'text-blue-600'
                  : 'text-gray-400'
                }`}>
                  {phase.label}
                </p>
                <p className={`text-xs mt-0.5 ${
                  isActive ? 'text-blue-400' : 'text-gray-300'
                }`}>
                  {isActive ? phase.desc : ''}
                </p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
