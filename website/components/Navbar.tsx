"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useReducedMotion } from "./useReducedMotion";

const links = [
  { label: "Problem", href: "#problem" },
  { label: "Solution", href: "#solution" },
  { label: "Lifecycle", href: "#lifecycle" },
  { label: "Agents", href: "#agents" },
  { label: "Install", href: "#install" },
  { label: "Features", href: "#features" },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const reduced = useReducedMotion();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-[100] transition-all duration-300 ${
        scrolled ? "bg-bg/95 backdrop-blur-md border-b border-accent/10" : ""
      }`}
      aria-label="Main navigation"
    >
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <a href="#" className="font-display font-bold text-xl text-accent tracking-tight italic" aria-label="Mnemo home">
          mnemo
        </a>

        <div className="hidden md:flex items-center gap-8">
          {links.map((l) => (
            <a key={l.href} href={l.href} className="font-mono text-xs uppercase tracking-wider text-zinc-400 hover:text-accent transition-colors">
              {l.label}
            </a>
          ))}
          <a href="#install" className="px-5 py-2 bg-accent text-bg font-mono font-semibold text-xs uppercase tracking-wider hover:bg-accent-light transition-colors">
            Get Started
          </a>
        </div>

        <button
          className="md:hidden flex flex-col gap-1.5 p-2"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
        >
          <span className={`block w-6 h-0.5 bg-accent transition-transform ${menuOpen ? "rotate-45 translate-y-2" : ""}`} />
          <span className={`block w-6 h-0.5 bg-accent transition-opacity ${menuOpen ? "opacity-0" : ""}`} />
          <span className={`block w-6 h-0.5 bg-accent transition-transform ${menuOpen ? "-rotate-45 -translate-y-2" : ""}`} />
        </button>
      </div>

      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={reduced ? { opacity: 1 } : { opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, height: 0 }}
            className="md:hidden bg-bg/98 backdrop-blur-md border-b border-accent/10 overflow-hidden"
          >
            <div className="px-6 py-4 flex flex-col gap-4">
              {links.map((l) => (
                <a key={l.href} href={l.href} className="font-mono text-sm text-zinc-300 hover:text-accent transition-colors" onClick={() => setMenuOpen(false)}>
                  {l.label}
                </a>
              ))}
              <a href="#install" className="px-5 py-2 bg-accent text-bg font-mono font-semibold text-xs uppercase tracking-wider text-center" onClick={() => setMenuOpen(false)}>
                Get Started
              </a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
