import { useState } from "react";
import BackendStatusBanner from "./components/BackendStatusBanner";
import Schematic from "./components/Schematic";
import SurrogateControls from "./components/SurrogateControls";
import WinderHealthPanel from "./components/WinderHealthPanel";

export default function App() {
  const [winderStatus, setWinderStatus] = useState("healthy");

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <BackendStatusBanner />
      <header className="border-b border-slate-800 px-6 py-4">
        <h1 className="text-xl font-semibold text-slate-100">HoistDigiTwin</h1>
        <p className="text-sm text-slate-400">
          A digital twin of a mine hoist circuit. Change the settings below and see how the twin's own trained
          models respond.
        </p>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8 grid gap-8 lg:grid-cols-[2fr_1fr]">
        <section className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
          <Schematic winderStatus={winderStatus} />
        </section>

        <aside className="flex flex-col gap-6">
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
            <SurrogateControls />
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
            <WinderHealthPanel onStatusChange={setWinderStatus} />
          </div>
        </aside>
      </main>
    </div>
  );
}
