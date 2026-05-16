"use client";
import { motion, useInView } from "framer-motion";
import { useRef, useState, useEffect, useCallback } from "react";
import { useReducedMotion } from "./useReducedMotion";

const features = [
  { title: "Semantic Search", desc: "Find relevant context by meaning, not just keywords. Natural language queries across your entire knowledge base.", icon: "⌕", span: false },
  { title: "Knowledge Graph", desc: "Interconnected nodes of engineering context — architecture, patterns, decisions — all linked semantically.", icon: "◈", span: false },
  { title: "Natural Decay", desc: "Stale information fades naturally. Frequently accessed knowledge is reinforced and stays fresh.", icon: "◔", span: false },
  { title: "Multi-Agent", desc: "Works with Kiro, Claude Code, Cursor, Copilot, and Amazon Q. One memory shared across all agents.", icon: "⬡", span: false },
  { title: "Cross-Session", desc: "Context persists indefinitely across sessions. Pick up exactly where you left off, every time.", icon: "⇌", span: false },
  { title: "Zero Config", desc: "One command to install, one command to init. No configuration files, no setup wizards, no friction.", icon: "⚡", span: false },
];

function AnimatedCounter({ target, suffix = "", prefix = "", display }: { target: number; suffix?: string; prefix?: string; display?: string }) {
  const [count, setCount] = useState<number | null>(null);
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const animatedRef = useRef(false);
  const reduced = useReducedMotion();

  const animate = useCallback(() => {
    if (animatedRef.current) return;
    animatedRef.current = true;
    if (reduced || display) {
      setCount(target);
      return;
    }
    const duration = 1200;
    const startTime = Date.now();
    let rafId: number;
    const tick = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 4);
      setCount(Math.round(eased * target));
      if (progress < 1) {
        rafId = requestAnimationFrame(tick);
      }
    };
    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, [target, reduced, display]);

  useEffect(() => {
    if (!inView) return;
    const cleanup = animate();
    return cleanup;
  }, [inView, animate]);

  if (display) return <span ref={ref}>{inView ? display : <span className="text-zinc-700">···</span>}</span>;
  return <span ref={ref}>{count !== null ? `${prefix}${count}${suffix}` : <span className="text-zinc-700">···</span>}</span>;
}

const stats = [
  { value: 10, suffix: "x", prefix: "", label: "fewer repeated explanations" },
  { value: 0, suffix: "", prefix: "", label: "context lost between sessions", display: "Zero" },
  { value: 5, suffix: "+", prefix: "", label: "agents supported" },
];

export default function Features() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-100px" });
  const reduced = useReducedMotion();

  return (
    <section id="features" className="relative py-32" aria-labelledby="features-heading" ref={ref}>
      <div className="absolute left-0 top-0 w-full h-[1px] bg-gradient-to-r from-transparent via-zinc-800 to-transparent" aria-hidden="true" />

      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          className="mb-16"
          initial={reduced ? undefined : { opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
        >
          <h2 id="features-heading" className="font-display font-black tracking-tight leading-[0.85]">
            <span className="block text-2xl sm:text-3xl text-zinc-500 italic">Built for the way</span>
            <span className="block text-4xl sm:text-5xl lg:text-[5.5rem] text-zinc-100 italic">you work</span>
          </h2>
          <p className="mt-4 text-zinc-400 text-lg max-w-2xl">
            Every feature designed to make AI coding sessions feel continuous, not fragmented.
          </p>
        </motion.div>

        {/* Feature grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          {features.map((feature, i) => (
            <motion.div
              key={i}
              className={`group relative border border-zinc-800/80 p-6 bg-dim/50 transition-all duration-300 hover:border-cyan/30 hover:bg-dim/80 hover:-translate-y-1 hover:shadow-lg hover:shadow-cyan/5 ${
                feature.span ? "lg:col-span-2" : ""
              }`}
              initial={reduced ? undefined : { opacity: 0, y: 30 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.1 + i * 0.08, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            >
              <div className="font-mono text-xl text-cyan mb-4 transition-transform duration-300 origin-left group-hover:scale-125 group-hover:text-accent" aria-hidden="true">
                {feature.icon}
              </div>
              <h3 className="font-display font-semibold text-lg text-white mb-2">{feature.title}</h3>
              <p className="text-sm text-zinc-400 leading-relaxed">{feature.desc}</p>
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" aria-hidden="true">
                <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan/40 to-transparent" />
                <div className="absolute bottom-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-accent/20 to-transparent" />
              </div>
            </motion.div>
          ))}
        </div>

        {/* Stats bar — MASSIVE numbers with gradient text */}
        <motion.div
          className="mt-24 relative py-16 -mx-6 px-6 overflow-hidden"
          initial={reduced ? undefined : { opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.5, duration: 0.6 }}
        >
          {/* Background treatment for stats */}
          <div className="absolute inset-0 bg-gradient-to-r from-accent/[0.03] via-cyan/[0.05] to-accent/[0.03]" aria-hidden="true" />
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-accent/30 to-transparent" aria-hidden="true" />
          <div className="absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan/30 to-transparent" aria-hidden="true" />
          {/* Subtle pattern */}
          <div className="absolute inset-0 opacity-[0.02]" style={{
            backgroundImage: `radial-gradient(circle, rgba(34,211,238,0.8) 1px, transparent 1px)`,
            backgroundSize: "24px 24px",
          }} aria-hidden="true" />

          <div className="relative grid sm:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {stats.map((stat, i) => (
              <motion.div
                key={i}
                className="text-center"
                initial={reduced ? undefined : { opacity: 0, scale: 0.8 }}
                animate={inView ? { opacity: 1, scale: 1 } : {}}
                transition={{ delay: 0.6 + i * 0.15, duration: 0.5, type: "spring" }}
              >
                <div className="font-display font-black text-7xl sm:text-8xl lg:text-[8rem] leading-none bg-gradient-to-b from-accent via-accent-light to-cyan bg-clip-text text-transparent">
                  <AnimatedCounter target={stat.value} suffix={stat.suffix} prefix={stat.prefix} display={stat.display} />
                </div>
                <p className="mt-4 text-zinc-400 text-sm font-mono">{stat.label}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
