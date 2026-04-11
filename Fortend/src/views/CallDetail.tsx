// src/views/CallDetail.tsx — FULL UPDATED VERSION

import React, { useState, useEffect } from "react";
import {
  ArrowLeft,
  Play,
  Pause,
  Download,
  Share2,
  Headset,
  Calendar,
  Clock,
} from "lucide-react";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import { CallInteraction, CallFromAPI } from "../types";
import { api } from "../services/api";

interface CallDetailProps{
  onBack: () => void;
  callId: string;
  interactions: CallInteraction[];
}

const formatDuration = (seconds?: number): string => {
  if (typeof seconds !== "number" || Number.isNaN(seconds) || seconds <= 0) {
    return "Unknown";
  }
  const rounded = Math.round(seconds);
  const mins = Math.floor(rounded / 60);
  const secs = rounded % 60;
  return `${mins}m ${secs.toString().padStart(2, "0")}s`;
};

const parseDurationLabel = (value?: string): number | undefined => {
  if (!value) return undefined;
  const lowered = value.toLowerCase();
  const minMatch = lowered.match(/(\d+)\s*m/);
  const secMatch = lowered.match(/(\d+)\s*s/);
  const mins = minMatch ? Number(minMatch[1]) : 0;
  const secs = secMatch ? Number(secMatch[1]) : 0;
  const total = mins * 60 + secs;
  return total > 0 ? total : undefined;
};

const normalizeConfidence = (value?: number): number => {
  if (typeof value !== "number" || Number.isNaN(value)) return 0.5;
  return Math.max(0, Math.min(1, value));
};

