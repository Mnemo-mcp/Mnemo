'use client';

import { useEffect, useState } from 'react';

const STATS = [
  { value: '56', label: 'MCP Tools' },
  { value: '14', label: 'Languages' },
  { value: '140+', label: 'Tests' },
  { value: '0', label: 'External DBs' },
];

export default function Hero() {
  const [visible, setVisible] = useState(false);
  useEffect(() => setVisible(true), []);

  return (
    <section className="min-h-[90vh] flex flex-col justify-center pt-20 pb-16 px-6">
      <div className={`max-w-5xl mx-auto transition-all duration-500 ${visible ? 'opacity-100' : 'opacity-0 translate-y-2'}`}>
        <p className="text-accent font-mono text-sm mb-6">Persistent engineering cognition for AI agents</p>

        <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold leading-[1.1] mb-6 text-white tracking-tight">
          Your agent forgets everything.
          <br />
          <span className="text-accent">Mnemo doesn&apos;t.</span>
        </h1>

        <p className="text-lg text-gray-400 max-w-2xl leading-relaxed mb-10">
          One local process gives your AI coding agent a knowledge graph, persistent memory, and hybrid search engine that survives across every chat session. No databases. No infrastructure.
        </p>

        <div className="flex flex-wrap gap-3 mb-16">
          <a href="#install" className="px-5 py-2.5 rounded-lg bg-accent text-black text-sm font-medium hover:bg-accent/90 transition-colors">
            Install Mnemo
          </a>
          <a href="https://github.com/Mnemo-mcp/Mnemo" className="px-5 py-2.5 rounded-lg border border-border text-sm text-gray-300 hover:border-gray-500 transition-colors">
            View on GitHub
          </a>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-8 pt-8 border-t border-border-subtle">
          {STATS.map((s) => (
            <div key={s.label}>
              <div className="text-2xl font-bold text-white">{s.value}</div>
              <div className="text-xs text-gray-500 mt-1 font-mono">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
