"use client";

import React, { useState } from "react";
import { 
  ShieldAlert, 
  Send, 
  CheckCircle, 
  Flame, 
  MapPin, 
  FolderHeart, 
  HelpCircle,
  ArrowLeft
} from "lucide-react";
import Link from "next/link";

const BACKEND_BASE_URL = "http://127.0.0.1:8000";

const LOCATIONS = [
  "Dallas", 
  "New Jersey", 
  "Chicago", 
  "Bay Area", 
  "New York", 
  "London", 
  "Seattle", 
  "Toronto", 
  "Other NRI Hub"
];

const CATEGORIES = [
  "Roommate Gola",
  "Consultancy Struggles",
  "Matchmaking Gola",
  "Corporate Gossip",
  "General Frustrations",
  "Hidden Gems / Gossip"
];

export default function SubmitConfession() {
  const [rawText, setRawText] = useState("");
  const [location, setLocation] = useState("Dallas");
  const [category, setCategory] = useState("General Frustrations");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedText = rawText.trim();
    if (!trimmedText) {
      setError("Please write your story before submitting.");
      return;
    }

    if (trimmedText.length < 20) {
      setError("Your story is a bit too short! Please write at least 20 characters so our AI can curate it beautifully.");
      return;
    }

    setSubmitting(true);

    try {
      const res = await fetch(`${BACKEND_BASE_URL}/api/submissions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          raw_text: trimmedText,
          location,
          category
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Submission failed.");
      }

      setSubmitted(true);
      setRawText("");
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to submit confession. Is the server offline?");
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-zinc-950 p-6 flex items-center justify-center relative text-zinc-100">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_60%_at_50%_-10%,rgba(99,102,241,0.12),rgba(255,255,255,0))] pointer-events-none" />
        
        <div className="max-w-md w-full bg-zinc-900/40 backdrop-blur-md border border-zinc-900 rounded-3xl p-8 shadow-2xl text-center space-y-6 animate-fade-in relative">
          <div className="flex justify-center">
            <div className="p-4 bg-emerald-950/50 border border-emerald-500/30 text-emerald-400 rounded-full animate-bounce">
              <CheckCircle className="w-12 h-12" />
            </div>
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-black tracking-tight bg-gradient-to-r from-emerald-400 to-teal-300 bg-clip-text text-transparent">
              Confession Submitted!
            </h2>
            <p className="text-sm text-zinc-400 leading-relaxed">
              Your story has been securely ingested into the **Swayam-Admin Curation pipeline**. 
            </p>
          </div>

          <div className="p-4 bg-zinc-950/60 border border-zinc-900 rounded-2xl text-left text-xs text-zinc-500 space-y-2">
            <p className="font-semibold text-zinc-400 flex items-center gap-1.5">
              <Flame className="w-3.5 h-3.5 text-indigo-400" />
              What happens next?
            </p>
            <ul className="list-disc pl-4 space-y-1">
              <li>Our **Gemini 2.5 Flash** editor will translate it to authentic Tanglish.</li>
              <li>Personal names/company specifics will be automatically redacted.</li>
              <li>A rule-paper graphic will be drawn and queued for admin review.</li>
              <li>Keep an eye on the Instagram page to see your story live!</li>
            </ul>
          </div>

          <div className="flex flex-col gap-3">
            <button
              onClick={() => setSubmitted(false)}
              className="w-full py-3 bg-zinc-900 border border-zinc-800 hover:border-zinc-700 hover:bg-zinc-800 text-zinc-300 font-bold rounded-2xl active:scale-[0.98] transition cursor-pointer text-sm"
            >
              Submit Another Confession
            </button>
            
            <Link 
              href="/"
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-2xl active:scale-[0.98] transition text-sm flex items-center justify-center gap-1.5 shadow-lg shadow-indigo-500/10"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 p-6 flex items-center justify-center relative text-zinc-100">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_60%_at_50%_-10%,rgba(99,102,241,0.15),rgba(255,255,255,0))] pointer-events-none" />

      <div className="max-w-xl w-full bg-zinc-900/30 backdrop-blur-md border border-zinc-900 rounded-3xl p-6 md:p-8 shadow-2xl space-y-8 relative group hover:border-zinc-900/80 transition-all duration-300">
        
        {/* Title and subtitle header */}
        <div className="space-y-3 text-center">
          <div className="flex items-center justify-center gap-2">
            <Flame className="w-6 h-6 text-indigo-500 animate-pulse" />
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-zinc-100 to-zinc-500 bg-clip-text text-transparent">
              Swayam Confessions
            </h1>
          </div>
          <p className="text-xs md:text-sm text-zinc-400 max-w-sm mx-auto leading-relaxed">
            Share your NRI struggles, consultancy tea, roommate drama, or matchmaking frustrations anonymously. Your identity is 100% secure.
          </p>
        </div>

        {/* Warning security trust box */}
        <div className="flex gap-3 p-4 bg-indigo-950/20 border border-indigo-500/10 rounded-2xl text-xs text-indigo-300 leading-relaxed">
          <ShieldAlert className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">100% Privacy Ensured:</span> We do not collect cookies, IP addresses, or accounts. Additionally, our **Gemini 2.5 Flash** editor programmatically scrubs all company/college names and individual identities before any post is created!
          </div>
        </div>

        {/* Confession Submit Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          
          {/* Metadata selectors container */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* Field A: Location dropdown */}
            <div className="space-y-2">
              <label className="text-xs text-zinc-400 font-mono tracking-wider uppercase flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-zinc-500" />
                Your Location
              </label>
              <div className="relative">
                <select
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  className="w-full p-3.5 bg-zinc-950/80 border border-zinc-900 rounded-xl text-sm text-zinc-300 focus:outline-none focus:border-indigo-500/50 cursor-pointer appearance-none"
                >
                  {LOCATIONS.map((loc) => (
                    <option key={loc} value={loc} className="bg-zinc-950 text-zinc-300">{loc}</option>
                  ))}
                </select>
                <div className="absolute inset-y-0 right-4 flex items-center pointer-events-none text-zinc-500">▼</div>
              </div>
            </div>

            {/* Field B: Category dropdown */}
            <div className="space-y-2">
              <label className="text-xs text-zinc-400 font-mono tracking-wider uppercase flex items-center gap-1.5">
                <FolderHeart className="w-3.5 h-3.5 text-zinc-500" />
                Category
              </label>
              <div className="relative">
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full p-3.5 bg-zinc-950/80 border border-zinc-900 rounded-xl text-sm text-zinc-300 focus:outline-none focus:border-indigo-500/50 cursor-pointer appearance-none"
                >
                  {CATEGORIES.map((cat) => (
                    <option key={cat} value={cat} className="bg-zinc-950 text-zinc-300">{cat}</option>
                  ))}
                </select>
                <div className="absolute inset-y-0 right-4 flex items-center pointer-events-none text-zinc-500">▼</div>
              </div>
            </div>

          </div>

          {/* Main textarea block */}
          <div className="space-y-2">
            <label className="text-xs text-zinc-400 font-mono tracking-wider uppercase flex items-center justify-between">
              <span>Tell your story</span>
              <span className={`text-xs ${rawText.length >= 20 ? "text-indigo-400" : "text-zinc-600"}`}>
                {rawText.length} chars
              </span>
            </label>
            <textarea
              rows={6}
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="E.g., I joined this consultancy in Chicago and they are running OPT scams... roommate eats Sona Masoori like a monster... matches ask for GC only..."
              className="w-full p-4 bg-zinc-950/60 border border-zinc-900 rounded-2xl text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500/50 leading-relaxed resize-none"
            />
          </div>

          {/* Form Error states */}
          {error && (
            <p className="text-xs text-rose-400 font-medium bg-rose-950/20 border border-rose-500/20 p-3.5 rounded-xl flex items-center gap-2">
              <HelpCircle className="w-4 h-4 shrink-0" />
              {error}
            </p>
          )}

          {/* Submit action trigger button */}
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 text-white font-bold rounded-2xl active:scale-[0.98] hover:scale-[1.01] transition flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-indigo-500/20 text-sm"
          >
            <Send className={`w-4 h-4 ${submitting ? "animate-pulse" : ""}`} />
            {submitting ? "Encrypting & Posting..." : "Submit Anonymously"}
          </button>

        </form>

      </div>
    </div>
  );
}
