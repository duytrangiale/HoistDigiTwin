import { useEffect, useState } from "react";

// The hoist circuit, redrawn as SVG to match the reference process diagram:
// two sources on the left feeding a shared conveyor, three ore bins, two
// flasks, and a tall production shaft on the right with the winder at
// surface level. Source names are generic (Source A / Source B), matching
// config.yaml's own naming, rather than any site specific codes.
//
// The animation (ore flow, skip cycling, one active source at a time) is
// illustrative, running on its own timers, not driven by a live simulation
// tick. Two things ARE real: the skip cycle speed and the ore flow speed
// scale with the winder speed and feed rate sliders respectively, the same
// direction those settings actually push the real simulation, see
// phase7_plan.md.

const STROKE = "#94a3b8";
const FILL = "#1e293b";
const LABEL = "#e2e8f0";
const MUTED = "#94a3b8";
const SOURCE_SWITCH_SECONDS = 5;

const STATUS_COLOR = {
  healthy: "#0ca30c",
  watch: "#fab219",
  "schedule maintenance soon": "#d03b3b",
};

function Box({ x, y, w, h, label, fill = FILL, labelColor = LABEL, fontSize = 13 }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} fill={fill} stroke={STROKE} strokeWidth={1.5} rx={5} />
      <text x={x + w / 2} y={y + h / 2} fill={labelColor} fontSize={fontSize} textAnchor="middle" dominantBaseline="middle">
        {label}
      </text>
    </g>
  );
}

function Hopper({ x, y, w, h, label }) {
  const botW = w * 0.4;
  const points = [
    [x, y],
    [x + w, y],
    [x + w / 2 + botW / 2, y + h],
    [x + w / 2 - botW / 2, y + h],
  ]
    .map((p) => p.join(","))
    .join(" ");
  return (
    <g>
      <polygon points={points} fill={FILL} stroke={STROKE} strokeWidth={1.5} />
      <text x={x + w / 2} y={y + h + 16} fill={LABEL} fontSize={13} textAnchor="middle">
        {label}
      </text>
    </g>
  );
}

function SourceStack({ x, label, active }) {
  return (
    <g opacity={active ? 1 : 0.4}>
      <text x={x + 45} y={16} fill="#7dd3fc" fontSize={14} fontWeight="600" textAnchor="middle">
        {label}
        {active ? " (feeding now)" : ""}
      </text>
      <Hopper x={x} y={26} w={90} h={44} label="ROM bin" />
      <line x1={x + 45} y1={86} x2={x + 45} y2={104} stroke={STROKE} strokeWidth={1.5} />
      <Box x={x + 12} y={104} w={66} h={28} label="Crusher" />
      <line x1={x + 45} y1={132} x2={x + 45} y2={150} stroke={STROKE} strokeWidth={1.5} />
      <Box x={x + 12} y={150} w={66} h={28} label="Surge bin" />
      <line x1={x + 45} y1={178} x2={x + 45} y2={196} stroke={STROKE} strokeWidth={1.5} />
      <Box x={x + 12} y={196} w={66} h={24} label="Feeder" />
    </g>
  );
}

function FlowDots({ path, count = 3, duration = 2.2, color = "#eda100" }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <circle key={i} r={4} fill={color}>
          <animateMotion dur={`${duration}s`} repeatCount="indefinite" begin={`${(i * duration) / count}s`} path={path} />
        </circle>
      ))}
    </>
  );
}

function OreBin({ x, y, label, phase, fillBoost }) {
  const clipId = `bin-clip-${x}-${y}`;
  // fill level oscillates around a baseline set by fillBoost (0 to 1), so a
  // higher feed rate visibly keeps these bins fuller on average
  const baseline = 30 + fillBoost * 40;
  const swing = 18;
  const lowH = Math.max(8, baseline - swing);
  const highH = Math.min(78, baseline + swing);
  return (
    <g>
      <rect x={x} y={y} width={90} height={100} fill={FILL} stroke={STROKE} strokeWidth={1.5} rx={5} />
      <clipPath id={clipId}>
        <rect x={x + 7} y={y + 12} width={76} height={82} rx={3} />
      </clipPath>
      <rect x={x + 7} y={y + 94 - lowH} width={76} height={lowH} fill="#256abf" clipPath={`url(#${clipId})`}>
        <animate attributeName="height" values={`${lowH};${highH};${lowH}`} dur="7s" begin={`${phase}s`} repeatCount="indefinite" />
        <animate
          attributeName="y"
          values={`${y + 94 - lowH};${y + 94 - highH};${y + 94 - lowH}`}
          dur="7s"
          begin={`${phase}s`}
          repeatCount="indefinite"
        />
      </rect>
      <text x={x + 45} y={y + 20} fill={LABEL} fontSize={13} textAnchor="middle">
        {label}
      </text>
    </g>
  );
}

