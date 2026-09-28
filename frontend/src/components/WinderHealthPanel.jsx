import { useEffect, useState } from "react";
import { predictWinderRul } from "../api";

const STATUS_COLOR = {
  healthy: "text-emerald-400",
  watch: "text-amber-400",
  "schedule maintenance soon": "text-rose-400",
};

export default function WinderHealthPanel({ onStatusChange }) {
  const [currentReading, setCurrentReading] = useState(95);
  const [elapsedHours, setElapsedHours] = useState(20);
  const [prediction, setPrediction] = useState(null);
  const [status, setStatus] = useState("idle");

  useEffect(() => {
    const timer = setTimeout(() => {
      setStatus("loading");
      predictWinderRul({ current_reading: currentReading, elapsed_hours: elapsedHours })
        .then((result) => {
          setPrediction(result);
          setStatus("idle");
          onStatusChange?.(result.status);
        })
        .catch(() => setStatus("error"));
    }, 250);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentReading, elapsedHours]);

  return (
    <div>
      <h2 className="text-sm font-semibold text-slate-100 mb-1">Winder health</h2>
      <p className="text-xs text-slate-500 mb-3">
        The Phase 6 model: a health reading and hours since the last repair, predicting how many hours are left
        before this winder needs attention.
      </p>

      <label className="text-xs text-slate-400 block mb-3">
        <div className="flex justify-between mb-1">
          <span>Current health reading</span>
          <span className="text-slate-300">{currentReading}</span>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          step={1}
          value={currentReading}
          onChange={(e) => setCurrentReading(Number(e.target.value))}
          className="w-full accent-sky-500"
        />
      </label>

      <label className="text-xs text-slate-400 block">
        <div className="flex justify-between mb-1">
          <span>Hours since last repair</span>
          <span className="text-slate-300">{elapsedHours}</span>
        </div>
        <input
          type="range"
          min={0}
          max={400}
          step={1}
          value={elapsedHours}
          onChange={(e) => setElapsedHours(Number(e.target.value))}
          className="w-full accent-sky-500"
        />
      </label>

      <div className="mt-4 rounded border border-slate-800 bg-slate-950/60 p-3">
        {status === "error" && (
          <p className="text-xs text-rose-400">
            Could not reach the backend. If this is the first request in a while, it may still be waking up, try
            again in a moment.
          </p>
        )}
        {prediction && (
          <>
            <p className="text-xs text-slate-400">Predicted remaining life</p>
            <p className="text-2xl font-semibold text-sky-400">
              {Math.round(prediction.predicted_remaining_hours).toLocaleString()} hours
            </p>
            <p className={`text-xs mt-1 font-medium ${STATUS_COLOR[prediction.status]}`}>{prediction.status}</p>
          </>
        )}
        {status === "loading" && !prediction && <p className="text-xs text-slate-500">Loading...</p>}
      </div>
    </div>
  );
}
