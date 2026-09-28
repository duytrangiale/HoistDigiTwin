import { useEffect, useState } from "react";

// The hoist circuit, redrawn as SVG to match the process diagram this was
// built from. Source names are generic (Source A / Source B), matching
// config.yaml's own naming, rather than any site specific codes. The
// dashed rectangle marks the same "model boundary" the original diagram
// annotates: everything from the merged feed conveyor onward is what the
// simulation actually models, the two upstream sources are context only.
//
// The animation (ore flow, skip cycling, bin levels, one active source at
// a time) is illustrative, running on its own timers, not driven by a live
// simulation tick, see phase7_plan.md for why.

const STROKE = "#94a3b8";
const FILL = "#1e293b";
const LABEL = "#cbd5e1";
const SOURCE_SWITCH_SECONDS = 5;

function Box({ x, y, w, h, label, fill = FILL }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} fill={fill} stroke={STROKE} strokeWidth={1.5} rx={4} />
      <text x={x + w / 2} y={y + h / 2} fill={LABEL} fontSize={11} textAnchor="middle" dominantBaseline="middle">
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
      <text x={x + w / 2} y={y + h + 14} fill={LABEL} fontSize={11} textAnchor="middle">
        {label}
      </text>
    </g>
  );
}

function SourceStack({ x, label, active }) {
  return (
    <g opacity={active ? 1 : 0.45}>
      <text x={x + 40} y={14} fill={active ? "#7dd3fc" : "#7dd3fc"} fontSize={12} fontWeight="600" textAnchor="middle">
        {label}
        {active ? " (active)" : ""}
      </text>
      <Hopper x={x} y={22} w={80} h={40} label="ROM bin" />
      <line x1={x + 40} y1={76} x2={x + 40} y2={92} stroke={STROKE} strokeWidth={1.5} />
      <Box x={x + 10} y={92} w={60} h={26} label="Crusher" />
      <line x1={x + 40} y1={118} x2={x + 40} y2={134} stroke={STROKE} strokeWidth={1.5} />
      <Box x={x + 10} y={134} w={60} h={26} label="Surge bin" />
      <line x1={x + 40} y1={160} x2={x + 40} y2={176} stroke={STROKE} strokeWidth={1.5} />
      <Box x={x + 10} y={176} w={60} h={22} label="Feeder" />
    </g>
  );
}

// a small dot that repeatedly travels along a path, standing in for ore
// moving on a conveyor. Several, staggered in time, read as a flow.
function FlowDots({ path, count = 3, duration = 2.2, color = "#fbbf24" }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <circle key={i} r={3.5} fill={color}>
          <animateMotion dur={`${duration}s`} repeatCount="indefinite" begin={`${(i * duration) / count}s`} path={path} />
        </circle>
      ))}
    </>
  );
}

function OreBin({ x, y, label, phase }) {
  // fill level rises and falls slowly, phase offset so the three bins
  // are not perfectly in sync
  const clipId = `bin-clip-${x}-${y}`;
  return (
    <g>
      <rect x={x} y={y} width={80} height={90} fill={FILL} stroke={STROKE} strokeWidth={1.5} rx={4} />
      <clipPath id={clipId}>
        <rect x={x + 6} y={y + 10} width={68} height={74} rx={2} />
      </clipPath>
      <rect x={x + 6} y={y + 40} width={68} height={44} fill="#334155" clipPath={`url(#${clipId})`}>
        <animate
          attributeName="height"
          values="30;60;30"
          dur="7s"
          begin={`${phase}s`}
          repeatCount="indefinite"
        />
        <animate attributeName="y" values={`${y + 54};${y + 24};${y + 54}`} dur="7s" begin={`${phase}s`} repeatCount="indefinite" />
      </rect>
      <text x={x + 40} y={y + 18} fill={LABEL} fontSize={11} textAnchor="middle">
        {label}
      </text>
    </g>
  );
}

const BINS_Y = 280;
const FLASKS_Y = 400;
const WINDER_Y = 470;
const SHAFT_Y = 500;
const SHAFT_H = 110;

