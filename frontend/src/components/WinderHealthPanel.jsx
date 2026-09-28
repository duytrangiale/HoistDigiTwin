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
      <h2 className="text-base font-semibold text-slate-100 mb-1">Predicting a breakdown before it happens</h2>
      <p className="text-sm text-slate-300 mb-4">
        Real equipment does not fail at a totally random moment, it wears out. This winder has a simulated health
        signal that genuinely declines over time, like a real condition monitoring sensor would report, and a model
        trained to read that signal and predict how many hours of life are left. Try dragging the health reading
        down and watch the winder icon on the schematic change colour.
      </p>

      <label className="text-sm text-slate-300 block mb-4">
        <div className="flex justify-between items-baseline mb-1">
          <span className="font-medium text-slate-200">Current health reading</span>
          <span className="text-slate-300 text-xs">{currentReading} / 100</span>
        </div>
        <p className="text-xs text-slate-300 mb-1">
          100 means freshly repaired, 0 means right at the point of failure. A real sensor reading like this would
          come from vibration, temperature, or wear measurements on the actual machine.
        </p>
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

      <label className="text-sm text-slate-300 block">
        <div className="flex justify-between items-baseline mb-1">
          <span className="font-medium text-slate-200">Hours since last repair</span>
          <span className="text-slate-300 text-xs">{elapsedHours} hours</span>
        </div>
        <p className="text-xs text-slate-300 mb-1">
          How long this winder has been running since it was last serviced. The model uses this alongside the
          reading above, since a low reading early in a run means something different from the same reading after a
          long run.
        </p>
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
            <p className="text-xs text-slate-300">Predicted hours of life remaining</p>
            <p className="text-3xl font-semibold text-sky-400">
              {Math.round(prediction.predicted_remaining_hours).toLocaleString()}
            </p>
            <p className={`text-sm mt-1 font-medium ${STATUS_COLOR[prediction.status]}`}>
              {prediction.status === "healthy" && "Healthy, no action needed."}
              {prediction.status === "watch" && "Getting close, worth keeping an eye on."}
              {prediction.status === "schedule maintenance soon" && "Step in now, before it fails on its own."}
            </p>
          </>
        )}
        {status === "loading" && !prediction && <p className="text-xs text-slate-300">Loading...</p>}
      </div>
    </div>
  );
}
