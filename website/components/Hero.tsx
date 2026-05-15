'use client';

import { useEffect, useState } from 'react';
import Terminal from './Terminal';

const STATS = [
  { value: '56', label: 'MCP Tools' },
  { value: '14', label: 'Languages' },
  { value: '140+', label: 'Tests' },
  { value: '0', label: 'External DBs' },
];

const TERMINAL_LINES = [
  '$ mnemo init',
  '[mnemo] Parsed 157 files · 14 languages · tree-sitter AST',
  '[mnemo] Graph: 880 nodes, 1455 edges',
  '[mnemo] Architecture: Clean Architecture + CQRS detected',
  '[mnemo] 56 MCP tools ready.',
  '',
  '$ mnemo recall',
  '  Decision: CosmosDB for persistence (team expertise)',
  '  Pattern: Handler-per-payer integration strategy',
  '  Plan: SOAP Migration [2/4] → next: update models',
  '  Warning: PaymentService has 3 regression risks',
];

export default function Hero() {
  const [visible, setVisible] = useState(false);
  useEffect(() => setVisible(true), []);

  return (
    <section className="min-h-[90vh] flex flex-col justify-center pt-20 pb-16 px-6">
      <div className={`max-w-6xl mx-auto transition-all duration-500 ${visible ? 'opacity-100' : 'opacity-0 translate-y-2'}`}>
        <div className="grid lg:grid-cols-[1fr_1.1fr] gap-12 items-center">
          <div>
            <p className="text-accent font-mono text-sm mb-6">Persistent engineering cognition for AI agents</p>

            <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold leading-[1.1] mb-6 text-white tracking-tight">
              Your agent forgets everything.
              <br />
              <span className="text-accent">Mnemo doesn&apos;t.</span>
            </h1>

            <p className="text-lg text-gray-400 max-w-lg leading-relaxed mb-8">
              One local process gives your AI agent a knowledge graph, persistent memory, and hybrid search engine across every session.
            </p>

            <div className="flex flex-wrap gap-3">
              <a href="#install" className="px-5 py-2.5 rounded-lg bg-accent text-black text-sm font-medium hover:bg-accent/90 transition-colors">
                Install Mnemo
              </a>
              <a href="https://github.com/Mnemo-mcp/Mnemo" className="px-5 py-2.5 rounded-lg border border-border text-sm text-gray-300 hover:border-gray-500 transition-colors">
                View on GitHub
              </a>
            </div>
          </div>

          <div>
            <Terminal lines={TERMINAL_LINES} />
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-8 pt-10 mt-12 border-t border-border-subtle">
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