// matches the status strings src/serve/api.py's predict_winder_rul returns
const WINDER_COLOR = {
  healthy: "#22c55e",
  watch: "#f59e0b",
  "schedule maintenance soon": "#f43f5e",
};

export default function Schematic({ winderStatus = "healthy" }) {
  const [activeSource, setActiveSource] = useState("A");

  useEffect(() => {
    const id = setInterval(() => {
      setActiveSource((s) => (s === "A" ? "B" : "A"));
    }, SOURCE_SWITCH_SECONDS * 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <svg viewBox="0 0 1100 640" className="w-full h-auto" role="img" aria-label="Hoist circuit schematic">
      <rect x={0} y={0} width={1100} height={640} fill="#0b1220" />

      {/* the two ore sources, outside the model boundary. Only one feeds
          the conveyor at a time, matching source_switch_process in the
          real simulation */}
      <g transform="translate(40, 20)">
        <SourceStack x={0} label="Source A" active={activeSource === "A"} />
      </g>
      <g transform="translate(180, 20)">
        <SourceStack x={0} label="Source B" active={activeSource === "B"} />
      </g>

      {/* feed lines merging onto the shared conveyor */}
      <path d="M 90 218 L 90 250 L 330 250" fill="none" stroke={STROKE} strokeWidth={1.5} opacity={activeSource === "A" ? 1 : 0.3} />
      <path
        d="M 230 218 L 230 235 L 330 235 L 330 250"
        fill="none"
        stroke={STROKE}
        strokeWidth={1.5}
        opacity={activeSource === "B" ? 1 : 0.3}
      />
      {activeSource === "A" && <FlowDots path="M 90 218 L 90 250 L 330 250 L 510 250 L 510 280" />}
      {activeSource === "B" && <FlowDots path="M 230 218 L 230 235 L 330 235 L 330 250 L 510 250 L 510 280" />}

      {/* the model boundary, matching the original diagram's own annotation */}
      <rect
        x={330}
        y={30}
        width={720}
        height={585}
        fill="none"
        stroke="#475569"
        strokeWidth={1.5}
        strokeDasharray="6 5"
        rx={10}
      />
      <text x={340} y={22} fill="#64748b" fontSize={11}>
        the model boundary
      </text>

      {/* feed conveyor into the three ore bins */}
      <line x1={330} y1={250} x2={510} y2={250} stroke={STROKE} strokeWidth={2} />
      <line x1={510} y1={250} x2={510} y2={BINS_Y} stroke={STROKE} strokeWidth={2} />
      <text x={340} y={242} fill="#64748b" fontSize={10}>
        conveyor
      </text>

      <OreBin x={470} y={BINS_Y} label="Ore bin 1" phase={0} />
      <OreBin x={580} y={BINS_Y} label="Ore bin 2" phase={2.3} />
      <OreBin x={690} y={BINS_Y} label="Ore bin 3" phase={4.6} />

      {/* feeders and the lower conveyor to the flasks */}
      <line x1={510} y1={BINS_Y + 90} x2={510} y2={FLASKS_Y - 20} stroke={STROKE} strokeWidth={1.5} />
      <line x1={620} y1={BINS_Y + 90} x2={620} y2={FLASKS_Y - 40} stroke={STROKE} strokeWidth={1.5} />
      <line x1={730} y1={BINS_Y + 90} x2={730} y2={FLASKS_Y - 40} stroke={STROKE} strokeWidth={1.5} />
      <line x1={510} y1={FLASKS_Y - 20} x2={730} y2={FLASKS_Y - 20} stroke={STROKE} strokeWidth={1.5} />
      <text x={520} y={FLASKS_Y - 28} fill="#64748b" fontSize={10}>
        conveyor
      </text>
      <line x1={580} y1={FLASKS_Y - 20} x2={580} y2={FLASKS_Y} stroke={STROKE} strokeWidth={1.5} />
      <line x1={680} y1={FLASKS_Y - 20} x2={680} y2={FLASKS_Y} stroke={STROKE} strokeWidth={1.5} />
      <FlowDots path={`M 510 ${BINS_Y + 90} L 510 ${FLASKS_Y - 20} L 580 ${FLASKS_Y - 20} L 580 ${FLASKS_Y}`} count={2} duration={2.6} />

      <Box x={550} y={FLASKS_Y} w={60} h={30} label="Flask west" />
      <Box x={650} y={FLASKS_Y} w={60} h={30} label="Flask east" />

      {/* the winder at the surface, and where a hoisted skip dumps */}
      <circle
        id="winder"
        cx={560}
        cy={WINDER_Y}
        r={20}
        fill={WINDER_COLOR[winderStatus] ?? WINDER_COLOR.healthy}
        stroke={STROKE}
        strokeWidth={1.5}
        style={{ transition: "fill 0.4s" }}
      />
      <text x={560} y={WINDER_Y + 4} fill="#0b1220" fontSize={10} textAnchor="middle" fontWeight="600">
        winder
      </text>
      <Box x={640} y={WINDER_Y - 15} w={90} h={30} label="surface surge bin" />

      {/* the production shaft, skip west and skip east inside it, each
          cycling up toward the surface and back down, out of phase with
          each other, so the winder always has one skip in motion */}
      <rect x={540} y={SHAFT_Y} width={190} height={SHAFT_H} fill="#0f172a" stroke={STROKE} strokeWidth={1.5} />
      <text x={545} y={SHAFT_Y - 6} fill="#64748b" fontSize={10}>
        production shaft
      </text>
      <line x1={580} y1={FLASKS_Y + 30} x2={580} y2={SHAFT_Y} stroke={STROKE} strokeWidth={1.5} />
      <line x1={680} y1={FLASKS_Y + 30} x2={680} y2={SHAFT_Y} stroke={STROKE} strokeWidth={1.5} />
      <line x1={560} y1={WINDER_Y + 20} x2={560} y2={SHAFT_Y + 20} stroke="#64748b" strokeWidth={1} strokeDasharray="2 3" />
      <line x1={700} y1={WINDER_Y + 20} x2={700} y2={SHAFT_Y + 70} stroke="#64748b" strokeWidth={1} strokeDasharray="2 3" />

      {/* each skip is a group, rect and label together, moved with a
          transform so the label travels with the box instead of a
          static box moving away from a fixed label */}
      <g id="skip-west" transform={`translate(0, ${SHAFT_Y + 20})`}>
        <animateTransform
          attributeName="transform"
          type="translate"
          values={`0,${SHAFT_Y + 20}; 0,${WINDER_Y + 18}; 0,${SHAFT_Y + 20}`}
          keyTimes="0;0.5;1"
          dur="6s"
          repeatCount="indefinite"
        />
        <rect x={560} y={0} width={40} height={28} fill="#38bdf8" stroke={STROKE} strokeWidth={1.5} rx={3} />
        <text x={580} y={18} fill="#0b1220" fontSize={9} textAnchor="middle">
          skip W
        </text>
      </g>
      <g id="skip-east" transform={`translate(0, ${SHAFT_Y + 70})`}>
        <animateTransform
          attributeName="transform"
          type="translate"
          values={`0,${SHAFT_Y + 70}; 0,${WINDER_Y + 18}; 0,${SHAFT_Y + 70}`}
          keyTimes="0;0.5;1"
          dur="6s"
          begin="-3s"
          repeatCount="indefinite"
        />
        <rect x={660} y={0} width={40} height={28} fill="#38bdf8" stroke={STROKE} strokeWidth={1.5} rx={3} />
        <text x={680} y={18} fill="#0b1220" fontSize={9} textAnchor="middle">
          skip E
        </text>
      </g>

      <text x={340} y={628} fill="#475569" fontSize={10}>
        Schematic, not to scale. Animation is illustrative, not a live simulation feed.
      </text>
    </svg>
  );
}
