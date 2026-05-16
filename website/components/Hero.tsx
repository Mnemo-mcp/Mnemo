"use client";
import { motion, useScroll, useTransform } from "framer-motion";
import { useEffect, useState, useRef } from "react";
import { useReducedMotion } from "./useReducedMotion";

export default function Hero() {
  const [mousePos, setMousePos] = useState({ x: -500, y: -500 });
  const heroRef = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: heroRef, offset: ["start start", "end start"] });
  const bgY = useTransform(scrollYProgress, [0, 1], ["0%", "30%"]);
  const textY = useTransform(scrollYProgress, [0, 1], ["0%", "15%"]);
  const graphOpacity = useTransform(scrollYProgress, [0, 0.6], [1, 0]);

  useEffect(() => {
    if (reduced) return;
    const handleMouse = (e: MouseEvent) => {
      if (heroRef.current) {
        const rect = heroRef.current.getBoundingClientRect();
        setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
      }
    };
    window.addEventListener("mousemove", handleMouse);
    return () => window.removeEventListener("mousemove", handleMouse);
  }, [reduced]);

  return (
    <section ref={heroRef} className="relative min-h-screen flex items-center overflow-hidden" aria-label="Hero">
      <motion.div className="absolute inset-0" style={reduced ? undefined : { y: bgY }} aria-hidden="true">
        <div className="absolute top-[-10%] left-[-5%] w-[800px] h-[800px] rounded-full bg-accent/[0.12] blur-[160px] animate-float" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[700px] h-[700px] rounded-full bg-cyan/[0.10] blur-[140px]" style={{ animationDelay: "2.5s" }} />
        <div className="absolute top-[40%] left-[50%] w-[400px] h-[400px] rounded-full bg-accent/[0.06] blur-[120px]" />
        <div className="absolute inset-0 opacity-[0.08]" style={{
          backgroundImage: `radial-gradient(ellipse 80% 50% at 30% 40%, rgba(245,158,11,0.4), transparent),
                           radial-gradient(ellipse 60% 60% at 70% 60%, rgba(34,211,238,0.3), transparent)`,
        }} />
        <div className="absolute inset-0 opacity-[0.03]" style={{
          backgroundImage: `linear-gradient(rgba(34,211,238,0.6) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,0.6) 1px, transparent 1px)`,
          backgroundSize: "80px 80px",
        }} />
        <div className="absolute top-0 right-[12%] w-[2px] h-full bg-gradient-to-b from-transparent via-accent/20 to-transparent rotate-[12deg] origin-top" />
        <div className="absolute top-0 left-[5%] w-[1px] h-[60%] bg-gradient-to-b from-transparent via-cyan/15 to-transparent -rotate-[6deg] origin-top" />
      </motion.div>

      {/* Cursor glow */}
      {!reduced && (
        <div
          className="absolute pointer-events-none w-[500px] h-[500px] rounded-full transition-opacity duration-300"
          style={{
            left: mousePos.x - 250,
            top: mousePos.y - 250,
            background: "radial-gradient(circle, rgba(245,158,11,0.18) 0%, rgba(34,211,238,0.08) 40%, transparent 70%)",
            opacity: mousePos.x > 0 ? 1 : 0,
          }}
          aria-hidden="true"
        />
      )}

      {/* Decorative graph on right side — large, asymmetric */}
      <motion.div
        className="absolute right-[-5%] top-[15%] w-[45vw] max-w-[600px] h-[70vh] hidden lg:block pointer-events-none"
        style={reduced ? undefined : { opacity: graphOpacity }}
        aria-hidden="true"
      >
        <svg viewBox="0 0 300 400" className="w-full h-full opacity-[0.15]">
          <defs>
            <linearGradient id="hero-node-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#F59E0B" />
              <stop offset="100%" stopColor="#22D3EE" />
            </linearGradient>
          </defs>
          {[[80,60],[220,40],[150,140],[50,200],[250,180],[120,280],[200,300],[280,260],[40,340],[180,380]].map(([cx,cy], i) => (
            <g key={i}>
              <circle cx={cx} cy={cy} r={i === 2 ? 8 : 4} fill="url(#hero-node-grad)" opacity={0.6 - i * 0.04}>
                {!reduced && <animate attributeName="r" values={`${i===2?8:4};${i===2?10:5.5};${i===2?8:4}`} dur={`${3+i*0.4}s`} repeatCount="indefinite" />}
              </circle>
            </g>
          ))}
          {[[0,2],[1,2],[2,3],[2,4],[3,5],[4,6],[5,8],[6,7],[7,9],[4,7]].map(([a,b], i) => {
            const pts = [[80,60],[220,40],[150,140],[50,200],[250,180],[120,280],[200,300],[280,260],[40,340],[180,380]];
            return (
              <line key={`l${i}`} x1={pts[a][0]} y1={pts[a][1]} x2={pts[b][0]} y2={pts[b][1]} stroke="url(#hero-node-grad)" strokeWidth="0.8" opacity="0.3">
                {!reduced && <animate attributeName="opacity" values="0.15;0.4;0.15" dur={`${2.5+i*0.3}s`} repeatCount="indefinite" />}
              </line>
            );
          })}
        </svg>
      </motion.div>

      <motion.div className="relative z-10 max-w-7xl mx-auto px-6 pt-32 pb-20 w-full" style={reduced ? undefined : { y: textY }}>
        {/* Asymmetric layout — text pushed left */}
        <div className="max-w-5xl">
          <motion.div
            className="font-mono text-xs text-cyan/80 tracking-[0.3em] uppercase mb-6 flex items-center gap-3"
            initial={reduced ? undefined : { opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            <span className="w-16 h-[1px] bg-gradient-to-r from-cyan/80 to-transparent" />
            Persistent Engineering Cognition
          </motion.div>

          <motion.h1
            className="font-display font-black tracking-tight leading-[0.82]"
            initial={reduced ? undefined : { opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          >
            <span className="block text-5xl sm:text-7xl md:text-8xl lg:text-[10rem] text-zinc-100">
              Your agent
            </span>
            <span className="block text-4xl sm:text-5xl md:text-6xl lg:text-[5rem] text-zinc-100 mt-1 lg:mt-2 lg:ml-[15%]">
              forgets{" "}
              <span className="text-forget italic line-through decoration-forget/50 decoration-[3px]">everything</span>.
            </span>
            <span className="block mt-2 lg:mt-4 lg:-ml-[3%]">
              <span className="text-5xl sm:text-7xl md:text-8xl lg:text-[12rem] bg-gradient-to-r from-accent via-accent-light to-cyan bg-clip-text text-transparent relative">
                Mnemo doesn&apos;t.
                <span className="absolute -bottom-2 left-0 w-[80%] h-[3px] bg-gradient-to-r from-accent via-cyan to-transparent" aria-hidden="true" />
              </span>
            </span>
          </motion.h1>

          <motion.p
            className="mt-10 text-lg sm:text-xl text-zinc-400 max-w-xl leading-relaxed lg:ml-[15%]"
            initial={reduced ? undefined : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.7 }}
          >
            Every session starts where the last one ended — architecture decisions, patterns, and context preserved forever.
          </motion.p>

          <motion.div
            className="mt-12 flex flex-wrap gap-4 items-center lg:ml-[15%]"
            initial={reduced ? undefined : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.7 }}
          >
            <a
              href="#install"
              className="group relative px-8 py-3.5 bg-accent text-bg font-mono font-semibold text-sm uppercase tracking-wider hover:bg-accent-light transition-all hover:shadow-[0_0_40px_rgba(245,158,11,0.4)] hover:-translate-y-0.5"
            >
              Get Started
            </a>
            <a
              href="#lifecycle"
              className="px-8 py-3.5 border border-zinc-700 text-zinc-400 font-mono text-sm uppercase tracking-wider hover:border-cyan/50 hover:text-cyan transition-all hover:shadow-[0_0_20px_rgba(34,211,238,0.1)] hover:-translate-y-0.5"
            >
              See How It Works
            </a>
          </motion.div>
        </div>
      </motion.div>

      <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-b from-transparent to-bg pointer-events-none" aria-hidden="true" />
    </section>
  );
}
