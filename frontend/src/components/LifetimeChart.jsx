// One simulated winder life: the true health line and the noisy reading a
// condition monitoring sensor would actually report, over the hours since
// its last repair. Real data from notebooks/06_combined.ipynb, not a
// placeholder.

const WIDTH = 560;
const HEIGHT = 260;
const MARGIN = { top: 16, right: 16, bottom: 34, left: 40 };

export default function LifetimeChart({ data }) {
  const plotW = WIDTH - MARGIN.left - MARGIN.right;
  const plotH = HEIGHT - MARGIN.top - MARGIN.bottom;
  const maxX = Math.max(...data.map((d) => d.elapsedHours));

  const xScale = (x) => (x / maxX) * plotW;
  const yScale = (y) => plotH - (Math.max(0, y) / 100) * plotH;

  const linePath = data.map((d, i) => `${i === 0 ? "M" : "L"} ${xScale(d.elapsedHours)} ${yScale(d.trueHealth)}`).join(" ");

  const yTicks = [0, 25, 50, 75, 100];
  const xTicks = [0, Math.round(maxX / 2), Math.round(maxX)];

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full h-auto">
      <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={0} y1={yScale(t)} x2={plotW} y2={yScale(t)} stroke="#334155" strokeWidth={1} />
            <text x={-8} y={yScale(t)} fill="#cbd5e1" fontSize={11} textAnchor="end" dominantBaseline="middle">
              {t}
            </text>
          </g>
        ))}
        {xTicks.map((t) => (
          <text key={t} x={xScale(t)} y={plotH + 20} fill="#cbd5e1" fontSize={11} textAnchor="middle">
            {t}h
          </text>
        ))}

        <path d={linePath} fill="none" stroke="#3987e5" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        {data.map((d, i) => (
          <circle key={i} cx={xScale(d.elapsedHours)} cy={yScale(d.observedHealth)} r={4} fill="#eda100" />
        ))}

        <text x={plotW / 2} y={plotH + 32} fill="#94a3b8" fontSize={11} textAnchor="middle">
          hours since last repair
        </text>
      </g>

      <g transform={`translate(${MARGIN.left + 8}, 12)`} fontSize={11}>
        <line x1={0} y1={-4} x2={16} y2={-4} stroke="#3987e5" strokeWidth={2} />
        <text x={22} y={0} fill="#cbd5e1">
          true health
        </text>
        <circle cx={110} cy={-4} r={4} fill="#eda100" />
        <text x={120} y={0} fill="#cbd5e1">
          noisy reading
        </text>
      </g>
    </svg>
  );
}
