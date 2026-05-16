import { createClient } from '@supabase/supabase-js'

// Paste VITE_SUPABASE_URL here
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL

// Paste VITE_SUPABASE_ANON_KEY here
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn("Missing Supabase environment variables. Please fill in your .env file.");
}

export const supabase = createClient(supabaseUrl || "", supabaseAnonKey || "")
