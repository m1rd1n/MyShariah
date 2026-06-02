/**
 * lib/supabase.ts — Supabase client for Next.js
 *
 * Uses the SERVICE ROLE key — this file is server-side only.
 * Never import this in a Client Component ("use client").
 * The service role key bypasses RLS and must stay secret.
 *
 * SETUP:
 *   Add to .env.local:
 *     NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
 *     SUPABASE_SERVICE_KEY=your-service-role-key
 */

import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.SUPABASE_SERVICE_KEY!

if (!supabaseUrl || !supabaseKey) {
  console.warn(
    '[Supabase] Missing env vars. Add NEXT_PUBLIC_SUPABASE_URL and ' +
    'SUPABASE_SERVICE_KEY to .env.local'
  )
}

// Single client instance reused across all API route calls
export const supabase = createClient(supabaseUrl ?? '', supabaseKey ?? '')
