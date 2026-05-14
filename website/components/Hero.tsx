'use client';

import Terminal from './Terminal';
import Stats from './Stats';

export default function Hero() {
  const terminalLines = [
    '$ mnemo init',
    '[mnemo] Parsed 157 files · 14 languages · tree-sitter AST',
    '[mnemo] Graph built: 880 nodes, 1455 edges',
    '[mnemo] Architecture: Clean Architecture + CQRS detected',
    '[mnemo] 56 MCP tools online. Ready.',
    '',
    '$ mnemo recall',
    '# Active Context',
    '  Decision: CosmosDB for persistence (team expertise)',
    '  Pattern: Handler-per-payer integration strategy',
    '  Plan: SOAP Migration [2/4] → next: update XML models',
    '  Warning: PaymentService has 3 regression risks',
  ];

  return (
    <section className="relative min-h-screen flex items-center justify-center pt-20 pb-16 px-6 overflow-hidden">
      <div className="absolute inset-0 grid-bg opacity-40" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent-pink/5 rounded-full blur-[128px]" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-blue/5 rounded-full blur-[128px]" />

      <div className="relative z-10 max-w-4xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 border border-accent-pink/30 text-accent-pink text-xs font-medium tracking-wider uppercase mb-8 rounded-full">
          Local-first · No external databases · 56 MCP tools
        </div>

        <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold leading-[1.05] mb-6 tracking-tight">
          <span className="text-white">Your agent forgets</span>
          <br />
          <span className="text-gradient">everything.</span>
          <br />
          <span className="text-white">Mnemo doesn&apos;t.</span>
        </h1>

        <p className="text-base md:text-lg text-gray-400 max-w-2xl mx-auto mb-4 leading-relaxed">
          Persistent engineering cognition for AI coding agents.
          A knowledge graph, memory lifecycle, and hybrid search engine
          that runs as one local process — no infrastructure required.
        </p>

        <p className="text-sm text-gray-600 max-w-xl mx-auto mb-10">
          Works with Amazon Q, Cursor, Claude Code, Kiro, Copilot, Gemini CLI, and 5 more MCP clients.
        </p>

        <div className="flex flex-wrap justify-center gap-4 mb-12">
          <a href="#install" className="px-6 py-3 text-sm font-semibold bg-accent-pink text-white rounded-lg hover:bg-accent-pink/90 transition-colors">
            Install Mnemo
          </a>
          <a href="https://github.com/Mnemo-mcp/Mnemo" className="px-6 py-3 text-sm font-semibold border border-white/20 text-white rounded-lg hover:bg-white/5 transition-colors">
            Source on GitHub
          </a>
        </div>

        <div className="max-w-2xl mx-auto mb-12">
          <Terminal lines={terminalLines} />
        </div>

        <Stats />
      </div>
    </section>
  );
}
