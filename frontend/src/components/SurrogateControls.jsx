import { useEffect, useState } from "react";
import { predictTonnes } from "../api";

// Bounds match src/surrogate/sampling.py's PARAM_RANGES exactly, the box a
// model was actually trained on and checked against the real simulation.
// Going outside it would be extrapolation nobody has verified, so the API
// itself also rejects anything outside these ranges. The "what this means"
// text is written for someone who has never seen this project before.
const PARAMS = [
  {
    key: "feed_rate_multiplier",
    label: "Feed rate",
    min: 0.5,
    max: 1.5,
    step: 0.01,
    default: 1.0,
    unit: "x normal",
    help: "How fast ore is fed into the system from the mine. 1.0 is the normal rate. More ore only helps if the winder can actually move it, that trade off is exactly what this dashboard lets you explore.",
  },
  {
    key: "skip_payload_tonnes",
    label: "Skip payload",
    min: 8,
    max: 16,
    step: 0.1,
    default: 12,
    unit: "tonnes",
    help: "How much ore each skip carries per trip up the shaft. A bigger load per trip means more ore moved for the same number of trips.",
  },
  {
    key: "winder_speed_multiplier",
    label: "Winder speed",
    min: 0.7,
    max: 1.4,
    step: 0.01,
    default: 1.0,
    unit: "x normal",
    help: "How fast the winder hoists and lowers a skip. Faster means each trip up and down the shaft takes less time, so more trips fit in a day.",
  },
  {
    key: "breakdown_mtbf_hours",
    label: "Breakdown MTBF",
    min: 100,
    max: 400,
    step: 1,
    default: 200,
    unit: "hours",
    help: "Mean time between failures, the average number of hours the winder runs before an unplanned breakdown. Higher is more reliable.",
  },
  {
    key: "scheduled_downtime_hours_per_month",
    label: "Scheduled downtime",
    min: 5,
    max: 40,
    step: 0.5,
    default: 20,
    unit: "hours/month",
    help: "Planned maintenance time taken out of production every month on purpose, to prevent breakdowns. Less of it frees up more time to hoist ore, but see the predictive maintenance section for why some of it is worth keeping.",
  },
];

const DEFAULT_SETTINGS = Object.fromEntries(PARAMS.map((p) => [p.key, p.default]));

export default function SurrogateControls({ onSettingsChange, onPredictionChange }) {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [prediction, setPrediction] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | error
  const [openHelp, setOpenHelp] = useState(null);

  useEffect(() => {
    onSettingsChange?.(settings);
    // a short debounce so dragging a slider does not fire a request per
    // pixel moved, just once movement settles
    const timer = setTimeout(() => {
      setStatus("loading");
      predictTonnes(settings)
        .then((result) => {
          setPrediction(result);
          setStatus("idle");
          onPredictionChange?.(result);
        })
        .catch(() => setStatus("error"));
    }, 250);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings]);

  return (
    <div>
      <h2 className="text-base font-semibold text-slate-100 mb-1">What settings drive the twin</h2>
      <p className="text-sm text-slate-300 mb-4">
        This model was trained on thousands of simulated years of the hoist circuit, then checked against the real
        thing. Move a slider and it predicts, in under a millisecond, what a full year of simulation would find, a
        fast stand in for something that would otherwise take about 10 seconds to actually run.
      </p>
      <div className="flex flex-col gap-4">
        {PARAMS.map((p) => (
          <div key={p.key} className="text-sm text-slate-300">
            <div className="flex justify-between items-baseline mb-1">
              <button
                type="button"
                onClick={() => setOpenHelp((h) => (h === p.key ? null : p.key))}
                className="text-left font-medium text-slate-200 hover:text-sky-400 flex items-center gap-1.5"
              >
                {p.label}
                <span className="text-slate-300 text-xs border border-slate-600 rounded-full w-4 h-4 inline-flex items-center justify-center">
                  ?
                </span>
              </button>
              <span className="text-slate-300 text-xs">
                {settings[p.key]} {p.unit}
              </span>
            </div>
            {openHelp === p.key && <p className="text-xs text-slate-300 mb-2 bg-slate-800/50 rounded p-2">{p.help}</p>}
            <input
              type="range"
              min={p.min}
              max={p.max}
              step={p.step}
              value={settings[p.key]}
              onChange={(e) => setSettings((s) => ({ ...s, [p.key]: Number(e.target.value) }))}
              className="w-full accent-sky-500"
            />
          </div>
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
            <p className="text-xs text-slate-300">Predicted monthly tonnes hoisted</p>
            <p className="text-3xl font-semibold text-sky-400">
              {Math.round(prediction.predicted_monthly_tonnes).toLocaleString()}
            </p>
            <p className="text-xs text-slate-300 mt-1">
              {Math.round(prediction.predicted_annual_tonnes).toLocaleString()} tonnes a year at this rate, also
              shown live on the schematic above
            </p>
          </>
        )}
        {status === "loading" && !prediction && <p className="text-xs text-slate-300">Loading...</p>}
      </div>
    </div>
  );
}
