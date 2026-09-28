// A small horizontal bar chart, hand rolled to match the schematic's own
// style rather than pull in a charting library for three simple charts.
// Rounded bar ends, a legend only when there is more than one series,
// value labels read as plain text, never coloured like the bars
// themselves, a hairline zero line when values go negative.

export default function BarChart({ data, seriesKeys, seriesLabels, seriesColors, valueFormat = (v) => `${v}` }) {
  const allValues = data.flatMap((d) => seriesKeys.map((k) => d[k]));
  const maxAbs = Math.max(...allValues.map(Math.abs), 1);
  const hasNegative = allValues.some((v) => v < 0);
  const zeroPct = hasNegative ? 50 : 0;
  const barHeight = seriesKeys.length > 1 ? 10 : 16;
  const rowHeight = seriesKeys.length > 1 ? 26 : 20;

  return (
    <div>
      {seriesKeys.length > 1 && (
        <div className="flex gap-4 mb-3 text-xs text-slate-400">
          {seriesKeys.map((k, i) => (
            <span key={k} className="flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: seriesColors[i] }} />
              {seriesLabels[i]}
            </span>
          ))}
        </div>
      )}
      <div className="flex flex-col gap-3">
        {data.map((d) => (
          <div key={d.label} className="flex items-center gap-3 text-xs">
            <div className="w-36 text-slate-400 text-right shrink-0">{d.label}</div>
            <div className="flex-1 relative" style={{ height: rowHeight }}>
              {hasNegative && <div className="absolute top-0 bottom-0 w-px bg-slate-700" style={{ left: `${zeroPct}%` }} />}
              {seriesKeys.map((k, i) => {
                const value = d[k];
                const widthPct = (Math.abs(value) / maxAbs) * (hasNegative ? 50 : 100);
                const top = seriesKeys.length > 1 ? i * (barHeight + 4) : (rowHeight - barHeight) / 2;
                const left = hasNegative ? (value < 0 ? zeroPct - widthPct : zeroPct) : 0;
                return (
                  <div
                    key={k}
                    className="absolute"
                    style={{
                      left: `${left}%`,
                      width: `${widthPct}%`,
                      top,
                      height: barHeight,
                      background: seriesColors[i],
                      borderRadius: value < 0 ? "4px 0 0 4px" : "0 4px 4px 0",
                    }}
                  />
                );
              })}
            </div>
            <div className="w-32 text-slate-300 shrink-0">
              {seriesKeys.map((k) => valueFormat(d[k])).join(" vs ")}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
