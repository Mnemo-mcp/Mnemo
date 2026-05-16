"use client";
import { motion, useInView } from "framer-motion";
import { useRef, useState } from "react";
import { useReducedMotion } from "./useReducedMotion";

const agents = [
  { name: "Kiro", shape: "hexagon" },
  { name: "Claude Code", shape: "diamond" },
  { name: "Cursor", shape: "triangle" },
  { name: "Copilot", shape: "circle" },
  { name: "Amazon Q", shape: "square" },
];

function AgentIcon({ shape, className }: { shape: string; className?: string }) {
  const base = className || "w-8 h-8";
  switch (shape) {
    case "hexagon":
      return <svg className={base} viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 2L21 7V17L12 22L3 17V7L12 2Z" stroke="currentColor" strokeWidth="1.5" /></svg>;
    case "diamond":
      return <svg className={base} viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 2L22 12L12 22L2 12L12 2Z" stroke="currentColor" strokeWidth="1.5" /></svg>;
    case "triangle":
      return <svg className={base} viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3L22 21H2L12 3Z" stroke="currentColor" strokeWidth="1.5" /></svg>;
    case "circle":
      return <svg className={base} viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5" /></svg>;
    case "square":
      return <svg className={base} viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="3" y="3" width="18" height="18" stroke="currentColor" strokeWidth="1.5" /></svg>;
    default:
      return null;
  }
}

