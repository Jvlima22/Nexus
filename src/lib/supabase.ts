import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

if (!url || !anonKey) {
  console.warn(
    "[supabase] VITE_SUPABASE_URL ou VITE_SUPABASE_ANON_KEY ausentes — auth e queries vão falhar até o .env ser preenchido.",
  );
}

export const supabase: SupabaseClient = createClient(url ?? "http://localhost", anonKey ?? "anon", {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