// layout, left to right and top to bottom, matching the reference diagram's
// own orientation: sources feed a shared conveyor into three ore bins, a
// second conveyor carries ore to two flasks, which feed the shaft on the
// right, winder at the top of it, at surface level
const BINS_Y = 330;
const FLASKS_Y = 470;
const SHAFT_X = 1180;
const SHAFT_W = 230;
const SHAFT_Y = 190;
const SHAFT_H = 480;
const WINDER_X = 1240;
const WINDER_Y = 140;
const READOUT_X = 1045;

// each skip's own lane inside the shaft, and the two points its rope
// actually travels between: low, where its flask loads it, high, near the
// surface where the winder dumps it. Shared by the flask connector paths,
// the skip's own animation, and its rope, so all three always agree.
const SKIP_W_X = SHAFT_X + 56;
const SKIP_W_LOW_Y = SHAFT_Y + 238;
const SKIP_E_X = SHAFT_X + 176;
const SKIP_E_LOW_Y = SHAFT_Y + 438;
const SKIP_HIGH_Y = SHAFT_Y + 40;

export default function Schematic({
  winderStatus = "healthy",
  feedRateMultiplier = 1,
  winderSpeedMultiplier = 1,
  predictedMonthlyTonnes = null,
}) {
  const [activeSource, setActiveSource] = useState("A");

  useEffect(() => {
    const id = setInterval(() => {
      setActiveSource((s) => (s === "A" ? "B" : "A"));
    }, SOURCE_SWITCH_SECONDS * 1000);
    return () => clearInterval(id);
  }, []);

  const flowDuration = Math.max(0.6, 2.2 / feedRateMultiplier);
  const skipDuration = Math.max(1.5, 6 / winderSpeedMultiplier);
  const fillBoost = Math.min(1, Math.max(0, (feedRateMultiplier - 0.5) / 1.0));

  return (
    <svg viewBox="0 0 1500 750" className="w-full h-auto" role="img" aria-label="Hoist circuit schematic">
      <rect x={0} y={0} width={1500} height={750} fill="#0b1220" />

      {/* surface line */}
      <line x1={880} y1={110} x2={1480} y2={110} stroke="#334155" strokeWidth={1.5} />
      <text x={890} y={102} fill={MUTED} fontSize={12} letterSpacing="1">
        SURFACE
      </text>

      {/* the two ore sources, outside the model boundary. Only one feeds
          the conveyor at a time, matching source_switch_process in the
          real simulation */}
      <g transform="translate(30, 20)">
        <SourceStack x={0} label="Source A" active={activeSource === "A"} />
      </g>
      <g transform="translate(210, 20)">
        <SourceStack x={0} label="Source B" active={activeSource === "B"} />
      </g>

      <path d="M 105 246 L 105 300 L 460 300" fill="none" stroke={STROKE} strokeWidth={1.5} opacity={activeSource === "A" ? 1 : 0.3} />
      <path
        d="M 285 246 L 285 280 L 460 280 L 460 300"
        fill="none"
        stroke={STROKE}
        strokeWidth={1.5}
        opacity={activeSource === "B" ? 1 : 0.3}
      />
      {activeSource === "A" && <FlowDots path="M 105 246 L 105 300 L 460 300 L 610 300 L 610 330" duration={flowDuration} />}
      {activeSource === "B" && (
        <FlowDots path="M 285 246 L 285 280 L 460 280 L 460 300 L 610 300 L 610 330" duration={flowDuration} />
      )}

      {/* the model boundary, matching the original diagram's own annotation */}
      <rect x={460} y={30} width={990} height={690} fill="none" stroke="#475569" strokeWidth={1.5} strokeDasharray="7 6" rx={12} />
      <text x={472} y={22} fill={MUTED} fontSize={13}>
        the model boundary
      </text>

      {/* one conveyor arriving from the merge point, feeding all three
          bins, not just the first one */}
      <line x1={460} y1={300} x2={880} y2={300} stroke={STROKE} strokeWidth={2} />
      <line x1={610} y1={300} x2={610} y2={BINS_Y} stroke={STROKE} strokeWidth={2} />
      <line x1={745} y1={300} x2={745} y2={BINS_Y} stroke={STROKE} strokeWidth={2} />
      <line x1={880} y1={300} x2={880} y2={BINS_Y} stroke={STROKE} strokeWidth={2} />
      <text x={472} y={292} fill={MUTED} fontSize={12}>
        conveyor
      </text>
      <FlowDots path={`M 610 300 L 745 300 L 880 300`} count={2} duration={flowDuration * 1.4} />

      <OreBin x={565} y={BINS_Y} label="Ore bin 1" phase={0} fillBoost={fillBoost} />
      <OreBin x={700} y={BINS_Y} label="Ore bin 2" phase={2.3} fillBoost={fillBoost} />
      <OreBin x={835} y={BINS_Y} label="Ore bin 3" phase={4.6} fillBoost={fillBoost} />

      {/* feeders below all three bins draining onto one shared conveyor,
          which carries on to the two flasks */}
      <line x1={610} y1={BINS_Y + 100} x2={610} y2={BINS_Y + 115} stroke={STROKE} strokeWidth={1.5} />
      <line x1={745} y1={BINS_Y + 100} x2={745} y2={BINS_Y + 115} stroke={STROKE} strokeWidth={1.5} />
      <line x1={880} y1={BINS_Y + 100} x2={880} y2={BINS_Y + 115} stroke={STROKE} strokeWidth={1.5} />
      <line x1={610} y1={BINS_Y + 115} x2={880} y2={BINS_Y + 115} stroke={STROKE} strokeWidth={1.5} />
      <text x={620} y={BINS_Y + 107} fill={MUTED} fontSize={12}>
        feeders
      </text>
      <text x={620} y={BINS_Y + 128} fill={MUTED} fontSize={12}>
        conveyor
      </text>
      <line x1={682} y1={BINS_Y + 115} x2={682} y2={FLASKS_Y} stroke={STROKE} strokeWidth={1.5} />
      <line x1={812} y1={BINS_Y + 115} x2={812} y2={FLASKS_Y} stroke={STROKE} strokeWidth={1.5} />
      <FlowDots
        path={`M 610 ${BINS_Y + 100} L 610 ${BINS_Y + 115} L 880 ${BINS_Y + 115} L 812 ${BINS_Y + 115} L 812 ${FLASKS_Y}`}
        count={2}
        duration={flowDuration * 1.2}
      />

      <Box x={645} y={FLASKS_Y} w={75} h={36} label="Flask west" />
      <Box x={775} y={FLASKS_Y} w={75} h={36} label="Flask east" />

      {/* the predicted tonnes readout, in the open space between the
          bins/flasks and the shaft, the live number this whole panel
          leads with */}
      {predictedMonthlyTonnes != null && (
        <g>
          <text x={READOUT_X} y={330} fill={MUTED} fontSize={13} textAnchor="middle">
            predicted, from the live surrogate
          </text>
          <text x={READOUT_X} y={368} fill="#38bdf8" fontSize={30} fontWeight="700" textAnchor="middle">
            {Math.round(predictedMonthlyTonnes).toLocaleString()}
          </text>
          <text x={READOUT_X} y={392} fill={MUTED} fontSize={13} textAnchor="middle">
            tonnes / month
          </text>
        </g>
      )}

      {/* the winder at the surface, with the surge bin it dumps into
          stacked above it, clear of the shaft's own label */}
      <Box x={WINDER_X - 80} y={50} w={160} h={44} label="surface surge bin" fontSize={13} />
      <circle
        id="winder"
        cx={WINDER_X}
        cy={WINDER_Y}
        r={28}
        fill={STATUS_COLOR[winderStatus] ?? STATUS_COLOR.healthy}
        stroke={STROKE}
        strokeWidth={1.5}
        style={{ transition: "fill 0.4s" }}
      />
      <text x={WINDER_X} y={WINDER_Y + 5} fill="#0b1220" fontSize={13} textAnchor="middle" fontWeight="700">
        winder
      </text>

      {/* the production shaft, skip west and skip east inside it, cycling
          up toward the surface and back down, out of phase with each
          other. Cycle speed scales with the winder speed slider. */}
      <rect x={SHAFT_X} y={SHAFT_Y} width={SHAFT_W} height={SHAFT_H} fill="#0f172a" stroke={STROKE} strokeWidth={1.5} />
      <text x={SHAFT_X + SHAFT_W - 8} y={SHAFT_Y - 12} fill={MUTED} fontSize={13} textAnchor="end">
        production shaft
      </text>
      {/* flasks load their own skip where it rests, lower in the shaft, not
          at the top where it dumps. Right angled, like every other
          conveyor here, rather than a diagonal that would cut across the
          other flask's box or the readout above. */}
      <path
        d={`M 682 ${FLASKS_Y + 36} L 682 ${FLASKS_Y + 70} L ${SKIP_W_X} ${FLASKS_Y + 70} L ${SKIP_W_X} ${SKIP_W_LOW_Y}`}
        fill="none"
        stroke={STROKE}
        strokeWidth={1.5}
      />
      <path
        d={`M 812 ${FLASKS_Y + 36} L 812 ${FLASKS_Y + 95} L ${SKIP_E_X} ${FLASKS_Y + 95} L ${SKIP_E_X} ${SKIP_E_LOW_Y}`}
        fill="none"
        stroke={STROKE}
        strokeWidth={1.5}
      />

      {/* the rope each skip actually hangs from, its lower end animated in
          exact lockstep with that skip's own animation below, so it reads
          as attached rather than the skip floating free */}
      <line x1={WINDER_X - 8} y1={WINDER_Y + 24} x2={SKIP_W_X} y2={SKIP_W_LOW_Y} stroke="#cbd5e1" strokeWidth={1.5}>
        <animate
          attributeName="y2"
          values={`${SKIP_W_LOW_Y};${SKIP_HIGH_Y};${SKIP_W_LOW_Y}`}
          keyTimes="0;0.5;1"
          dur={`${skipDuration}s`}
          repeatCount="indefinite"
        />
      </line>
      <line x1={WINDER_X + 8} y1={WINDER_Y + 24} x2={SKIP_E_X} y2={SKIP_E_LOW_Y} stroke="#cbd5e1" strokeWidth={1.5}>
        <animate
          attributeName="y2"
          values={`${SKIP_E_LOW_Y};${SKIP_HIGH_Y};${SKIP_E_LOW_Y}`}
          keyTimes="0;0.5;1"
          dur={`${skipDuration}s`}
          begin={`${-skipDuration / 2}s`}
          repeatCount="indefinite"
        />
      </line>

      <g transform={`translate(0, ${SKIP_W_LOW_Y})`}>
        <animateTransform
          attributeName="transform"
          type="translate"
          values={`0,${SKIP_W_LOW_Y}; 0,${SKIP_HIGH_Y}; 0,${SKIP_W_LOW_Y}`}
          keyTimes="0;0.5;1"
          dur={`${skipDuration}s`}
          repeatCount="indefinite"
        />
        <rect x={SKIP_W_X - 26} y={0} width={52} height={36} fill="#3987e5" stroke={STROKE} strokeWidth={1.5} rx={4} />
        <text x={SKIP_W_X} y={23} fill="#0b1220" fontSize={11} textAnchor="middle" fontWeight="600">
          skip W
        </text>
      </g>
      <g transform={`translate(0, ${SKIP_E_LOW_Y})`}>
        <animateTransform
          attributeName="transform"
          type="translate"
          values={`0,${SKIP_E_LOW_Y}; 0,${SKIP_HIGH_Y}; 0,${SKIP_E_LOW_Y}`}
          keyTimes="0;0.5;1"
          dur={`${skipDuration}s`}
          begin={`${-skipDuration / 2}s`}
          repeatCount="indefinite"
        />
        <rect x={SKIP_E_X - 26} y={0} width={52} height={36} fill="#3987e5" stroke={STROKE} strokeWidth={1.5} rx={4} />
        <text x={SKIP_E_X} y={23} fill="#0b1220" fontSize={11} textAnchor="middle" fontWeight="600">
          skip E
        </text>
      </g>

      <text x={472} y={732} fill={MUTED} fontSize={12}>
        Schematic, not to scale. Ore flow and skip speed track the feed rate and winder speed sliders, everything
        else is illustrative.
      </text>
    </svg>
  );
}
