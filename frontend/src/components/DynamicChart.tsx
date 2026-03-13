"use client";

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";

type ChartType = "bar" | "line" | "pie" | "area" | "table";

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

interface DynamicChartProps {
  data: Record<string, unknown>[];
  chartType: ChartType;
}

function inferKeys(data: Record<string, unknown>[]): { xKey: string; valueKeys: string[] } {
  if (data.length === 0) return { xKey: "", valueKeys: [] };
  const keys = Object.keys(data[0]);
  const numericKeys = keys.filter((k) => {
    const v = data[0][k];
    return typeof v === "number" || (typeof v === "string" && !isNaN(Number(v)));
  });
  const nonNumericKeys = keys.filter((k) => !numericKeys.includes(k));
  const xKey = nonNumericKeys[0] || numericKeys[0] || keys[0];
  const valueKeys = xKey ? keys.filter((k) => k !== xKey).slice(0, 5) : keys.slice(0, 5);
  return { xKey, valueKeys };
}

export default function DynamicChart({ data, chartType }: DynamicChartProps) {
  const { xKey, valueKeys } = inferKeys(data);

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-zinc-200 bg-zinc-50 text-zinc-500">
        No data to display
      </div>
    );
  }

  if (chartType === "table") {
    const cols = Object.keys(data[0]);
    return (
      <div className="overflow-x-auto rounded-lg border border-zinc-200">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-200 bg-zinc-50">
              {cols.map((c) => (
                <th key={c} className="px-4 py-2 text-left font-medium">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.slice(0, 100).map((row, i) => (
              <tr key={i} className="border-b border-zinc-100">
                {cols.map((c) => (
                  <td key={c} className="px-4 py-2">
                    {String(row[c] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  const commonProps = {
    data,
    margin: { top: 16, right: 16, left: 16, bottom: 16 },
  };

  const renderChart = () => {
    switch (chartType) {
      case "bar":
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            {valueKeys.map((k, i) => (
              <Bar key={k} dataKey={k} fill={COLORS[i % COLORS.length]} />
            ))}
          </BarChart>
        );
      case "line":
        return (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            {valueKeys.map((k, i) => (
              <Line key={k} type="monotone" dataKey={k} stroke={COLORS[i % COLORS.length]} strokeWidth={2} />
            ))}
          </LineChart>
        );
      case "area":
        return (
          <AreaChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            {valueKeys.map((k, i) => (
              <Area key={k} type="monotone" dataKey={k} stackId="1" fill={COLORS[i % COLORS.length]} stroke={COLORS[i % COLORS.length]} />
            ))}
          </AreaChart>
        );
      case "pie":
        const pieData = data.map((row) => ({
          name: String(row[xKey] ?? ""),
          value: Number(row[valueKeys[0]] ?? 0),
        }));
        return (
          <PieChart {...commonProps}>
            <Pie
              data={pieData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={120}
              label={(e) => e.name}
            >
              {pieData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        );
      default:
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey={valueKeys[0] || "value"} fill={COLORS[0]} />
          </BarChart>
        );
    }
  };

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
}
