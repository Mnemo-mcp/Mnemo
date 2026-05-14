'use client';

import { useEffect, useState } from 'react';

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? 'bg-surface/95 border-b border-border-subtle' : ''}`}>
      <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
        <a href="#" className="flex items-center gap-3">
          <img src="/Mnemo/icon.png" alt="Mnemo" className="w-7 h-7 rounded-sm" />
          <span className="font-display text-base font-bold tracking-tight">Mnemo</span>
        </a>

        <div className="hidden md:flex items-center gap-10">
          <a href="#features" className="text-xs text-text-muted hover:text-text-primary transition-colors uppercase tracking-[0.2em] font-mono">Features</a>
          <a href="#install" className="text-xs text-text-muted hover:text-text-primary transition-colors uppercase tracking-[0.2em] font-mono">Install</a>
          <a href="https://github.com/Mnemo-mcp/Mnemo" className="text-xs text-text-muted hover:text-text-primary transition-colors uppercase tracking-[0.2em] font-mono">GitHub</a>
        </div>

        <a href="#install" className="hidden sm:inline-flex px-4 py-2 rounded-sm bg-accent text-surface text-xs font-semibold hover:bg-accent-bright transition-colors">
          Get Started
        </a>
      </div>
    </nav>
  );
}
