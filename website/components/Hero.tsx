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
    <section className="min-h-screen flex flex-col justify-center pt-24 pb-20 px-6">
      <div className="max-w-5xl mx-auto">
        <div className={`transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
          <div className="accent-line mb-8" />

          <h1 className="heading text-4xl sm:text-5xl md:text-6xl lg:text-7xl leading-[1.1] mb-8">
            Your agent forgets everything.
            <br />
            <span className="text-accent">Mnemo doesn&apos;t.</span>
          </h1>

          <p className="font-body text-lg md:text-xl text-text-secondary max-w-2xl leading-relaxed mb-6">
            Persistent engineering cognition for AI coding agents. One local process gives your agent a knowledge graph, memory lifecycle, and hybrid search engine across every session.
          </p>

          <p className="text-sm text-text-muted max-w-xl mb-12">
            Works with Amazon Q, Cursor, Claude Code, Kiro, Copilot, Gemini CLI, and 5 more MCP clients. No external databases. No API keys. Everything in .mnemo/.
          </p>

          <div className="flex flex-wrap gap-4 mb-16">
            <a href="#install" className="px-6 py-3 text-sm font-semibold bg-accent text-surface rounded-sm hover:bg-accent-bright transition-colors">
              Install Mnemo
            </a>
            <a href="https://github.com/Mnemo-mcp/Mnemo" className="px-6 py-3 text-sm font-semibold border border-border text-text-primary rounded-sm hover:border-accent/50 transition-colors">
              View Source
            </a>
          </div>
        </div>

        <div className={`grid grid-cols-2 sm:grid-cols-4 gap-8 pt-12 border-t border-border-subtle transition-all duration-700 delay-200 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
          {STATS.map((s) => (
            <div key={s.label}>
              <div className="font-display text-3xl md:text-4xl font-bold text-accent">{s.value}</div>
              <div className="text-xs text-text-muted mt-1 uppercase tracking-[0.15em] font-mono">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
