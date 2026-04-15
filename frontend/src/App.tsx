import React, { useEffect, useState } from "react";
import Navbar from "./components/Navbar";
import Home from "./views/Home";
import Analytics from "./views/Analytics";
import CallDetail from "./views/CallDetail";
import { ViewState, CallInteraction, CallFromAPI } from "./types";
import { api } from "./services/api";

function generateCustomerId() {
  return "CUST-" + Math.floor(100000 + Math.random() * 900000);
}

function formatDuration(seconds?: number): string {
  if (typeof seconds !== "number" || Number.isNaN(seconds) || seconds <= 0) {
    return "Unknown";
  }
  const totalSeconds = Math.round(seconds);
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${mins}m ${secs.toString().padStart(2, "0")}s`;
}

function parseDurationLabel(value?: string): number | undefined {
  if (!value) return undefined;
  const lowered = value.toLowerCase();
  const minMatch = lowered.match(/(\d+)\s*m/);
  const secMatch = lowered.match(/(\d+)\s*s/);
  const mins = minMatch ? Number(minMatch[1]) : 0;
  const secs = secMatch ? Number(secMatch[1]) : 0;
  const total = mins * 60 + secs;
  return total > 0 ? total : undefined;
}

function mapApiCallToInteraction(apiCall: CallFromAPI): CallInteraction {
  const customerId =
    apiCall.customer_id && apiCall.customer_id.trim() !== ""
      ? apiCall.customer_id
      : generateCustomerId();

  const durationSeconds =
    typeof apiCall.duration_seconds === "number"
      ? apiCall.duration_seconds
      : parseDurationLabel(apiCall.duration);

  return {
    id: apiCall.call_id,
    customerId,
    customerName: customerId,
    agentName: "Agent",
    date: apiCall.created_at || "",
    duration: formatDuration(durationSeconds),
    durationSeconds,
    sentiment: apiCall.sentiment || "neutral",
    sentimentConfidence:
      typeof apiCall.sentiment_confidence === "number"
        ? apiCall.sentiment_confidence
        : undefined,
    tags: apiCall.tags || [],
    summary: apiCall.summary || "",
    transcript: apiCall.transcript || "",
    rawTranscript: apiCall.raw_transcript || apiCall.transcript || "",
    refinedTranscript: apiCall.refined_transcript || apiCall.transcript || "",
    transcriptProvider: apiCall.transcript_provider || "",
    transcriptRefined: Boolean(apiCall.transcript_refined),
    transcriptRefiner: apiCall.transcript_refiner || "",
    emotion: apiCall.emotion || "",
    sentimentReason: apiCall.sentiment_reason || "",
    analysisProvider: apiCall.analysis_provider || "",
    analysis: apiCall.analysis,
  };
}

function App() {
  const [currentView, setCurrentView] = useState<ViewState>("HOME");
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
  const [interactions, setInteractions] = useState<CallInteraction[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadCalls = async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await api.getAllCalls();
      const mapped = data.map(mapApiCallToInteraction);
      setInteractions(mapped);
    } catch (err) {
      console.error(err);
      setError("Failed to load call data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCalls();
  }, []);

  const navigateTo = (view: ViewState) => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    setCurrentView(view);
  };

  const handleSelectCall = (callId: string) => {
    setSelectedCallId(callId);
    navigateTo("CALL_DETAIL");
  };

  const handleNewAnalysis = async () => {
    await loadCalls();
    setCurrentView("ANALYTICS");
  };

  const renderView = () => {
    if (loading) return <div className="p-10 text-center">Loading...</div>;
    if (error) return <div className="p-10 text-center text-red-500">{error}</div>;

    switch (currentView) {
      case "HOME":
        return <Home onNavigate={navigateTo} />;

      case "ANALYTICS":
        return (
          <Analytics
            interactions={interactions}
            onSelectCall={handleSelectCall}
            onAnalysisComplete={handleNewAnalysis}
          />
        );

      case "CALL_DETAIL":
        return (
          <CallDetail
            callId={selectedCallId || ""}
            interactions={interactions}
            onBack={() => navigateTo("ANALYTICS")}
          />
        );

      default:
        return <Home onNavigate={navigateTo} />;
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar currentView={currentView} onNavigate={navigateTo} />
      <main>{renderView()}</main>
    </div>
  );
}

export default App;
