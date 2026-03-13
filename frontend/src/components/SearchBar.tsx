"use client";

interface SearchBarProps {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
  placeholder?: string;
}

export default function SearchBar({ value, onChange, onSubmit, loading, placeholder = "Ask a question about your data..." }: SearchBarProps) {
  return (
    <div className="flex w-full gap-2">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onSubmit()}
        placeholder={placeholder}
        disabled={loading}
        className="flex-1 rounded-lg border border-zinc-300 px-4 py-3 text-base outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 disabled:bg-zinc-100 disabled:opacity-70"
      />
      <button
        onClick={onSubmit}
        disabled={loading || !value.trim()}
        className="rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? "..." : "Query"}
      </button>
    </div>
  );
}