const CallDetail: React.FC<CallDetailProps> = ({
  onBack,
  callId,
  interactions,
}) => {
  const [activeTab, setActiveTab] = useState<
    "TRANSCRIPT" | "SUMMARY" | "SENTIMENT"
  >("TRANSCRIPT");
  const [isPlaying, setIsPlaying] = useState(false);

  const [loading, setLoading] = useState(false);
  const [call, setCall] = useState<CallInteraction | null>(
    interactions.find((c) => c.id === callId) || null
  );
  const [error, setError] = useState<string | null>(null);

  // ------------------------------------------------------------------------------
  // FETCH CALL IF NOT FOUND IN LOCAL INTERACTIONS
  // ------------------------------------------------------------------------------
  useEffect(() => {
    if (call) return; // already loaded from App state

    const load = async () => {
      try {
        setLoading(true);
        const apiCall: CallFromAPI = await api.getCallById(callId);
        const durationSeconds =
          typeof apiCall.duration_seconds === "number"
            ? apiCall.duration_seconds
            : parseDurationLabel(apiCall.duration);

        setCall({
          id: apiCall.call_id,
          callId: apiCall.call_id,
          customerName: apiCall.customer_id || "Unknown Customer",
          agentName: "Agent",
          date: apiCall.created_at
            ? new Date(apiCall.created_at).toLocaleString()
            : new Date().toLocaleString(),
          duration: formatDuration(durationSeconds),
          durationSeconds,
          sentiment: apiCall.sentiment || "neutral",
          sentimentConfidence:
            typeof apiCall.sentiment_confidence === "number"
              ? apiCall.sentiment_confidence
              : undefined,
          tags: apiCall.tags || [],
          summary: apiCall.summary,
          transcript: apiCall.transcript,
          rawTranscript: apiCall.raw_transcript || apiCall.transcript,
          refinedTranscript: apiCall.refined_transcript || apiCall.transcript,
          transcriptProvider: apiCall.transcript_provider,
          transcriptRefined: Boolean(apiCall.transcript_refined),
          transcriptRefiner: apiCall.transcript_refiner,
          emotion: apiCall.emotion,
          sentimentReason: apiCall.sentiment_reason,
          analysisProvider: apiCall.analysis_provider,
          analysis: apiCall.analysis,
        });
      } catch (err: any) {
        console.error(err);
        setError("Failed to load call details.");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [call, callId]);

  // ------------------------------------------------------------------------------
  // HANDLE LOADING / ERROR
  //  ------------------------------------------------------------------------------
  if (loading || !call) {
    return (
      <div className="min-h-screen pt-24 pb-12 bg-slate-50 text-center">
        {error ? (
          <p className="text-red-500 text-sm">{error}</p>
        ) : (
          <p className="text-slate-500">Loading call details...</p>
        )}
      </div>
    );
  }
  <div className="grid grid-cols-2 gap-4 mb-6">
  <div>
    <p className="text-sm text-slate-500">Customer ID</p>
    <p className="font-medium text-slate-900">
      {call.customerId || "NA"}
    </p>
  </div>

  <div>
    <p className="text-sm text-slate-500">Agent</p>
    <p className="font-medium text-slate-900">
      {call.agentName}
    </p>
  </div>
</div>


  // ------------------------------------------------------------------------------
  // PARSE TRANSCRIPT → into rows
  // ------------------------------------------------------------------------------
  const getTranscriptLines = () => {
    if (call.transcript) {
      return call.transcript
        .split("\n")
        .map((line, idx) => {
          const hasSpeaker = line.includes(":");
          const rawSpeaker = hasSpeaker ? line.split(":")[0].trim() : "";
          const fallbackSpeaker = idx % 2 === 0 ? "Agent" : "Customer";
          let speaker = rawSpeaker || fallbackSpeaker;

          if (/^speaker$/i.test(speaker)) {
            speaker = fallbackSpeaker;
          } else if (/customer|caller|client/i.test(speaker)) {
            speaker = "Customer";
          } else if (/agent|support|representative|rep/i.test(speaker)) {
            speaker = "Agent";
          }

          const text = hasSpeaker ? line.split(":").slice(1).join(":") : line;

          return {
            time: `00:${idx < 10 ? "0" + idx : idx}`,
            speaker: speaker.trim(),
            text: text.trim(),
          };
        })
        .filter((l) => l.text);
    }

    return [];
  };

  const transcriptLines = getTranscriptLines();
  const sentimentConfidence = normalizeConfidence(call.sentimentConfidence);
  const confidencePercent = Math.round(sentimentConfidence * 100);

  // ------------------------------------------------------------------------------
  // SENTIMENT BADGE COLORS
  // ------------------------------------------------------------------------------
  const getSentimentColor = (sentiment: string) => {
    const s = sentiment.toLowerCase();
    if (s.includes("positive"))
      return "bg-green-50 border-green-200 text-green-700";
    if (s.includes("negative"))
      return "bg-red-50 border-red-200 text-red-700";
    return "bg-gray-50 border-gray-200 text-gray-700";
  };

  // ------------------------------------------------------------------------------
  // UI VIEW
  // ------------------------------------------------------------------------------
  return (
    <div className="min-h-screen pt-24 pb-12 bg-slate-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Back Navigation */}
        <div className="mb-8">
          <button
            onClick={onBack}
            className="flex items-center text-sm text-slate-500 hover:text-slate-900 mb-4 transition-colors"
          >
            <ArrowLeft size={16} className="mr-1" />
            Back to Dashboard
          </button>

          {/* Header */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <h1 className="text-2xl font-display font-bold text-slate-900 flex items-center gap-3">
                {call.customerName}
                <span
                  className={`text-sm px-2 py-1 rounded-full border font-normal capitalize ${getSentimentColor(
                    call.sentiment.toString()
                  )}`}
                >
                  {call.sentiment}
                </span>
              </h1>

              <div className="flex items-center gap-4 mt-2 text-sm text-slate-500">
                <span className="flex items-center gap-1">
                  <Headset size={14} /> {call.agentName}
                </span>
                <span className="flex items-center gap-1">
                  <Calendar size={14} /> {call.date}
                </span>
                <span className="flex items-center gap-1">
                  <Clock size={14} /> {call.duration}
                </span>
              </div>
            </div>

            {/* Share / Export Buttons */}
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="gap-2">
                <Share2 size={16} />
                Share
              </Button>
              <Button variant="outline" size="sm" className="gap-2">
                <Download size={16} />
                Export
              </Button>
            </div>
          </div>
        </div>

        {/* Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Fake Audio Player */}
            <Card className="p-6 bg-slate-900 text-white border-slate-800">
              <div className="flex items-center gap-4 mb-4">
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="h-12 w-12 rounded-full bg-white text-slate-900 flex items-center justify-center hover:bg-slate-100 transition-colors"
                >
                  {isPlaying ? (
                    <Pause size={20} fill="currentColor" />
                  ) : (
                    <Play size={20} fill="currentColor" className="ml-1" />
                  )}
                </button>

                <div className="flex-1">
                  <div className="flex justify-between text-xs text-slate-400 mb-2">
                    <span>00:00</span>
                    <span>{call.duration}</span>
                  </div>

                  {/* Fake waveform */}
                  <div className="h-12 flex items-center gap-1">
                    {[...Array(40)].map((_, i) => (
                      <div
                        key={i}
                        className={`w-1.5 rounded-full transition-all duration-300 ${
                          i < 15 || isPlaying
                            ? "bg-blue-500 animate-pulse"
                            : "bg-slate-700"
                        }`}
                        style={{
                          height: `${20 + Math.random() * 80}%`,
                          animationDuration: `${0.5 + Math.random()}s`,
                        }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </Card>

            {/* Tabs + Content */}
            <Card className="min-h-[500px]">
              {/* Tabs */}
              <div className="border-b border-slate-100">
                <div className="flex gap-6 px-6">
                  {["TRANSCRIPT", "SUMMARY", "SENTIMENT"].map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab as any)}
                      className={`py-4 text-sm font-medium border-b-2 transition-colors ${
                        activeTab === tab
                          ? "border-primary-600 text-primary-600"
                          : "border-transparent text-slate-500 hover:text-slate-700"
                      }`}
                    >
                      {tab.charAt(0) + tab.slice(1).toLowerCase()}
                    </button>
                  ))}
                </div>
              </div>

              {/* TAB CONTENT */}
              <div className="p-6">
                {/* TRANSCRIPT */}
                {activeTab === "TRANSCRIPT" && (
                  <div className="space-y-6">
                    {transcriptLines.length === 0 && (
                      <p className="text-slate-500 text-sm">No transcript.</p>
                    )}

                    {(call.transcriptProvider || call.transcriptRefined) && (
                      <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
                        <div>
                          Transcript source: {call.transcriptProvider || "unknown"}
                        </div>
                        <div>
                          Refined for readability: {call.transcriptRefined ? "Yes" : "No"}
                        </div>
                        {call.transcriptRefined && call.transcriptRefiner && (
                          <div>
                            Refined by: {call.transcriptRefiner}
                          </div>
                        )}
                      </div>
                    )}

                    {transcriptLines.map((line, idx) => (
                      <div key={idx} className="flex gap-4">
                        <div className="text-xs text-slate-400 w-12 pt-1 font-mono">
                          {line.time}
                        </div>
                        <div className="flex-1">
                          <p className="text-xs font-bold text-slate-700 mb-1 capitalize">
                            {line.speaker}
                          </p>
                          <p className="text-slate-600 leading-relaxed text-sm">
                            {line.text}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* SUMMARY */}
                {activeTab === "SUMMARY" && (
                  <div className="space-y-4">
                    <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                      <h4 className="text-blue-900 font-semibold mb-2 text-sm">
                        AI Executive Summary
                      </h4>
                      {call.analysisProvider && (
                        <p className="mb-2 text-xs text-blue-700/80">
                          Generated by {call.analysisProvider}
                        </p>
                      )}
                      <p className="text-blue-800 text-sm leading-relaxed">
                        {call.summary ||
                          call.analysis?.call_summary ||
                          "No summary available for this call."}
                      </p>
                    </div>

                    {call.analysis?.key_points && (
                      <div>
                        <h4 className="font-semibold text-slate-900 text-sm mb-2">
                          Key Topics
                        </h4>
                        <div className="flex gap-2 flex-wrap">
                          {call.analysis.key_points.map(
                            (point: string, i: number) => (
                              <span
                                key={i}
                                className="px-3 py-1 bg-slate-100 rounded-full text-xs text-slate-600 border border-slate-200"
                              >
                                {point}
                              </span>
                            )
                          )}
                        </div>
                      </div>
                    )}

                    {call.analysis?.action_items &&
                      call.analysis.action_items.length > 0 && (
                        <div>
                          <h4 className="font-semibold text-slate-900 text-sm mb-2">
                            Action Items
                          </h4>
                          <ul className="list-disc list-inside text-sm text-slate-600 space-y-1">
                            {call.analysis.action_items.map(
                              (item: string, i: number) => (
                                <li key={i}>{item}</li>
                              )
                            )}
                          </ul>
                        </div>
                      )}
                  </div>
                )}

                {/* SENTIMENT */}
                {activeTab === "SENTIMENT" && (
                  <div className="space-y-6">
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">
                          Overall Sentiment
                        </span>
                        <span
                          className={`font-semibold capitalize ${
                            call.sentiment
                              .toString()
                              .toLowerCase()
                              .includes("pos")
                              ? "text-green-600"
                              : call.sentiment
                                  .toString()
                                  .toLowerCase()
                                  .includes("neg")
                              ? "text-red-600"
                              : "text-gray-600"
                          }`}
                        >
                          {call.sentiment}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs text-slate-500">
                        <span>Model Confidence</span>
                        <span>{confidencePercent}%</span>
                      </div>

                      <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            call.sentiment
                              .toString()
                              .toLowerCase()
                              .includes("pos")
                              ? "bg-green-500"
                              : call.sentiment
                                  .toString()
                                  .toLowerCase()
                                  .includes("neg")
                              ? "bg-red-500"
                              : "bg-gray-400"
                          }`}
                          style={{ width: `${confidencePercent}%` }}
                        ></div>
                      </div>
                    </div>

                    {call.emotion && (
                      <div className="mt-4 p-4 bg-slate-50 rounded-lg">
                        <h4 className="font-semibold text-slate-900 text-sm mb-1">
                          Detected Emotion
                        </h4>
                        <p className="text-sm text-slate-600 capitalize">
                          {call.emotion}
                        </p>
                      </div>
                    )}

                    {call.sentimentReason && (
                      <div className="p-4 bg-slate-50 rounded-lg">
                        <h4 className="font-semibold text-slate-900 text-sm mb-1">
                          Why This Sentiment
                        </h4>
                        <p className="text-sm text-slate-600 leading-relaxed">
                          {call.sentimentReason}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <Card className="p-6">
              <h3 className="font-semibold text-slate-900 mb-4 text-sm uppercase tracking-wider">
                Customer Profile
              </h3>

              <div className="flex items-center gap-3 mb-6">
                <div className="h-12 w-12 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 font-bold text-lg">
                  {call.customerName.charAt(0)}
                </div>

                <div>
                  <div className="font-medium text-slate-900">
                    {call.customerName}
                  </div>
                  <div className="text-xs text-slate-500">Enterprise Plan</div>
                </div>
              </div>

              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Call ID</span>
                  <span className="text-slate-900 text-right truncate w-32 font-mono">
                    {call.id}
                  </span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CallDetail;
