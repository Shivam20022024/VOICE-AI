import React, { useState, useMemo, useEffect } from "react";
import {
  UploadCloud,
  Users,
  ArrowUpRight,
  Clock,
  BarChart3,
  Download,
  CalendarDays,
  FileAudio,
} from "lucide-react";

import {
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from "recharts";

import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import { CallInteraction } from "../types";
import { api } from "../services/api";

interface AnalyticsProps {
  onSelectCall: (callId: string) => void;
  interactions: CallInteraction[];
  onAnalysisComplete: () => void;
}

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: React.ReactNode;
}

interface ChartDatum {
  name: string;
  value: number;
}

const TOPIC_COLORS = ["#0f766e", "#2563eb", "#16a34a", "#ea580c", "#7c3aed"];
const SENTIMENT_COLORS = ["#16a34a", "#94a3b8", "#dc2626"];
const WEEKDAY_COLORS = [
  "#2563eb",
  "#16a34a",
  "#ea580c",
  "#dc2626",
  "#7c3aed",
  "#0d9488",
  "#ca8a04",
];

const downloadAudio = (callId: string) => {
  window.open(`http://localhost:8000/download/audio/${callId}`, "_blank");
};

const formatShortDate = (value?: string) => {
  if (!value) return "N/A";
  const date = new Date(value);
  if (isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

const totalFromData = (data: ChartDatum[]) =>
  data.reduce((sum, item) => sum + item.value, 0);

const parseDurationLabelToSeconds = (value?: string): number | undefined => {
  if (!value) return undefined;
  const lowered = value.toLowerCase();
  const minMatch = lowered.match(/(\d+)\s*m/);
  const secMatch = lowered.match(/(\d+)\s*s/);
  const mins = minMatch ? Number(minMatch[1]) : 0;
  const secs = secMatch ? Number(secMatch[1]) : 0;
  const total = mins * 60 + secs;
  return total > 0 ? total : undefined;
};

const formatDurationFromSeconds = (seconds?: number): string => {
  if (typeof seconds !== "number" || Number.isNaN(seconds) || seconds <= 0) {
    return "--";
  }
  const rounded = Math.round(seconds);
  const mins = Math.floor(rounded / 60);
  const secs = rounded % 60;
  return `${mins}m ${secs.toString().padStart(2, "0")}s`;
};

const Analytics: React.FC<AnalyticsProps> = ({
  onSelectCall,
  interactions,
  onAnalysisComplete,
}) => {
  const [viewState, setViewState] = useState<"ANALYZING" | "DASHBOARD">("DASHBOARD");
  const [totalCalls, setTotalCalls] = useState<number>(0);

  const processFile = async (file: File) => {
    setViewState("ANALYZING");
    try {
      await api.uploadAudio(file);
      await onAnalysisComplete();
    } finally {
      setViewState("DASHBOARD");
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) processFile(e.target.files[0]);
  };

  useEffect(() => {
    setTotalCalls(interactions.length);
  }, [interactions]);

  const avgDuration = useMemo(() => {
    const durations = interactions
      .map(i =>
        typeof i.durationSeconds === "number"
          ? i.durationSeconds
          : parseDurationLabelToSeconds(i.duration)
      )
      .filter((v): v is number => typeof v === "number" && v > 0);

    if (!durations.length) return "--";
    const avgSeconds = durations.reduce((sum, current) => sum + current, 0) / durations.length;
    return formatDurationFromSeconds(avgSeconds);
  }, [interactions]);

  const conversionRate = useMemo(() => {
    if (!interactions.length) return 0;
    const positives = interactions.filter(i =>
      (i.sentiment || "").toLowerCase().includes("positive")
    ).length;
    return Math.round((positives / interactions.length) * 100);
  }, [interactions]);

  const latestCallDate = useMemo(() => {
    if (!interactions.length) return "No calls yet";
    const latest = [...interactions]
      .map(i => new Date(i.date))
      .filter(d => !isNaN(d.getTime()))
      .sort((a, b) => b.getTime() - a.getTime())[0];
    if (!latest) return "No valid date";
    return latest.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }, [interactions]);

  const sentimentData = useMemo(() => {
    const c = { positive: 0, neutral: 0, negative: 0 };
    interactions.forEach(i => {
      const s = (i.sentiment || "neutral").toLowerCase();
      if (s.includes("positive")) c.positive++;
      else if (s.includes("negative")) c.negative++;
      else c.neutral++;
    });
    return [
      { name: "Positive", value: c.positive },
      { name: "Neutral", value: c.neutral },
      { name: "Negative", value: c.negative },
    ];
  }, [interactions]);

  const trendingTopics = useMemo(() => {
    const topicCount: Record<string, number> = {};
    interactions.forEach(call => {
      if (Array.isArray(call.tags)) {
        call.tags.forEach(tag => {
          topicCount[tag] = (topicCount[tag] || 0) + 1;
        });
      }
    });

    return Object.entries(topicCount).map(([name, value]) => ({
      name,
      value,
    }));
  }, [interactions]);

  const weeklyCallsPieData = useMemo(() => {
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const map: Record<string, number> = {
      Mon: 0,
      Tue: 0,
      Wed: 0,
      Thu: 0,
      Fri: 0,
      Sat: 0,
      Sun: 0,
    };

    interactions.forEach(call => {
      if (!call.date) return;
      const d = new Date(call.date);
      if (!isNaN(d.getTime())) {
        const day = d.toLocaleString("en-US", { weekday: "short" });
        if (map[day] !== undefined) map[day]++;
      }
    });

    return days.map(day => ({
      name: day,
      value: map[day],
    }));
  }, [interactions]);

  if (viewState === "ANALYZING") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <h3 className="text-xl font-semibold">Processing with AI...</h3>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-24 pb-12 bg-slate-100/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs font-semibold tracking-[0.14em] uppercase text-slate-500">
                Voice Performance Dashboard
              </p>
              <h1 className="mt-2 text-2xl sm:text-3xl font-bold text-slate-900">
                Call Analytics Overview
              </h1>
              <p className="mt-2 text-sm text-slate-600">
                Monitor call quality, sentiment trends, and weekly performance in one place.
              </p>
            </div>

            <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
              <CalendarDays size={16} className="text-slate-500" />
              Latest call: <span className="font-semibold text-slate-900">{latestCallDate}</span>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <Button onClick={() => document.getElementById("file-upload")?.click()} className="gap-2">
              <UploadCloud size={16} />
              Upload New Audio
            </Button>
            <Button variant="outline" onClick={() => api.downloadOverallExcel()} className="gap-2">
              <Download size={16} />
              Overall Calls
            </Button>
            <Button variant="outline" onClick={() => api.downloadWeeklyCallsExcel()} className="gap-2">
              <Download size={16} />
              Weekly Calls
            </Button>
            <Button variant="outline" onClick={() => api.downloadWeeklySalesExcel()} className="gap-2">
              <Download size={16} />
              Weekly Sales
            </Button>
          </div>

          <input
            id="file-upload"
            type="file"
            hidden
            accept="audio/*"
            onChange={handleFileInput}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <StatCard
            title="Total Calls"
            value={totalCalls}
            subtitle="Records analyzed"
            icon={<Users size={18} />}
          />
          <StatCard
            title="Connection Rate"
            value="100%"
            subtitle="Reachability baseline"
            icon={<ArrowUpRight size={18} />}
          />
          <StatCard
            title="Avg Duration"
            value={avgDuration}
            subtitle="Talk time per interaction"
            icon={<Clock size={18} />}
          />
          <StatCard
            title="Conversion Rate"
            value={`${conversionRate}%`}
            subtitle="Positive sentiment share"
            icon={<BarChart3 size={18} />}
          />
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          <Card className="p-6">
            <div className="mb-4">
              <h3 className="font-semibold text-slate-900">Trending Topics</h3>
              <p className="text-xs text-slate-500 mt-1">Top tags from recent interactions</p>
            </div>
            <div className="relative">
              <ResponsiveContainer height={250}>
                <PieChart>
                  <Pie data={trendingTopics} dataKey="value" nameKey="name" innerRadius={62} outerRadius={92}>
                    {trendingTopics.map((_, i) => (
                      <Cell key={i} fill={TOPIC_COLORS[i % TOPIC_COLORS.length]} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-slate-900">{totalFromData(trendingTopics)}</span>
                <span className="text-xs text-slate-500">Total Tags</span>
              </div>
            </div>
            <div className="mt-4 space-y-2">
              {trendingTopics.length ? (
                trendingTopics.slice(0, 5).map((item, i) => (
                  <div key={item.name} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2 text-slate-700">
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: TOPIC_COLORS[i % TOPIC_COLORS.length] }}
                      />
                      <span>{item.name}</span>
                    </div>
                    <span className="font-semibold text-slate-900">{item.value}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500">No topic data available.</p>
              )}
            </div>
          </Card>

          <Card className="p-6">
            <div className="mb-4">
              <h3 className="font-semibold text-slate-900">Sentiment Distribution</h3>
              <p className="text-xs text-slate-500 mt-1">Positive, neutral, and negative split</p>
            </div>
            <div className="relative">
              <ResponsiveContainer height={250}>
                <PieChart>
                  <Pie data={sentimentData} dataKey="value" nameKey="name" innerRadius={62} outerRadius={92}>
                    {SENTIMENT_COLORS.map(color => (
                      <Cell key={color} fill={color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-slate-900">{totalFromData(sentimentData)}</span>
                <span className="text-xs text-slate-500">Total Calls</span>
              </div>
            </div>
            <div className="mt-4 space-y-2">
              {sentimentData.map((item, i) => (
                <div key={item.name} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2 text-slate-700">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: SENTIMENT_COLORS[i % SENTIMENT_COLORS.length] }}
                    />
                    <span>{item.name}</span>
                  </div>
                  <span className="font-semibold text-slate-900">{item.value}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-6">
            <div className="mb-4">
              <h3 className="font-semibold text-slate-900">Weekly Calls</h3>
              <p className="text-xs text-slate-500 mt-1">Distribution by day of week</p>
            </div>
            <div className="relative">
              <ResponsiveContainer height={250}>
                <PieChart>
                  <Pie data={weeklyCallsPieData} dataKey="value" nameKey="name" innerRadius={62} outerRadius={92}>
                    {weeklyCallsPieData.map((_, i) => (
                      <Cell key={i} fill={WEEKDAY_COLORS[i % WEEKDAY_COLORS.length]} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-slate-900">{totalFromData(weeklyCallsPieData)}</span>
                <span className="text-xs text-slate-500">Calls This Week</span>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2">
              {weeklyCallsPieData.map((item, i) => (
                <div key={item.name} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2 text-slate-700">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: WEEKDAY_COLORS[i % WEEKDAY_COLORS.length] }}
                    />
                    <span>{item.name}</span>
                  </div>
                  <span className="font-semibold text-slate-900">{item.value}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <Card className="overflow-hidden">
          <div className="border-b border-slate-200 bg-slate-50 px-6 py-4">
            <h3 className="text-base font-semibold text-slate-900">Recent Calls</h3>
            <p className="text-xs text-slate-500 mt-1">Review interactions and open detailed analysis.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-white">
                <tr className="text-slate-600">
                  <th className="px-6 py-3 text-left font-semibold">Customer</th>
                  <th className="px-6 py-3 text-left font-semibold">Sentiment</th>
                  <th className="px-6 py-3 text-left font-semibold">Date</th>
                  <th className="px-6 py-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {!interactions.length ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-14 text-center text-slate-500">
                      <div className="inline-flex flex-col items-center gap-3">
                        <span className="h-10 w-10 rounded-full bg-slate-100 text-slate-500 inline-flex items-center justify-center">
                          <FileAudio size={18} />
                        </span>
                        <p className="text-sm">No calls found. Upload audio to populate this dashboard.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  interactions.map(call => (
                    <tr key={call.id} className="border-t border-slate-100 hover:bg-slate-50/80">
                      <td className="px-6 py-4 text-slate-800 font-medium">
                        {call.customerId || `CUST-${call.id.slice(-4)}`}
                      </td>
                      <td className="px-6 py-4">
                        <SentimentBadge sentiment={call.sentiment} />
                      </td>
                      <td className="px-6 py-4 text-slate-600">{formatShortDate(call.date)}</td>
                      <td className="px-6 py-4">
                        <div className="flex gap-2 justify-end">
                          <Button size="sm" variant="ghost" onClick={() => onSelectCall(call.id)}>
                            View
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => downloadAudio(call.id)}>
                            Download Audio
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
};

const StatCard: React.FC<StatCardProps> = ({ title, value, subtitle, icon }) => (
  <Card className="p-5 flex items-start justify-between">
    <div className="space-y-1.5">
      <p className="text-xs uppercase tracking-[0.08em] text-slate-500">{title}</p>
      <h4 className="text-2xl font-bold text-slate-900">{value}</h4>
      <p className="text-xs text-slate-500">{subtitle}</p>
    </div>
    <div className="p-2.5 bg-slate-100 rounded-lg text-slate-700">{icon}</div>
  </Card>
);

const SentimentBadge: React.FC<{ sentiment?: string }> = ({ sentiment }) => {
  const raw = (sentiment || "Neutral").toLowerCase();
  const normalized = raw.includes("positive")
    ? "positive"
    : raw.includes("negative")
      ? "negative"
      : "neutral";
  const map: Record<string, string> = {
    positive: "bg-green-100 text-green-700",
    negative: "bg-red-100 text-red-700",
    neutral: "bg-slate-100 text-slate-700",
  };

  return (
    <span className={`px-3 py-1 rounded-full text-xs font-medium ${map[normalized]}`}>
      {sentiment || "Neutral"}
    </span>
  );
};

export default Analytics;
