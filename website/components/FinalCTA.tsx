"use client";
import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import { useReducedMotion } from "./useReducedMotion";

export default function FinalCTA() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-100px" });
  const reduced = useReducedMotion();

  return (
    <section className="relative py-32 overflow-hidden" aria-labelledby="cta-heading" ref={ref}>
      {/* BOLD full gradient background — breaks from dark theme dramatically */}
      <div className="absolute inset-0" aria-hidden="true">
        <div className="absolute inset-0 bg-gradient-to-br from-accent/[0.15] via-cyan/[0.08] to-accent/[0.12]" />
        <div className="absolute inset-0 bg-gradient-to-t from-bg/80 via-transparent to-bg/60" />
        <div className="absolute inset-0 opacity-[0.04]" style={{
          backgroundImage: `linear-gradient(45deg, rgba(245,158,11,0.5) 1px, transparent 1px), linear-gradient(-45deg, rgba(34,211,238,0.5) 1px, transparent 1px)`,
          backgroundSize: "40px 40px",
        }} />
        <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-accent via-cyan to-accent" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[900px] bg-accent/[0.1] rounded-full blur-[250px]" />
        <div className="absolute bottom-0 right-[10%] w-[500px] h-[500px] bg-cyan/[0.06] rounded-full blur-[180px]" />
      </div>

      <div className="relative max-w-4xl mx-auto px-6 text-center">
        <motion.h2
          id="cta-heading"
          className="font-display font-black text-4xl sm:text-5xl lg:text-[5.5rem] tracking-tight italic leading-[0.9]"
          initial={reduced ? undefined : { opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
        >
          <span className="bg-gradient-to-r from-zinc-100 via-accent-light to-zinc-100 bg-clip-text text-transparent">
            Stop re-explaining your codebase
          </span>
        </motion.h2>

        <motion.p
          className="mt-6 text-lg text-zinc-300 max-w-xl mx-auto"
          initial={reduced ? undefined : { opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.2, duration: 0.6 }}
        >
          Give your AI agent the memory it deserves. Install Mnemo and never repeat yourself again.
        </motion.p>

        <motion.div
          className="mt-10 inline-block bg-bg/80 backdrop-blur-sm border border-accent/40 px-8 py-4 shadow-[0_0_40px_rgba(245,158,11,0.1)]"
          initial={reduced ? undefined : { opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.3, duration: 0.6 }}
        >
          <code className="font-mono text-lg text-accent-light">
            <span className="text-zinc-500">$ </span>pip install mnemo-dev
          </code>
        </motion.div>

        <motion.div
          className="mt-8"
          initial={reduced ? undefined : { opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.4, duration: 0.6 }}
        >
          <a
            href="#install"
            className="inline-block px-10 py-4 bg-accent text-bg font-mono font-semibold text-sm uppercase tracking-wider hover:bg-accent-light transition-all hover:shadow-[0_0_50px_rgba(245,158,11,0.5)] hover:-translate-y-1"
          >
            Get Started
          </a>
        </motion.div>
      </div>
    </section>
  );
}
