'use client'

/**
 * components/Sidebar.tsx
 *
 * NEXT.JS NOTE: We need "use client" here because we use usePathname()
 * to highlight the active nav link. Any component using hooks or browser
 * APIs must be a Client Component with this directive at the top.
 */

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const navItems = [
  { href: '/',       label: 'Dashboard',  icon: '▦' },
  { href: '/upload', label: 'New Audit',  icon: '↑' },
  { href: '/log',    label: 'Audit Log',  icon: '≡' },
]

export default function Sidebar() {
  const pathname = usePathname()

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href)

  return (
    <aside className="w-64 bg-slate-900 flex flex-col shrink-0">

      {/* Logo / title */}
      <div className="px-6 py-5 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">SA</span>
          </div>
          <div>
            <p className="text-white text-sm font-semibold">Shariah Audit</p>
            <p className="text-slate-400 text-xs">Auto-Auditor v1.0</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ href, label, icon }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
              isActive(href)
                ? 'bg-emerald-600 text-white font-medium'
                : 'text-slate-400 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <span className="text-base">{icon}</span>
            {label}
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-slate-700">
        <p className="text-slate-500 text-xs">Bank Islam Malaysia Berhad</p>
        <p className="text-slate-600 text-xs mt-0.5">Shariah Governance Division</p>
      </div>
    </aside>
  )
}
