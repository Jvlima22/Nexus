import { getSupabaseAdmin } from "@/lib/supabase-admin";

/**
 * Valida um access_token do Supabase e devolve o user_id.
 * Server-side helper — usar dentro de server functions.
 */
export async function requireUser(accessToken: string): Promise<{ userId: string; email: string }> {
  if (!accessToken) {
    throw new Response("Não autenticado", { status: 401 });
  }
  const admin = getSupabaseAdmin();
  const { data, error } = await admin.auth.getUser(accessToken);
  if (error || !data.user) {
    throw new Response("Sessão inválida", { status: 401 });
  }
  return { userId: data.user.id, email: data.user.email ?? "" };
}
