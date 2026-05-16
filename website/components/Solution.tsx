"use client";
import { motion, useInView, useScroll, useTransform } from "framer-motion";
import { useRef, useState } from "react";
import { useReducedMotion } from "./useReducedMotion";

const nodes = [
  { x: 50, y: 40, label: "Architecture" },
  { x: 155, y: 25, label: "Patterns" },
  { x: 100, y: 100, label: "Mnemo" },
  { x: 25, y: 135, label: "Decisions" },
  { x: 175, y: 125, label: "Context" },
  { x: 70, y: 175, label: "History" },
  { x: 145, y: 180, label: "Errors" },
];

const edges: [number, number][] = [
  [0, 2], [1, 2], [2, 3], [2, 4], [2, 5], [2, 6], [0, 1], [3, 5], [4, 6],
];

export default function Solution() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-100px" });
  const reduced = useReducedMotion();
  const containerRef = useRef(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ["start end", "end start"] });
  const graphScale = useTransform(scrollYProgress, [0, 0.5], [0.85, 1]);
  const graphRotate = useTransform(scrollYProgress, [0, 1], [-2, 2]);
  const [hoveredNode, setHoveredNode] = useState<number | null>(null);

  return (
    <section id="solution" className="relative py-32 lg:py-40" aria-labelledby="solution-heading" ref={ref}>
      <div className="absolute left-0 top-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan/20 to-transparent" aria-hidden="true" />
      <div className="absolute right-0 top-[20%] w-[500px] h-[500px] bg-cyan/[0.04] blur-[200px]" aria-hidden="true" />
      {/* Contrasting cyan bleed on right */}
      <div className="absolute right-0 top-0 w-[4px] h-full bg-gradient-to-b from-transparent via-cyan/40 to-transparent" aria-hidden="true" />

      <div className="max-w-7xl mx-auto px-6" ref={containerRef}>
        {/* Reversed asymmetric layout — graph takes more space, overlaps */}
        <div className="grid lg:grid-cols-[1fr_1.5fr] gap-12 lg:gap-0 items-center">
          <motion.div
            className="order-2 lg:order-1 lg:pr-8"
            initial={reduced ? undefined : { opacity: 0, x: -40 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.7 }}
          >
            <h2 id="solution-heading" className="font-display font-black tracking-tight leading-[0.85]">
              <span className="block text-2xl sm:text-3xl text-zinc-500 italic">Memory that</span>
              <span className="block text-5xl sm:text-6xl lg:text-[8rem] text-cyan italic -mt-1">persists</span>
            </h2>
            <p className="mt-6 text-lg text-zinc-400 leading-relaxed max-w-lg">
              Mnemo builds a living knowledge graph of your engineering context. Every decision, pattern, and architectural choice is preserved — growing stronger with each session.
            </p>
            <ul className="mt-8 space-y-4">
              {["Semantic connections between concepts", "Natural decay of stale information", "Instant recall at session start"].map((item, i) => (
                <motion.li
                  key={i}
                  className="flex items-center gap-3 text-zinc-300 font-mono text-sm"
                  initial={reduced ? undefined : { opacity: 0, x: -20 }}
                  animate={inView ? { opacity: 1, x: 0 } : {}}
                  transition={{ delay: 0.4 + i * 0.15, duration: 0.5 }}
                >
                  <span className="text-cyan">▸</span>
                  {item}
                </motion.li>
              ))}
            </ul>
          </motion.div>

          {/* Animated knowledge graph — larger, overlapping into left column */}
          <motion.div
            className="relative order-1 lg:order-2 lg:-ml-12"
            style={reduced ? undefined : { scale: graphScale, rotate: graphRotate }}
          >
            <motion.div
              className="relative bg-dim border border-cyan/15 p-8 overflow-hidden shadow-[0_0_80px_rgba(34,211,238,0.06)]"
              initial={reduced ? undefined : { opacity: 0, scale: 0.9 }}
              animate={inView ? { opacity: 1, scale: 1 } : {}}
              transition={{ delay: 0.3, duration: 0.8 }}
            >
              <svg viewBox="0 0 200 210" className="w-full h-auto" aria-label="Knowledge graph showing persistent memory connections">
                <defs>
                  <linearGradient id="edge-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#22D3EE" stopOpacity="0.5" />
                    <stop offset="100%" stopColor="#F59E0B" stopOpacity="0.2" />
                  </linearGradient>
                  <linearGradient id="edge-active" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#22D3EE" stopOpacity="0.9" />
                    <stop offset="100%" stopColor="#F59E0B" stopOpacity="0.7" />
                  </linearGradient>
                </defs>
                {edges.map(([from, to], i) => {
                  const n1 = nodes[from];
                  const n2 = nodes[to];
                  const mx = (n1.x + n2.x) / 2 + (i % 2 === 0 ? 15 : -15);
                  const my = (n1.y + n2.y) / 2 - (i % 2 === 0 ? 15 : -10);
                  const pathId = `edge-path-${i}`;
                  const isActive = hoveredNode === from || hoveredNode === to;
                  return (
                    <g key={`edge-${i}`}>
                      <motion.path
                        id={pathId}
                        d={`M ${n1.x} ${n1.y} Q ${mx} ${my} ${n2.x} ${n2.y}`}
                        stroke={isActive ? "url(#edge-active)" : "url(#edge-grad)"}
                        strokeWidth={isActive ? "2.5" : "1.2"}
                        fill="none"
                        initial={reduced ? { opacity: 1 } : { pathLength: 0, opacity: 0 }}
                        animate={inView ? { pathLength: 1, opacity: 1 } : {}}
                        transition={{ delay: 0.5 + i * 0.12, duration: 0.9, ease: "easeOut" }}
                      />
                      {!reduced && inView && (
                        <circle r="2.5" fill="#22D3EE" opacity="0.8">
                          <animateMotion dur={`${2.5 + i * 0.3}s`} repeatCount="indefinite" begin={`${i * 0.4}s`}>
                            <mpath href={`#${pathId}`} />
                          </animateMotion>
                          <animate attributeName="opacity" values="0;0.9;0.9;0" dur={`${2.5 + i * 0.3}s`} repeatCount="indefinite" begin={`${i * 0.4}s`} />
                        </circle>
                      )}
                    </g>
                  );
                })}
                {nodes.map((node, i) => {
                  const isCenter = i === 2;
                  const isHovered = hoveredNode === i;
                  const isConnected = hoveredNode !== null && edges.some(([a, b]) => (a === hoveredNode && b === i) || (b === hoveredNode && a === i));
                  const highlight = isHovered || isConnected;
                  return (
                    <motion.g
                      key={`node-${i}`}
                      initial={reduced ? { opacity: 1 } : { scale: 0, opacity: 0 }}
                      animate={inView ? { scale: 1, opacity: 1 } : {}}
                      transition={{ delay: 0.8 + i * 0.12, type: "spring", stiffness: 200 }}
                      onMouseEnter={() => setHoveredNode(i)}
                      onMouseLeave={() => setHoveredNode(null)}
                      className="cursor-pointer"
                    >
                      {isCenter && !reduced && (
                        <circle cx={node.x} cy={node.y} r="14" fill="none" stroke="rgba(34,211,238,0.3)" strokeWidth="1" className="animate-ping-svg" />
                      )}
                      {highlight && (
                        <circle cx={node.x} cy={node.y} r={isCenter ? 22 : 14} fill="none" stroke="rgba(34,211,238,0.3)" strokeWidth="1" />
                      )}
                      <circle
                        cx={node.x} cy={node.y}
                        r={isCenter ? 14 : highlight ? 8 : 6}
                        fill={isCenter ? "#22D3EE" : highlight ? "rgba(34,211,238,0.7)" : "rgba(34,211,238,0.4)"}
                        className={!reduced && !isCenter && !highlight ? "node-pulse" : ""}
                        style={!reduced && !isCenter ? { animationDelay: `${i * 0.5}s` } : undefined}
                      />
                      <text x={node.x} y={node.y + (isCenter ? 24 : 15)} textAnchor="middle" className={`text-[6px] font-mono ${highlight ? "fill-cyan" : "fill-zinc-400"}`}>
                        {node.label}
                      </text>
                    </motion.g>
                  );
                })}
              </svg>
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 bg-cyan/10 rounded-full blur-[100px]" aria-hidden="true" />
            </motion.div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
