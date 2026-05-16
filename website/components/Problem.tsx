"use client";
import { motion, useInView, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { useReducedMotion } from "./useReducedMotion";

const fragments = [
  { text: "useAuth hook pattern", delay: 0 },
  { text: "DB schema decisions", delay: 0.3 },
  { text: "API rate limiting approach", delay: 0.6 },
  { text: "Error boundary strategy", delay: 0.9 },
  { text: "Caching layer design", delay: 1.2 },
];

export default function Problem() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-100px" });
  const reduced = useReducedMotion();
  const containerRef = useRef(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ["start end", "end start"] });
  const parallaxY = useTransform(scrollYProgress, [0, 1], [40, -40]);

  return (
    <section id="problem" className="relative py-32 lg:py-40 overflow-hidden" aria-labelledby="problem-heading" ref={ref}>
      {/* Aggressive red treatment — full-bleed left edge + background bleed */}
      <div className="absolute left-0 top-0 w-[4px] h-full bg-gradient-to-b from-transparent via-forget/80 to-transparent" aria-hidden="true" />
      <div className="absolute left-0 top-[10%] w-[600px] h-[600px] bg-forget/[0.08] blur-[200px] -rotate-12" aria-hidden="true" />
      <div className="absolute right-[10%] bottom-[10%] w-[300px] h-[300px] bg-forget/[0.04] blur-[120px]" aria-hidden="true" />
      {/* Diagonal slash */}
      <div className="absolute top-0 left-[20%] w-[1px] h-full bg-gradient-to-b from-transparent via-forget/20 to-transparent rotate-[8deg] origin-top" aria-hidden="true" />

      <div className="max-w-7xl mx-auto px-6" ref={containerRef}>
        {/* Overlapping layout — text overlaps the terminal slightly */}
        <div className="grid lg:grid-cols-[1.2fr_1fr] gap-8 lg:gap-0 items-center">
          <motion.div
            className="relative z-10 lg:pr-0"
            initial={reduced ? undefined : { opacity: 0, y: 30 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.2, duration: 0.7 }}
          >
            <h2 id="problem-heading" className="font-display font-black tracking-tight leading-[0.85]">
              <span className="block text-3xl sm:text-4xl text-zinc-500 italic">Every session</span>
              <span className="block text-5xl sm:text-6xl lg:text-[7rem] text-zinc-100 -mt-1">starts from</span>
              <span className="block text-6xl sm:text-7xl lg:text-[10rem] text-forget italic -mt-2 lg:-mt-4 lg:-ml-2">zero</span>
            </h2>
            <p className="mt-6 text-lg text-zinc-400 leading-relaxed max-w-md">
              You explain your architecture. Again. Your patterns. Again. Every new AI session is a blank slate — weeks of context, gone.
            </p>
            <div className="mt-6 font-mono text-sm text-forget/90 flex items-center gap-3">
              <span className="text-forget">▸</span>
              Context lost every single session
            </div>
          </motion.div>

          {/* Terminal visual with parallax — overlaps into text column */}
          <motion.div
            className="relative lg:-ml-20"
            initial={reduced ? undefined : { opacity: 0, x: 30 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
            style={reduced ? undefined : { y: parallaxY }}
          >
            <div className="relative bg-dim border border-forget/20 overflow-hidden shadow-[0_0_60px_rgba(239,68,68,0.08)]">
              <div className="flex items-center gap-2 px-4 py-2 border-b border-forget/10 bg-bg">
                <div className="w-2.5 h-2.5 rounded-full bg-forget/60" />
                <div className="w-2.5 h-2.5 rounded-full bg-accent/40" />
                <div className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
                <span className="ml-2 font-mono text-[10px] text-zinc-600">session_history</span>
              </div>
              <div className="p-5 space-y-2">
                {fragments.map((item, i) => (
                  <motion.div
                    key={i}
                    className="relative border border-zinc-800/50 p-3 font-mono text-xs overflow-hidden"
                    initial={reduced ? { opacity: 0.2 } : { opacity: 1 }}
                    animate={inView ? {
                      opacity: [1, 1, 0.5, 0],
                      x: [0, 0, -2, 30],
                      filter: ["blur(0px)", "blur(0px)", "blur(2px)", "blur(10px)"],
                    } : {}}
                    transition={{
                      delay: 0.6 + item.delay,
                      duration: 1.6,
                      times: [0, 0.4, 0.7, 1],
                      ease: "easeInOut",
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-forget">✕</span>
                      <span className="text-zinc-400">{item.text}</span>
                      <span className="text-forget/70 ml-auto text-[10px] uppercase tracking-wider">lost</span>
                    </div>
                    <motion.div
                      className="absolute top-1/2 left-0 h-[2px] bg-forget/80"
                      initial={{ width: "0%" }}
                      animate={inView ? { width: "100%" } : {}}
                      transition={{ delay: 1.0 + item.delay, duration: 0.5, ease: "easeIn" }}
                    />
                  </motion.div>
                ))}
                <motion.div
                  className="border border-forget/30 border-dashed p-4 font-mono text-xs text-center"
                  initial={reduced ? { opacity: 1 } : { opacity: 0, scale: 0.95 }}
                  animate={inView ? { opacity: 1, scale: 1 } : {}}
                  transition={{ delay: 2.8, duration: 0.4 }}
                >
                  <span className="text-forget">context: null</span>
                  <span className="text-zinc-600 ml-2">// new session starts here</span>
                </motion.div>
              </div>
              {/* Scan line */}
              <motion.div
                className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-forget to-transparent pointer-events-none"
                initial={{ top: "0%" }}
                animate={inView ? { top: ["0%", "100%"] } : {}}
                transition={{ delay: 0.8, duration: 2, ease: "linear" }}
              />
            </div>
            <div className="absolute -inset-4 -z-10 bg-forget/[0.04] blur-lg" aria-hidden="true" />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
