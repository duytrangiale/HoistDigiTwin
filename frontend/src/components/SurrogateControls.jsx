import { useEffect, useState } from "react";
import { predictTonnes } from "../api";

// bounds match src/surrogate/sampling.py's PARAM_RANGES exactly, the box
// the surrogate was actually trained on. Going outside it would be
// extrapolation the model was never checked against, so the API itself
// also rejects anything outside these ranges.
const PARAMS = [
  { key: "feed_rate_multiplier", label: "Feed rate", min: 0.5, max: 1.5, step: 0.01, default: 1.0 },
  { key: "skip_payload_tonnes", label: "Skip payload (t)", min: 8, max: 16, step: 0.1, default: 12 },
  { key: "winder_speed_multiplier", label: "Winder speed", min: 0.7, max: 1.4, step: 0.01, default: 1.0 },
  { key: "breakdown_mtbf_hours", label: "Breakdown MTBF (hours)", min: 100, max: 400, step: 1, default: 200 },
  {
    key: "scheduled_downtime_hours_per_month",
    label: "Scheduled downtime (hours/month)",
    min: 5,
    max: 40,
    step: 0.5,
    default: 20,
  },
];

const DEFAULT_SETTINGS = Object.fromEntries(PARAMS.map((p) => [p.key, p.default]));

export default function SurrogateControls() {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [prediction, setPrediction] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | error

  useEffect(() => {
    // a short debounce so dragging a slider does not fire a request per
    // pixel moved, just once movement settles
    const timer = setTimeout(() => {
      setStatus("loading");
      predictTonnes(settings)
        .then((result) => {
          setPrediction(result);
          setStatus("idle");
        })
        .catch(() => setStatus("error"));
    }, 250);
    return () => clearTimeout(timer);
  }, [settings]);

  return (
    <div>
      <h2 className="text-sm font-semibold text-slate-100 mb-3">Surrogate controls</h2>
      <div className="flex flex-col gap-3">
        {PARAMS.map((p) => (
          <label key={p.key} className="text-xs text-slate-400">
            <div className="flex justify-between mb-1">
              <span>{p.label}</span>
              <span className="text-slate-300">{settings[p.key]}</span>
            </div>
            <input
              type="range"
              min={p.min}
              max={p.max}
              step={p.step}
              value={settings[p.key]}
              onChange={(e) => setSettings((s) => ({ ...s, [p.key]: Number(e.target.value) }))}
              className="w-full accent-sky-500"
            />
          </label>
        ))}
      </div>

      <div className="mt-4 rounded border border-slate-800 bg-slate-950/60 p-3">
        {status === "error" && (
          <p className="text-xs text-rose-400">
            Could not reach the backend. If this is the first request in a while, it may still be waking up, try
            again in a moment.
          </p>
        )}
        {prediction && (
          <>
            <p className="text-xs text-slate-400">Predicted monthly tonnes</p>
            <p className="text-2xl font-semibold text-sky-400">
              {Math.round(prediction.predicted_monthly_tonnes).toLocaleString()}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              {Math.round(prediction.predicted_annual_tonnes).toLocaleString()} tonnes a year
            </p>
          </>
        )}
        {status === "loading" && !prediction && <p className="text-xs text-slate-500">Loading...</p>}
      </div>
    </div>
  );
}
