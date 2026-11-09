import { type CSSProperties, useEffect, useRef, useState } from "react";
import {
  Box,
  Cursor,
  curve,
  Glow,
  Plate,
  Press,
  path,
  playSound,
  Ripple,
  Signal,
  useDemoTap,
  type Vec3,
} from "react-isokit";
import { Callout } from "react-isokit/drafting";
import "./isp-pipeline.css";

/* The MOD-ISP workflow as a figure (see process() in app.py). The server decodes an
   upload once, then computes classical, learned and hybrid outputs from it. This figure
   traces two of them: hybrid (DECODE, GATE ranks tiles, NEURAL restores the routed tiles,
   FINISH blends them back and finishes) and the classical baseline, which never touches
   GATE or NEURAL. The learned path (every tile, no gate) is described in the page text. */

type Stage = "decode" | "gate" | "restore" | "finish";
type Slot = { id: Stage; x: number; label: string; screen: string };
type Kind = "hybrid" | "classical";
type Status = "idle" | "run" | "ok" | "on";
type Run = { id: number; kind: Kind | null; step: number; prev: Kind };

const BASE = { x: 0, y: 0, z: 0, w: 244, d: 116, h: 8 };
const ST = { y: 12, z: BASE.h, w: 44, d: 34, h: 46 };
const LID = ST.z + ST.h;
const MID = ST.y + ST.d / 2;
const GLAND = { w: 6, d: 6, h: 3 };
const STAGES: readonly Slot[] = [
  { id: "decode", x: 10, label: "DECODE", screen: "rggb" },
  { id: "gate", x: 70, label: "GATE", screen: "tile rank" },
  { id: "restore", x: 130, label: "NEURAL", screen: "learned" },
  { id: "finish", x: 190, label: "FINISH", screen: "output" },
];
const FIRST = STAGES[0] ?? { id: "decode", x: 10, label: "DECODE", screen: "" };
const LAST = STAGES[STAGES.length - 1] ?? FIRST;
const DEPLOY = { x: 12, y: 66, z: BASE.h, w: 78, d: 36, h: 7 };
const ROLLBACK = { x: 104, y: 70, z: BASE.h, w: 68, d: 28, h: 6 };

// Each stage takes two steps: it starts (run), then finishes (ok).
const HYBRID_STEPS = STAGES.flatMap((_, i) => [280 + 680 * i, 640 + 680 * i]);
const STEPS: Readonly<Record<Kind, readonly number[]>> = {
  hybrid: HYBRID_STEPS,
  classical: [300],
};
const CURRENT: readonly Stage[] = STAGES.flatMap((s) => [s.id, s.id]);
const SIGNAL_MS = 320;
const TRACE_MS = 280;
const BUILD_MS = (HYBRID_STEPS[1] ?? 0) - (HYBRID_STEPS[0] ?? 0);
const LAMP_MS = 70;
const FAN_BLADES = [0, 90, 180, 270] as const;
const ARM = { x: 30, y: 30.5, length: 6.5 };
const PLATE_STYLE = { "--lamp": `${LAMP_MS}ms` } as CSSProperties;
const CHECK = "M0 3l2.2 2.2L6.6 .8";
const BYPASS = "M0 5h10M7 2l3 3-3 3";

const out = (x: number) => x + ST.w - 7;
const into = (x: number) => x + 7;
const cable = (x: number, next: number): Vec3[] =>
  curve(
    [out(x), MID, LID + GLAND.h],
    [out(x) + 7, MID, LID + 16],
    [into(next) - 7, MID, LID + 16],
    [into(next), MID, LID + GLAND.h],
    32,
  );
const CABLES = STAGES.slice(0, -1).flatMap((stage, i) => {
  const next = STAGES[i + 1];
  return next ? [cable(stage.x, next.x)] : [];
});
const BUS_Y = ST.y + ST.d + 10;
const trace = (from: number, y: number, to: number): Vec3[] => [
  [from, y, BASE.h],
  [from, BUS_Y, BASE.h],
  [to, BUS_Y, BASE.h],
  [to, ST.y + ST.d, BASE.h],
];
const HYBRID_TRACE = trace(DEPLOY.x + 60, DEPLOY.y, FIRST.x + ST.w / 2);
const CLASSICAL_TRACE = trace(ROLLBACK.x + 12, ROLLBACK.y, LAST.x + ST.w / 2);
const groove = (points: readonly Vec3[]) =>
  `M${points.map(([x, y]) => `${x} ${y}`).join("L")}`;

