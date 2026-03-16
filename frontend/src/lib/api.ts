const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

const req = {
  "prompt": "What is the average monthly income by city tier?"
}

export async function queryBI(req: QueryRequest): Promise<QueryResponse> {
  console.log(`${API_BASE}/query`)
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API Error: ${text}`);
  }

  const data: QueryResponse = await res.json();
  return data;
}

export interface UploadCSVResponse {
  table_name: string;
  rows: number;
  columns: string[];
}

export async function uploadCSV(file: File): Promise<UploadCSVResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/upload-csv`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Upload Error: ${text}`);
  }

  const data: UploadCSVResponse = await res.json();
  return data;
}
