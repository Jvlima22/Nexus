import { getSupabaseAdmin } from "@/lib/supabase-admin";

export type AuditAction = "connect" | "test" | "revoke" | "error";

export async function logAudit(
  userId: string,
  broker: string,
  action: AuditAction,
  detail: Record<string, unknown> = {},
): Promise<void> {
  const admin = getSupabaseAdmin();
  await admin.from("broker_audit_log").insert({
    user_id: userId,
    broker,
    action,
    detail,
  });
}
