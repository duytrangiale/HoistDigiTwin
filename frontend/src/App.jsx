import { useState } from "react";
import BackendStatusBanner from "./components/BackendStatusBanner";
import BarChart from "./components/BarChart";
import Schematic from "./components/Schematic";
import SurrogateControls from "./components/SurrogateControls";
import WinderHealthPanel from "./components/WinderHealthPanel";
import { POLICY_COMPARISON, SENSITIVITY_RANKING, WINDER_MODEL_ACCURACY } from "./data/analysisResults";

export default function App() {
  const [winderStatus, setWinderStatus] = useState("healthy");
  const [surrogateSettings, setSurrogateSettings] = useState({ feed_rate_multiplier: 1, winder_speed_multiplier: 1 });
  const [tonnesPrediction, setTonnesPrediction] = useState(null);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <BackendStatusBanner />

      <header className="border-b border-slate-800 px-6 py-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-semibold text-slate-100">HoistDigiTwin</h1>
        <p className="text-sm text-slate-400 mt-2 max-w-3xl">
          A digital twin is a computer model of a real piece of equipment or process, built so you can try things on
          it that would be too slow, expensive, or risky to try on the real thing. This one models a mine hoist
          circuit: ore comes in from two sources, gets stored in bins, and is hoisted up a shaft by two skips. Below,
          a fast trained model stands in for a much slower simulation of that circuit, and a second model predicts
          when the hoist's winder needs maintenance before it actually breaks. Move the sliders and watch the
          diagram and the numbers respond together.
        </p>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 flex flex-col gap-10">
        <section className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
          <Schematic
            winderStatus={winderStatus}
            feedRateMultiplier={surrogateSettings.feed_rate_multiplier}
            winderSpeedMultiplier={surrogateSettings.winder_speed_multiplier}
            predictedMonthlyTonnes={tonnesPrediction?.predicted_monthly_tonnes}
          />
        </section>

        <section className="grid gap-8 lg:grid-cols-[1.1fr_1fr]">
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-5">
            <SurrogateControls onSettingsChange={setSurrogateSettings} onPredictionChange={setTonnesPrediction} />
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-5">
            <h2 className="text-base font-semibold text-slate-100 mb-1">Which setting actually matters most</h2>
            <p className="text-sm text-slate-400 mb-4">
              Before trusting a model's opinion, it was checked one setting at a time against the real simulation.
              This shows how many extra tonnes a month each setting is worth on its own, moved from typical to its
              best value. Winder speed and skip payload dominate, feed rate barely matters on its own since without
              the other two, the winder is already the bottleneck.
            </p>
            <BarChart
              data={SENSITIVITY_RANKING.map((d) => ({ label: d.label, value: d.tonnesGained }))}
              seriesKeys={["value"]}
              seriesLabels={["Tonnes gained"]}
              seriesColors={["#3987e5"]}
              valueFormat={(v) => `${v >= 0 ? "+" : ""}${Math.round(v).toLocaleString()} t`}
            />
          </div>
        </section>

        <section className="grid gap-8 lg:grid-cols-[1.1fr_1fr]">
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-5">
            <WinderHealthPanel onStatusChange={setWinderStatus} />
          </div>

          <div className="flex flex-col gap-6">
            <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-5">
              <h2 className="text-base font-semibold text-slate-100 mb-1">How accurate is the prediction</h2>
              <p className="text-sm text-slate-400 mb-4">
                Checked on readings the model never trained on. It is most accurate exactly where it matters, close
                to failure, and less precise far from it, where nobody would act on a warning that early anyway.
                Lower is better, hours of error.
              </p>
              <BarChart
                data={WINDER_MODEL_ACCURACY.map((d) => ({ label: d.label, value: d.rmse }))}
                seriesKeys={["value"]}
                seriesLabels={["Error, hours"]}
                seriesColors={["#3987e5"]}
                valueFormat={(v) => `${v}h error`}
              />
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-5">
              <h2 className="text-base font-semibold text-slate-100 mb-1">What watching the signal is actually worth</h2>
              <p className="text-sm text-slate-400 mb-4">
                Two ways of running the winder, compared over 20 repeated simulated years each, same underlying
                conditions both times. Reactive fixes it only after it breaks. Predictive acts on the early warning
                above.
              </p>
              <BarChart
                data={[
                  {
                    label: "Breakdowns/year",
                    reactive: POLICY_COMPARISON.reactive.breakdownsPerYear,
                    predictive: POLICY_COMPARISON.predictive.breakdownsPerYear,
                  },
                  {
                    label: "Downtime hrs/year",
                    reactive: POLICY_COMPARISON.reactive.downtimeHoursPerYear,
                    predictive: POLICY_COMPARISON.predictive.downtimeHoursPerYear,
                  },
                ]}
                seriesKeys={["reactive", "predictive"]}
                seriesLabels={["Reactive", "Predictive"]}
                seriesColors={["#94a3b8", "#0ca30c"]}
                valueFormat={(v) => `${Math.round(v * 10) / 10}`}
              />
              <p className="text-xs text-slate-500 mt-4">
                Predictive maintenance added about {POLICY_COMPARISON.annualTonnesDiff.toLocaleString()} tonnes a
                year and cut downtime by about {Math.abs(POLICY_COMPARISON.downtimeHoursDiff)} hours a year, both
                differences far too large to be chance. See <code>reports/combined.md</code> for the full write up.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-800 px-6 py-6 max-w-7xl mx-auto text-xs text-slate-500">
        A portfolio project. The backend is on Render's free tier and sleeps after 15 minutes of inactivity, the
        first request after a while may take up to a minute to wake it up.
      </footer>
    </div>
  );
}
