import { createClient } from "@supabase/supabase-js";

// The anon key is a public, RLS-protected key — safe to ship in the frontend.
// Overridable via Vite env if you ever rotate projects.
const SUPABASE_URL =
  import.meta.env.VITE_SUPABASE_URL || "https://dugsdvoqlpqcagrhnyvc.supabase.co";
const SUPABASE_ANON_KEY =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR1Z3Nkdm9xbHBxY2FncmhueXZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODIwMTksImV4cCI6MjA5Njc1ODAxOX0.a9ZxtuGYMNezh2Ghd5rStxikDanE7xWwFCYWjoW5HcE";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
  },
});
