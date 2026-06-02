'use client'

/**
 * app/upload/page.tsx — Contract upload
 *
 * NEXT.JS NOTE: "use client" is needed here because we use useState,
 * useRef, and event handlers. This component runs in the browser.
 *
 * On submit, it calls our Next.js API route POST /api/audit/start,
 * which in turn triggers the FastAPI Python backend.
 */

import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'

export default function UploadPage() {
  const router = useRouter()

  const [contractId, setContractId]     = useState('')
  const [contractText, setContractText] = useState('')
  const [fileName, setFileName]         = useState('')
  const [isDragging, setIsDragging]     = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError]               = useState('')

  const fileRef = useRef<HTMLInputElement>(null)

  // ── File handling ────────────────────────────────────────────────────────
  const handleFile = async (file: File) => {
    if (file.type !== 'application/pdf' && !file.name.endsWith('.txt')) {
      setError('Please upload a PDF or .txt contract file.')
      return
    }
    setFileName(file.name)
    setError('')

    // For MVP: read file as text
    // In production: send the raw PDF to FastAPI and use PyMuPDF server-side
    const text = await file.text()
    setContractText(text)

    // Auto-fill contract ID from filename if empty
    if (!contractId) {
      const name = file.name.replace(/\.(pdf|txt)$/i, '').toUpperCase()
      setContractId(name)
    }
  }

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) handleFile(e.target.files[0])
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0])
  }

  // ── Submit ────────────────────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!contractId.trim())   return setError('Contract ID is required.')
    if (!contractText.trim()) return setError('Please upload a contract file first.')

    setIsSubmitting(true)
    setError('')

    try {
      const res = await fetch('/api/audit/start', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ contractId: contractId.trim(), contractText }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.error ?? 'Failed to start audit')
      }

      const { contractId: id } = await res.json()
      // Navigate to the live status page
      router.push(`/audit/${id}`)
    } catch (err: any) {
      setError(err.message ?? 'Something went wrong.')
      setIsSubmitting(false)
    }
  }

  return (
    <div className="p-8 max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">New Audit</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload a Murabaha contract to begin agentic Shariah analysis
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">

        {/* Contract ID */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Contract ID
          </label>
          <input
            type="text"
            value={contractId}
            onChange={e => setContractId(e.target.value)}
            placeholder="e.g. MUR-2024-0088"
            className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
        </div>

        {/* File drop zone */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Contract File
          </label>
          <div
            onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={onDrop}
            onClick={() => fileRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
              isDragging
                ? 'border-emerald-400 bg-emerald-50'
                : fileName
                ? 'border-emerald-300 bg-emerald-50'
                : 'border-gray-200 hover:border-gray-300 bg-gray-50'
            }`}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.txt"
              onChange={onFileChange}
              className="hidden"
            />

            {fileName ? (
              <div>
                <div className="text-3xl mb-2">📄</div>
                <p className="text-sm font-medium text-emerald-700">{fileName}</p>
                <p className="text-xs text-gray-400 mt-1">Click to replace</p>
              </div>
            ) : (
              <div>
                <div className="text-3xl mb-2">↑</div>
                <p className="text-sm font-medium text-gray-600">
                  Drop your contract PDF here
                </p>
                <p className="text-xs text-gray-400 mt-1">or click to browse</p>
                <p className="text-xs text-gray-300 mt-3">PDF or TXT — max 10MB</p>
              </div>
            )}
          </div>
        </div>

        {/* What the system will do */}
        <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
          <p className="text-xs font-medium text-blue-700 mb-2">The audit pipeline will:</p>
          <ol className="space-y-1">
            {[
              '🔍  Extract and classify all contract clauses',
              '⚖️   Cross-reference each clause against BNM guidelines',
              '😈  Adversarially probe for loopholes (max 3 passes)',
              '🕌  Simulate Shariah board deliberation and generate risk score',
            ].map(step => (
              <li key={step} className="text-xs text-blue-600">{step}</li>
            ))}
          </ol>
        </div>

        {/* Error */}
        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full bg-emerald-600 text-white py-3 rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? 'Starting audit...' : 'Start Shariah Audit →'}
        </button>
      </form>
    </div>
  )
}
