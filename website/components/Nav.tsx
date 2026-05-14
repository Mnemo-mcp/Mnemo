'use client';

import { useEffect, useState } from 'react';

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', fn, { passive: true });
    return () => window.removeEventListener('scroll', fn);
  }, []);

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-200 ${scrolled ? 'bg-surface/90 backdrop-blur-sm border-b border-border-subtle' : ''}`}>
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <a href="#" className="flex items-center gap-2.5">
          <img src="/Mnemo/icon.png" alt="Mnemo" className="w-7 h-7 rounded" />
          <span className="font-semibold text-sm text-white">Mnemo</span>
        </a>

        <div className="hidden md:flex items-center gap-8">
          <a href="#features" className="text-sm text-gray-400 hover:text-white transition-colors">Features</a>
          <a href="#install" className="text-sm text-gray-400 hover:text-white transition-colors">Install</a>
          <a href="https://github.com/Mnemo-mcp/Mnemo" className="text-sm text-gray-400 hover:text-white transition-colors">GitHub</a>
        </div>

        <a href="#install" className="px-4 py-2 rounded-lg bg-accent text-black text-sm font-medium hover:bg-accent/90 transition-colors">
          Get Started
        </a>
      </div>
    </nav>
  );
}