const finished = (run: Run) =>
  run.kind === null || run.step >= STEPS[run.kind].length;
const shownPath = (run: Run): Kind =>
  finished(run) ? (run.kind ?? run.prev) : run.prev;

function statusOf(i: number, run: Run): Status {
  const last = i === STAGES.length - 1;
  if (run.kind === "hybrid") {
    if (run.step >= 2 * i + 2) return last ? "on" : "ok";
    if (run.step >= 2 * i + 1) return "run";
    return last ? "ok" : "idle";
  }
  if (run.kind === "classical") {
    if (i === 0) return "ok";
    return last ? (finished(run) ? "on" : "ok") : "idle";
  }
  return last ? "ok" : "idle";
}

function readoutOf(run: Run): string {
  if (run.kind === null) return "ready · hybrid";
  if (run.kind === "classical")
    return finished(run) ? "done · classical" : "classical · skips gate";
  return finished(run)
    ? "done · hybrid"
    : `processing · ${CURRENT[run.step] ?? "finish"}`;
}

function TopMark({ stage }: { stage: Stage }) {
  const cx = ST.w / 2;
  const cy = ST.d / 2;
  if (stage === "restore")
    return (
      <g transform={`translate(${cx} ${cy})`}>
        <circle className="ik-well" r={8} />
        <g className="dp-fan ik-loop">
          {FAN_BLADES.map((turn) => (
            <path
              key={turn}
              className="ik-line"
              d="M1.8 .6Q4.4-2.8 6.9-1.4"
              transform={`rotate(${turn})`}
            />
          ))}
        </g>
        <circle className="ik-face ik-top" r={2.2} />
      </g>
    );
  if (stage === "gate")
    return (
      <g transform={`translate(${cx} ${cy})`}>
        <circle className="ik-detail" r={7.5} />
        <path className="ik-detail" d={CHECK} transform="translate(-3.3 -3)" />
      </g>
    );
  if (stage === "decode")
    return (
      <g transform={`translate(${cx} ${cy})`}>
        {[
          [-7, -7],
          [1.5, -7],
          [-7, 1.5],
          [1.5, 1.5],
        ].map(([x, y]) => (
          <rect
            key={`${x}-${y}`}
            className="ik-well"
            x={x}
            y={y}
            width={5.5}
            height={5.5}
            rx={1.2}
          />
        ))}
      </g>
    );
  return (
    <g transform={`translate(${cx} ${cy})`}>
      <path
        className="ik-detail"
        d="M-6.5 1v5.5h13V1M0 3.5v-10M-3.5-3L0-6.5 3.5-3"
      />
    </g>
  );
}

