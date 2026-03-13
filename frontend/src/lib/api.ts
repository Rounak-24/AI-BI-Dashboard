const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface QueryRequest {
  prompt: string;
  follow_up_context?: string | null;
  conversation_id?: string | null;
}

export interface QueryResponse {
  sql: string | null;
  data: Record<string, unknown>[];
  chart_type: string | null;
  insight: string;
  error: string | null;
}

export async function queryBI(req: QueryRequest): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function uploadCSV(file: File): Promise<{ table_name: string; rows: number; columns: string[] }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/upload-csv`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
