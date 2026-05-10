import { createClient } from '@supabase/supabase-js'

// BURAYA VITE_SUPABASE_URL KEY'İNİ YAPIŞTIR
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL

// BURAYA VITE_SUPABASE_ANON_KEY KEY'İNİ YAPIŞTIR
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn("Eksik Supabase ortam değişkenleri. Lütfen .env dosyasını doldurun.");
}

export const supabase = createClient(supabaseUrl || "", supabaseAnonKey || "")
