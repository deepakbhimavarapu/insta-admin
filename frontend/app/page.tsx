"use client";

import React, { useState, useEffect } from "react";
import { 
  Sparkles, 
  Trash2, 
  Check, 
  Calendar, 
  RefreshCw, 
  ChevronLeft, 
  ChevronRight, 
  Clock, 
  Users, 
  ShieldCheck, 
  AlertTriangle,
  Flame,
  Globe
} from "lucide-react";

// Types representing backend models
interface DashboardItem {
  id: string;
  adapted_text: string;
  tone_location: string;
  graphic_urls: string[];
  caption_options: string[];
  created_at: string;
}

interface DashboardResponse {
  pending_count: number;
  scheduled_queue_count: number;
  items: DashboardItem[];
}

const BACKEND_BASE_URL = "http://127.0.0.1:8000";

export default function Dashboard() {
  const [items, setItems] = useState<DashboardItem[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [scheduledCount, setScheduledCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refilling, setRefilling] = useState(false);
  const [scouting, setScouting] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "info" | "error" } | null>(null);

  // Per-card state hooks
  const [activeSlideIndex, setActiveSlideIndex] = useState<Record<string, number>>({});
  const [selectedCaptionIndex, setSelectedCaptionIndex] = useState<Record<string, number>>({});
  const [customCaptions, setCustomCaptions] = useState<Record<string, string>>({});
  const [scheduleOffsets, setScheduleOffsets] = useState<Record<string, number>>({});

  const showToast = (message: string, type: "success" | "info" | "error" = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const fetchDashboardData = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const res = await fetch(`${BACKEND_BASE_URL}/api/dashboard`);
      if (!res.ok) throw new Error("Backend server is starting up or offline.");
      const data: DashboardResponse = await res.json();
      setItems(data.items);
      setPendingCount(data.pending_count);
      setScheduledCount(data.scheduled_queue_count);

      // Initialize default states for newly fetched cards
      const slides: Record<string, number> = {};
      const captions: Record<string, number> = {};
      const offsets: Record<string, number> = {};
      
      data.items.forEach((item) => {
        slides[item.id] = 0;
        captions[item.id] = 0;
        offsets[item.id] = 4; // Default schedule +4 hours
      });

      setActiveSlideIndex((prev) => ({ ...slides, ...prev }));
      setSelectedCaptionIndex((prev) => ({ ...captions, ...prev }));
      setScheduleOffsets((prev) => ({ ...offsets, ...prev }));
    } catch (err: any) {
      console.error(err);
      showToast(err.message || "Could not fetch dashboard metrics.", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleReviewAction = async (id: string, action: "approve" | "reject") => {
    try {
      let payload: any = { action };
      
      if (action === "approve") {
        const item = items.find((i) => i.id === id);
        if (!item) return;
        
        // Fetch chosen caption index or customized text
        const capIdx = selectedCaptionIndex[id] ?? 0;
        const caption = capIdx === 3 ? (customCaptions[id] || "") : item.caption_options[capIdx];
        
        if (!caption.trim()) {
          showToast("Caption cannot be completely empty for approval.", "error");
          return;
        }
        
        payload.selected_caption = caption;
        payload.schedule_hours = scheduleOffsets[id] ?? 4;
      }

      const res = await fetch(`${BACKEND_BASE_URL}/api/review/${id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error(`Server returned error: ${res.statusText}`);

      showToast(
        action === "approve" 
          ? "Confession approved and added to publishing queue!" 
          : "Confession archived.",
        "success"
      );

      // Splice item out locally for seamless transition
      setItems((prev) => prev.filter((item) => item.id !== id));
      setPendingCount((prev) => prev - 1);
      if (action === "approve") setScheduledCount((prev) => prev + 1);

      // Silently refresh metrics (FastAPI refills queue in background)
      setTimeout(() => fetchDashboardData(true), 2000);
    } catch (err: any) {
      console.error(err);
      showToast(err.message || "Failed to submit review choice.", "error");
    }
  };

  const triggerRefill = async () => {
    setRefilling(true);
    showToast("Starting Agentic Refill Loop. Gemini is translating in background...", "info");
    try {
      const res = await fetch(`${BACKEND_BASE_URL}/api/refill`, { method: "POST" });
      if (!res.ok) throw new Error("Refill request rejected by backend.");
      
      // Give the server 8 seconds to process background models
      setTimeout(async () => {
        await fetchDashboardData(true);
        setRefilling(false);
        showToast("Dashboard queue refilled!", "success");
      }, 8000);
    } catch (err: any) {
      console.error(err);
      showToast(err.message || "Failed to trigger queue refill.", "error");
      setRefilling(false);
    }
  };

  const triggerScout = async () => {
    setScouting(true);
    showToast("Scout Agent crawling Reddit boards and submissions...", "info");
    try {
      // Trigger a raw fetch pipeline
      await triggerRefill();
      setScouting(false);
    } catch (err) {
      setScouting(false);
    }
  };

  // Slide navigation
  const nextSlide = (id: string, total: number) => {
    const current = activeSlideIndex[id] ?? 0;
    if (current < total - 1) {
      setActiveSlideIndex((prev) => ({ ...prev, [id]: current + 1 }));
    }
  };

  const prevSlide = (id: string) => {
    const current = activeSlideIndex[id] ?? 0;
    if (current > 0) {
      setActiveSlideIndex((prev) => ({ ...prev, [id]: current - 1 }));
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 p-6 md:p-12 relative text-zinc-100">
      
      {/* Dynamic Floating Toast Alerts */}
      {toast && (
        <div className={`fixed bottom-8 right-8 z-50 flex items-center gap-3 px-6 py-4 rounded-xl shadow-2xl backdrop-blur-md border animate-bounce ${
          toast.type === "success" ? "bg-emerald-950/90 border-emerald-500/50 text-emerald-300" :
          toast.type === "error" ? "bg-rose-950/90 border-rose-500/50 text-rose-300" :
          "bg-blue-950/90 border-blue-500/50 text-blue-300"
        }`}>
          {toast.type === "success" && <ShieldCheck className="w-5 h-5 text-emerald-400" />}
          {toast.type === "error" && <AlertTriangle className="w-5 h-5 text-rose-400" />}
          {toast.type === "info" && <Clock className="w-5 h-5 text-blue-400" />}
          <span className="text-sm font-medium">{toast.message}</span>
        </div>
      )}

      {/* Grid background mesh design */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(99,102,241,0.15),rgba(255,255,255,0))] pointer-events-none" />

      {/* Main Container */}
      <div className="max-w-7xl mx-auto space-y-10 relative">
        
        {/* Header Block */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 bg-zinc-900/40 backdrop-blur-md border border-zinc-900 rounded-3xl p-6 md:p-8 shadow-xl">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <span className="flex h-3 w-3 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
              </span>
              <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-zinc-200 to-zinc-500 bg-clip-text text-transparent flex items-center gap-2">
                Swayam-Admin <span className="text-xs text-indigo-400 font-mono px-2 py-0.5 border border-indigo-500/30 rounded bg-indigo-950/30">v2.5 Live</span>
              </h1>
            </div>
            <p className="text-sm text-zinc-400 max-w-lg">
              Autonomous Diaspora Curation Engine. Review, approve, and programmatically schedule confessions directly to Instagram feed.
            </p>
          </div>

          {/* Stat Metrics Header widgets */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-3 bg-zinc-950/80 px-5 py-3 border border-zinc-900 rounded-2xl">
              <div className="p-2 bg-indigo-950/50 rounded-xl text-indigo-400">
                <Users className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs text-zinc-500">Pending Queue</div>
                <div className="text-lg font-bold text-indigo-300">{pendingCount} <span className="text-xs text-zinc-500">/ 10</span></div>
              </div>
            </div>

            <div className="flex items-center gap-3 bg-zinc-950/80 px-5 py-3 border border-zinc-900 rounded-2xl">
              <div className="p-2 bg-emerald-950/50 rounded-xl text-emerald-400">
                <Calendar className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs text-zinc-500">Scheduled Queue</div>
                <div className="text-lg font-bold text-emerald-300">{scheduledCount} posts</div>
              </div>
            </div>

            <div className="flex gap-2">
              <button 
                onClick={triggerScout}
                disabled={scouting || refilling}
                className="p-3 bg-zinc-900 border border-zinc-800 hover:border-zinc-700 disabled:opacity-50 text-zinc-300 rounded-2xl hover:bg-zinc-800 transition shadow-lg cursor-pointer"
                title="Trigger Scrapers"
              >
                <Globe className={`w-5 h-5 ${scouting ? "animate-spin text-indigo-400" : ""}`} />
              </button>

              <button 
                onClick={triggerRefill}
                disabled={refilling || scouting}
                className="px-5 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 disabled:opacity-50 text-white font-semibold rounded-2xl hover:scale-[1.02] active:scale-[0.98] transition shadow-lg shadow-indigo-500/20 flex items-center gap-2 cursor-pointer"
              >
                <RefreshCw className={`w-4 h-4 ${refilling ? "animate-spin" : ""}`} />
                {refilling ? "Refilling..." : "Refill Queue"}
              </button>
            </div>
          </div>
        </header>

        {/* Dashboard Cards Listing */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <RefreshCw className="w-12 h-12 text-indigo-500 animate-spin" />
            <p className="text-sm text-zinc-500 font-medium animate-pulse">Synchronizing dashboard states...</p>
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-32 border border-dashed border-zinc-800 rounded-3xl bg-zinc-900/10 backdrop-blur-sm gap-4 text-center px-6">
            <Flame className="w-12 h-12 text-zinc-600" />
            <h3 className="text-lg font-bold text-zinc-300">All Confessions Reviewed!</h3>
            <p className="text-sm text-zinc-500 max-w-md">
              The pending review queue is empty. Click "Refill Queue" to let the Scout and Editor agents crawl and generate 10 new confessions instantly.
            </p>
            <button 
              onClick={triggerRefill}
              disabled={refilling}
              className="mt-2 px-6 py-3 bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-300 font-semibold rounded-2xl hover:bg-zinc-800 transition cursor-pointer flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${refilling ? "animate-spin" : ""}`} />
              Refill Database Now
            </button>
          </div>
        ) : (
          <div className="space-y-8 animate-fade-in">
            {items.map((item) => {
              const currentSlide = activeSlideIndex[item.id] ?? 0;
              const totalSlides = item.graphic_urls.length;
              const currentCapIdx = selectedCaptionIndex[item.id] ?? 0;
              const currentOffset = scheduleOffsets[item.id] ?? 4;
              
              // Resolve active image source URL
              const imgUrl = `${BACKEND_BASE_URL}${item.graphic_urls[currentSlide]}`;

              return (
                <div 
                  key={item.id} 
                  className="bg-zinc-900/30 backdrop-blur-md border border-zinc-900 rounded-3xl p-6 md:p-8 flex flex-col lg:flex-row gap-8 shadow-2xl relative group hover:border-zinc-800/80 transition-all duration-300"
                >
                  
                  {/* Visual Left: Image Slider Sheet */}
                  <div className="w-full lg:w-[480px] shrink-0 space-y-3">
                    <div className="relative aspect-square w-full bg-zinc-950 rounded-2xl overflow-hidden border border-zinc-900 shadow-lg group-hover:border-zinc-800/50 transition">
                      
                      {/* Image render element */}
                      <img 
                        src={imgUrl} 
                        alt="Handwritten journal slide card" 
                        className="w-full h-full object-cover select-none pointer-events-none" 
                      />

                      {/* Overlap banner indicating tone location badge */}
                      <div className="absolute top-4 left-4 bg-zinc-950/80 backdrop-blur-md border border-zinc-800/80 px-3.5 py-1.5 rounded-full text-xs font-bold text-zinc-300 flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                        {item.tone_location} dialect
                      </div>

                      {/* Slide indices overlay controllers */}
                      {totalSlides > 1 && (
                        <>
                          <div className="absolute inset-y-0 left-2 flex items-center">
                            <button 
                              onClick={() => prevSlide(item.id)}
                              disabled={currentSlide === 0}
                              className="p-2 rounded-full bg-zinc-950/80 border border-zinc-800/50 text-zinc-300 hover:bg-zinc-900 hover:text-white disabled:opacity-20 transition"
                            >
                              <ChevronLeft className="w-5 h-5" />
                            </button>
                          </div>

                          <div className="absolute inset-y-0 right-2 flex items-center">
                            <button 
                              onClick={() => nextSlide(item.id, totalSlides)}
                              disabled={currentSlide === totalSlides - 1}
                              className="p-2 rounded-full bg-zinc-950/80 border border-zinc-800/50 text-zinc-300 hover:bg-zinc-900 hover:text-white disabled:opacity-20 transition"
                            >
                              <ChevronRight className="w-5 h-5" />
                            </button>
                          </div>

                          {/* Pagination Dots indicator */}
                          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-1.5 bg-zinc-950/70 backdrop-blur px-3 py-1.5 rounded-full">
                            {Array.from({ length: totalSlides }).map((_, i) => (
                              <div 
                                key={i} 
                                className={`h-1.5 rounded-full transition-all ${i === currentSlide ? "w-3.5 bg-indigo-400" : "w-1.5 bg-zinc-600"}`} 
                              />
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Visual Right: Metadata, Text rewrites, Captions & Schedule controls */}
                  <div className="flex-1 flex flex-col justify-between space-y-6">
                    <div className="space-y-6">
                      
                      {/* Section 1: Tanglish raw review box */}
                      <div>
                        <div className="text-xs text-zinc-500 font-mono tracking-wider uppercase mb-2">Live Gemini 2.5 Translation</div>
                        <div className="p-5 bg-zinc-950/60 border border-zinc-900/60 rounded-2xl text-zinc-300 leading-relaxed max-h-[160px] overflow-y-auto text-sm font-medium">
                          {item.adapted_text}
                        </div>
                      </div>

                      {/* Section 2: Choose post Caption Tab switcher */}
                      <div className="space-y-3">
                        <div className="text-xs text-zinc-500 font-mono tracking-wider uppercase flex items-center justify-between">
                          <span>Auto-Caption Variants</span>
                          <span className="text-indigo-400 font-bold">{currentCapIdx === 3 ? "Manual Edit Mode" : `Option ${currentCapIdx + 1}`}</span>
                        </div>

                        {/* Caption Select Toggles */}
                        <div className="grid grid-cols-4 gap-2">
                          {[0, 1, 2, 3].map((idx) => (
                            <button
                              key={idx}
                              onClick={() => setSelectedCaptionIndex((prev) => ({ ...prev, [item.id]: idx }))}
                              className={`py-2 px-3 text-xs font-semibold rounded-xl border text-center transition cursor-pointer ${
                                currentCapIdx === idx 
                                  ? "bg-indigo-950/40 border-indigo-500/50 text-indigo-300" 
                                  : "bg-zinc-950/30 border-zinc-900 text-zinc-400 hover:border-zinc-800"
                              }`}
                            >
                              {idx === 3 ? "Custom" : `Option ${idx + 1}`}
                            </button>
                          ))}
                        </div>

                        {/* Interactive Textarea based on selection */}
                        <div className="relative">
                          {currentCapIdx === 3 ? (
                            <textarea
                              rows={3}
                              placeholder="Write custom caption here... #hashtags"
                              value={customCaptions[item.id] || ""}
                              onChange={(e) => setCustomCaptions((prev) => ({ ...prev, [item.id]: e.target.value }))}
                              className="w-full p-4 bg-zinc-950/90 border border-zinc-900 rounded-2xl text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500/50 leading-relaxed resize-none"
                            />
                          ) : (
                            <div className="w-full p-4 bg-zinc-950/40 border border-zinc-900 rounded-2xl text-sm text-zinc-400 leading-relaxed max-h-[100px] overflow-y-auto italic">
                              {item.caption_options[currentCapIdx]}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Section 3: Schedule Offset slider chips */}
                      <div className="space-y-3">
                        <div className="text-xs text-zinc-500 font-mono tracking-wider uppercase flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-zinc-500" />
                          <span>Schedule Publication</span>
                        </div>
                        <div className="flex gap-2 flex-wrap">
                          {[4, 8, 12, 24].map((hours) => (
                            <button
                              key={hours}
                              onClick={() => setScheduleOffsets((prev) => ({ ...prev, [item.id]: hours }))}
                              className={`py-2 px-4 text-xs font-semibold rounded-xl border transition cursor-pointer flex items-center gap-1.5 ${
                                currentOffset === hours 
                                  ? "bg-emerald-950/40 border-emerald-500/50 text-emerald-300" 
                                  : "bg-zinc-950/30 border-zinc-900 text-zinc-400 hover:border-zinc-800"
                              }`}
                            >
                              +{hours} hours
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Section 4: Card Quick Action trigger buttons */}
                    <div className="flex gap-4 border-t border-zinc-900 pt-6">
                      <button
                        onClick={() => handleReviewAction(item.id, "reject")}
                        className="flex-1 py-3.5 px-4 bg-zinc-900 hover:bg-rose-950/20 border border-zinc-800 hover:border-rose-500/30 text-rose-400 font-bold rounded-2xl active:scale-[0.98] transition flex items-center justify-center gap-2 cursor-pointer shadow-lg"
                      >
                        <Trash2 className="w-4.5 h-4.5" />
                        Reject & Archive
                      </button>

                      <button
                        onClick={() => handleReviewAction(item.id, "approve")}
                        className="flex-1 py-3.5 px-4 bg-indigo-600 hover:bg-indigo-500 border border-indigo-500/30 text-white font-bold rounded-2xl active:scale-[0.98] hover:scale-[1.01] transition flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-indigo-500/10"
                      >
                        <Check className="w-4.5 h-4.5" />
                        Approve & Schedule
                      </button>
                    </div>

                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