export default function Agents() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-100px" });
  const reduced = useReducedMotion();
  const [hoveredAgent, setHoveredAgent] = useState<number | null>(null);

  return (
    <section id="agents" className="relative py-32" aria-labelledby="agents-heading" ref={ref}>
      <div className="absolute left-0 top-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan/20 to-transparent" aria-hidden="true" />

      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          className="text-center mb-16"
          initial={reduced ? undefined : { opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
        >
          <h2 id="agents-heading" className="font-display font-black text-4xl sm:text-5xl lg:text-[4.5rem] tracking-tight italic leading-[0.9]">
            One memory.{" "}
            <span className="text-cyan">Every agent.</span>
          </h2>
          <p className="mt-4 text-zinc-400 text-lg max-w-xl mx-auto">
            Mnemo works with every AI coding agent you use — seamlessly sharing context across all of them.
          </p>
        </motion.div>

        <div className="relative" aria-label="Supported AI agents connected to central Mnemo node">
          {/* Mobile: stacked */}
          <div className="md:hidden space-y-3">
            <div className="flex justify-center mb-6">
              <motion.div
                className="w-16 h-16 bg-cyan/10 border-2 border-cyan flex items-center justify-center"
                initial={reduced ? undefined : { scale: 0 }}
                animate={inView ? { scale: 1 } : {}}
                transition={{ delay: 0.3, type: "spring", stiffness: 150 }}
              >
                <span className="font-display font-bold text-cyan text-lg italic">M</span>
              </motion.div>
            </div>
            {agents.map((agent, i) => (
              <motion.div
                key={agent.name}
                className="flex items-center gap-4 bg-dim border border-zinc-800/80 p-4 transition-all duration-300 hover:border-cyan/30 hover:bg-cyan/[0.02]"
                initial={reduced ? undefined : { opacity: 0, x: i % 2 === 0 ? -20 : 20 }}
                animate={inView ? { opacity: 1, x: 0 } : {}}
                transition={{ delay: 0.4 + i * 0.1, duration: 0.5 }}
              >
                <div className="w-10 h-10 border border-cyan/30 flex items-center justify-center flex-shrink-0 text-cyan">
                  <AgentIcon shape={agent.shape} className="w-5 h-5" />
                </div>
                <span className="text-sm text-zinc-300 font-mono">{agent.name}</span>
              </motion.div>
            ))}
          </div>

          {/* Desktop: hub-spoke */}
          <div className="hidden md:flex justify-center items-center min-h-[420px]">
            <motion.div
              className="absolute z-10 w-24 h-24 bg-cyan/10 border-2 border-cyan flex items-center justify-center transition-shadow duration-300"
              initial={reduced ? undefined : { scale: 0 }}
              animate={inView ? { scale: 1 } : {}}
              transition={{ delay: 0.3, type: "spring", stiffness: 150 }}
              whileHover={reduced ? undefined : { scale: 1.1 }}
              style={{ boxShadow: hoveredAgent !== null ? "0 0 30px rgba(34,211,238,0.2)" : "none" }}
            >
              <span className="font-display font-bold text-cyan text-2xl italic">M</span>
            </motion.div>

            {agents.map((agent, i) => {
              const angle = (i * 360) / agents.length - 90;
              const rad = (angle * Math.PI) / 180;
              // Push Claude Code and Amazon Q slightly further out
              const radius = (i === 1 || i === 4) ? 179.5 : 175;
              const x = Math.round(Math.cos(rad) * radius);
              const y = Math.round(Math.sin(rad) * radius) + ((i === 1 || i === 4) ? -10 : 0);
              const isHovered = hoveredAgent === i;

              return (
                <motion.div
                  key={agent.name}
                  className="absolute flex flex-col items-center gap-2"
                  initial={reduced ? { x, y } : { opacity: 0, scale: 0, x, y }}
                  animate={inView ? { opacity: 1, scale: 1, x, y } : { x, y }}
                  transition={{ delay: 0.5 + i * 0.12, type: "spring", stiffness: 150 }}
                  whileHover={reduced ? undefined : { scale: 1.15 }}
                  onHoverStart={() => setHoveredAgent(i)}
                  onHoverEnd={() => setHoveredAgent(null)}
                >
                  <div className={`w-14 h-14 bg-dim border flex items-center justify-center transition-all duration-300 ${
                    isHovered ? "border-cyan bg-cyan/10 shadow-[0_0_25px_rgba(34,211,238,0.35)]" : "border-zinc-700 hover:border-cyan/50"
                  } text-cyan`}>
                    <AgentIcon shape={agent.shape} className="w-7 h-7" />
                  </div>
                  <span className={`font-mono text-[10px] whitespace-nowrap transition-colors ${isHovered ? "text-cyan" : "text-zinc-400"}`}>{agent.name}</span>
                </motion.div>
              );
            })}

            {/* Connection lines */}
            <svg className="absolute w-[400px] h-[400px] pointer-events-none" viewBox="-200 -200 400 400" aria-hidden="true">
              <defs>
                <linearGradient id="conn-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#22D3EE" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#F59E0B" stopOpacity="0.2" />
                </linearGradient>
              </defs>
              {agents.map((_, i) => {
                const angle = (i * 360) / agents.length - 90;
                const rad = (angle * Math.PI) / 180;
                const radius = 170;
                const x2 = Math.round(Math.cos(rad) * radius);
                const y2 = Math.round(Math.sin(rad) * radius);
                const isActive = hoveredAgent === i || hoveredAgent === null;
                const x1s = Math.round(Math.cos(rad) * 55);
                const y1s = Math.round(Math.sin(rad) * 55);
                // Agents 1 (Claude Code) and 4 (Amazon Q) are upper sides — extend lines closer
                const endRadius = (i === 1 || i === 4) ? 148 : 128;
                const x2s = Math.round(Math.cos(rad) * endRadius);
                const y2s = Math.round(Math.sin(rad) * endRadius);
                return (
                  <g key={i}>
                    <motion.line
                      x1={x1s} y1={y1s} x2={x2s} y2={y2s}
                      stroke={isActive ? "url(#conn-grad)" : "rgba(34,211,238,0.05)"}
                      strokeWidth={hoveredAgent === i ? "2" : "1"}
                      strokeDasharray={hoveredAgent === i ? "none" : "4 4"}
                      initial={reduced ? { opacity: 1 } : { pathLength: 0, opacity: 0 }}
                      animate={inView ? { pathLength: 1, opacity: 1 } : {}}
                      transition={{ delay: 0.7 + i * 0.1, duration: 0.8 }}
                    />
                    {!reduced && inView && (
                      <circle r="2.5" fill="#22D3EE" opacity="0">
                        <animateMotion dur={`${2 + i * 0.3}s`} repeatCount="indefinite" begin={`${i * 0.5}s`} path={`M0,0 L${x2},${y2}`} />
                        <animate attributeName="opacity" values="0;0.7;0.7;0" dur={`${2 + i * 0.3}s`} repeatCount="indefinite" begin={`${i * 0.5}s`} />
                      </circle>
                    )}
                  </g>
                );
              })}
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
}
