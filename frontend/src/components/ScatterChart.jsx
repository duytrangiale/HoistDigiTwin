// Predicted versus true remaining life on held out validation lives, the
// same style of check used throughout the project's own notebooks. A
// tight diagonal means the model is trustworthy; the dashed line is where
// a perfect prediction would land.

const WIDTH = 560;
const HEIGHT = 320;
const MARGIN = { top: 16, right: 16, bottom: 34, left: 44 };

export default function ScatterChart({ data }) {
  const plotW = WIDTH - MARGIN.left - MARGIN.right;
  const plotH = HEIGHT - MARGIN.top - MARGIN.bottom;
  const maxVal = Math.max(...data.map((d) => Math.max(d.trueHours, d.predictedHours)), 1) * 1.05;

  const xScale = (x) => (Math.max(0, x) / maxVal) * plotW;
  const yScale = (y) => plotH - (Math.max(0, y) / maxVal) * plotH;

  const ticks = [0, Math.round(maxVal / 2), Math.round(maxVal)];

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full h-auto">
      <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={0} y1={yScale(t)} x2={plotW} y2={yScale(t)} stroke="#334155" strokeWidth={1} />
            <text x={-10} y={yScale(t)} fill="#cbd5e1" fontSize={11} textAnchor="end" dominantBaseline="middle">
              {t}
            </text>
            <text x={xScale(t)} y={plotH + 20} fill="#cbd5e1" fontSize={11} textAnchor="middle">
              {t}
            </text>
          </g>
        ))}

        <line x1={xScale(0)} y1={yScale(0)} x2={xScale(maxVal)} y2={yScale(maxVal)} stroke="#64748b" strokeWidth={1} strokeDasharray="4 4" />

        {data.map((d, i) => (
          <circle key={i} cx={xScale(d.trueHours)} cy={yScale(d.predictedHours)} r={3.5} fill="#3987e5" opacity={0.65} />
        ))}

        <text x={plotW / 2} y={plotH + 32} fill="#94a3b8" fontSize={11} textAnchor="middle">
          true remaining hours
        </text>
        <text x={-32} y={plotH / 2} fill="#94a3b8" fontSize={11} textAnchor="middle" transform={`rotate(-90, -32, ${plotH / 2})`}>
          predicted remaining hours
        </text>
      </g>
    </svg>
  );
}
