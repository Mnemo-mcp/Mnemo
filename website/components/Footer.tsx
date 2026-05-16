"use client";

export default function Footer() {
  return (
    <footer className="border-t border-zinc-800/80 py-12" aria-label="Site footer">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-6">
            <span className="font-display font-bold text-xl text-accent italic">mnemo</span>
            <span className="font-mono text-[10px] text-zinc-400 border border-zinc-700 px-2 py-0.5">AGPL-3.0</span>
          </div>

          <nav className="flex items-center gap-6" aria-label="Footer navigation">
            <a href="https://github.com/Mnemo-mcp/Mnemo" target="_blank" rel="noopener noreferrer" className="font-mono text-xs text-zinc-400 hover:text-accent transition-colors">
              GitHub
            </a>
            <a href="https://github.com/Mnemo-mcp/Mnemo#readme" target="_blank" rel="noopener noreferrer" className="font-mono text-xs text-zinc-400 hover:text-accent transition-colors">
              Documentation
            </a>
            <a href="https://github.com/Mnemo-mcp/Mnemo/issues" target="_blank" rel="noopener noreferrer" className="font-mono text-xs text-zinc-400 hover:text-accent transition-colors">
              Community
            </a>
          </nav>
        </div>

        <div className="mt-8 pt-6 border-t border-zinc-800/50 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="font-mono text-[10px] text-zinc-500">
            © {new Date().getFullYear()} Mnemo. Persistent engineering cognition for AI coding agents.
          </p>
          <p className="font-mono text-[10px] text-zinc-500">
            Built for developers who are tired of repeating themselves.
          </p>
        </div>
      </div>
    </footer>
  );
}
