"use client";
import { motion, useInView, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { useReducedMotion } from "./useReducedMotion";

const steps = [
  { cmd: "mnemo init", title: "Initialize", desc: "Seed the knowledge graph with your project's architecture and patterns.", icon: "⬡" },
  { cmd: "recall", title: "Recall", desc: "Agent pulls relevant context automatically at session start.", icon: "◎" },
  { cmd: "during session", title: "Learn", desc: "Passive learning — new decisions and patterns are captured as you work.", icon: "◈" },
  { cmd: "between sessions", title: "Evolve", desc: "Stale info decays naturally. Frequently used knowledge is reinforced.", icon: "◉" },
];

export default function Lifecycle() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-100px" });
  const reduced = useReducedMotion();
  const containerRef = useRef(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ["start end", "end start"] });
  const progressWidth = useTransform(scrollYProgress, [0.2, 0.7], ["0%", "100%"]);

  return (
    <section id="lifecycle" className="relative py-32" aria-labelledby="lifecycle-heading" ref={ref}>
      <div className="absolute left-0 top-0 w-full h-[1px] bg-gradient-to-r from-transparent via-accent/15 to-transparent" aria-hidden="true" />

      <div className="max-w-7xl mx-auto px-6" ref={containerRef}>
        <motion.div
          className="mb-20"
          initial={reduced ? undefined : { opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
        >
          <h2 id="lifecycle-heading" className="font-display font-black tracking-tight leading-[0.85]">
            <span className="block text-2xl sm:text-3xl text-zinc-500 italic">Four stages of</span>
            <span className="block text-4xl sm:text-5xl lg:text-[5rem] text-zinc-100 italic">persistent cognition</span>
          </h2>
          <p className="mt-4 text-zinc-400 text-lg max-w-2xl">
            From initialization to evolution — a continuous cycle of learning and recall.
          </p>
        </motion.div>

        {/* Timeline */}
        <div className="relative">
          {/* Horizontal connector (desktop) */}
          <div className="hidden md:block absolute top-8 left-0 right-0 h-[1px] bg-zinc-800" aria-hidden="true" />
          <motion.div
            className="hidden md:block absolute top-[31px] left-0 h-[2px] bg-gradient-to-r from-accent via-cyan to-accent origin-left"
            style={reduced ? undefined : { width: progressWidth }}
            aria-hidden="true"
          />
          {/* Vertical connector (mobile) */}
          <div className="md:hidden absolute top-0 bottom-0 left-[15px] w-[1px] bg-zinc-800" aria-hidden="true" />

          <div className="grid md:grid-cols-4 gap-10 md:gap-5">
            {steps.map((step, i) => (
              <motion.div
                key={i}
                className="relative pl-12 md:pl-0 group"
                initial={reduced ? undefined : { opacity: 0, y: 40 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ delay: 0.3 + i * 0.2, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              >
                <motion.div
                  className="absolute left-0 md:left-1/2 md:-translate-x-1/2 top-0 w-8 h-8 bg-bg border-2 border-accent flex items-center justify-center transition-all duration-300 group-hover:border-cyan group-hover:shadow-[0_0_15px_rgba(34,211,238,0.3)]"
                  whileHover={reduced ? undefined : { scale: 1.2 }}
                  transition={{ type: "spring", stiffness: 300 }}
                >
                  <span className="text-accent text-xs group-hover:text-cyan transition-colors" aria-hidden="true">{step.icon}</span>
                </motion.div>

                <div className="md:pt-16 md:text-center">
                  <span className="inline-block font-mono text-xs text-cyan bg-cyan/5 border border-cyan/20 px-2 py-1 mb-3">
                    {step.cmd}
                  </span>
                  <h3 className="font-display font-semibold text-lg text-white mb-2">{step.title}</h3>
                  <p className="text-sm text-zinc-400 leading-relaxed">{step.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
