"use client";
import { motion, useInView, AnimatePresence } from "framer-motion";
import { useRef, useState } from "react";
import { useReducedMotion } from "./useReducedMotion";

const accordionItems = [
  {
    id: "accordion-btn-0",
    title: "MCP Protocol",
    content: "Mnemo uses the Model Context Protocol (MCP) to communicate with AI coding agents. This standardized protocol ensures compatibility across all major agents without custom integrations.",
  },
  {
    id: "accordion-btn-1",
    title: "Local-First Storage",
    content: "All knowledge is stored locally on your machine. No cloud dependency, no data leaving your environment. Your engineering context stays private and under your control.",
  },
  {
    id: "accordion-btn-2",
    title: "Graph Structure",
    content: "Knowledge is stored as a directed graph with semantic edges. Nodes represent concepts (architecture decisions, patterns, errors) and edges represent relationships (depends-on, supersedes, relates-to).",
  },
];

export default function Architecture() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-100px" });
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const [hoveredBox, setHoveredBox] = useState<string | null>(null);
  const reduced = useReducedMotion();

  return (
    <section id="architecture" className="relative py-32" aria-labelledby="arch-heading" ref={ref}>
      <div className="absolute left-0 top-0 w-full h-[1px] bg-gradient-to-r from-transparent via-zinc-800 to-transparent" aria-hidden="true" />

      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          className="mb-16"
          initial={reduced ? undefined : { opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
        >
          <h2 id="arch-heading" className="font-display font-black tracking-tight leading-[0.85]">
            <span className="block text-2xl sm:text-3xl text-zinc-500 italic">What&apos;s</span>
            <span className="block text-4xl sm:text-5xl lg:text-[5rem] text-zinc-100 italic">under the hood</span>
          </h2>
          <p className="mt-4 text-zinc-400 text-lg max-w-2xl">
            A lightweight layer between your agent and your codebase.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-2 gap-12 items-start">
          {/* Architecture diagram with animated flow */}
          <motion.div
            className="relative"
            initial={reduced ? undefined : { opacity: 0, x: -30 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.2, duration: 0.7 }}
          >
            <div className="bg-dim border border-zinc-800/80 overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2 border-b border-zinc-800/50 bg-bg">
                <div className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
                <div className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
                <div className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
                <span className="ml-2 font-mono text-[10px] text-zinc-600">architecture.svg</span>
              </div>
              <div className="p-4">
                <svg viewBox="0 0 400 220" className="w-full h-auto" aria-label="Architecture diagram showing AI Agent connecting to Mnemo which connects to your Codebase">
                  <g
                    role="button"
                    aria-label="AI Agent node — sends queries via MCP protocol, receives enriched context"
                    tabIndex={0}
                    onMouseEnter={() => setHoveredBox("agent")}
                    onMouseLeave={() => setHoveredBox(null)}
                    onFocus={() => setHoveredBox("agent")}
                    onBlur={() => setHoveredBox(null)}
                    className="cursor-pointer"
                  >
                    <motion.rect
                      x="20" y="80" width="100" height="60"
                      fill={hoveredBox === "agent" ? "rgba(34,211,238,0.08)" : "none"}
                      stroke={hoveredBox === "agent" ? "#22D3EE" : "rgba(255,255,255,0.1)"}
                      strokeWidth={hoveredBox === "agent" ? "2" : "1"}
                      initial={reduced ? undefined : { opacity: 0 }}
                      animate={inView ? { opacity: 1 } : {}}
                      transition={{ delay: 0.3, duration: 0.5 }}
                    />
                    <text x="70" y="105" textAnchor="middle" className="text-[11px] fill-zinc-400 pointer-events-none" style={{ fontFamily: "monospace" }}>AI Agent</text>
                    <text x="70" y="125" textAnchor="middle" className="text-[8px] fill-zinc-500 pointer-events-none" style={{ fontFamily: "monospace" }}>(Kiro, Cursor...)</text>
                  </g>

                  <g
                    role="button"
                    aria-label="Mnemo node — stores knowledge graph, handles semantic search and decay"
                    tabIndex={0}
                    onMouseEnter={() => setHoveredBox("mnemo")}
                    onMouseLeave={() => setHoveredBox(null)}
                    onFocus={() => setHoveredBox("mnemo")}
                    onBlur={() => setHoveredBox(null)}
                    className="cursor-pointer"
                  >
                    <motion.rect
                      x="155" y="60" width="100" height="100"
                      fill={hoveredBox === "mnemo" ? "rgba(245,158,11,0.1)" : "rgba(245,158,11,0.03)"}
                      stroke="#F59E0B"
                      strokeWidth={hoveredBox === "mnemo" ? "2.5" : "1.5"}
                      initial={reduced ? undefined : { opacity: 0, scale: 0.9 }}
                      animate={inView ? { opacity: 1, scale: 1 } : {}}
                      transition={{ delay: 0.5, duration: 0.5 }}
                      style={{ transformOrigin: "205px 110px" }}
                    />
                    <text x="205" y="95" textAnchor="middle" className="text-[12px] font-bold pointer-events-none" fill="#F59E0B" style={{ fontFamily: "monospace" }}>Mnemo</text>
                    <text x="205" y="115" textAnchor="middle" className="text-[8px] fill-zinc-400 pointer-events-none" style={{ fontFamily: "monospace" }}>Knowledge Graph</text>
                    <text x="205" y="130" textAnchor="middle" className="text-[8px] fill-zinc-400 pointer-events-none" style={{ fontFamily: "monospace" }}>Semantic Memory</text>
                    <text x="205" y="145" textAnchor="middle" className="text-[8px] fill-zinc-400 pointer-events-none" style={{ fontFamily: "monospace" }}>MCP Server</text>
                  </g>

                  <g
                    role="button"
                    aria-label="Codebase node — indexed for architecture patterns, decisions and history"
                    tabIndex={0}
                    onMouseEnter={() => setHoveredBox("codebase")}
                    onMouseLeave={() => setHoveredBox(null)}
                    onFocus={() => setHoveredBox("codebase")}
                    onBlur={() => setHoveredBox(null)}
                    className="cursor-pointer"
                  >
                    <motion.rect
                      x="290" y="80" width="100" height="60"
                      fill={hoveredBox === "codebase" ? "rgba(34,211,238,0.08)" : "none"}
                      stroke={hoveredBox === "codebase" ? "#22D3EE" : "rgba(255,255,255,0.1)"}
                      strokeWidth={hoveredBox === "codebase" ? "2" : "1"}
                      initial={reduced ? undefined : { opacity: 0 }}
                      animate={inView ? { opacity: 1 } : {}}
                      transition={{ delay: 0.3, duration: 0.5 }}
                    />
                    <text x="340" y="105" textAnchor="middle" className="text-[11px] fill-zinc-400 pointer-events-none" style={{ fontFamily: "monospace" }}>Codebase</text>
                    <text x="340" y="125" textAnchor="middle" className="text-[8px] fill-zinc-500 pointer-events-none" style={{ fontFamily: "monospace" }}>Your Project</text>
                  </g>

                  {/* Arrows with hover-highlighted flow */}
                  <motion.path
                    d="M120 105 L155 105"
                    stroke={hoveredBox === "agent" || hoveredBox === "mnemo" ? "#22D3EE" : "#F59E0B"}
                    strokeWidth={hoveredBox === "agent" || hoveredBox === "mnemo" ? "2.5" : "1.5"}
                    fill="none" markerEnd="url(#arrowhead)"
                    initial={reduced ? undefined : { pathLength: 0 }}
                    animate={inView ? { pathLength: 1 } : {}}
                    transition={{ delay: 0.7, duration: 0.6 }}
                  />
                  <motion.path
                    d="M155 115 L120 115"
                    stroke={hoveredBox === "agent" || hoveredBox === "mnemo" ? "rgba(34,211,238,0.7)" : "rgba(245,158,11,0.4)"}
                    strokeWidth="1" fill="none" markerEnd="url(#arrowhead2)"
                    initial={reduced ? undefined : { pathLength: 0 }}
                    animate={inView ? { pathLength: 1 } : {}}
                    transition={{ delay: 0.9, duration: 0.6 }}
                  />
                  <motion.path
                    d="M255 105 L290 105"
                    stroke={hoveredBox === "codebase" || hoveredBox === "mnemo" ? "#22D3EE" : "#F59E0B"}
                    strokeWidth={hoveredBox === "codebase" || hoveredBox === "mnemo" ? "2.5" : "1.5"}
                    fill="none" markerEnd="url(#arrowhead)"
                    initial={reduced ? undefined : { pathLength: 0 }}
                    animate={inView ? { pathLength: 1 } : {}}
                    transition={{ delay: 1.1, duration: 0.6 }}
                  />
                  <motion.path
                    d="M290 115 L255 115"
                    stroke={hoveredBox === "codebase" || hoveredBox === "mnemo" ? "rgba(34,211,238,0.7)" : "rgba(245,158,11,0.4)"}
                    strokeWidth="1" fill="none" markerEnd="url(#arrowhead2)"
                    initial={reduced ? undefined : { pathLength: 0 }}
                    animate={inView ? { pathLength: 1 } : {}}
                    transition={{ delay: 1.3, duration: 0.6 }}
                  />

                  {/* Labels */}
                  <text x="137" y="98" textAnchor="middle" className="text-[7px] fill-zinc-500" style={{ fontFamily: "monospace" }}>query</text>
                  <text x="137" y="130" textAnchor="middle" className="text-[7px] fill-zinc-500" style={{ fontFamily: "monospace" }}>context</text>
                  <text x="272" y="98" textAnchor="middle" className="text-[7px] fill-zinc-500" style={{ fontFamily: "monospace" }}>index</text>
                  <text x="272" y="130" textAnchor="middle" className="text-[7px] fill-zinc-500" style={{ fontFamily: "monospace" }}>read</text>

                  {/* Animated data flow dots — enhanced on hover */}
                  {!reduced && (
                    <>
                      <circle r="3" fill="#22D3EE" cx="120" cy="105" opacity={hoveredBox === "agent" || hoveredBox === "mnemo" ? "0.9" : "0.5"} className="arch-dot-right" />
                      <circle r="3" fill="#22D3EE" cx="255" cy="105" opacity={hoveredBox === "codebase" || hoveredBox === "mnemo" ? "0.9" : "0.5"} className="arch-dot-right-delayed" />
                      <circle r="2.5" fill="#F59E0B" cx="155" cy="115" opacity={hoveredBox === "agent" || hoveredBox === "mnemo" ? "0.9" : "0.4"} className="arch-dot-left" />
                      <circle r="2.5" fill="#F59E0B" cx="290" cy="115" opacity={hoveredBox === "codebase" || hoveredBox === "mnemo" ? "0.9" : "0.4"} className="arch-dot-left-delayed" />
                    </>
                  )}

                  <defs>
                    <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                      <polygon points="0 0, 8 3, 0 6" fill="#F59E0B" />
                    </marker>
                    <marker id="arrowhead2" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                      <polygon points="0 0, 8 3, 0 6" fill="rgba(245,158,11,0.4)" />
                    </marker>
                  </defs>
                </svg>
              </div>
              {hoveredBox && (
                <div className="px-4 pb-3" aria-live="polite">
                  <p className="font-mono text-[10px] text-cyan/80">
                    {hoveredBox === "agent" && "→ Sends queries via MCP protocol, receives enriched context"}
                    {hoveredBox === "mnemo" && "→ Stores knowledge graph, handles semantic search & decay"}
                    {hoveredBox === "codebase" && "→ Indexed for architecture patterns, decisions & history"}
                  </p>
                </div>
              )}
            </div>
          </motion.div>

          {/* Accordion */}
          <motion.div
            className="space-y-2"
            initial={reduced ? undefined : { opacity: 0, x: 30 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.4, duration: 0.7 }}
          >
            {accordionItems.map((item, i) => (
              <div key={i} className="border border-zinc-800/80 overflow-hidden transition-colors hover:border-zinc-700">
                <button
                  id={item.id}
                  className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-accent/[0.02] transition-colors"
                  onClick={() => setOpenIndex(openIndex === i ? null : i)}
                  aria-expanded={openIndex === i}
                  aria-controls={`accordion-panel-${i}`}
                >
                  <span className="font-display font-semibold text-white text-sm">{item.title}</span>
                  <motion.span
                    className="text-accent font-mono text-sm"
                    animate={{ rotate: openIndex === i ? 45 : 0 }}
                    transition={{ duration: 0.2 }}
                    aria-hidden="true"
                  >
                    +
                  </motion.span>
                </button>
                <AnimatePresence initial={false}>
                  {openIndex === i && (
                    <motion.div
                      id={`accordion-panel-${i}`}
                      role="region"
                      aria-labelledby={item.id}
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: reduced ? 0 : 0.3, ease: [0.22, 1, 0.36, 1] }}
                      className="overflow-hidden"
                    >
                      <p className="px-6 pb-4 text-sm text-zinc-400 leading-relaxed">{item.content}</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}