export default function IspPipeline() {
  const [run, setRun] = useState<Run>({
    id: 0,
    kind: null,
    step: 0,
    prev: "hybrid",
  });
  const [touched, setTouched] = useState(false);
  const timers = useRef<number[]>([]);
  const stop = useRef(() => {});
  const stopMotor = useRef(() => {});
  const clear = () => {
    for (const timer of timers.current) window.clearTimeout(timer);
    timers.current = [];
  };
  useEffect(
    () => () => {
      for (const timer of timers.current) window.clearTimeout(timer);
      stop.current();
      stopMotor.current();
    },
    [],
  );

  const start = (kind: Kind, audible: boolean) => {
    const id = run.id + 1;
    const prev = shownPath(run);
    const steps = STEPS[kind];
    const end = steps[steps.length - 1] ?? 0;
    clear();
    stop.current();
    stopMotor.current();
    if (audible && kind === "classical") stop.current = playSound("whoosh");
    setRun({ id, kind, step: 0, prev });
    timers.current = steps.map((at, i) =>
      window.setTimeout(() => {
        const step = i + 1;
        setRun((r) => (r.id === id ? { ...r, step } : r));
        if (!audible || kind !== "hybrid") return;
        stop.current();
        if (step === 1)
          stopMotor.current = playSound("motor", { duration: BUILD_MS / 1000 });
        else if (step === steps.length) stop.current = playSound("relay");
        else if (step % 2 === 1) stop.current = playSound("process");
      }, at),
    );
    if (!audible) return;
    if (kind === "classical")
      timers.current.push(
        window.setTimeout(() => (stop.current = playSound("relay")), end),
      );
    if (kind === "hybrid")
      timers.current.push(
        window.setTimeout(
          () => (stop.current = playSound("success")),
          end + LAMP_MS,
        ),
      );
  };
  const {
    ref: demoAnchor,
    phase,
    dismiss,
    plate,
  } = useDemoTap(
    () => {
      if (run.kind === null) start("hybrid", false);
    },
    { delay: 500 },
  );
  const press = (action: () => void) => {
    dismiss();
    setTouched(true);
    action();
  };

  const shown = shownPath(run);

  return (
    <Plate
      {...plate}
      fig="Pipeline"
      name="Image workflow"
      hint={run.kind === null ? "Press process" : "Process or classical"}
      readout={readoutOf(run)}
      className="fig-isp-pipeline"
      style={PLATE_STYLE}
      data-kind={run.kind ?? "idle"}
      credit={false}
      fit={[
        BASE,
        {
          x: FIRST.x,
          y: ST.y,
          z: 0,
          w: LAST.x + ST.w - FIRST.x,
          d: ST.d,
          h: LID + 16,
        },
      ]}
      aspect={1.55}
      label="An image pipeline of four stages, decode, gate, neural and finish, joined by cables. Press process to trace the hybrid path through every stage, or press classical to trace the baseline path, which never uses the gate or the neural stage."
    >
      <g ref={demoAnchor}>
        <Box
          {...BASE}
          r={10}
          top={
            <>
              <path className="ik-detail" d={groove(HYBRID_TRACE)} />
              <path className="ik-detail" d={groove(CLASSICAL_TRACE)} />
              {[
                [6, 6],
                [BASE.w - 6, 6],
                [6, BASE.d - 6],
                [BASE.w - 6, BASE.d - 6],
              ].map(([x, y]) => (
                <circle
                  key={`${x}-${y}`}
                  className="ik-detail"
                  cx={x}
                  cy={y}
                  r={1.8}
                />
              ))}
            </>
          }
          front={Array.from({ length: 8 }, (_, k) => (
            <path
              key={k}
              className="ik-detail"
              d={`M${BASE.w - 40 + k * 3.4} 2.5v3`}
            />
          ))}
        />

        {STAGES.map((stage, i) => {
          const status = statusOf(i, run);
          const last = i === STAGES.length - 1;
          return (
            <g key={stage.id}>
              <g className="dp-stage" data-s={status}>
                <Box
                  x={stage.x}
                  {...ST}
                  r={5}
                  top={<TopMark stage={stage.id} />}
                  front={
                    <>
                      <rect
                        className="ik-screen"
                        x={4}
                        y={4}
                        width={36}
                        height={20}
                        rx={2.5}
                      />
                      <g
                        key={`${run.id}-${status}-${shown}`}
                        className="ik-enter"
                      >
                        <text
                          className="ik-screen-text ik-dim"
                          x={7.5}
                          y={10.8}
                          fontSize={5.2}
                        >
                          {stage.screen}
                        </text>
                        {last && run.kind === "classical" && finished(run) ? (
                          <path
                            className="ik-screen-line"
                            d={BYPASS}
                            transform="translate(29 7.4) scale(.6)"
                          />
                        ) : null}
                        {status === "run" ? (
                          <g className="dp-busy ik-loop">
                            {[0, 1, 2].map((k) => (
                              <rect
                                key={k}
                                className="dp-pip"
                                x={7.5 + k * 5}
                                y={16.4}
                                width={3}
                                height={3}
                                rx={0.6}
                                style={{ animationDelay: `${k * 90}ms` }}
                              />
                            ))}
                          </g>
                        ) : last ? (
                          <text
                            className="ik-screen-text"
                            x={7.5}
                            y={20.6}
                            fontSize={5.8}
                          >
                            {shown}
                          </text>
                        ) : status === "ok" ? (
                          <>
                            <path
                              className="ik-screen-line"
                              d={CHECK}
                              transform="translate(7.5 15.2)"
                            />
                            <text
                              className="ik-screen-text"
                              x={17}
                              y={20.6}
                              fontSize={6.6}
                            >
                              ok
                            </text>
                          </>
                        ) : (
                          <text
                            className="ik-screen-text ik-dim"
                            x={7.5}
                            y={20.6}
                            fontSize={6.6}
                          >
                            idle
                          </text>
                        )}
                      </g>
                      <Glow
                        on={status === "run" || status === "on"}
                        className="dp-glow"
                      >
                        <circle
                          className="dp-light ik-loop"
                          cx={7}
                          cy={30.5}
                          r={2}
                        />
                      </Glow>
                      <text className="ik-label dp-name" x={12} y={32.6}>
                        {stage.label}
                      </text>
                      {last ? (
                        <>
                          <path
                            className="ik-detail"
                            d={`M${ARM.x + ARM.length + 1.2} ${ARM.y - 2.4}v4.8`}
                          />
                          <g transform={`translate(${ARM.x} ${ARM.y})`}>
                            <g className="dp-arm">
                              <path
                                className="ik-line"
                                d={`M0 0h${ARM.length}`}
                              />
                            </g>
                            <circle className="ik-fill" r={1} />
                          </g>
                        </>
                      ) : null}
                      {Array.from({ length: 10 }, (_, k) => (
                        <path
                          key={k}
                          className="ik-detail"
                          d={`M${6 + k * 3.6} 37.5v4.5`}
                        />
                      ))}
                    </>
                  }
                  side={
                    <>
                      {Array.from({ length: 3 }, (_, k) => (
                        <path
                          key={k}
                          className="ik-detail"
                          d={`M${4 + k * 3.4} 10v26`}
                        />
                      ))}
                      {last ? (
                        <rect
                          className="ik-well"
                          x={20}
                          y={20}
                          width={8}
                          height={6}
                          rx={1.2}
                        />
                      ) : null}
                    </>
                  }
                />
              </g>
              {i > 0 ? (
                <Box
                  x={into(stage.x) - GLAND.w / 2}
                  y={MID - GLAND.d / 2}
                  z={LID}
                  {...GLAND}
                  r={1.5}
                />
              ) : null}
              {!last ? (
                <Box
                  x={out(stage.x) - GLAND.w / 2}
                  y={MID - GLAND.d / 2}
                  z={LID}
                  {...GLAND}
                  r={1.5}
                />
              ) : null}
            </g>
          );
        })}

        {CABLES.map((points, i) => (
          <g key={`cable-${points.length}-${i}`}>
            <path className="ik-line dp-cable" d={path(points)} />
            {run.kind === "hybrid" && run.step >= 2 * i + 2 ? (
              <Signal
                key={`s-${run.id}`}
                points={points}
                duration={SIGNAL_MS}
              />
            ) : null}
          </g>
        ))}

        {run.kind === "hybrid" ? (
          <Signal
            key={`h-${run.id}`}
            points={HYBRID_TRACE}
            duration={TRACE_MS}
          />
        ) : null}
        {run.kind === "classical" ? (
          <Signal
            key={`c-${run.id}`}
            points={CLASSICAL_TRACE}
            duration={STEPS.classical[0] ?? TRACE_MS}
          />
        ) : null}

        {!touched &&
        run.kind === null &&
        phase !== "aim" &&
        phase !== "press" ? (
          <Ripple {...DEPLOY} r={6} />
        ) : null}
        <Press
          label="Process an image through the hybrid pipeline"
          material="plastic"
          onPress={() => press(() => start("hybrid", true))}
          data-hot={run.kind === null}
        >
          <g>
            <Box
              {...DEPLOY}
              r={6}
              top={
                <>
                  <text className="ik-label dp-key" x={10} y={21}>
                    PROCESS
                  </text>
                  <path
                    className="ik-detail ik-thick"
                    d="M0 6h12M7 1l5 5-5 5"
                    transform={`translate(${DEPLOY.w - 22} 12.5)`}
                  />
                </>
              }
            />
          </g>
        </Press>
        <Press
          label="Process an image through the classical path only"
          material="plastic"
          onPress={() => press(() => start("classical", true))}
        >
          <g>
            <Box
              {...ROLLBACK}
              r={5}
              top={
                <>
                  <path
                    className="ik-detail ik-thick"
                    d={BYPASS}
                    transform="translate(7 10.5) scale(1.1)"
                  />
                  <text className="ik-label dp-key-small" x={21} y={17.2}>
                    CLASSICAL
                  </text>
                </>
              }
            />
          </g>
        </Press>

        <Callout
          at={[LAST.x + ST.w, ST.y + ST.d, LID]}
          dx={24}
          dy={-20}
          label={`out · ${shown}`}
        />
        <Cursor
          at={[
            DEPLOY.x + DEPLOY.w / 2,
            DEPLOY.y + DEPLOY.d / 2,
            DEPLOY.z + DEPLOY.h,
          ]}
          phase={phase}
        />
      </g>
    </Plate>
  );
}
