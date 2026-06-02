import { NextResponse } from 'next/server'

export async function GET() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? ''
  const key = process.env.SUPABASE_SERVICE_KEY ?? ''
  const api = process.env.NEXT_PUBLIC_API_URL ?? ''

  return NextResponse.json({
    NEXT_PUBLIC_SUPABASE_URL: {
      present:   url.length > 0,
      length:    url.length,
      starts_with: url.slice(0, 8),        // shows "https://" or "" without leaking host
      has_trailing_slash: url.endsWith('/'),
    },
    SUPABASE_SERVICE_KEY: {
      present: key.length > 0,
      length:  key.length,
    },
    NEXT_PUBLIC_API_URL: {
      value: api,    // safe to show — it's just localhost
    },
  })
}
