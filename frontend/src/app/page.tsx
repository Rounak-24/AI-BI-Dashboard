"use client";

import { useState, useCallback } from "react";
import SearchBar from "@/components/SearchBar";
import DynamicChart from "@/components/DynamicChart";
import { queryBI, uploadCSV, type QueryResponse } from "@/lib/api";

type ChartType = "bar" | "line" | "pie" | "area" | "table";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [followUpSql, setFollowUpSql] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const runQuery = useCallback(async (queryPrompt?: string) => {
    const q = (queryPrompt ?? prompt).trim();
    if (!q) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await queryBI({
        prompt: q,
        follow_up_context: followUpSql,
      });
      setResult(res);
      if (res.sql) setFollowUpSql(res.sql);
    } catch (e) {
      setResult({
        sql: null,
        data: [],
        chart_type: null,
        insight: e instanceof Error ? e.message : "Request failed",
        error: "REQUEST_FAILED",
      });
    } finally {
      setLoading(false);
    }
  }, [prompt, followUpSql]);

  const handleUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    try {
      const r = await uploadCSV(file);
      setUploadError(null);
      setPrompt(`Show me data from the ${r.table_name} table`);
      alert(`Uploaded ${r.rows} rows. Table: ${r.table_name}. You can now query it.`);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }, []);

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto max-w-4xl px-4 py-4">
          <h1 className="text-xl font-semibold text-zinc-900">BI Dashboard</h1>
          <p className="text-sm text-zinc-500">Ask questions in plain English to explore your data</p>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-6">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <SearchBar value={prompt} onChange={setPrompt} onSubmit={() => runQuery()} loading={loading} />
          <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-zinc-300 bg-white px-4 py-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50">
            <input
              type="file"
              accept=".csv"
              onChange={handleUpload}
              disabled={uploading}
              className="hidden"
            />
            {uploading ? "Uploading..." : "Upload CSV"}
          </label>
        </div>

        {uploadError && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {uploadError}
          </div>
        )}

        {loading && (
          <div className="flex h-48 items-center justify-center rounded-lg border border-zinc-200 bg-white">
            <div className="flex flex-col items-center gap-2">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
              <span className="text-sm text-zinc-500">Generating response...</span>
            </div>
          </div>
        )}

        {!loading && result && (
          <div className="space-y-4">
            {result.error ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-800">
                <p className="font-medium">Unable to answer</p>
                <p className="text-sm">{result.insight}</p>
              </div>
            ) : (
              <>
                <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
                  <p className="mb-2 text-sm font-medium text-zinc-600">Insight</p>
                  <p className="text-zinc-900">{result.insight}</p>
                </div>
                {result.sql && (
                  <details className="rounded-lg border border-zinc-200 bg-zinc-900 text-zinc-100">
                    <summary className="cursor-pointer px-4 py-2 text-sm font-mono">View SQL</summary>
                    <pre className="overflow-x-auto px-4 pb-4 pt-1 text-xs">{result.sql}</pre>
                  </details>
                )}
                <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
                  <DynamicChart
                    data={result.data}
                    chartType={(result.chart_type as ChartType) || "table"}
                  />
                </div>
              </>
            )}
          </div>
        )}

        {!loading && !result && (
          <div className="rounded-lg border border-dashed border-zinc-300 bg-white p-12 text-center">
            <p className="mb-2 text-zinc-600">Example questions</p>
            <div className="flex flex-wrap justify-center gap-2">
              {[
                "Average monthly income by city tier",
                "Count of customers by shopping preference",
                "Online vs store spend by gender",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    setPrompt(q);
                    runQuery(q);
                  }}
                  className="rounded-full border border-zinc-300 px-4 py-2 text-sm text-zinc-700 hover:bg-zinc-50"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
