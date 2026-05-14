export default function Footer() {
  return (
    <footer className="border-t border-border-subtle py-12 px-6">
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <img src="/Mnemo/icon.png" alt="Mnemo" className="w-5 h-5 rounded-sm" />
          <span className="font-display text-sm font-bold">Mnemo</span>
          <span className="text-xs text-text-muted">v0.4.0</span>
        </div>

        <div className="flex items-center gap-8">
          <a href="https://pypi.org/project/mnemo-dev/" className="text-xs text-text-muted hover:text-accent transition-colors font-mono">PyPI</a>
          <a href="https://www.npmjs.com/package/@mnemo-dev/mcp" className="text-xs text-text-muted hover:text-accent transition-colors font-mono">npm</a>
          <a href="https://github.com/Mnemo-mcp/Mnemo" className="text-xs text-text-muted hover:text-accent transition-colors font-mono">GitHub</a>
        </div>

        <p className="text-xs text-text-muted">AGPL-3.0</p>
      </div>
    </footer>
  );
}
